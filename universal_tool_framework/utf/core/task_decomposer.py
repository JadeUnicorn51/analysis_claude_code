"""
任务分解器

负责分析任务复杂度并将复杂任务分解为可执行的TodoItem列表
"""

import uuid
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config.settings import FrameworkConfig
from ..models.task import Task, TodoItem, TaskComplexity, TaskStatus
from ..models.execution import ExecutionContext
from ..utils.logging import get_logger


class TaskDecomposer:
    """
    任务分解器
    
    基于Claude Code的任务分解逻辑，实现智能的任务分析和分解
    """
    
    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # 复杂度分析规则
        self._complexity_rules = self._init_complexity_rules()
        
        # 任务分解模板
        self._decomposition_templates = self._init_decomposition_templates()
    
    async def analyze_complexity(self, user_query: str) -> TaskComplexity:
        """
        分析任务复杂度
        
        Args:
            user_query: 用户查询
            
        Returns:
            TaskComplexity: 复杂度分析结果
        """
        self.logger.info(f"分析任务复杂度: {user_query}")
        
        # 基于规则的复杂度分析
        score = self._calculate_complexity_score(user_query)
        needs_todo_list = score >= self.config.task.complexity_threshold
        estimated_steps = self._estimate_steps(user_query, score)
        required_tools = self._identify_required_tools(user_query)
        reasoning = self._generate_reasoning(user_query, score, needs_todo_list)
        
        complexity = TaskComplexity(
            score=score,
            needs_todo_list=needs_todo_list,
            estimated_steps=estimated_steps,
            required_tools=required_tools,
            reasoning=reasoning
        )
        
        self.logger.info(f"复杂度分析完成: score={score}, needs_todo={needs_todo_list}")
        return complexity
    
    async def decompose_task(
        self,
        task: Task,
        context: ExecutionContext
    ) -> List[TodoItem]:
        """
        分解任务为TodoItem列表
        
        Args:
            task: 要分解的任务
            context: 执行上下文
            
        Returns:
            List[TodoItem]: TodoItem列表
        """
        self.logger.info(f"开始分解任务: {task.id}")
        
        if not task.complexity or not task.complexity.needs_todo_list:
            # 简单任务不需要分解
            return []
        
        # 根据任务类型选择分解策略
        task_type = self._classify_task_type(task.query)
        todos = await self._decompose_by_type(task, task_type, context)
        
        # 分析依赖关系
        todos = self._analyze_dependencies(todos)
        
        # 设置优先级
        todos = self._set_priorities(todos)
        
        self.logger.info(f"任务分解完成: {len(todos)} 个TodoItem")
        return todos
    
    async def update_todo_list(
        self,
        current_todos: List[TodoItem],
        user_feedback: Dict[str, Any]
    ) -> List[TodoItem]:
        """
        根据用户反馈更新TodoList
        
        Args:
            current_todos: 当前TodoList
            user_feedback: 用户反馈
            
        Returns:
            List[TodoItem]: 更新后的TodoList
        """
        self.logger.info("根据用户反馈更新TodoList")
        
        # 这里可以实现更复杂的更新逻辑
        # 例如：添加新步骤、修改现有步骤、调整优先级等
        
        updated_todos = current_todos.copy()
        
        if 'add_steps' in user_feedback:
            # 添加新步骤
            for step in user_feedback['add_steps']:
                new_todo = TodoItem(
                    id=str(uuid.uuid4()),
                    content=step['content'],
                    tools_needed=step.get('tools', []),
                    priority=step.get('priority', 0)
                )
                updated_todos.append(new_todo)
        
        if 'modify_steps' in user_feedback:
            # 修改现有步骤
            for modification in user_feedback['modify_steps']:
                todo_id = modification['id']
                for todo in updated_todos:
                    if todo.id == todo_id:
                        if 'content' in modification:
                            todo.content = modification['content']
                        if 'priority' in modification:
                            todo.priority = modification['priority']
                        break
        
        if 'remove_steps' in user_feedback:
            # 移除步骤
            remove_ids = set(user_feedback['remove_steps'])
            updated_todos = [todo for todo in updated_todos if todo.id not in remove_ids]
        
        # 重新分析依赖关系
        updated_todos = self._analyze_dependencies(updated_todos)
        
        return updated_todos
    
    def _calculate_complexity_score(self, user_query: str) -> int:
        """计算复杂度评分"""
        score = 1  # 基础分数
        
        query_lower = user_query.lower()
        
        # 基于关键词的评分
        for rule in self._complexity_rules:
            if any(keyword in query_lower for keyword in rule['keywords']):
                score += rule['score_increment']
        
        # 基于查询长度的评分
        word_count = len(user_query.split())
        if word_count > 20:
            score += 2
        elif word_count > 10:
            score += 1
        
        # 基于逻辑连接词的评分
        logical_connectors = ['然后', '接着', '之后', '并且', '同时', 'and', 'then', 'after']
        connector_count = sum(1 for connector in logical_connectors if connector in query_lower)
        score += connector_count
        
        # 限制评分范围
        return min(max(score, 1), 10)
    
    def _estimate_steps(self, user_query: str, complexity_score: int) -> int:
        """估算步骤数"""
        # 基础步骤数基于复杂度
        base_steps = max(1, complexity_score // 2)
        
        # 根据查询内容调整
        query_lower = user_query.lower()
        
        # 检查是否包含多个动作
        action_words = ['分析', '创建', '生成', '搜索', '下载', '上传', '处理', '转换']
        action_count = sum(1 for word in action_words if word in query_lower)
        
        estimated_steps = base_steps + action_count
        
        return min(estimated_steps, self.config.task.max_todo_items)
    
    def _identify_required_tools(self, user_query: str) -> List[str]:
        """识别需要的工具类型"""
        query_lower = user_query.lower()
        required_tools = []
        
        # 文件操作
        if any(keyword in query_lower for keyword in ['文件', '读取', '写入', '保存', 'file']):
            required_tools.extend(['file_read', 'file_write'])
        
        # 网络请求
        if any(keyword in query_lower for keyword in ['搜索', '下载', '获取', '请求', 'search', 'fetch']):
            required_tools.append('web_request')
        
        # 数据处理
        if any(keyword in query_lower for keyword in ['分析', '处理', '转换', 'analyze', 'process']):
            required_tools.append('data_processing')
        
        # 系统操作
        if any(keyword in query_lower for keyword in ['执行', '运行', '命令', 'execute', 'run']):
            required_tools.append('system_command')
        
        return list(set(required_tools))
    
    def _generate_reasoning(
        self,
        user_query: str,
        score: int,
        needs_todo_list: bool
    ) -> str:
        """生成复杂度分析原因"""
        reasoning_parts = []
        
        if score <= 2:
            reasoning_parts.append("任务相对简单")
        elif score <= 5:
            reasoning_parts.append("任务复杂度中等")
        else:
            reasoning_parts.append("任务复杂度较高")
        
        if needs_todo_list:
            reasoning_parts.append("需要分解为多个步骤执行")
        else:
            reasoning_parts.append("可以直接执行")
        
        return "，".join(reasoning_parts)
    
    def _classify_task_type(self, user_query: str) -> str:
        """分类任务类型"""
        query_lower = user_query.lower()
        
        if any(keyword in query_lower for keyword in ['分析', '研究', 'analyze', 'research']):
            return 'analysis'
        elif any(keyword in query_lower for keyword in ['创建', '生成', '建立', 'create', 'generate']):
            return 'creation'
        elif any(keyword in query_lower for keyword in ['搜索', '查找', '获取', 'search', 'find']):
            return 'information_gathering'
        elif any(keyword in query_lower for keyword in ['处理', '转换', '修改', 'process', 'convert']):
            return 'data_processing'
        else:
            return 'general'
    
    async def _decompose_by_type(
        self,
        task: Task,
        task_type: str,
        context: ExecutionContext
    ) -> List[TodoItem]:
        """根据任务类型分解"""
        
        decomposition_template = self._decomposition_templates.get(
            task_type,
            self._decomposition_templates['general']
        )
        
        todos = []
        
        for i, step_template in enumerate(decomposition_template):
            todo = TodoItem(
                id=str(uuid.uuid4()),
                content=step_template['content'].format(query=task.query),
                tools_needed=step_template.get('tools', []),
                priority=step_template.get('priority', 0),
                estimated_duration=step_template.get('duration', 60)
            )
            todos.append(todo)
        
        return todos
    
    def _analyze_dependencies(self, todos: List[TodoItem]) -> List[TodoItem]:
        """分析TodoItem之间的依赖关系"""
        # 简单的依赖分析：基于工具类型和内容
        
        for i, todo in enumerate(todos):
            # 文件写入通常依赖于文件读取
            if 'file_write' in todo.tools_needed:
                for j, prev_todo in enumerate(todos[:i]):
                    if 'file_read' in prev_todo.tools_needed:
                        todo.dependencies.append(prev_todo.id)
            
            # 数据处理通常依赖于数据获取
            if 'data_processing' in todo.tools_needed:
                for j, prev_todo in enumerate(todos[:i]):
                    if 'web_request' in prev_todo.tools_needed or 'file_read' in prev_todo.tools_needed:
                        todo.dependencies.append(prev_todo.id)
        
        return todos
    
    def _set_priorities(self, todos: List[TodoItem]) -> List[TodoItem]:
        """设置TodoItem优先级"""
        
        # 基于依赖关系和工具类型设置优先级
        for todo in todos:
            # 无依赖的优先级更高
            if not todo.dependencies:
                todo.priority += 10
            
            # 数据收集类任务优先级更高
            if any(tool in todo.tools_needed for tool in ['web_request', 'file_read']):
                todo.priority += 5
            
            # 输出类任务优先级较低
            if any(tool in todo.tools_needed for tool in ['file_write']):
                todo.priority -= 5
        
        return todos
    
    def _init_complexity_rules(self) -> List[Dict[str, Any]]:
        """初始化复杂度分析规则"""
        return [
            {
                'keywords': ['分析', '研究', '深入', 'analyze', 'research'],
                'score_increment': 2
            },
            {
                'keywords': ['生成', '创建', '建立', 'generate', 'create'],
                'score_increment': 2
            },
            {
                'keywords': ['多个', '批量', '大量', 'multiple', 'batch'],
                'score_increment': 3
            },
            {
                'keywords': ['复杂', '详细', '完整', 'complex', 'detailed'],
                'score_increment': 2
            },
            {
                'keywords': ['自动化', '流程', 'automate', 'workflow'],
                'score_increment': 3
            }
        ]
    
    def _init_decomposition_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """初始化任务分解模板"""
        return {
            'analysis': [
                {
                    'content': '收集与"{query}"相关的信息',
                    'tools': ['web_request', 'file_read'],
                    'priority': 10,
                    'duration': 120
                },
                {
                    'content': '分析收集到的数据',
                    'tools': ['data_processing'],
                    'priority': 5,
                    'duration': 180
                },
                {
                    'content': '生成分析报告',
                    'tools': ['file_write'],
                    'priority': 0,
                    'duration': 60
                }
            ],
            'creation': [
                {
                    'content': '设计"{query}"的结构',
                    'tools': ['data_processing'],
                    'priority': 10,
                    'duration': 90
                },
                {
                    'content': '创建基础框架',
                    'tools': ['file_write'],
                    'priority': 5,
                    'duration': 120
                },
                {
                    'content': '完善和优化内容',
                    'tools': ['file_read', 'file_write'],
                    'priority': 0,
                    'duration': 150
                }
            ],
            'information_gathering': [
                {
                    'content': '搜索"{query}"相关信息',
                    'tools': ['web_request'],
                    'priority': 10,
                    'duration': 90
                },
                {
                    'content': '整理和筛选信息',
                    'tools': ['data_processing'],
                    'priority': 5,
                    'duration': 60
                },
                {
                    'content': '保存整理后的信息',
                    'tools': ['file_write'],
                    'priority': 0,
                    'duration': 30
                }
            ],
            'general': [
                {
                    'content': '准备执行"{query}"',
                    'tools': ['data_processing'],
                    'priority': 5,
                    'duration': 60
                },
                {
                    'content': '执行主要任务',
                    'tools': ['system_command'],
                    'priority': 10,
                    'duration': 120
                },
                {
                    'content': '完成并输出结果',
                    'tools': ['file_write'],
                    'priority': 0,
                    'duration': 30
                }
            ]
        }
