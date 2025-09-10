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

from utf.utils.logging import get_logger


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
        response_content = self._generate_intelligent_response(user_input, tools)
        
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
    
    def _generate_intelligent_response(self, user_input: str, tools: Optional[List[Dict[str, Any]]]) -> str:
        """生成智能响应"""
        
        # 任务分析关键词
        analysis_keywords = ['分析', '研究', '调查', 'analyze', 'research']
        creation_keywords = ['创建', '生成', '制作', 'create', 'generate', 'make']
        file_keywords = ['文件', '读取', '写入', 'file', 'read', 'write']
        time_keywords = ['时间', '日期', 'time', 'date']
        
        if any(keyword in user_input for keyword in analysis_keywords):
            return self._get_analysis_response(user_input)
        elif any(keyword in user_input for keyword in creation_keywords):
            return self._get_creation_response(user_input)
        elif any(keyword in user_input for keyword in file_keywords):
            return self._get_file_response(user_input)
        elif any(keyword in user_input for keyword in time_keywords):
            return "我将获取当前时间信息。"
        else:
            return self._get_general_response(user_input)
    
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
