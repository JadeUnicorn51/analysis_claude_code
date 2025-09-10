"""
交互管理器

负责处理用户交互、中断检测、响应收集等功能
"""

import asyncio
import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from utf.config.settings import FrameworkConfig
from utf.models.execution import UserInteractionEvent, UserInteractionResponse
from utf.utils.logging import get_logger


class InteractionManager:
    """
    交互管理器
    
    管理用户与框架的实时交互，支持中断、确认、修改等操作
    """
    
    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # 交互状态管理
        self._pending_interactions: Dict[str, UserInteractionEvent] = {}
        self._interaction_responses: Dict[str, UserInteractionResponse] = {}
        self._interruption_requests: Dict[str, bool] = {}  # task_id -> interruption_requested
        
        # 异步事件
        self._response_events: Dict[str, asyncio.Event] = {}
        
        self.logger.info("InteractionManager initialized")
    
    async def check_interruption_request(self, task_id: str) -> bool:
        """
        检查用户是否请求中断
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否有中断请求
        """
        if not self.config.interaction.allow_user_interruption:
            return False
        
        return self._interruption_requests.get(task_id, False)
    
    def request_interruption(self, task_id: str) -> None:
        """
        请求中断任务
        
        Args:
            task_id: 要中断的任务ID
        """
        if self.config.interaction.allow_user_interruption:
            self._interruption_requests[task_id] = True
            self.logger.info(f"用户请求中断任务: {task_id}")
    
    def clear_interruption_request(self, task_id: str) -> None:
        """
        清除中断请求
        
        Args:
            task_id: 任务ID
        """
        self._interruption_requests.pop(task_id, None)
    
    async def create_interaction_event(
        self,
        event_type: str,
        data: Any,
        task_id: str,
        response_required: bool = True,
        timeout_seconds: Optional[int] = None
    ) -> UserInteractionEvent:
        """
        创建交互事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            task_id: 关联任务ID
            response_required: 是否需要用户响应
            timeout_seconds: 超时时间
            
        Returns:
            UserInteractionEvent: 交互事件
        """
        event_id = str(uuid.uuid4())
        timeout = timeout_seconds or self.config.interaction.user_response_timeout
        
        event = UserInteractionEvent(
            id=event_id,
            type=event_type,
            data=data,
            task_id=task_id,
            response_required=response_required,
            timeout_seconds=timeout
        )
        
        if response_required:
            self._pending_interactions[event_id] = event
            self._response_events[event_id] = asyncio.Event()
        
        self.logger.info(f"创建交互事件: {event_id}, 类型: {event_type}")
        return event
    
    async def wait_for_user_response(
        self,
        event_id: str,
        timeout_seconds: Optional[int] = None
    ) -> Optional[UserInteractionResponse]:
        """
        等待用户响应
        
        Args:
            event_id: 事件ID
            timeout_seconds: 超时时间
            
        Returns:
            Optional[UserInteractionResponse]: 用户响应，超时返回None
        """
        if event_id not in self._response_events:
            self.logger.warning(f"事件不存在或不需要响应: {event_id}")
            return None
        
        timeout = timeout_seconds or self.config.interaction.user_response_timeout
        
        try:
            # 等待响应事件
            await asyncio.wait_for(
                self._response_events[event_id].wait(),
                timeout=timeout
            )
            
            # 获取响应
            response = self._interaction_responses.get(event_id)
            if response:
                self.logger.info(f"收到用户响应: {event_id}, 动作: {response.action}")
            
            return response
            
        except asyncio.TimeoutError:
            self.logger.warning(f"等待用户响应超时: {event_id}")
            return None
        finally:
            # 清理资源
            self._cleanup_interaction(event_id)
    
    def submit_user_response(
        self,
        event_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        提交用户响应
        
        Args:
            event_id: 事件ID
            action: 用户选择的动作
            data: 响应数据
            
        Returns:
            bool: 是否成功提交
        """
        if event_id not in self._pending_interactions:
            self.logger.warning(f"无效的事件ID: {event_id}")
            return False
        
        response = UserInteractionResponse(
            event_id=event_id,
            action=action,
            data=data
        )
        
        self._interaction_responses[event_id] = response
        
        # 触发响应事件
        if event_id in self._response_events:
            self._response_events[event_id].set()
        
        self.logger.info(f"用户响应已提交: {event_id}, 动作: {action}")
        return True
    
    async def request_user_confirmation(
        self,
        message: str,
        task_id: str,
        options: Optional[List[Dict[str, str]]] = None,
        timeout_seconds: Optional[int] = None
    ) -> Optional[str]:
        """
        请求用户确认
        
        Args:
            message: 确认消息
            task_id: 任务ID
            options: 可选项列表
            timeout_seconds: 超时时间
            
        Returns:
            Optional[str]: 用户选择的动作，超时返回None
        """
        if not self.config.interaction.confirmation_required:
            return "continue"  # 如果不需要确认，默认继续
        
        default_options = [
            {"action": "continue", "label": "继续"},
            {"action": "cancel", "label": "取消"}
        ]
        
        event = await self.create_interaction_event(
            event_type="confirmation_request",
            data={
                "message": message,
                "options": options or default_options
            },
            task_id=task_id,
            timeout_seconds=timeout_seconds
        )
        
        response = await self.wait_for_user_response(event.id, timeout_seconds)
        return response.action if response else None
    
    async def request_user_input(
        self,
        prompt: str,
        task_id: str,
        input_type: str = "text",
        validation_rules: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None
    ) -> Optional[Any]:
        """
        请求用户输入
        
        Args:
            prompt: 输入提示
            task_id: 任务ID
            input_type: 输入类型 (text, number, choice, etc.)
            validation_rules: 验证规则
            timeout_seconds: 超时时间
            
        Returns:
            Optional[Any]: 用户输入，超时返回None
        """
        event = await self.create_interaction_event(
            event_type="input_request",
            data={
                "prompt": prompt,
                "input_type": input_type,
                "validation_rules": validation_rules or {}
            },
            task_id=task_id,
            timeout_seconds=timeout_seconds
        )
        
        response = await self.wait_for_user_response(event.id, timeout_seconds)
        return response.data.get("input") if response and response.data else None
    
    async def show_progress(
        self,
        task_id: str,
        current_step: int,
        total_steps: int,
        message: str,
        percentage: Optional[float] = None
    ) -> None:
        """
        显示进度信息
        
        Args:
            task_id: 任务ID
            current_step: 当前步骤
            total_steps: 总步骤数
            message: 进度消息
            percentage: 完成百分比
        """
        if percentage is None:
            percentage = (current_step / total_steps) * 100 if total_steps > 0 else 0
        
        await self.create_interaction_event(
            event_type="progress_update",
            data={
                "current_step": current_step,
                "total_steps": total_steps,
                "message": message,
                "percentage": percentage
            },
            task_id=task_id,
            response_required=False
        )
    
    async def display_notification(
        self,
        task_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        显示通知
        
        Args:
            task_id: 任务ID
            notification_type: 通知类型 (info, warning, error, success)
            title: 通知标题
            message: 通知内容
            data: 额外数据
        """
        await self.create_interaction_event(
            event_type="notification",
            data={
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "data": data or {}
            },
            task_id=task_id,
            response_required=False
        )
    
    def get_pending_interactions(self, task_id: Optional[str] = None) -> List[UserInteractionEvent]:
        """
        获取待处理的交互事件
        
        Args:
            task_id: 可选的任务ID过滤
            
        Returns:
            List[UserInteractionEvent]: 待处理的交互事件列表
        """
        events = list(self._pending_interactions.values())
        
        if task_id:
            events = [event for event in events if event.task_id == task_id]
        
        return events
    
    def cancel_interaction(self, event_id: str) -> bool:
        """
        取消交互事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            bool: 是否成功取消
        """
        if event_id in self._pending_interactions:
            # 如果有等待的协程，设置事件以解除阻塞
            if event_id in self._response_events:
                self._response_events[event_id].set()
            
            self._cleanup_interaction(event_id)
            self.logger.info(f"交互事件已取消: {event_id}")
            return True
        
        return False
    
    def _cleanup_interaction(self, event_id: str) -> None:
        """清理交互资源"""
        self._pending_interactions.pop(event_id, None)
        self._interaction_responses.pop(event_id, None)
        self._response_events.pop(event_id, None)
    
    def cleanup_task_interactions(self, task_id: str) -> None:
        """
        清理任务相关的所有交互
        
        Args:
            task_id: 任务ID
        """
        # 收集要清理的事件ID
        event_ids_to_cleanup = []
        
        for event_id, event in self._pending_interactions.items():
            if event.task_id == task_id:
                event_ids_to_cleanup.append(event_id)
        
        # 清理事件
        for event_id in event_ids_to_cleanup:
            self.cancel_interaction(event_id)
        
        # 清理中断请求
        self.clear_interruption_request(task_id)
        
        self.logger.info(f"任务交互已清理: {task_id}, 清理事件数: {len(event_ids_to_cleanup)}")
    
    def get_interaction_statistics(self) -> Dict[str, Any]:
        """
        获取交互统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "pending_interactions": len(self._pending_interactions),
            "active_tasks_with_interactions": len(set(
                event.task_id for event in self._pending_interactions.values()
            )),
            "interruption_requests": len(self._interruption_requests),
            "total_responses_received": len(self._interaction_responses)
        }
