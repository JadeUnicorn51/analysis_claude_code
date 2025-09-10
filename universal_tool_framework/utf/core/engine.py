"""
Universal Tool Framework 核心执行引擎

基于Claude Code架构的任务执行引擎，实现了完整的"问题→规划→工具执行→结果"流程
"""

import asyncio
import uuid
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime

from utf.config.settings import FrameworkConfig
from utf.models.task import Task, TodoItem, TaskStatus, TaskResult, TaskComplexity
from utf.models.execution import ExecutionContext, UserInteractionEvent
from utf.core.task_decomposer import TaskDecomposer
from utf.core.tool_orchestrator import ToolOrchestrator
from utf.core.interaction_manager import InteractionManager
from utf.utils.logging import get_logger


class UniversalTaskEngine:
    """
    通用任务执行引擎
    
    这是框架的核心引擎，负责：
    1. 任务分析与分解
    2. 工具编排与执行
    3. 用户交互管理
    4. 结果汇总输出
    """
    
    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # 核心组件
        self.task_decomposer = TaskDecomposer(config)
        self.tool_orchestrator = ToolOrchestrator(config)
        self.interaction_manager = InteractionManager(config)
        
        # 运行时状态
        self._active_tasks: Dict[str, Task] = {}
        self._execution_contexts: Dict[str, ExecutionContext] = {}
        
        self.logger.info("UniversalTaskEngine initialized")
    
    async def execute_task(
        self, 
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[TaskResult, None]:
        """
        执行任务的主入口
        
        Args:
            user_query: 用户查询/任务描述
            context: 可选的执行上下文
            
        Yields:
            TaskResult: 任务执行结果流
        """
        task_id = str(uuid.uuid4())
        session_id = context.get('session_id', str(uuid.uuid4())) if context else str(uuid.uuid4())
        
        self.logger.info(f"开始执行任务: {task_id}")
        
        try:
            # 创建执行上下文
            execution_context = self._create_execution_context(task_id, session_id, context)
            self._execution_contexts[task_id] = execution_context
            
            # 第1步：任务分析与分解
            yield TaskResult(
                type="task_analysis_started",
                data={"task_id": task_id, "query": user_query},
                task_id=task_id
            )
            
            complexity = await self.task_decomposer.analyze_complexity(user_query)
            
            yield TaskResult(
                type="complexity_analysis_completed",
                data=complexity.model_dump(),
                task_id=task_id
            )
            
            # 创建任务对象
            task = Task(
                id=task_id,
                query=user_query,
                description=user_query,
                complexity=complexity
            )
            
            self._active_tasks[task_id] = task
            
            # 根据复杂度决定执行策略
            if complexity.needs_todo_list:
                # 复杂任务：分解为TodoList执行
                yield TaskResult(
                    type="task_decomposition_started",
                    data={"task_id": task_id},
                    task_id=task_id
                )
                
                todo_list = await self.task_decomposer.decompose_task(task, execution_context)
                task.todo_list = todo_list
                
                yield TaskResult(
                    type="todo_list_generated",
                    data={
                        "task_id": task_id,
                        "todo_count": len(todo_list),
                        "todos": [todo.model_dump() for todo in todo_list]
                    },
                    task_id=task_id
                )
                
                # 执行TodoList
                async for result in self._execute_todo_list(task, execution_context):
                    yield result
            else:
                # 简单任务：直接执行
                async for result in self._execute_simple_task(task, execution_context):
                    yield result
            
            # 任务完成
            task.update_status()
            
            yield TaskResult(
                type="task_completed",
                data={
                    "task_id": task_id,
                    "status": task.status.value,
                    "progress": task.progress_percentage,
                    "duration": (datetime.now() - task.created_at).total_seconds()
                },
                task_id=task_id
            )
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {task_id}, 错误: {str(e)}")
            yield TaskResult(
                type="task_failed",
                data={
                    "task_id": task_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                task_id=task_id
            )
        finally:
            # 清理资源
            self._cleanup_task(task_id)
    
    async def _execute_todo_list(
        self,
        task: Task,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResult, None]:
        """
        执行TodoList的核心逻辑
        
        实现了Claude Code的核心执行模式：
        1. 顺序处理TodoItem
        2. 支持用户中断和修改
        3. 智能工具选择和执行
        4. 实时进度反馈
        """
        task.started_at = datetime.now()
        task.status = TaskStatus.IN_PROGRESS
        
        while True:
            # 获取可执行的TodoItem
            ready_todos = task.get_ready_todos()
            
            if not ready_todos:
                # 检查是否还有未完成的依赖
                if task.pending_todos:
                    self.logger.warning(f"存在无法执行的TodoItem，可能存在循环依赖")
                    break
                else:
                    # 所有TodoItem都已完成
                    break
            
            # 选择下一个执行的TodoItem
            current_todo = ready_todos[0]  # 按优先级排序后的第一个
            
            yield TaskResult(
                type="todo_started",
                data={
                    "task_id": task.id,
                    "todo_id": current_todo.id,
                    "todo": current_todo.model_dump()
                },
                task_id=task.id,
                todo_id=current_todo.id
            )
            
            # 检查用户中断
            if self.config.interaction.allow_user_interruption:
                interruption_check = await self._check_user_interruption(task, current_todo)
                if interruption_check:
                    async for result in self._handle_user_interruption(task, current_todo, context):
                        yield result
                    continue  # 重新开始循环
            
            # 执行TodoItem
            current_todo.mark_started()
            
            try:
                async for result in self._execute_todo_item(current_todo, task, context):
                    yield result
                
                current_todo.mark_completed()
                
                yield TaskResult(
                    type="todo_completed",
                    data={
                        "task_id": task.id,
                        "todo_id": current_todo.id,
                        "progress": task.progress_percentage
                    },
                    task_id=task.id,
                    todo_id=current_todo.id
                )
                
            except Exception as e:
                current_todo.mark_failed(str(e))
                
                yield TaskResult(
                    type="todo_failed",
                    data={
                        "task_id": task.id,
                        "todo_id": current_todo.id,
                        "error": str(e)
                    },
                    task_id=task.id,
                    todo_id=current_todo.id
                )
                
                # 根据配置决定是否继续
                if not self.config.task.retry_failed_todos:
                    break
    
    async def _execute_todo_item(
        self,
        todo: TodoItem,
        task: Task,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResult, None]:
        """执行单个TodoItem"""
        
        # 使用工具编排器执行
        async for result in self.tool_orchestrator.execute_todo(todo, task, context):
            yield TaskResult(
                type="tool_execution_result",
                data=result,
                task_id=task.id,
                todo_id=todo.id
            )
    
    async def _execute_simple_task(
        self,
        task: Task,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResult, None]:
        """执行简单任务"""
        
        task.started_at = datetime.now()
        task.status = TaskStatus.IN_PROGRESS
        
        # 创建单个TodoItem
        simple_todo = TodoItem(
            id=str(uuid.uuid4()),
            content=task.description,
            tools_needed=[]  # 将由工具编排器动态选择
        )
        
        task.todo_list = [simple_todo]
        
        async for result in self._execute_todo_item(simple_todo, task, context):
            yield result
        
        simple_todo.mark_completed()
    
    async def _check_user_interruption(
        self,
        task: Task,
        current_todo: TodoItem
    ) -> bool:
        """检查用户是否请求中断"""
        # 这里可以实现检查用户中断的逻辑
        # 例如检查某个标志位、队列等
        return await self.interaction_manager.check_interruption_request(task.id)
    
    async def _handle_user_interruption(
        self,
        task: Task,
        current_todo: TodoItem,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResult, None]:
        """处理用户中断"""
        
        # 创建交互事件
        interaction_event = UserInteractionEvent(
            id=str(uuid.uuid4()),
            type="interruption_options",
            data={
                "options": [
                    {"action": "continue", "label": "继续执行"},
                    {"action": "modify", "label": "修改计划"},
                    {"action": "pause", "label": "暂停"},
                    {"action": "abort", "label": "终止任务"}
                ]
            },
            task_id=task.id,
            response_required=True,
            timeout_seconds=self.config.interaction.user_response_timeout
        )
        
        yield TaskResult(
            type="user_interaction_required",
            data=interaction_event.model_dump(),
            task_id=task.id
        )
        
        # 等待用户响应
        response = await self.interaction_manager.wait_for_user_response(
            interaction_event.id,
            timeout_seconds=interaction_event.timeout_seconds
        )
        
        if response:
            yield TaskResult(
                type="user_interaction_response",
                data=response.model_dump(),
                task_id=task.id
            )
            
            # 根据用户选择执行相应操作
            if response.action == "modify":
                # 重新分解任务
                new_todos = await self.task_decomposer.decompose_task(task, context)
                task.todo_list = new_todos
                
                yield TaskResult(
                    type="task_modified",
                    data={
                        "task_id": task.id,
                        "new_todo_count": len(new_todos)
                    },
                    task_id=task.id
                )
            elif response.action == "abort":
                task.status = TaskStatus.CANCELLED
                
                yield TaskResult(
                    type="task_aborted",
                    data={"task_id": task.id},
                    task_id=task.id
                )
    
    def _create_execution_context(
        self,
        task_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]]
    ) -> ExecutionContext:
        """创建执行上下文"""
        
        return ExecutionContext(
            session_id=session_id,
            task_id=task_id,
            user_id=context.get('user_id') if context else None,
            working_directory=context.get('working_directory') if context else None,
            environment_variables=context.get('environment', {}) if context else {},
            permissions=context.get('permissions', []) if context else [],
            max_execution_time=self.config.security.max_execution_time,
            allow_network_access=context.get('allow_network', True) if context else True,
            allow_file_write=context.get('allow_file_write', True) if context else True
        )
    
    def _cleanup_task(self, task_id: str) -> None:
        """清理任务资源"""
        self._active_tasks.pop(task_id, None)
        self._execution_contexts.pop(task_id, None)
        self.logger.info(f"任务资源已清理: {task_id}")
    
    def get_active_tasks(self) -> Dict[str, Task]:
        """获取活跃任务"""
        return self._active_tasks.copy()
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self._active_tasks.get(task_id)
        return task.status if task else None
        
    def mark_started(self) -> None:
        """标记任务开始 - 临时实现"""
        pass
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._active_tasks.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            self._cleanup_task(task_id)
            self.logger.info(f"任务已取消: {task_id}")
            return True
        return False
