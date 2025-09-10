"""
执行相关的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field

from utf.models.tool import ToolCall, ToolResult


class ExecutionStrategy(str, Enum):
    """执行策略枚举"""
    PARALLEL = "parallel"      # 并发执行
    SEQUENTIAL = "sequential"  # 串行执行
    MIXED = "mixed"           # 混合执行


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    COMPLETED = "completed"   # 执行完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"   # 已取消


class ToolExecutionBatch(BaseModel):
    """工具执行批次"""
    id: str = Field(..., description="批次ID")
    tool_calls: List[ToolCall] = Field(..., description="工具调用列表")
    strategy: ExecutionStrategy = Field(..., description="执行策略")
    is_concurrent_safe: bool = Field(..., description="是否并发安全")
    dependencies: List[str] = Field(default=[], description="依赖的批次ID")
    estimated_duration: float = Field(default=0.0, description="预估执行时间")


class ExecutionPlan(BaseModel):
    """执行计划"""
    id: str = Field(..., description="计划ID")
    task_id: str = Field(..., description="关联的任务ID")
    todo_id: Optional[str] = Field(None, description="关联的TodoItem ID")
    batches: List[ToolExecutionBatch] = Field(..., description="执行批次列表")
    total_estimated_duration: float = Field(default=0.0, description="总预估时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    metadata: Dict[str, Any] = Field(default={}, description="计划元数据")

    @property
    def total_tool_calls(self) -> int:
        """总工具调用数"""
        return sum(len(batch.tool_calls) for batch in self.batches)

    @property
    def parallel_batches(self) -> List[ToolExecutionBatch]:
        """并发执行的批次"""
        return [batch for batch in self.batches if batch.strategy == ExecutionStrategy.PARALLEL]

    @property
    def sequential_batches(self) -> List[ToolExecutionBatch]:
        """串行执行的批次"""
        return [batch for batch in self.batches if batch.strategy == ExecutionStrategy.SEQUENTIAL]

    def get_ready_batches(self, completed_batch_ids: Set[str]) -> List[ToolExecutionBatch]:
        """获取可执行的批次（依赖已满足）"""
        ready_batches = []
        for batch in self.batches:
            if all(dep_id in completed_batch_ids for dep_id in batch.dependencies):
                ready_batches.append(batch)
        return ready_batches


class ExecutionContext(BaseModel):
    """执行上下文"""
    session_id: str = Field(..., description="会话ID")
    task_id: str = Field(..., description="任务ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    working_directory: Optional[str] = Field(None, description="工作目录")
    environment_variables: Dict[str, str] = Field(default={}, description="环境变量")
    permissions: List[str] = Field(default=[], description="权限列表")
    max_execution_time: Optional[int] = Field(None, description="最大执行时间(秒)")
    allow_network_access: bool = Field(default=True, description="是否允许网络访问")
    allow_file_write: bool = Field(default=True, description="是否允许文件写入")
    metadata: Dict[str, Any] = Field(default={}, description="上下文元数据")

    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions

    def get_env_var(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        return self.environment_variables.get(key, default)


class ExecutionResult(BaseModel):
    """执行结果"""
    id: str = Field(..., description="结果ID")
    execution_plan_id: str = Field(..., description="关联的执行计划ID")
    batch_id: str = Field(..., description="批次ID")
    status: ExecutionStatus = Field(..., description="执行状态")
    tool_results: List[ToolResult] = Field(default=[], description="工具执行结果")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default={}, description="结果元数据")

    @property
    def execution_duration(self) -> Optional[float]:
        """执行耗时(秒)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """成功率"""
        if not self.tool_results:
            return 0.0
        successful_count = sum(1 for result in self.tool_results if result.success)
        return successful_count / len(self.tool_results)

    @property
    def failed_tools(self) -> List[ToolResult]:
        """失败的工具结果"""
        return [result for result in self.tool_results if not result.success]

    def mark_started(self) -> None:
        """标记开始执行"""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """标记执行完成"""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self, error_message: str) -> None:
        """标记执行失败"""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message


class UserInteractionEvent(BaseModel):
    """用户交互事件"""
    id: str = Field(..., description="事件ID")
    type: str = Field(..., description="事件类型")
    data: Any = Field(..., description="事件数据")
    task_id: str = Field(..., description="关联任务ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    response_required: bool = Field(default=False, description="是否需要用户响应")
    timeout_seconds: Optional[int] = Field(None, description="超时时间")


class UserInteractionResponse(BaseModel):
    """用户交互响应"""
    event_id: str = Field(..., description="对应的事件ID")
    action: str = Field(..., description="用户选择的动作")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
