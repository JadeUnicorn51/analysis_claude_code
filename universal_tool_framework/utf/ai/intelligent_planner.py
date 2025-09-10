"""
智能规划器

基于LLM的智能任务分析、分解和执行规划
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from utf.ai.llm_client import LLMClient, LLMMessage
from utf.models.task import Task, TodoItem, TaskComplexity, TaskStatus
from utf.models.execution import ExecutionContext
from utf.utils.logging import get_logger


class IntelligentPlanner:
    """
    智能规划器
    
    使用LLM进行智能的任务分析、分解和执行规划
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = get_logger(__name__)
        
        # 系统提示词
        self.system_prompts = self._init_system_prompts()
        
        self.logger.info("IntelligentPlanner initialized")
    
    async def analyze_task_complexity(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> TaskComplexity:
        """
        使用LLM分析任务复杂度
        
        Args:
            user_query: 用户查询
            context: 额外上下文
            
        Returns:
            TaskComplexity: 复杂度分析结果
        """
        self.logger.info(f"开始智能分析任务复杂度: {user_query}")
        
        # 构建分析提示
        analysis_prompt = self._build_complexity_analysis_prompt(user_query, context)
        
        messages = [
            LLMMessage(role="system", content=self.system_prompts["complexity_analyzer"]),
            LLMMessage(role="user", content=analysis_prompt)
        ]
        
        try:
            response = await self.llm_client.chat_completion(messages)
            
            # 解析LLM响应
            complexity = self._parse_complexity_response(response.content)
            
            self.logger.info(f"复杂度分析完成: 评分={complexity.score}, 需要分解={complexity.needs_todo_list}")
            return complexity
            
        except Exception as e:
            self.logger.error(f"复杂度分析失败: {e}")
            # 返回默认复杂度
            return TaskComplexity(
                score=3,
                needs_todo_list=True,
                estimated_steps=3,
                required_tools=["general_processor"],
                reasoning="LLM分析失败，使用默认复杂度"
            )
    
    async def decompose_task_intelligently(
        self,
        task: Task,
        available_tools: List[str],
        context: ExecutionContext
    ) -> List[TodoItem]:
        """
        使用LLM智能分解任务
        
        Args:
            task: 要分解的任务
            available_tools: 可用工具列表
            context: 执行上下文
            
        Returns:
            List[TodoItem]: 分解后的TodoItem列表
        """
        self.logger.info(f"开始智能分解任务: {task.id}")
        
        # 构建分解提示
        decomposition_prompt = self._build_decomposition_prompt(task, available_tools, context)
        
        messages = [
            LLMMessage(role="system", content=self.system_prompts["task_decomposer"]),
            LLMMessage(role="user", content=decomposition_prompt)
        ]
        
        try:
            response = await self.llm_client.chat_completion(messages)
            
            # 解析分解结果
            todo_items = self._parse_decomposition_response(response.content, task.id)
            
            self.logger.info(f"任务分解完成: 生成了 {len(todo_items)} 个步骤")
            return todo_items
            
        except Exception as e:
            self.logger.error(f"任务分解失败: {e}")
            # 返回默认分解
            return self._create_default_decomposition(task)
    
    async def optimize_execution_plan(
        self,
        todo_items: List[TodoItem],
        available_tools: List[str],
        context: ExecutionContext
    ) -> List[TodoItem]:
        """
        使用LLM优化执行计划
        
        Args:
            todo_items: 原始TodoItem列表
            available_tools: 可用工具列表
            context: 执行上下文
            
        Returns:
            List[TodoItem]: 优化后的TodoItem列表
        """
        self.logger.info(f"开始优化执行计划: {len(todo_items)} 个步骤")
        
        # 构建优化提示
        optimization_prompt = self._build_optimization_prompt(todo_items, available_tools, context)
        
        messages = [
            LLMMessage(role="system", content=self.system_prompts["plan_optimizer"]),
            LLMMessage(role="user", content=optimization_prompt)
        ]
        
        try:
            response = await self.llm_client.chat_completion(messages)
            
            # 解析优化结果
            optimized_items = self._parse_optimization_response(response.content, todo_items)
            
            self.logger.info(f"执行计划优化完成")
            return optimized_items
            
        except Exception as e:
            self.logger.error(f"执行计划优化失败: {e}")
            # 返回原始计划
            return todo_items
    
    async def suggest_tool_selection(
        self,
        todo_item: TodoItem,
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        使用LLM建议工具选择
        
        Args:
            todo_item: TodoItem
            available_tools: 可用工具列表
            context: 额外上下文
            
        Returns:
            List[str]: 建议的工具列表
        """
        # 构建工具选择提示
        tool_selection_prompt = self._build_tool_selection_prompt(todo_item, available_tools, context)
        
        messages = [
            LLMMessage(role="system", content=self.system_prompts["tool_selector"]),
            LLMMessage(role="user", content=tool_selection_prompt)
        ]
        
        try:
            response = await self.llm_client.chat_completion(messages)
            
            # 解析工具选择结果
            suggested_tools = self._parse_tool_selection_response(response.content, available_tools)
            
            self.logger.info(f"工具选择建议: {suggested_tools}")
            return suggested_tools
            
        except Exception as e:
            self.logger.error(f"工具选择建议失败: {e}")
            # 返回默认工具
            return ["general_processor"]
    
    def _build_complexity_analysis_prompt(self, user_query: str, context: Optional[Dict[str, Any]]) -> str:
        """构建复杂度分析提示"""
        prompt = f"""
请分析以下任务的复杂度：

用户任务: {user_query}

请从以下维度进行分析：
1. 任务的复杂程度 (1-10分，1最简单，10最复杂)
2. 是否需要分解为多个步骤
3. 预估需要多少个执行步骤
4. 需要什么类型的工具
5. 分析的理由

请以以下JSON格式回复：
{{
    "score": 数字 (1-10),
    "needs_todo_list": 布尔值,
    "estimated_steps": 数字,
    "required_tools": ["工具类型1", "工具类型2"],
    "reasoning": "分析理由"
}}

上下文信息: {json.dumps(context, ensure_ascii=False) if context else "无"}
"""
        return prompt
    
    def _build_decomposition_prompt(
        self,
        task: Task,
        available_tools: List[str],
        context: ExecutionContext
    ) -> str:
        """构建任务分解提示"""
        prompt = f"""
请将以下任务分解为可执行的步骤：

任务描述: {task.description}
任务复杂度: {task.complexity.score if task.complexity else "未知"}/10
可用工具: {', '.join(available_tools)}

分解原则：
1. 每个步骤应该是独立可执行的
2. 步骤之间可以有依赖关系
3. 选择最适合的工具
4. 考虑执行顺序和并发性
5. 步骤描述要清晰具体

请以以下JSON格式回复：
{{
    "steps": [
        {{
            "content": "步骤描述",
            "tools_needed": ["工具名称"],
            "priority": 数字 (0-10),
            "estimated_duration": 预估秒数,
            "dependencies": ["依赖的步骤索引"]
        }}
    ],
    "reasoning": "分解思路"
}}

工作目录: {context.working_directory or "当前目录"}
允许的操作: {"文件读写" if context.allow_file_write else "仅读取"}
"""
        return prompt
    
    def _build_optimization_prompt(
        self,
        todo_items: List[TodoItem],
        available_tools: List[str],
        context: ExecutionContext
    ) -> str:
        """构建执行计划优化提示"""
        
        # 转换TodoItem为简化格式
        items_data = []
        for i, item in enumerate(todo_items):
            items_data.append({
                "index": i,
                "content": item.content,
                "tools": item.tools_needed,
                "priority": item.priority,
                "dependencies": item.dependencies
            })
        
        prompt = f"""
请优化以下执行计划：

当前执行步骤:
{json.dumps(items_data, ensure_ascii=False, indent=2)}

可用工具: {', '.join(available_tools)}

优化目标：
1. 提高执行效率
2. 优化依赖关系
3. 合理安排并发执行
4. 减少资源冲突
5. 提升成功率

请提供优化建议，包括：
- 步骤顺序调整
- 工具选择优化
- 依赖关系优化
- 优先级调整

以JSON格式回复优化方案：
{{
    "optimizations": [
        {{
            "step_index": 步骤索引,
            "changes": {{
                "priority": 新优先级,
                "tools_needed": ["新工具列表"],
                "dependencies": ["新依赖列表"]
            }},
            "reason": "优化原因"
        }}
    ],
    "overall_improvements": "整体改进说明"
}}
"""
        return prompt
    
    def _build_tool_selection_prompt(
        self,
        todo_item: TodoItem,
        available_tools: List[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建工具选择提示"""
        prompt = f"""
请为以下任务步骤选择最合适的工具：

任务步骤: {todo_item.content}
当前已选工具: {', '.join(todo_item.tools_needed) if todo_item.tools_needed else '无'}
可用工具列表: {', '.join(available_tools)}

选择标准：
1. 工具功能匹配度
2. 执行效率
3. 可靠性
4. 资源消耗
5. 并发安全性

请以JSON格式回复：
{{
    "recommended_tools": ["工具1", "工具2"],
    "reasoning": "选择理由",
    "alternatives": ["备选工具1", "备选工具2"]
}}

上下文: {json.dumps(context, ensure_ascii=False) if context else "无"}
"""
        return prompt
    
    def _parse_complexity_response(self, response_content: str) -> TaskComplexity:
        """解析复杂度分析响应"""
        try:
            # 尝试从响应中提取JSON
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_content[start:end]
                data = json.loads(json_str)
                
                return TaskComplexity(
                    score=max(1, min(10, int(data.get('score', 3)))),
                    needs_todo_list=bool(data.get('needs_todo_list', True)),
                    estimated_steps=max(1, int(data.get('estimated_steps', 3))),
                    required_tools=data.get('required_tools', ['general_processor']),
                    reasoning=data.get('reasoning', 'LLM分析结果')
                )
        except Exception as e:
            self.logger.error(f"解析复杂度响应失败: {e}")
        
        # 返回默认值
        return TaskComplexity(
            score=3,
            needs_todo_list=True,
            estimated_steps=3,
            required_tools=['general_processor'],
            reasoning='解析失败，使用默认复杂度'
        )
    
    def _parse_decomposition_response(self, response_content: str, task_id: str) -> List[TodoItem]:
        """解析任务分解响应"""
        try:
            # 提取JSON
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_content[start:end]
                data = json.loads(json_str)
                
                todo_items = []
                steps = data.get('steps', [])
                
                for i, step in enumerate(steps):
                    todo_item = TodoItem(
                        id=str(uuid.uuid4()),
                        content=step.get('content', f'步骤 {i+1}'),
                        tools_needed=step.get('tools_needed', ['general_processor']),
                        priority=step.get('priority', 0),
                        estimated_duration=step.get('estimated_duration', 60),
                        dependencies=step.get('dependencies', [])
                    )
                    todo_items.append(todo_item)
                
                return todo_items
                
        except Exception as e:
            self.logger.error(f"解析分解响应失败: {e}")
        
        # 返回默认分解
        return self._create_default_decomposition_from_id(task_id)
    
    def _parse_optimization_response(self, response_content: str, original_items: List[TodoItem]) -> List[TodoItem]:
        """解析优化响应"""
        try:
            # 提取JSON
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_content[start:end]
                data = json.loads(json_str)
                
                # 应用优化
                optimized_items = original_items.copy()
                optimizations = data.get('optimizations', [])
                
                for opt in optimizations:
                    step_index = opt.get('step_index', 0)
                    if 0 <= step_index < len(optimized_items):
                        changes = opt.get('changes', {})
                        item = optimized_items[step_index]
                        
                        if 'priority' in changes:
                            item.priority = changes['priority']
                        if 'tools_needed' in changes:
                            item.tools_needed = changes['tools_needed']
                        if 'dependencies' in changes:
                            item.dependencies = changes['dependencies']
                
                return optimized_items
                
        except Exception as e:
            self.logger.error(f"解析优化响应失败: {e}")
        
        return original_items
    
    def _parse_tool_selection_response(self, response_content: str, available_tools: List[str]) -> List[str]:
        """解析工具选择响应"""
        try:
            # 提取JSON
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_content[start:end]
                data = json.loads(json_str)
                
                recommended_tools = data.get('recommended_tools', [])
                
                # 验证工具是否可用
                valid_tools = [tool for tool in recommended_tools if tool in available_tools]
                
                return valid_tools if valid_tools else ['general_processor']
                
        except Exception as e:
            self.logger.error(f"解析工具选择响应失败: {e}")
        
        return ['general_processor']
    
    def _create_default_decomposition(self, task: Task) -> List[TodoItem]:
        """创建默认任务分解"""
        return [
            TodoItem(
                id=str(uuid.uuid4()),
                content=f"分析任务: {task.description}",
                tools_needed=['general_processor'],
                priority=10
            ),
            TodoItem(
                id=str(uuid.uuid4()),
                content=f"执行主要操作",
                tools_needed=['general_processor'],
                priority=5
            ),
            TodoItem(
                id=str(uuid.uuid4()),
                content=f"完成并整理结果",
                tools_needed=['general_processor'],
                priority=0
            )
        ]
    
    def _create_default_decomposition_from_id(self, task_id: str) -> List[TodoItem]:
        """从任务ID创建默认分解"""
        return [
            TodoItem(
                id=str(uuid.uuid4()),
                content="执行任务的第一步",
                tools_needed=['general_processor'],
                priority=5
            )
        ]
    
    def _init_system_prompts(self) -> Dict[str, str]:
        """初始化系统提示词"""
        return {
            "complexity_analyzer": """
你是一个专业的任务复杂度分析师。你的职责是分析用户提出的任务，评估其复杂度并给出合理的分解建议。

分析标准：
- 1-3分：简单任务，可以直接完成
- 4-6分：中等复杂度，需要2-5个步骤
- 7-10分：复杂任务，需要多个步骤和仔细规划

考虑因素：
- 任务涉及的领域数量
- 需要的工具类型
- 依赖关系复杂度
- 潜在风险和不确定性
- 执行时间预估

请始终以JSON格式回复，确保数据格式正确。
""",
            
            "task_decomposer": """
你是一个专业的任务分解专家。你需要将复杂任务分解为清晰、可执行的步骤序列。

分解原则：
1. 每个步骤都应该是原子性的、可独立执行的
2. 步骤描述要具体明确，避免模糊表达
3. 合理安排步骤间的依赖关系
4. 选择最适合的工具完成每个步骤
5. 考虑执行效率和资源优化

工具选择指南：
- general_processor: 通用处理、分析、问候等
- file_read: 读取文件内容
- file_write: 创建或修改文件
- 其他专用工具根据具体需求选择

请始终以JSON格式回复，确保结构清晰。
""",
            
            "plan_optimizer": """
你是一个执行计划优化专家。你的任务是分析现有的执行计划，提出改进建议以提高效率和成功率。

优化重点：
1. 识别可并行执行的步骤
2. 优化资源使用和工具选择
3. 减少不必要的依赖关系
4. 提高整体执行效率
5. 降低执行风险

考虑因素：
- 工具性能特性
- 资源竞争和冲突
- 执行时间优化
- 错误处理和恢复

请以JSON格式提供具体的优化建议。
""",
            
            "tool_selector": """
你是一个工具选择专家。你需要为特定的任务步骤选择最合适的工具。

选择标准：
1. 功能匹配度 - 工具是否能完成所需功能
2. 效率 - 执行速度和资源消耗
3. 可靠性 - 工具的稳定性和成功率
4. 安全性 - 权限要求和安全风险
5. 并发性 - 是否支持并发执行

工具特性：
- general_processor: 通用处理，适合分析、计算、文本处理
- file_read: 专门用于读取文件，支持大文件和编码检测
- file_write: 专门用于写入文件，支持原子操作和安全写入

请以JSON格式提供工具选择建议和理由。
"""
        }
    
    async def regenerate_failed_step(
        self,
        failed_todo: TodoItem,
        error_info: str,
        available_tools: List[str]
    ) -> TodoItem:
        """
        重新生成失败的步骤
        
        Args:
            failed_todo: 失败的TodoItem
            error_info: 错误信息
            available_tools: 可用工具列表
            
        Returns:
            TodoItem: 重新生成的步骤
        """
        regenerate_prompt = f"""
以下任务步骤执行失败，请重新设计：

原始步骤: {failed_todo.content}
使用的工具: {', '.join(failed_todo.tools_needed)}
失败原因: {error_info}
可用工具: {', '.join(available_tools)}

请重新设计这个步骤，避免之前的错误：
1. 分析失败原因
2. 选择更合适的工具
3. 调整执行策略
4. 提供替代方案

以JSON格式回复：
{{
    "new_content": "新的步骤描述",
    "new_tools": ["新工具列表"],
    "changes_made": "所做的改变",
    "reasoning": "重新设计的理由"
}}
"""
        
        messages = [
            LLMMessage(role="system", content="你是一个问题解决专家，擅长从失败中学习并提出改进方案。"),
            LLMMessage(role="user", content=regenerate_prompt)
        ]
        
        try:
            response = await self.llm_client.chat_completion(messages)
            
            # 解析重新生成的步骤
            start = response.content.find('{')
            end = response.content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response.content[start:end]
                data = json.loads(json_str)
                
                # 创建新的TodoItem
                new_todo = TodoItem(
                    id=str(uuid.uuid4()),
                    content=data.get('new_content', failed_todo.content),
                    tools_needed=data.get('new_tools', failed_todo.tools_needed),
                    priority=failed_todo.priority,
                    dependencies=failed_todo.dependencies,
                    metadata={
                        'regenerated': True,
                        'original_failure': error_info,
                        'changes_made': data.get('changes_made', ''),
                        'reasoning': data.get('reasoning', '')
                    }
                )
                
                self.logger.info(f"步骤重新生成完成: {new_todo.content}")
                return new_todo
        
        except Exception as e:
            self.logger.error(f"步骤重新生成失败: {e}")
        
        # 返回原始步骤（可能需要降级处理）
        return failed_todo
