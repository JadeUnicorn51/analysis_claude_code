"""
工具编排器

负责智能选择工具、规划执行策略、管理并发执行
"""

import asyncio
import uuid
import time
from typing import List, Dict, Any, Optional, AsyncGenerator, Set
from datetime import datetime

from ..config.settings import FrameworkConfig
from ..models.task import Task, TodoItem
from ..models.tool import Tool, ToolCall, ToolResult
from ..models.execution import (
    ExecutionPlan, ExecutionContext, ToolExecutionBatch,
    ExecutionStrategy, ExecutionResult, ExecutionStatus
)
from ..utils.logging import get_logger


class ToolOrchestrator:
    """
    工具编排器
    
    基于Claude Code的工具调度逻辑，实现智能的工具选择和执行管理
    """
    
    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # 工具注册表
        self._tools: Dict[str, Tool] = {}
        self._register_tools()
        
        # 执行状态跟踪
        self._active_executions: Dict[str, ExecutionResult] = {}
        self._execution_semaphore = asyncio.Semaphore(config.concurrency.max_parallel_tools)
    
    async def execute_todo(
        self,
        todo: TodoItem,
        task: Task,
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行TodoItem
        
        Args:
            todo: 要执行的TodoItem
            task: 关联的任务
            context: 执行上下文
            
        Yields:
            Dict[str, Any]: 执行结果
        """
        self.logger.info(f"开始执行TodoItem: {todo.id}")
        
        try:
            # 1. 分析TodoItem需求
            required_tools = await self._analyze_todo_requirements(todo, context)
            
            # 2. 选择合适的工具
            selected_tools = await self._select_tools(required_tools, todo, context)
            
            if not selected_tools:
                yield {
                    "type": "warning",
                    "message": f"未找到适合的工具执行TodoItem: {todo.content}"
                }
                return
            
            # 3. 创建工具调用
            tool_calls = self._create_tool_calls(selected_tools, todo, context)
            
            # 4. 规划执行策略
            execution_plan = await self._create_execution_plan(tool_calls, todo, context)
            
            yield {
                "type": "execution_plan_created",
                "plan": execution_plan.model_dump(),
                "tool_count": len(tool_calls)
            }
            
            # 5. 执行工具调用
            async for result in self._execute_plan(execution_plan, context):
                yield result
            
        except Exception as e:
            self.logger.error(f"TodoItem执行失败: {todo.id}, 错误: {str(e)}")
            yield {
                "type": "error",
                "message": f"执行失败: {str(e)}",
                "todo_id": todo.id
            }
    
    async def _analyze_todo_requirements(
        self,
        todo: TodoItem,
        context: ExecutionContext
    ) -> List[str]:
        """分析TodoItem的工具需求"""
        
        # 如果已指定工具，直接使用
        if todo.tools_needed:
            return todo.tools_needed
        
        # 基于内容分析需要的工具
        content_lower = todo.content.lower()
        required_tools = []
        
        # 文件操作
        if any(keyword in content_lower for keyword in ['读取', '查看', '分析文件', 'read', 'view']):
            required_tools.append('file_read')
        
        if any(keyword in content_lower for keyword in ['写入', '保存', '创建文件', 'write', 'save']):
            required_tools.append('file_write')
        
        # 网络操作
        if any(keyword in content_lower for keyword in ['搜索', '获取', '下载', 'search', 'fetch']):
            required_tools.append('web_search')
        
        # 数据处理
        if any(keyword in content_lower for keyword in ['处理', '分析', '转换', 'process', 'analyze']):
            required_tools.append('data_processor')
        
        # 系统命令
        if any(keyword in content_lower for keyword in ['执行', '运行', '命令', 'execute', 'run']):
            required_tools.append('system_command')
        
        # 如果没有匹配到特定工具，使用通用处理器
        if not required_tools:
            required_tools.append('general_processor')
        
        return required_tools
    
    async def _select_tools(
        self,
        required_tools: List[str],
        todo: TodoItem,
        context: ExecutionContext
    ) -> List[Tool]:
        """选择合适的工具"""
        
        selected_tools = []
        
        for tool_name in required_tools:
            tool = self._find_best_tool(tool_name, todo, context)
            if tool:
                selected_tools.append(tool)
            else:
                self.logger.warning(f"未找到工具: {tool_name}")
        
        return selected_tools
    
    def _find_best_tool(
        self,
        tool_type: str,
        todo: TodoItem,
        context: ExecutionContext
    ) -> Optional[Tool]:
        """查找最佳工具"""
        
        # 精确匹配
        if tool_type in self._tools:
            return self._tools[tool_type]
        
        # 模糊匹配
        for tool_name, tool in self._tools.items():
            if tool_type in tool_name or tool_type in tool.definition.description.lower():
                # 检查权限
                if self._check_tool_permissions(tool, context):
                    return tool
        
        return None
    
    def _check_tool_permissions(self, tool: Tool, context: ExecutionContext) -> bool:
        """检查工具权限"""
        for permission in tool.definition.required_permissions:
            if not context.has_permission(permission):
                return False
        return True
    
    def _create_tool_calls(
        self,
        tools: List[Tool],
        todo: TodoItem,
        context: ExecutionContext
    ) -> List[ToolCall]:
        """创建工具调用"""
        
        tool_calls = []
        
        for tool in tools:
            # 基于TodoItem内容生成参数
            parameters = self._generate_tool_parameters(tool, todo, context)
            
            tool_call = ToolCall(
                id=str(uuid.uuid4()),
                tool_name=tool.definition.name,
                parameters=parameters,
                context=context.model_dump()
            )
            
            tool_calls.append(tool_call)
        
        return tool_calls
    
    def _generate_tool_parameters(
        self,
        tool: Tool,
        todo: TodoItem,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """生成工具参数"""
        
        # 基础参数
        parameters = {
            "content": todo.content,
            "todo_id": todo.id,
            "working_directory": context.working_directory
        }
        
        # 根据工具类型添加特定参数
        tool_name = tool.definition.name
        
        if 'file_read' in tool_name:
            # 尝试从内容中提取文件路径
            import re
            file_patterns = [
                r'读取\s*([^\s]+)',
                r'查看\s*([^\s]+)',
                r'分析\s*([^\s]+\.[\w]+)'
            ]
            for pattern in file_patterns:
                match = re.search(pattern, todo.content)
                if match:
                    parameters["file_path"] = match.group(1)
                    break
        
        elif 'file_write' in tool_name:
            # 生成输出文件名
            parameters["file_path"] = f"output_{todo.id}.txt"
            parameters["content"] = todo.content
        
        elif 'web_search' in tool_name:
            # 提取搜索关键词
            parameters["query"] = todo.content
            parameters["max_results"] = 10
        
        return parameters
    
    async def _create_execution_plan(
        self,
        tool_calls: List[ToolCall],
        todo: TodoItem,
        context: ExecutionContext
    ) -> ExecutionPlan:
        """创建执行计划"""
        
        plan_id = str(uuid.uuid4())
        
        # 分析工具并发安全性
        batches = await self._group_tools_by_concurrency(tool_calls)
        
        execution_plan = ExecutionPlan(
            id=plan_id,
            task_id=context.task_id,
            todo_id=todo.id,
            batches=batches,
            total_estimated_duration=sum(batch.estimated_duration for batch in batches)
        )
        
        return execution_plan
    
    async def _group_tools_by_concurrency(
        self,
        tool_calls: List[ToolCall]
    ) -> List[ToolExecutionBatch]:
        """根据并发安全性分组工具"""
        
        batches = []
        concurrent_safe_calls = []
        
        for tool_call in tool_calls:
            tool = self._tools.get(tool_call.tool_name)
            if not tool:
                continue
            
            # 检查是否支持并发
            if tool.is_concurrency_safe(tool_call.parameters):
                concurrent_safe_calls.append(tool_call)
            else:
                # 不安全的工具需要单独执行
                batch = ToolExecutionBatch(
                    id=str(uuid.uuid4()),
                    tool_calls=[tool_call],
                    strategy=ExecutionStrategy.SEQUENTIAL,
                    is_concurrent_safe=False,
                    estimated_duration=tool.estimate_execution_time(tool_call.parameters)
                )
                batches.append(batch)
        
        # 创建并发安全的批次
        if concurrent_safe_calls:
            # 根据最大并发数分组
            max_concurrent = self.config.concurrency.max_parallel_tools
            for i in range(0, len(concurrent_safe_calls), max_concurrent):
                batch_calls = concurrent_safe_calls[i:i + max_concurrent]
                
                total_duration = 0
                for call in batch_calls:
                    tool = self._tools.get(call.tool_name)
                    if tool:
                        total_duration += tool.estimate_execution_time(call.parameters)
                
                batch = ToolExecutionBatch(
                    id=str(uuid.uuid4()),
                    tool_calls=batch_calls,
                    strategy=ExecutionStrategy.PARALLEL,
                    is_concurrent_safe=True,
                    estimated_duration=total_duration / len(batch_calls)  # 并发执行取平均
                )
                batches.append(batch)
        
        return batches
    
    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行执行计划"""
        
        completed_batches: Set[str] = set()
        
        for batch in plan.batches:
            # 检查依赖关系
            if not all(dep_id in completed_batches for dep_id in batch.dependencies):
                continue
            
            yield {
                "type": "batch_started",
                "batch_id": batch.id,
                "strategy": batch.strategy.value,
                "tool_count": len(batch.tool_calls)
            }
            
            # 执行批次
            batch_start_time = time.time()
            
            try:
                if batch.strategy == ExecutionStrategy.PARALLEL:
                    async for result in self._execute_batch_parallel(batch, context):
                        yield result
                else:
                    async for result in self._execute_batch_sequential(batch, context):
                        yield result
                
                completed_batches.add(batch.id)
                
                yield {
                    "type": "batch_completed",
                    "batch_id": batch.id,
                    "execution_time": time.time() - batch_start_time
                }
                
            except Exception as e:
                yield {
                    "type": "batch_failed",
                    "batch_id": batch.id,
                    "error": str(e),
                    "execution_time": time.time() - batch_start_time
                }
    
    async def _execute_batch_parallel(
        self,
        batch: ToolExecutionBatch,
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """并发执行批次"""
        
        # 执行并发工具调用 (异步生成器不能用create_task)
        if len(batch.tool_calls) == 1:
            # 单个工具调用，直接执行
            tool_call = batch.tool_calls[0]
            try:
                async for result in self._execute_single_tool_call(tool_call, context):
                    yield {
                        "type": "tool_result",
                        "call_id": tool_call.id,
                        "result": result.model_dump()
                    }
            except Exception as e:
                yield {
                    "type": "tool_error",
                    "call_id": tool_call.id,
                    "error": str(e)
                }
        else:
            # 多个工具调用，顺序执行 (暂不支持真正并发)
            for tool_call in batch.tool_calls:
                try:
                    async for result in self._execute_single_tool_call(tool_call, context):
                        yield {
                            "type": "tool_result",
                            "call_id": tool_call.id,
                            "result": result.model_dump()
                        }
                except Exception as e:
                    yield {
                        "type": "tool_error",
                        "call_id": tool_call.id,
                        "error": str(e)
                    }
    
    async def _execute_batch_sequential(
        self,
        batch: ToolExecutionBatch,
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """串行执行批次"""
        
        for tool_call in batch.tool_calls:
            try:
                async for result in self._execute_single_tool_call(tool_call, context):
                    yield {
                        "type": "tool_result",
                        "call_id": tool_call.id,
                        "result": result.model_dump()
                    }
            except Exception as e:
                yield {
                    "type": "tool_error",
                    "call_id": tool_call.id,
                    "error": str(e)
                }
    
    async def _execute_single_tool_call(
        self,
        tool_call: ToolCall,
        context: ExecutionContext
    ) -> AsyncGenerator[ToolResult, None]:
        """执行单个工具调用"""
        
        # 获取工具
        tool = self._tools.get(tool_call.tool_name)
        if not tool:
            raise ValueError(f"工具未找到: {tool_call.tool_name}")
        
        # 使用信号量控制并发
        async with self._execution_semaphore:
            # 添加调用ID到上下文
            execution_context = {
                **tool_call.context,
                "call_id": tool_call.id
            }
            
            # 执行工具
            async for result in tool.execute(tool_call.parameters, execution_context):
                yield result
    
    def _register_tools(self) -> None:
        """注册工具"""
        for tool in self.config.tools:
            self._tools[tool.definition.name] = tool
            self.logger.info(f"工具已注册: {tool.definition.name}")
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self._tools.keys())
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(tool_name)
