"""
工具基类实现
"""

import time
import asyncio
from typing import Any, Dict, Optional, AsyncGenerator
from abc import ABC, abstractmethod

from utf.models.tool import Tool, ToolDefinition, ToolResult


class BaseTool(Tool):
    """工具基类
    
    所有自定义工具都应该继承此类并实现必要的方法
    """
    
    def __init__(self):
        super().__init__()
        self._definition = self._create_definition()
    
    @property
    def definition(self) -> ToolDefinition:
        """获取工具定义"""
        if self._definition is None:
            self._definition = self._create_definition()
        return self._definition
    
    @abstractmethod
    def _create_definition(self) -> ToolDefinition:
        """创建工具定义
        
        子类必须实现此方法来定义工具的基本信息
        """
        pass
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行工具的主入口
        
        此方法包含完整的执行流程：验证->权限检查->执行->结果处理
        """
        start_time = time.time()
        tool_call_id = context.get('call_id', 'unknown') if context else 'unknown'
        
        try:
            # 1. 参数验证
            if not self.validate_parameters(parameters):
                execution_time = time.time() - start_time
                yield ToolResult.error_result(
                    tool_call_id=tool_call_id,
                    tool_name=self.definition.name,
                    error="参数验证失败",
                    execution_time=execution_time
                )
                return
            
            # 2. 权限检查
            if not self.check_permissions(parameters, context):
                execution_time = time.time() - start_time
                yield ToolResult.error_result(
                    tool_call_id=tool_call_id,
                    tool_name=self.definition.name,
                    error="权限检查失败",
                    execution_time=execution_time
                )
                return
            
            # 3. 执行前置处理
            await self._before_execute(parameters, context)
            
            # 4. 执行核心逻辑
            async for result in self._execute_core(parameters, context):
                yield result
            
            # 5. 执行后置处理
            await self._after_execute(parameters, context)
            
        except Exception as e:
            execution_time = time.time() - start_time
            yield ToolResult.error_result(
                tool_call_id=tool_call_id,
                tool_name=self.definition.name,
                error=f"执行异常: {str(e)}",
                execution_time=execution_time,
                metadata={"exception_type": type(e).__name__}
            )
    
    @abstractmethod
    async def _execute_core(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolResult, None]:
        """
        核心执行逻辑
        
        子类必须实现此方法来定义具体的工具功能
        """
        pass
    
    async def _before_execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        执行前置处理
        
        子类可以重写此方法来添加执行前的准备工作
        """
        pass
    
    async def _after_execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        执行后置处理
        
        子类可以重写此方法来添加执行后的清理工作
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        参数验证
        
        默认实现，子类可以重写以添加特定的验证逻辑
        """
        # 检查必需参数
        required_params = self._get_required_parameters()
        for param in required_params:
            if param not in parameters:
                return False
        
        return True
    
    def _get_required_parameters(self) -> list:
        """
        获取必需参数列表
        
        子类可以重写此方法来定义必需参数
        """
        return []
    
    def check_permissions(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        权限检查
        
        默认实现，子类可以重写以添加特定的权限检查逻辑
        """
        if not context:
            return True
        
        # 检查所需权限
        for permission in self.definition.required_permissions:
            if not context.get('permissions', {}).get(permission, False):
                return False
        
        return True
    
    def is_concurrency_safe(self, parameters: Dict[str, Any]) -> bool:
        """
        检查是否支持并发执行
        
        默认使用工具定义中的设置，子类可以重写以实现动态判断
        """
        return self.definition.is_concurrent_safe
    
    def estimate_execution_time(self, parameters: Dict[str, Any]) -> float:
        """
        估算执行时间
        
        默认返回1秒，子类可以重写以提供更精确的估算
        """
        return 1.0
    
    async def _sleep_if_needed(self, seconds: float) -> None:
        """工具内部使用的异步睡眠"""
        if seconds > 0:
            await asyncio.sleep(seconds)
    
    def _create_success_result(
        self,
        tool_call_id: str,
        data: Any,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """创建成功结果的便捷方法"""
        return ToolResult.success_result(
            tool_call_id=tool_call_id,
            tool_name=self.definition.name,
            data=data,
            execution_time=execution_time,
            metadata=metadata or {}
        )
    
    def _create_error_result(
        self,
        tool_call_id: str,
        error: str,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """创建错误结果的便捷方法"""
        return ToolResult.error_result(
            tool_call_id=tool_call_id,
            tool_name=self.definition.name,
            error=error,
            execution_time=execution_time,
            metadata=metadata or {}
        )
