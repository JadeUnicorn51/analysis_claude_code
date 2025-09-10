"""
工具生命周期管理

提供工具的注册、初始化、健康检查、卸载等生命周期管理功能
"""

import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from utf.models.tool import Tool, ToolDefinition
from utf.utils.logging import get_logger


class ToolState(Enum):
    """工具状态枚举"""
    UNREGISTERED = "unregistered"    # 未注册
    REGISTERED = "registered"        # 已注册
    INITIALIZING = "initializing"    # 初始化中
    READY = "ready"                 # 就绪
    BUSY = "busy"                   # 忙碌
    UNAVAILABLE = "unavailable"      # 不可用
    ERROR = "error"                 # 错误
    UNLOADING = "unloading"         # 卸载中
    UNLOADED = "unloaded"           # 已卸载


@dataclass
class ToolHealthStatus:
    """工具健康状态"""
    tool_name: str
    state: ToolState
    last_check_time: datetime
    response_time: float
    error_count: int
    success_count: int
    uptime: timedelta
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class ToolLifecycleEvent:
    """工具生命周期事件"""
    tool_name: str
    event_type: str
    timestamp: datetime
    old_state: Optional[ToolState]
    new_state: ToolState
    data: Dict[str, Any] = None


class ToolLifecycleManager:
    """
    工具生命周期管理器
    
    管理工具的完整生命周期，包括注册、初始化、监控、卸载等
    """
    
    def __init__(self, health_check_interval: int = 60):
        self.logger = get_logger(__name__)
        
        # 工具注册表
        self._tools: Dict[str, Tool] = {}
        self._tool_states: Dict[str, ToolState] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 健康状态
        self._health_status: Dict[str, ToolHealthStatus] = {}
        self._health_check_interval = health_check_interval
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 生命周期事件
        self._lifecycle_events: List[ToolLifecycleEvent] = []
        self._event_callbacks: List[Callable[[ToolLifecycleEvent], None]] = []
        
        # 工具依赖关系
        self._tool_dependencies: Dict[str, Set[str]] = {}
        self._reverse_dependencies: Dict[str, Set[str]] = {}
        
        # 并发控制
        self._tool_locks: Dict[str, asyncio.Lock] = {}
        
        self.logger.info("ToolLifecycleManager initialized")
    
    async def register_tool(
        self,
        tool: Tool,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        注册工具
        
        Args:
            tool: 工具实例
            dependencies: 依赖的其他工具名称
            metadata: 工具元数据
            
        Returns:
            bool: 注册是否成功
        """
        tool_name = tool.definition.name
        
        if tool_name in self._tools:
            self.logger.warning(f"工具已存在，将覆盖: {tool_name}")
        
        try:
            # 更新状态
            old_state = self._tool_states.get(tool_name)
            self._tool_states[tool_name] = ToolState.REGISTERED
            
            # 注册工具
            self._tools[tool_name] = tool
            self._tool_metadata[tool_name] = metadata or {}
            self._tool_locks[tool_name] = asyncio.Lock()
            
            # 处理依赖关系
            if dependencies:
                self._tool_dependencies[tool_name] = set(dependencies)
                for dep_name in dependencies:
                    if dep_name not in self._reverse_dependencies:
                        self._reverse_dependencies[dep_name] = set()
                    self._reverse_dependencies[dep_name].add(tool_name)
            
            # 创建健康状态记录
            self._health_status[tool_name] = ToolHealthStatus(
                tool_name=tool_name,
                state=ToolState.REGISTERED,
                last_check_time=datetime.now(),
                response_time=0.0,
                error_count=0,
                success_count=0,
                uptime=timedelta()
            )
            
            # 触发事件
            await self._emit_lifecycle_event(
                tool_name,
                "tool_registered",
                old_state,
                ToolState.REGISTERED,
                {"dependencies": dependencies, "metadata": metadata}
            )
            
            self.logger.info(f"工具已注册: {tool_name}")
            
            # 自动初始化
            await self.initialize_tool(tool_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"注册工具失败: {tool_name}, 错误: {e}")
            self._tool_states[tool_name] = ToolState.ERROR
            return False
    
    async def initialize_tool(self, tool_name: str) -> bool:
        """
        初始化工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 初始化是否成功
        """
        if tool_name not in self._tools:
            self.logger.error(f"工具未注册: {tool_name}")
            return False
        
        async with self._tool_locks[tool_name]:
            try:
                # 更新状态
                old_state = self._tool_states[tool_name]
                self._tool_states[tool_name] = ToolState.INITIALIZING
                
                await self._emit_lifecycle_event(
                    tool_name,
                    "tool_initializing",
                    old_state,
                    ToolState.INITIALIZING
                )
                
                # 检查依赖
                if not await self._check_dependencies(tool_name):
                    self._tool_states[tool_name] = ToolState.ERROR
                    return False
                
                # 执行初始化
                tool = self._tools[tool_name]
                if hasattr(tool, 'initialize'):
                    await tool.initialize()
                
                # 执行健康检查
                if await self._perform_health_check(tool_name):
                    self._tool_states[tool_name] = ToolState.READY
                    
                    await self._emit_lifecycle_event(
                        tool_name,
                        "tool_ready",
                        ToolState.INITIALIZING,
                        ToolState.READY
                    )
                    
                    self.logger.info(f"工具初始化成功: {tool_name}")
                    return True
                else:
                    self._tool_states[tool_name] = ToolState.ERROR
                    return False
                
            except Exception as e:
                self.logger.error(f"工具初始化失败: {tool_name}, 错误: {e}")
                self._tool_states[tool_name] = ToolState.ERROR
                
                await self._emit_lifecycle_event(
                    tool_name,
                    "tool_initialization_failed",
                    ToolState.INITIALIZING,
                    ToolState.ERROR,
                    {"error": str(e)}
                )
                
                return False
    
    async def unregister_tool(self, tool_name: str) -> bool:
        """
        卸载工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 卸载是否成功
        """
        if tool_name not in self._tools:
            self.logger.warning(f"工具未注册: {tool_name}")
            return True
        
        async with self._tool_locks[tool_name]:
            try:
                # 检查是否有其他工具依赖于此工具
                if tool_name in self._reverse_dependencies:
                    dependent_tools = self._reverse_dependencies[tool_name]
                    if dependent_tools:
                        self.logger.error(
                            f"无法卸载工具 {tool_name}，以下工具依赖于它: {dependent_tools}"
                        )
                        return False
                
                # 更新状态
                old_state = self._tool_states[tool_name]
                self._tool_states[tool_name] = ToolState.UNLOADING
                
                await self._emit_lifecycle_event(
                    tool_name,
                    "tool_unloading",
                    old_state,
                    ToolState.UNLOADING
                )
                
                # 执行清理
                tool = self._tools[tool_name]
                if hasattr(tool, 'cleanup'):
                    await tool.cleanup()
                
                # 清理数据
                del self._tools[tool_name]
                del self._tool_locks[tool_name]
                self._tool_states[tool_name] = ToolState.UNLOADED
                self._health_status.pop(tool_name, None)
                self._tool_metadata.pop(tool_name, None)
                
                # 清理依赖关系
                if tool_name in self._tool_dependencies:
                    for dep_name in self._tool_dependencies[tool_name]:
                        if dep_name in self._reverse_dependencies:
                            self._reverse_dependencies[dep_name].discard(tool_name)
                    del self._tool_dependencies[tool_name]
                
                if tool_name in self._reverse_dependencies:
                    del self._reverse_dependencies[tool_name]
                
                await self._emit_lifecycle_event(
                    tool_name,
                    "tool_unloaded",
                    ToolState.UNLOADING,
                    ToolState.UNLOADED
                )
                
                self.logger.info(f"工具已卸载: {tool_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"卸载工具失败: {tool_name}, 错误: {e}")
                self._tool_states[tool_name] = ToolState.ERROR
                return False
    
    async def get_tool_state(self, tool_name: str) -> Optional[ToolState]:
        """获取工具状态"""
        return self._tool_states.get(tool_name)
    
    async def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [
            name for name, state in self._tool_states.items()
            if state == ToolState.READY
        ]
    
    async def get_tool_health(self, tool_name: str) -> Optional[ToolHealthStatus]:
        """获取工具健康状态"""
        return self._health_status.get(tool_name)
    
    async def start_health_monitoring(self) -> None:
        """启动健康监控"""
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("健康监控已启动")
    
    async def stop_health_monitoring(self) -> None:
        """停止健康监控"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("健康监控已停止")
    
    async def force_health_check(self, tool_name: Optional[str] = None) -> Dict[str, bool]:
        """强制执行健康检查"""
        results = {}
        
        if tool_name:
            if tool_name in self._tools:
                results[tool_name] = await self._perform_health_check(tool_name)
        else:
            for name in self._tools.keys():
                results[name] = await self._perform_health_check(name)
        
        return results
    
    async def get_tool_dependencies(self, tool_name: str) -> Set[str]:
        """获取工具依赖"""
        return self._tool_dependencies.get(tool_name, set())
    
    async def get_dependent_tools(self, tool_name: str) -> Set[str]:
        """获取依赖此工具的其他工具"""
        return self._reverse_dependencies.get(tool_name, set())
    
    def add_lifecycle_callback(self, callback: Callable[[ToolLifecycleEvent], None]) -> None:
        """添加生命周期事件回调"""
        self._event_callbacks.append(callback)
    
    def get_lifecycle_events(
        self,
        tool_name: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ToolLifecycleEvent]:
        """获取生命周期事件"""
        events = self._lifecycle_events
        
        if tool_name:
            events = [e for e in events if e.tool_name == tool_name]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    async def _check_dependencies(self, tool_name: str) -> bool:
        """检查工具依赖"""
        dependencies = self._tool_dependencies.get(tool_name, set())
        
        for dep_name in dependencies:
            if dep_name not in self._tools:
                self.logger.error(f"依赖的工具未注册: {dep_name}")
                return False
            
            if self._tool_states.get(dep_name) != ToolState.READY:
                self.logger.error(f"依赖的工具未就绪: {dep_name}")
                return False
        
        return True
    
    async def _perform_health_check(self, tool_name: str) -> bool:
        """执行健康检查"""
        if tool_name not in self._tools:
            return False
        
        try:
            start_time = time.time()
            tool = self._tools[tool_name]
            
            # 执行健康检查
            is_healthy = True
            if hasattr(tool, 'health_check'):
                is_healthy = await tool.health_check()
            
            response_time = time.time() - start_time
            
            # 更新健康状态
            health_status = self._health_status[tool_name]
            health_status.last_check_time = datetime.now()
            health_status.response_time = response_time
            
            if is_healthy:
                health_status.success_count += 1
                if self._tool_states[tool_name] == ToolState.ERROR:
                    # 从错误状态恢复
                    self._tool_states[tool_name] = ToolState.READY
                    await self._emit_lifecycle_event(
                        tool_name,
                        "tool_recovered",
                        ToolState.ERROR,
                        ToolState.READY
                    )
            else:
                health_status.error_count += 1
                health_status.last_error = "健康检查失败"
                
                if self._tool_states[tool_name] == ToolState.READY:
                    self._tool_states[tool_name] = ToolState.UNAVAILABLE
                    await self._emit_lifecycle_event(
                        tool_name,
                        "tool_unhealthy",
                        ToolState.READY,
                        ToolState.UNAVAILABLE
                    )
            
            health_status.state = self._tool_states[tool_name]
            return is_healthy
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {tool_name}, 错误: {e}")
            
            # 更新健康状态
            health_status = self._health_status[tool_name]
            health_status.error_count += 1
            health_status.last_error = str(e)
            health_status.last_check_time = datetime.now()
            
            # 更新工具状态
            old_state = self._tool_states[tool_name]
            self._tool_states[tool_name] = ToolState.ERROR
            health_status.state = ToolState.ERROR
            
            await self._emit_lifecycle_event(
                tool_name,
                "tool_health_check_failed",
                old_state,
                ToolState.ERROR,
                {"error": str(e)}
            )
            
            return False
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # 对所有工具执行健康检查
                for tool_name in list(self._tools.keys()):
                    if self._tool_states.get(tool_name) in [ToolState.READY, ToolState.UNAVAILABLE, ToolState.ERROR]:
                        await self._perform_health_check(tool_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"健康检查循环异常: {e}")
    
    async def _emit_lifecycle_event(
        self,
        tool_name: str,
        event_type: str,
        old_state: Optional[ToolState],
        new_state: ToolState,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """发出生命周期事件"""
        event = ToolLifecycleEvent(
            tool_name=tool_name,
            event_type=event_type,
            timestamp=datetime.now(),
            old_state=old_state,
            new_state=new_state,
            data=data
        )
        
        # 保存事件
        self._lifecycle_events.append(event)
        
        # 限制事件历史长度
        if len(self._lifecycle_events) > 1000:
            self._lifecycle_events = self._lifecycle_events[-500:]
        
        # 触发回调
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"生命周期事件回调失败: {e}")
        
        self.logger.debug(f"生命周期事件: {tool_name} - {event_type}")
    
    def get_lifecycle_statistics(self) -> Dict[str, Any]:
        """获取生命周期统计"""
        tool_states = {}
        for state in ToolState:
            tool_states[state.value] = len([
                name for name, s in self._tool_states.items() if s == state
            ])
        
        health_summary = {
            'total_tools': len(self._tools),
            'healthy_tools': len([
                name for name, status in self._health_status.items()
                if status.state == ToolState.READY
            ]),
            'total_health_checks': sum(
                status.success_count + status.error_count
                for status in self._health_status.values()
            ),
            'total_errors': sum(
                status.error_count for status in self._health_status.values()
            )
        }
        
        return {
            'tool_states': tool_states,
            'health_summary': health_summary,
            'dependencies_count': len(self._tool_dependencies),
            'events_count': len(self._lifecycle_events)
        }


# 全局工具生命周期管理器实例
_global_tool_lifecycle_manager = None

def get_tool_lifecycle_manager() -> ToolLifecycleManager:
    """获取全局工具生命周期管理器"""
    global _global_tool_lifecycle_manager
    if _global_tool_lifecycle_manager is None:
        _global_tool_lifecycle_manager = ToolLifecycleManager()
    return _global_tool_lifecycle_manager
