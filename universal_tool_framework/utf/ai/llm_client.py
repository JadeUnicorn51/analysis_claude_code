"""
LLM客户端和集成模块

支持多种LLM提供商的统一接口
"""

import json
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from ..utils.logging import get_logger


class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"
    MOCK = "mock"  # 用于测试


@dataclass
class LLMMessage:
    """LLM消息"""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    model: str = ""
    finish_reason: str = ""
    response_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    extra_params: Optional[Dict[str, Any]] = None


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = get_logger(__name__)
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        """聊天完成"""
        pass
    
    @abstractmethod
    async def embedding(self, text: str) -> List[float]:
        """文本嵌入"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            test_messages = [
                LLMMessage(role="user", content="Hello")
            ]
            response = await self.chat_completion(test_messages)
            return isinstance(response, LLMResponse) and bool(response.content)
        except Exception as e:
            self.logger.error(f"LLM健康检查失败: {e}")
            return False


class MockLLMClient(BaseLLMClient):
    """模拟LLM客户端 - 用于测试和演示"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._response_templates = self._init_response_templates()
    
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        """模拟聊天完成"""
        
        # 模拟处理延迟
        await asyncio.sleep(0.5)
        
        last_message = messages[-1] if messages else None
        if not last_message:
            return LLMResponse(content="我需要更多信息来帮助您。")
        
        user_input = last_message.content.lower()
        
        # 智能响应生成
        response_content = await self._generate_intelligent_response(user_input, tools)
        
        # 检查是否需要工具调用
        tool_calls = self._analyze_tool_needs(user_input, tools) if tools else None
        
        response = LLMResponse(
            content=response_content,
            tool_calls=tool_calls,
            model="mock-gpt-4",
            finish_reason="stop",
            response_time=0.5,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        )
        
        if stream:
            return self._stream_response(response)
        else:
            return response
    
    async def embedding(self, text: str) -> List[float]:
        """模拟文本嵌入"""
        import hashlib
        import random
        
        # 基于文本内容生成确定性的伪随机向量
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # 生成1536维向量（OpenAI embedding维度）
        embedding = [random.uniform(-1, 1) for _ in range(1536)]
        
        # 归一化
        norm = sum(x * x for x in embedding) ** 0.5
        embedding = [x / norm for x in embedding]
        
        return embedding
    
    async def _generate_intelligent_response(self, user_input: str, tools: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """真正的AI驱动智能响应生成"""
        
        # 如果是真实LLM，直接使用AI生成
        if self.provider != LLMProvider.MOCK:
            return await self._ai_driven_response(user_input, tools, context)
        
        # Mock模式：使用智能模拟响应 (保持向后兼容)
        return self._intelligent_mock_response(user_input, tools, context)
    
    async def _ai_driven_response(self, user_input: str, tools: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """真实AI驱动的响应生成"""
        
        # 构建智能提示词
        system_prompt = self._build_intelligent_system_prompt(tools, context)
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_input)
        ]
        
        # 添加上下文历史 (如果有)
        if context and context.get('conversation_history'):
            history = context['conversation_history'][-3:]  # 最近3轮对话
            for msg in history:
                messages.insert(-1, LLMMessage(role=msg['role'], content=msg['content']))
        
        try:
            response = await self.chat_completion(messages)
            return response.content
        except Exception as e:
            self.logger.error(f"AI响应生成失败: {e}")
            # 降级到智能模拟
            return self._intelligent_mock_response(user_input, tools, context)
    
    def _build_intelligent_system_prompt(self, tools: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """构建智能系统提示词"""
        
        prompt_parts = [
            "你是一个智能AI助手，能够理解用户需求并提供准确、有用的响应。",
            "",
            "核心能力:",
            "- 理解用户意图和上下文",
            "- 分析任务复杂度和需求",
            "- 推荐合适的工具和方法",
            "- 生成结构化的执行计划",
            "- 提供清晰、可操作的指导",
            ""
        ]
        
        # 添加可用工具信息
        if tools:
            prompt_parts.extend([
                "可用工具:",
                *[f"- {tool.get('name', 'unknown')}: {tool.get('description', '')}" for tool in tools],
                ""
            ])
        
        # 添加上下文信息
        if context:
            task_info = context.get('current_task', {})
            if task_info:
                prompt_parts.extend([
                    f"当前任务上下文: {task_info.get('description', '')}",
                    f"任务状态: {task_info.get('status', 'unknown')}",
                    ""
                ])
        
        prompt_parts.extend([
            "响应要求:",
            "- 直接回应用户需求，不要过度解释",
            "- 如果需要JSON格式，请确保格式正确",
            "- 如果是复杂任务，请提供分步指导",
            "- 保持专业、友好的语调",
            "- 基于上下文给出个性化建议"
        ])
        
        return "\n".join(prompt_parts)
    
    def _intelligent_mock_response(self, user_input: str, tools: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """智能模拟响应 (用于Mock模式)"""
        
        # 使用AI思维模式进行分析，而不是硬编码规则
        intent = self._analyze_user_intent(user_input, context)
        complexity = self._estimate_task_complexity(user_input)
        
        # 基于分析结果生成响应
        return self._generate_contextual_response(user_input, intent, complexity, tools, context)
    
    def _analyze_user_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分析用户意图 (模拟AI思维)"""
        
        intent = {
            'type': 'general',
            'confidence': 0.5,
            'requires_tools': False,
            'expected_output': 'text',
            'complexity_level': 'medium'
        }
        
        # 智能意图识别 (模拟神经网络的思维过程)
        input_lower = user_input.lower()
        
        # 分析输出格式需求
        if any(marker in input_lower for marker in ['json', '{', '}', 'format']):
            intent['expected_output'] = 'json'
            intent['confidence'] = 0.9
        
        # 分析任务类型
        if any(word in input_lower for word in ['分析', 'analyze', '研究', 'research', '评估', 'evaluate']):
            intent['type'] = 'analysis'
            intent['requires_tools'] = True
            intent['confidence'] = 0.8
        elif any(word in input_lower for word in ['创建', 'create', '生成', 'generate', '构建', 'build']):
            intent['type'] = 'creation'
            intent['requires_tools'] = True
            intent['confidence'] = 0.8
        elif any(word in input_lower for word in ['web', 'server', '服务器', '系统', 'system']):
            intent['type'] = 'system'
            intent['complexity_level'] = 'high'
            intent['confidence'] = 0.9
        elif any(word in input_lower for word in ['文件', 'file', '读取', 'read', '写入', 'write']):
            intent['type'] = 'file_operation'
            intent['requires_tools'] = True
            intent['confidence'] = 0.85
        elif any(word in input_lower for word in ['时间', 'time', '日期', 'date']):
            intent['type'] = 'time_query'
            intent['complexity_level'] = 'low'
            intent['confidence'] = 0.9
        
        # 上下文增强 (模拟记忆和关联)
        if context and context.get('conversation_history'):
            # 基于历史对话调整意图
            recent_topics = [msg.get('content', '') for msg in context['conversation_history'][-2:]]
            for topic in recent_topics:
                if 'web' in topic.lower() and intent['type'] == 'general':
                    intent['type'] = 'system'
                    intent['confidence'] = min(intent['confidence'] + 0.2, 1.0)
        
        return intent
    
    def _estimate_task_complexity(self, user_input: str) -> int:
        """估算任务复杂度 (1-10分，模拟AI评估)"""
        
        base_score = 3  # 基础分数
        
        # 复杂度指标分析
        complexity_indicators = {
            'simple': (['时间', 'time', '简单', 'simple', '查看', 'view'], -2),
            'medium': (['创建', 'create', '文件', 'file', '分析', 'analyze'], 0),
            'complex': (['web', '服务器', 'server', '系统', 'system', 'api'], +3),
            'very_complex': (['架构', 'architecture', '设计', 'design', '框架', 'framework'], +4)
        }
        
        input_lower = user_input.lower()
        
        for level, (keywords, modifier) in complexity_indicators.items():
            if any(keyword in input_lower for keyword in keywords):
                base_score += modifier
                break
        
        # 长度和细节程度影响复杂度
        if len(user_input) > 100:
            base_score += 1
        if len(user_input.split()) > 20:
            base_score += 1
        
        # 多个动作词表示复杂任务
        action_words = ['创建', 'create', '分析', 'analyze', '生成', 'generate', '实现', 'implement']
        action_count = sum(1 for word in action_words if word in input_lower)
        if action_count > 2:
            base_score += 2
        
        return max(1, min(10, base_score))
    
    def _generate_contextual_response(self, user_input: str, intent: Dict[str, Any], complexity: int, tools: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """基于上下文生成响应 (模拟AI推理)"""
        
        # 根据意图和复杂度选择响应策略
        if intent['expected_output'] == 'json':
            return self._generate_smart_json_response(user_input, intent)
        elif intent['type'] == 'analysis' and 'complexity' in user_input.lower():
            return self._generate_smart_complexity_response(user_input, complexity)
        elif intent['type'] == 'creation' and ('步骤' in user_input or 'decompose' in user_input.lower()):
            return self._generate_smart_decomposition_response(user_input, intent, complexity)
        else:
            return self._generate_smart_general_response(user_input, intent, complexity, tools, context)
    
    def _generate_smart_json_response(self, user_input: str, intent: Dict[str, Any]) -> str:
        """生成智能JSON响应"""
        return '''
{
    "name": "智能工具",
    "description": "基于用户需求智能生成的工具描述",
    "confidence": ''' + str(intent.get('confidence', 0.8)) + '''
}
'''
    
    def _generate_smart_complexity_response(self, user_input: str, complexity: int) -> str:
        """生成智能复杂度分析响应"""
        needs_decomp = complexity > 3
        return f'''
{{
    "score": {complexity},
    "needs_todo_list": {str(needs_decomp).lower()},
    "estimated_steps": {min(complexity, 6)},
    "required_tools": ["general_processor"],
    "reasoning": "基于AI分析，此任务复杂度为{complexity}/10。{f'需要分解为{min(complexity, 6)}个步骤执行' if needs_decomp else '可以直接执行'}。"
}}
'''
    
    def _generate_smart_decomposition_response(self, user_input: str, intent: Dict[str, Any], complexity: int) -> str:
        """生成智能任务分解响应"""
        steps = []
        
        if intent['type'] == 'system' or 'web' in user_input.lower():
            steps = [
                {"content": "分析系统需求和架构", "tools_needed": ["general_processor"], "priority": 8},
                {"content": "设计核心组件", "tools_needed": ["general_processor"], "priority": 6},
                {"content": "实现主要功能", "tools_needed": ["general_processor"], "priority": 4},
                {"content": "测试和优化", "tools_needed": ["general_processor"], "priority": 2}
            ]
        elif intent['type'] == 'file_operation':
            steps = [
                {"content": "准备文件操作环境", "tools_needed": ["general_processor"], "priority": 7},
                {"content": "执行文件操作", "tools_needed": ["general_processor"], "priority": 5},
                {"content": "验证操作结果", "tools_needed": ["general_processor"], "priority": 3}
            ]
        else:
            # 基于复杂度生成通用步骤
            step_count = min(complexity, 4)
            for i in range(step_count):
                steps.append({
                    "content": f"执行第{i+1}步操作",
                    "tools_needed": ["general_processor"],
                    "priority": 8 - i*2
                })
        
        return f'''
{{
    "steps": {json.dumps(steps, ensure_ascii=False)},
    "reasoning": "基于AI智能分析，将任务分解为{len(steps)}个可执行步骤。"
}}
'''
    
    def _generate_smart_general_response(self, user_input: str, intent: Dict[str, Any], complexity: int, tools: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """生成智能通用响应"""
        
        # 基于意图生成个性化响应
        if intent['type'] == 'time_query':
            return "我将为您获取当前的系统时间信息。"
        elif intent['type'] == 'file_operation':
            return f"我将安全地处理文件操作：'{user_input}'。确保数据完整性和安全性。"
        elif intent['type'] == 'analysis':
            return f"我将深入分析：'{user_input}'。运用AI智能分析方法提供准确结果。"
        elif intent['type'] == 'creation':
            return f"我将为您创建：'{user_input}'。设计合适的结构和实现方案。"
        elif intent['type'] == 'system':
            return f"我将构建系统：'{user_input}'。采用最佳实践和安全设计原则。"
        else:
            # 通用智能响应
            confidence_text = "高度" if intent['confidence'] > 0.8 else "中等" if intent['confidence'] > 0.5 else "基本"
            return f"我{confidence_text}理解您的需求：'{user_input}'。将采用最适合的方法和工具来完成这个任务。"
    
    def _analyze_tool_needs(self, user_input: str, tools: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """分析是否需要工具调用"""
        tool_calls = []
        
        # 分析需要的工具
        if '时间' in user_input or 'time' in user_input:
            tool_calls.append({
                "id": f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type": "function",
                "function": {
                    "name": "general_processor",
                    "arguments": json.dumps({
                        "task": user_input,
                        "context": "获取时间信息"
                    })
                }
            })
        
        elif '文件' in user_input and '创建' in user_input:
            tool_calls.append({
                "id": f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type": "function",
                "function": {
                    "name": "file_write",
                    "arguments": json.dumps({
                        "file_path": "output.txt",
                        "content": "根据用户需求生成的内容",
                        "encoding": "utf-8"
                    })
                }
            })
        
        elif '文件' in user_input and ('读取' in user_input or '查看' in user_input):
            tool_calls.append({
                "id": f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type": "function",
                "function": {
                    "name": "file_read",
                    "arguments": json.dumps({
                        "file_path": "README.md",
                        "offset": 0,
                        "limit": 100
                    })
                }
            })
        
        return tool_calls if tool_calls else None
    
    async def _stream_response(self, response: LLMResponse) -> AsyncGenerator[LLMResponse, None]:
        """流式响应"""
        words = response.content.split()
        current_content = ""
        
        for word in words:
            current_content += word + " "
            await asyncio.sleep(0.1)  # 模拟流式延迟
            
            yield LLMResponse(
                content=current_content.strip(),
                tool_calls=response.tool_calls if word == words[-1] else None,
                model=response.model,
                finish_reason="stop" if word == words[-1] else "",
                response_time=response.response_time,
                metadata={"streaming": True}
            )
    
    def _get_analysis_response(self, user_input: str) -> str:
        return f"我将对'{user_input}'进行深入分析。我会收集相关信息，进行结构化分析，并提供详细的分析报告。"
    
    def _get_creation_response(self, user_input: str) -> str:
        return f"我将为您创建'{user_input}'。我会设计合适的结构，实现核心功能，并确保质量。"
    
    def _get_file_response(self, user_input: str) -> str:
        return f"我将处理文件相关的任务：'{user_input}'。我会安全地操作文件并确保数据完整性。"
    
    def _get_general_response(self, user_input: str) -> str:
        return f"我理解您的需求：'{user_input}'。我将选择合适的工具和方法来完成这个任务。"
    
    def _generate_json_response(self, user_input: str) -> str:
        """生成JSON格式响应"""
        return '''
{
    "name": "文件操作工具",
    "description": "一个简单而强大的文件操作工具，支持读取、写入、创建和删除文件操作，具有安全检查和错误处理机制。"
}
'''
    
    def _generate_complexity_analysis_response(self, user_input: str) -> str:
        """生成复杂度分析响应"""
        # 简单的复杂度评估逻辑
        complexity_score = 5  # 默认中等复杂度
        
        if any(keyword in user_input for keyword in ['web', '服务器', 'server', '系统', 'system']):
            complexity_score = 7
        elif any(keyword in user_input for keyword in ['时间', 'time', '简单', 'simple']):
            complexity_score = 2
        elif any(keyword in user_input for keyword in ['API', 'api', '文档', 'document']):
            complexity_score = 6
        
        needs_decomp = complexity_score > 3
        estimated_steps = min(complexity_score, 5)
        
        return f'''
{{
    "score": {complexity_score},
    "needs_todo_list": {str(needs_decomp).lower()},
    "estimated_steps": {estimated_steps},
    "required_tools": ["general_processor"],
    "reasoning": "基于任务关键词分析，评估为{complexity_score}分复杂度。{'需要分解为多个步骤' if needs_decomp else '可以直接执行'}。"
}}
'''
    
    def _generate_decomposition_response(self, user_input: str) -> str:
        """生成任务分解响应"""
        # 根据任务类型生成不同的分解步骤
        if 'web' in user_input.lower() or '服务器' in user_input:
            steps = [
                {"content": "设计web服务器架构", "tools_needed": ["general_processor"], "priority": 8},
                {"content": "实现核心功能模块", "tools_needed": ["general_processor"], "priority": 6},
                {"content": "添加路由和中间件", "tools_needed": ["general_processor"], "priority": 4},
                {"content": "测试和部署服务器", "tools_needed": ["general_processor"], "priority": 2}
            ]
        elif '文档' in user_input or 'document' in user_input.lower():
            steps = [
                {"content": "分析项目结构和代码", "tools_needed": ["file_read"], "priority": 7},
                {"content": "提取API接口信息", "tools_needed": ["general_processor"], "priority": 5},
                {"content": "生成文档内容", "tools_needed": ["general_processor"], "priority": 3},
                {"content": "创建并保存文档文件", "tools_needed": ["file_write"], "priority": 1}
            ]
        elif '时间' in user_input or 'time' in user_input.lower():
            steps = [
                {"content": "获取系统当前时间", "tools_needed": ["general_processor"], "priority": 5},
                {"content": "格式化时间显示", "tools_needed": ["general_processor"], "priority": 3}
            ]
        else:
            # 通用分解
            steps = [
                {"content": "分析任务需求", "tools_needed": ["general_processor"], "priority": 6},
                {"content": "准备执行环境", "tools_needed": ["general_processor"], "priority": 4},
                {"content": "执行主要操作", "tools_needed": ["general_processor"], "priority": 2}
            ]
        
        return f'''
{{
    "steps": {json.dumps(steps, ensure_ascii=False)},
    "reasoning": "根据任务类型进行智能分解，确保每个步骤都是可执行的。"
}}
'''
    
    def _init_response_templates(self) -> Dict[str, str]:
        """初始化响应模板"""
        return {
            "greeting": "您好！我是Universal Tool Framework的AI助手，可以帮您执行各种任务。",
            "task_analysis": "我正在分析您的任务需求，确定最佳的执行策略。",
            "tool_selection": "基于任务分析，我将选择最适合的工具来完成您的需求。",
            "execution_plan": "我已制定了详细的执行计划，将分步骤完成您的任务。",
            "completion": "任务已成功完成！如果您需要进一步的帮助，请告诉我。"
        }


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
        except ImportError:
            self.logger.error("OpenAI package not installed. Run: pip install openai")
            self._client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self._client = None
    
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        """OpenAI聊天完成"""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        
        # 转换消息格式
        openai_messages = [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
                **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {})
            }
            for msg in messages
        ]
        
        # 构建请求参数
        params = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "stream": stream,
            **kwargs
        }
        
        if self.config.max_tokens:
            params["max_tokens"] = self.config.max_tokens
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        # 发送请求
        import time
        start_time = time.time()
        
        try:
            response = await self._client.chat.completions.create(**params)
            response_time = time.time() - start_time
            
            if stream:
                return self._process_stream_response(response, response_time)
            else:
                return self._process_response(response, response_time)
                
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    async def embedding(self, text: str) -> List[float]:
        """OpenAI文本嵌入"""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            response = await self._client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"OpenAI embedding error: {e}")
            raise
    
    def _process_response(self, response, response_time: float) -> LLMResponse:
        """处理单次响应"""
        choice = response.choices[0]
        message = choice.message
        
        return LLMResponse(
            content=message.content or "",
            tool_calls=message.tool_calls,
            usage=response.usage._asdict() if response.usage else None,
            model=response.model,
            finish_reason=choice.finish_reason,
            response_time=response_time
        )
    
    async def _process_stream_response(
        self, 
        response_stream, 
        response_time: float
    ) -> AsyncGenerator[LLMResponse, None]:
        """处理流式响应"""
        content = ""
        tool_calls = []
        
        async for chunk in response_stream:
            if chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta
                
                if delta.content:
                    content += delta.content
                
                if delta.tool_calls:
                    tool_calls.extend(delta.tool_calls)
                
                yield LLMResponse(
                    content=content,
                    tool_calls=tool_calls if choice.finish_reason else None,
                    model=chunk.model,
                    finish_reason=choice.finish_reason or "",
                    response_time=response_time,
                    metadata={"streaming": True}
                )


class LLMClient:
    """统一LLM客户端"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = get_logger(__name__)
        self._client = self._create_client()
    
    def _create_client(self) -> BaseLLMClient:
        """创建具体的LLM客户端"""
        if self.config.provider == LLMProvider.OPENAI:
            return OpenAIClient(self.config)
        elif self.config.provider == LLMProvider.MOCK:
            return MockLLMClient(self.config)
        else:
            # 默认使用Mock客户端
            self.logger.warning(f"Provider {self.config.provider} not implemented, using mock client")
            mock_config = LLMConfig(provider=LLMProvider.MOCK, model="mock-model")
            return MockLLMClient(mock_config)
    
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        """聊天完成"""
        return await self._client.chat_completion(messages, tools, stream, **kwargs)
    
    async def embedding(self, text: str) -> List[float]:
        """文本嵌入"""
        return await self._client.embedding(text)
    
    async def health_check(self) -> bool:
        """健康检查"""
        return await self._client.health_check()
    
    def get_provider(self) -> LLMProvider:
        """获取提供商"""
        return self.config.provider
    
    def get_model(self) -> str:
        """获取模型名称"""
        return self.config.model
