"""
任务相关的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskComplexity(BaseModel):
    """任务复杂度分析结果"""
    score: int = Field(..., ge=1, le=10, description="复杂度评分(1-10)")
    needs_todo_list: bool = Field(..., description="是否需要分解为TodoList")
    estimated_steps: int = Field(..., ge=1, description="预估步骤数")
    required_tools: List[str] = Field(default=[], description="需要的工具类型")
    reasoning: str = Field(..., description="复杂度分析原因")


class TodoItem(BaseModel):
    """待办事项模型"""
    id: str = Field(..., description="唯一标识符")
    content: str = Field(..., description="任务内容描述")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    tools_needed: List[str] = Field(default=[], description="需要使用的工具名称")
    dependencies: List[str] = Field(default=[], description="依赖的其他TodoItem的ID")
    priority: int = Field(default=0, description="优先级(数字越大优先级越高)")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间(秒)")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始执行时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    metadata: Dict[str, Any] = Field(default={}, description="额外元数据")

    def mark_started(self) -> None:
        """标记任务开始"""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """标记任务完成"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self, reason: str = "") -> None:
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        if reason:
            self.metadata["failure_reason"] = reason

    @property
    def is_ready_to_execute(self) -> bool:
        """检查是否可以执行（所有依赖都已完成）"""
        return self.status == TaskStatus.PENDING

    @property
    def execution_duration(self) -> Optional[int]:
        """获取执行耗时（秒）"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class Task(BaseModel):
    """主任务模型"""
    id: str = Field(..., description="任务唯一标识符")
    query: str = Field(..., description="用户原始查询")
    description: str = Field(..., description="任务描述")
    complexity: Optional[TaskComplexity] = Field(None, description="复杂度分析")
    todo_list: List[TodoItem] = Field(default=[], description="分解后的待办事项")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="整体任务状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    metadata: Dict[str, Any] = Field(default={}, description="任务元数据")

    @property
    def pending_todos(self) -> List[TodoItem]:
        """获取待执行的TodoItem"""
        return [todo for todo in self.todo_list if todo.status == TaskStatus.PENDING]

    @property
    def completed_todos(self) -> List[TodoItem]:
        """获取已完成的TodoItem"""
        return [todo for todo in self.todo_list if todo.status == TaskStatus.COMPLETED]

    @property
    def progress_percentage(self) -> float:
        """获取任务完成百分比"""
        if not self.todo_list:
            return 0.0
        completed_count = len(self.completed_todos)
        return (completed_count / len(self.todo_list)) * 100

    def get_ready_todos(self) -> List[TodoItem]:
        """获取可以执行的TodoItem（依赖已满足）"""
        completed_ids = {todo.id for todo in self.completed_todos}
        ready_todos = []
        
        for todo in self.pending_todos:
            if all(dep_id in completed_ids for dep_id in todo.dependencies):
                ready_todos.append(todo)
        
        # 按优先级排序
        ready_todos.sort(key=lambda x: x.priority, reverse=True)
        return ready_todos

    def update_status(self) -> None:
        """根据TodoList状态更新整体任务状态"""
        if not self.todo_list:
            return
        
        if all(todo.status == TaskStatus.COMPLETED for todo in self.todo_list):
            self.status = TaskStatus.COMPLETED
            if not self.completed_at:
                self.completed_at = datetime.now()
        elif any(todo.status == TaskStatus.FAILED for todo in self.todo_list):
            self.status = TaskStatus.FAILED
        elif any(todo.status == TaskStatus.IN_PROGRESS for todo in self.todo_list):
            self.status = TaskStatus.IN_PROGRESS
            if not self.started_at:
                self.started_at = datetime.now()


class TaskResult(BaseModel):
    """任务执行结果"""
    type: str = Field(..., description="结果类型")
    data: Any = Field(..., description="结果数据")
    task_id: Optional[str] = Field(None, description="关联的任务ID")
    todo_id: Optional[str] = Field(None, description="关联的TodoItem ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    metadata: Dict[str, Any] = Field(default={}, description="额外元数据")

    class Config:
        """Pydantic配置"""
        use_enum_values = True
        extra = "allow"
