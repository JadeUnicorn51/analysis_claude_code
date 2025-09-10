"""
工具相关的数据模型
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """工具定义模型"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: Dict[str, Any] = Field(default={}, description="参数schema")
    is_concurrent_safe: bool = Field(default=True, description="是否支持并发执行")
    is_read_only: bool = Field(default=False, description="是否为只读工具")
    required_permissions: List[str] = Field(default=[], description="需要的权限")
    tags: List[str] = Field(default=[], description="工具标签")
    version: str = Field(default="1.0.0", description="工具版本")


class ToolCall(BaseModel):
    """工具调用请求"""
    id: str = Field(..., description="调用唯一标识符")
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(..., description="调用参数")
    context: Optional[Dict[str, Any]] = Field(None, description="执行上下文")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    metadata: Dict[str, Any] = Field(default={}, description="调用元数据")


class ToolResult(BaseModel):
    """工具执行结果"""
    tool_call_id: str = Field(..., description="对应的工具调用ID")
    tool_name: str = Field(..., description="工具名称")
    success: bool = Field(..., description="执行是否成功")
    data: Any = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(..., description="执行耗时(秒)")
    timestamp: datetime = Field(default_factory=datetime.now, description="完成时间")
    metadata: Dict[str, Any] = Field(default={}, description="执行元数据")
    
    @classmethod
    def success_result(
        cls,
        tool_call_id: str,
        tool_name: str,
        data: Any,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ToolResult":
        """创建成功结果"""
        return cls(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            success=True,
            data=data,
            execution_time=execution_time,
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(
        cls,
        tool_call_id: str,
        tool_name: str,
        error: str,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ToolResult":
        """创建错误结果"""
        return cls(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            success=False,
            error=error,
            execution_time=execution_time,
            metadata=metadata or {}
        )


class Tool(ABC):
    """工具抽象基类"""
    
    def __init__(self):
        self._definition: Optional[ToolDefinition] = None
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """工具定义"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行工具
        
        Args:
            parameters: 执行参数
            context: 执行上下文
            
        Yields:
            ToolResult: 执行结果（支持流式输出）
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        验证参数
        
        Args:
            parameters: 待验证的参数
            
        Returns:
            bool: 验证是否通过
        """
        # 默认实现，子类可以重写
        return True
    
    def is_concurrency_safe(self, parameters: Dict[str, Any]) -> bool:
        """
        检查是否支持并发执行
        
        Args:
            parameters: 执行参数
            
        Returns:
            bool: 是否支持并发
        """
        return self.definition.is_concurrent_safe
    
    def check_permissions(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        权限检查
        
        Args:
            parameters: 执行参数
            context: 执行上下文
            
        Returns:
            bool: 权限检查是否通过
        """
        # 默认实现，子类可以重写
        return True
    
    def estimate_execution_time(self, parameters: Dict[str, Any]) -> float:
        """
        估算执行时间
        
        Args:
            parameters: 执行参数
            
        Returns:
            float: 预估时间(秒)
        """
        # 默认返回1秒，子类可以重写
        return 1.0


class ToolExecutionError(Exception):
    """工具执行异常"""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.parameters = parameters
        self.original_error = original_error


class ToolValidationError(Exception):
    """工具参数验证异常"""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        invalid_parameters: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.invalid_parameters = invalid_parameters


class ToolPermissionError(Exception):
    """工具权限异常"""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        required_permissions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.required_permissions = required_permissions
