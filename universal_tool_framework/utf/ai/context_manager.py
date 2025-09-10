"""
智能上下文管理器

管理任务执行过程中的上下文信息，包括对话历史、中间结果、知识库等
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from utf.ai.llm_client import LLMClient, LLMMessage
from utf.models.task import Task, TodoItem, TaskResult
from utf.models.tool import ToolResult
from utf.utils.logging import get_logger


@dataclass
class ContextEntry:
    """上下文条目"""
    id: str
    type: str  # user_message, assistant_message, tool_result, task_result, knowledge
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    relevance_score: float = 1.0
    embedding: Optional[List[float]] = None


@dataclass
class ConversationMemory:
    """对话记忆"""
    task_id: str
    entries: List[ContextEntry] = field(default_factory=list)
    summary: str = ""
    last_updated: datetime = field(default_factory=datetime.now)


class ContextManager:
    """
    智能上下文管理器
    
    负责管理任务执行过程中的所有上下文信息
    """
    
    def __init__(self, llm_client: LLMClient, max_context_length: int = 8000):
        self.llm_client = llm_client
        self.max_context_length = max_context_length
        self.logger = get_logger(__name__)
        
        # 上下文存储
        self._conversations: Dict[str, ConversationMemory] = {}
        self._knowledge_base: Dict[str, ContextEntry] = {}
        self._embeddings_cache: Dict[str, List[float]] = {}
        
        # 上下文压缩和总结
        self._compression_threshold = max_context_length * 0.8
        
        self.logger.info("ContextManager initialized")
    
    async def add_user_message(
        self,
        task_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加用户消息到上下文"""
        entry = ContextEntry(
            id=f"user_{int(time.time() * 1000)}",
            type="user_message",
            content=message,
            metadata=metadata or {}
        )
        
        await self._add_context_entry(task_id, entry)
        self.logger.debug(f"添加用户消息到上下文: {task_id}")
    
    async def add_assistant_message(
        self,
        task_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加助手消息到上下文"""
        entry = ContextEntry(
            id=f"assistant_{int(time.time() * 1000)}",
            type="assistant_message",
            content=message,
            metadata=metadata or {}
        )
        
        await self._add_context_entry(task_id, entry)
        self.logger.debug(f"添加助手消息到上下文: {task_id}")
    
    async def add_tool_result(
        self,
        task_id: str,
        tool_result: ToolResult,
        relevance_score: float = 0.8
    ) -> None:
        """添加工具执行结果到上下文"""
        
        # 构建工具结果的文本描述
        content = self._format_tool_result(tool_result)
        
        entry = ContextEntry(
            id=f"tool_{tool_result.tool_call_id}",
            type="tool_result",
            content=content,
            relevance_score=relevance_score,
            metadata={
                "tool_name": tool_result.tool_name,
                "success": tool_result.success,
                "execution_time": tool_result.execution_time,
                "tool_metadata": tool_result.metadata
            }
        )
        
        await self._add_context_entry(task_id, entry)
        self.logger.debug(f"添加工具结果到上下文: {task_id}")
    
    async def add_task_result(
        self,
        task_id: str,
        task_result: TaskResult,
        relevance_score: float = 0.9
    ) -> None:
        """添加任务结果到上下文"""
        
        content = f"任务事件: {task_result.type}\n数据: {json.dumps(task_result.data, ensure_ascii=False, indent=2)}"
        
        entry = ContextEntry(
            id=f"task_{task_result.type}_{int(time.time() * 1000)}",
            type="task_result",
            content=content,
            relevance_score=relevance_score,
            metadata={
                "result_type": task_result.type,
                "todo_id": task_result.todo_id,
                "result_metadata": task_result.metadata
            }
        )
        
        await self._add_context_entry(task_id, entry)
    
    async def add_knowledge(
        self,
        knowledge_id: str,
        content: str,
        knowledge_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加知识到知识库"""
        entry = ContextEntry(
            id=knowledge_id,
            type="knowledge",
            content=content,
            metadata={
                "knowledge_type": knowledge_type,
                **(metadata or {})
            }
        )
        
        # 计算嵌入向量
        try:
            entry.embedding = await self.llm_client.embedding(content)
        except Exception as e:
            self.logger.warning(f"计算知识嵌入失败: {e}")
        
        self._knowledge_base[knowledge_id] = entry
        self.logger.info(f"添加知识到知识库: {knowledge_id}")
    
    async def get_relevant_context(
        self,
        task_id: str,
        query: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> List[LLMMessage]:
        """获取相关上下文用于LLM调用"""
        
        max_tokens = max_tokens or self.max_context_length
        
        if task_id not in self._conversations:
            return []
        
        conversation = self._conversations[task_id]
        
        # 如果有查询，使用语义搜索获取相关条目
        if query:
            relevant_entries = await self._semantic_search(query, conversation.entries)
        else:
            # 否则按时间顺序获取最近的条目
            relevant_entries = sorted(conversation.entries, key=lambda x: x.timestamp, reverse=True)
        
        # 构建LLM消息
        messages = []
        current_tokens = 0
        
        # 添加任务摘要（如果有）
        if conversation.summary:
            summary_msg = LLMMessage(
                role="system",
                content=f"任务上下文摘要: {conversation.summary}"
            )
            messages.append(summary_msg)
            current_tokens += len(conversation.summary) // 4  # 粗略估算token数
        
        # 添加相关条目
        for entry in relevant_entries:
            if current_tokens >= max_tokens:
                break
            
            # 转换为LLM消息格式
            llm_message = self._convert_entry_to_message(entry)
            if llm_message:
                messages.append(llm_message)
                current_tokens += len(entry.content) // 4  # 粗略估算token数
        
        self.logger.debug(f"获取相关上下文: {len(messages)} 条消息, 约 {current_tokens} tokens")
        return messages
    
    async def summarize_conversation(self, task_id: str) -> str:
        """总结对话内容"""
        if task_id not in self._conversations:
            return ""
        
        conversation = self._conversations[task_id]
        
        if not conversation.entries:
            return ""
        
        # 构建总结提示
        entries_text = "\n".join([
            f"[{entry.type}] {entry.content[:200]}..." if len(entry.content) > 200 else f"[{entry.type}] {entry.content}"
            for entry in conversation.entries[-20:]  # 最近20条
        ])
        
        summary_prompt = f"""
请总结以下任务执行过程中的关键信息：

{entries_text}

请提供简洁的总结，包括：
1. 主要任务目标
2. 已完成的关键步骤
3. 重要的中间结果
4. 当前状态
5. 需要注意的问题

总结应该控制在200字以内，突出重点。
"""
        
        try:
            messages = [
                LLMMessage(role="system", content="你是一个专业的总结助手，擅长提炼关键信息。"),
                LLMMessage(role="user", content=summary_prompt)
            ]
            
            response = await self.llm_client.chat_completion(messages)
            summary = response.content.strip()
            
            # 更新对话摘要
            conversation.summary = summary
            conversation.last_updated = datetime.now()
            
            self.logger.info(f"对话总结完成: {task_id}")
            return summary
            
        except Exception as e:
            self.logger.error(f"对话总结失败: {e}")
            return ""
    
    async def compress_context(self, task_id: str) -> None:
        """压缩上下文以释放内存"""
        if task_id not in self._conversations:
            return
        
        conversation = self._conversations[task_id]
        
        # 计算当前上下文长度
        total_length = sum(len(entry.content) for entry in conversation.entries)
        
        if total_length < self._compression_threshold:
            return
        
        self.logger.info(f"开始压缩上下文: {task_id}, 当前长度: {total_length}")
        
        # 生成摘要
        if not conversation.summary:
            await self.summarize_conversation(task_id)
        
        # 保留最重要的条目
        important_entries = sorted(
            conversation.entries,
            key=lambda x: (x.relevance_score, x.timestamp.timestamp()),
            reverse=True
        )[:50]  # 保留前50个最重要的条目
        
        # 更新对话
        conversation.entries = important_entries
        conversation.last_updated = datetime.now()
        
        new_length = sum(len(entry.content) for entry in conversation.entries)
        self.logger.info(f"上下文压缩完成: {task_id}, 新长度: {new_length}")
    
    async def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[ContextEntry]:
        """搜索知识库"""
        
        # 获取查询嵌入
        try:
            query_embedding = await self.llm_client.embedding(query)
        except Exception as e:
            self.logger.error(f"计算查询嵌入失败: {e}")
            return []
        
        # 计算相似度
        candidates = []
        for entry in self._knowledge_base.values():
            if knowledge_type and entry.metadata.get("knowledge_type") != knowledge_type:
                continue
            
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                candidates.append((entry, similarity))
        
        # 排序并返回前k个
        candidates.sort(key=lambda x: x[1], reverse=True)
        results = [entry for entry, _ in candidates[:top_k]]
        
        self.logger.debug(f"知识库搜索完成: 查询='{query}', 结果数={len(results)}")
        return results
    
    async def _add_context_entry(self, task_id: str, entry: ContextEntry) -> None:
        """添加上下文条目"""
        if task_id not in self._conversations:
            self._conversations[task_id] = ConversationMemory(task_id=task_id)
        
        conversation = self._conversations[task_id]
        
        # 计算嵌入向量（异步，不阻塞）
        try:
            if entry.content and len(entry.content) > 10:  # 只为有意义的内容计算嵌入
                entry.embedding = await self.llm_client.embedding(entry.content)
        except Exception as e:
            self.logger.warning(f"计算上下文嵌入失败: {e}")
        
        conversation.entries.append(entry)
        conversation.last_updated = datetime.now()
        
        # 检查是否需要压缩
        if len(conversation.entries) > 100:  # 超过100条时考虑压缩
            await self.compress_context(task_id)
    
    async def _semantic_search(
        self,
        query: str,
        entries: List[ContextEntry],
        top_k: int = 20
    ) -> List[ContextEntry]:
        """语义搜索上下文条目"""
        
        if not entries:
            return []
        
        # 获取查询嵌入
        try:
            query_embedding = await self.llm_client.embedding(query)
        except Exception as e:
            self.logger.warning(f"语义搜索失败: {e}")
            # 降级为时间排序
            return sorted(entries, key=lambda x: x.timestamp, reverse=True)[:top_k]
        
        # 计算相似度
        candidates = []
        for entry in entries:
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                # 综合相似度和相关性分数
                final_score = similarity * entry.relevance_score
                candidates.append((entry, final_score))
            else:
                # 没有嵌入的条目给予基础分数
                candidates.append((entry, entry.relevance_score * 0.5))
        
        # 排序并返回前k个
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in candidates[:top_k]]
    
    def _convert_entry_to_message(self, entry: ContextEntry) -> Optional[LLMMessage]:
        """将上下文条目转换为LLM消息"""
        
        if entry.type == "user_message":
            return LLMMessage(role="user", content=entry.content)
        
        elif entry.type == "assistant_message":
            return LLMMessage(role="assistant", content=entry.content)
        
        elif entry.type == "tool_result":
            # 工具结果作为系统消息
            return LLMMessage(
                role="system",
                content=f"工具执行结果: {entry.content}",
                metadata=entry.metadata
            )
        
        elif entry.type == "task_result":
            # 任务结果作为系统消息
            return LLMMessage(
                role="system",
                content=f"任务状态更新: {entry.content}",
                metadata=entry.metadata
            )
        
        elif entry.type == "knowledge":
            # 知识作为系统消息
            return LLMMessage(
                role="system",
                content=f"相关知识: {entry.content}",
                metadata=entry.metadata
            )
        
        return None
    
    def _format_tool_result(self, tool_result: ToolResult) -> str:
        """格式化工具结果为文本"""
        
        status = "成功" if tool_result.success else "失败"
        content = f"工具 {tool_result.tool_name} 执行{status}\n"
        content += f"执行时间: {tool_result.execution_time:.2f}秒\n"
        
        if tool_result.success and tool_result.data:
            if isinstance(tool_result.data, dict):
                if 'message' in tool_result.data:
                    content += f"结果: {tool_result.data['message']}\n"
                elif 'file_path' in tool_result.data:
                    content += f"文件: {tool_result.data['file_path']}\n"
                else:
                    content += f"数据: {json.dumps(tool_result.data, ensure_ascii=False)}\n"
            else:
                content += f"结果: {tool_result.data}\n"
        
        if not tool_result.success and tool_result.error:
            content += f"错误: {tool_result.error}\n"
        
        return content.strip()
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_conversation_stats(self, task_id: str) -> Dict[str, Any]:
        """获取对话统计信息"""
        if task_id not in self._conversations:
            return {}
        
        conversation = self._conversations[task_id]
        
        entry_types = {}
        for entry in conversation.entries:
            entry_types[entry.type] = entry_types.get(entry.type, 0) + 1
        
        total_length = sum(len(entry.content) for entry in conversation.entries)
        
        return {
            "total_entries": len(conversation.entries),
            "entry_types": entry_types,
            "total_length": total_length,
            "has_summary": bool(conversation.summary),
            "summary_length": len(conversation.summary) if conversation.summary else 0,
            "last_updated": conversation.last_updated.isoformat()
        }
    
    def cleanup_conversation(self, task_id: str) -> None:
        """清理对话上下文"""
        if task_id in self._conversations:
            del self._conversations[task_id]
            self.logger.info(f"清理对话上下文: {task_id}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用统计"""
        total_conversations = len(self._conversations)
        total_entries = sum(len(conv.entries) for conv in self._conversations.values())
        total_knowledge = len(self._knowledge_base)
        
        total_text_length = sum(
            sum(len(entry.content) for entry in conv.entries)
            for conv in self._conversations.values()
        ) + sum(len(entry.content) for entry in self._knowledge_base.values())
        
        return {
            "conversations": total_conversations,
            "context_entries": total_entries,
            "knowledge_entries": total_knowledge,
            "total_text_length": total_text_length,
            "estimated_memory_mb": total_text_length / (1024 * 1024)  # 粗略估算
        }
