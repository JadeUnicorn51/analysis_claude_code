"""
错误恢复和故障转移机制

提供完善的错误处理、恢复策略和故障转移功能
"""

import asyncio
import time
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..models.task import Task, TodoItem, TaskStatus
from ..models.tool import ToolResult
from ..utils.logging import get_logger


class ErrorType(Enum):
    """错误类型枚举"""
    VALIDATION_ERROR = "validation_error"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    FILE_ERROR = "file_error"
    TOOL_ERROR = "tool_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    RETRY = "retry"              # 重试
    FALLBACK = "fallback"        # 降级
    SKIP = "skip"                # 跳过
    ABORT = "abort"              # 中止
    MANUAL = "manual"            # 手动处理


@dataclass
class ErrorPattern:
    """错误模式定义"""
    error_type: ErrorType
    keywords: List[str]
    recovery_strategy: RecoveryStrategy
    max_retries: int = 3
    backoff_factor: float = 1.5
    timeout_seconds: float = 30.0
    fallback_action: Optional[str] = None


@dataclass
class RecoveryContext:
    """恢复上下文"""
    task_id: str
    todo_id: Optional[str]
    tool_name: str
    error: Exception
    error_type: ErrorType
    attempt_count: int
    max_attempts: int
    started_at: datetime
    metadata: Dict[str, Any]


class ErrorRecoveryManager:
    """
    错误恢复管理器
    
    提供智能的错误分类、恢复策略选择和执行
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 错误模式库
        self._error_patterns = self._init_error_patterns()
        
        # 恢复历史记录
        self._recovery_history: Dict[str, List[RecoveryContext]] = {}
        
        # 错误统计
        self._error_stats = {
            'total_errors': 0,
            'recovered_errors': 0,
            'failed_recoveries': 0,
            'error_types': {},
            'recovery_strategies': {}
        }
        
        # 熔断器状态
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("ErrorRecoveryManager initialized")
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理错误的主入口
        
        Args:
            error: 发生的异常
            context: 错误上下文
            
        Returns:
            Dict[str, Any]: 恢复结果
        """
        self._error_stats['total_errors'] += 1
        
        # 分类错误
        error_type = self._classify_error(error)
        
        # 创建恢复上下文
        recovery_context = RecoveryContext(
            task_id=context.get('task_id', 'unknown'),
            todo_id=context.get('todo_id'),
            tool_name=context.get('tool_name', 'unknown'),
            error=error,
            error_type=error_type,
            attempt_count=context.get('attempt_count', 1),
            max_attempts=context.get('max_attempts', 3),
            started_at=datetime.now(),
            metadata=context
        )
        
        # 记录错误
        self._record_error(recovery_context)
        
        # 检查熔断器
        if await self._check_circuit_breaker(recovery_context):
            return {
                'action': 'circuit_breaker_open',
                'message': f"熔断器开启，停止执行 {recovery_context.tool_name}",
                'should_continue': False
            }
        
        # 选择恢复策略
        strategy = self._select_recovery_strategy(recovery_context)
        
        # 执行恢复
        recovery_result = await self._execute_recovery(recovery_context, strategy)
        
        # 更新统计
        if recovery_result.get('success', False):
            self._error_stats['recovered_errors'] += 1
        else:
            self._error_stats['failed_recoveries'] += 1
        
        return recovery_result
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # 根据异常类型分类
        if isinstance(error, TimeoutError) or 'timeout' in error_message:
            return ErrorType.TIMEOUT_ERROR
        
        elif isinstance(error, PermissionError) or 'permission' in error_message:
            return ErrorType.PERMISSION_ERROR
        
        elif isinstance(error, (FileNotFoundError, IsADirectoryError, OSError)):
            return ErrorType.FILE_ERROR
        
        elif isinstance(error, (ConnectionError, TimeoutError)) or 'network' in error_message:
            return ErrorType.NETWORK_ERROR
        
        elif 'validation' in error_message or 'invalid' in error_message:
            return ErrorType.VALIDATION_ERROR
        
        # 根据错误模式匹配
        for pattern in self._error_patterns:
            if any(keyword in error_message for keyword in pattern.keywords):
                return pattern.error_type
        
        return ErrorType.UNKNOWN_ERROR
    
    def _select_recovery_strategy(self, context: RecoveryContext) -> RecoveryStrategy:
        """选择恢复策略"""
        
        # 查找匹配的错误模式
        for pattern in self._error_patterns:
            if pattern.error_type == context.error_type:
                # 检查重试次数
                if context.attempt_count >= pattern.max_retries:
                    if pattern.fallback_action:
                        return RecoveryStrategy.FALLBACK
                    else:
                        return RecoveryStrategy.ABORT
                
                return pattern.recovery_strategy
        
        # 默认策略
        if context.attempt_count < 3:
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.ABORT
    
    async def _execute_recovery(
        self,
        context: RecoveryContext,
        strategy: RecoveryStrategy
    ) -> Dict[str, Any]:
        """执行恢复策略"""
        
        self.logger.info(
            f"执行恢复策略: {strategy.value}, "
            f"错误类型: {context.error_type.value}, "
            f"尝试次数: {context.attempt_count}"
        )
        
        if strategy == RecoveryStrategy.RETRY:
            return await self._handle_retry(context)
        
        elif strategy == RecoveryStrategy.FALLBACK:
            return await self._handle_fallback(context)
        
        elif strategy == RecoveryStrategy.SKIP:
            return await self._handle_skip(context)
        
        elif strategy == RecoveryStrategy.ABORT:
            return await self._handle_abort(context)
        
        elif strategy == RecoveryStrategy.MANUAL:
            return await self._handle_manual(context)
        
        else:
            return {
                'action': 'unknown_strategy',
                'success': False,
                'message': f"未知的恢复策略: {strategy}"
            }
    
    async def _handle_retry(self, context: RecoveryContext) -> Dict[str, Any]:
        """处理重试策略"""
        
        # 计算延迟时间
        delay = self._calculate_backoff_delay(context.attempt_count)
        
        self.logger.warning(
            f"准备重试: {context.tool_name}, "
            f"延迟 {delay:.2f} 秒, "
            f"尝试 {context.attempt_count + 1}/{context.max_attempts}"
        )
        
        if delay > 0:
            await asyncio.sleep(delay)
        
        return {
            'action': 'retry',
            'success': True,
            'delay': delay,
            'next_attempt': context.attempt_count + 1,
            'message': f"将在 {delay:.2f} 秒后重试"
        }
    
    async def _handle_fallback(self, context: RecoveryContext) -> Dict[str, Any]:
        """处理降级策略"""
        
        self.logger.warning(f"执行降级处理: {context.tool_name}")
        
        # 这里可以实现具体的降级逻辑
        fallback_result = {
            'action': 'fallback',
            'success': True,
            'message': f"已切换到降级模式处理 {context.tool_name}",
            'fallback_data': {
                'original_error': str(context.error),
                'fallback_action': 'use_default_behavior'
            }
        }
        
        return fallback_result
    
    async def _handle_skip(self, context: RecoveryContext) -> Dict[str, Any]:
        """处理跳过策略"""
        
        self.logger.warning(f"跳过执行: {context.tool_name}")
        
        return {
            'action': 'skip',
            'success': True,
            'message': f"已跳过 {context.tool_name} 的执行",
            'skipped_reason': str(context.error)
        }
    
    async def _handle_abort(self, context: RecoveryContext) -> Dict[str, Any]:
        """处理中止策略"""
        
        self.logger.error(f"中止执行: {context.tool_name}, 错误: {context.error}")
        
        return {
            'action': 'abort',
            'success': False,
            'message': f"无法恢复，中止执行 {context.tool_name}",
            'final_error': str(context.error),
            'should_continue': False
        }
    
    async def _handle_manual(self, context: RecoveryContext) -> Dict[str, Any]:
        """处理手动干预策略"""
        
        self.logger.warning(f"需要手动干预: {context.tool_name}")
        
        return {
            'action': 'manual_intervention_required',
            'success': False,
            'message': f"需要手动处理 {context.tool_name} 的错误",
            'error_details': {
                'error_type': context.error_type.value,
                'error_message': str(context.error),
                'suggestions': self._get_manual_suggestions(context)
            }
        }
    
    def _calculate_backoff_delay(self, attempt_count: int) -> float:
        """计算退避延迟时间"""
        base_delay = 1.0
        max_delay = 30.0
        backoff_factor = 1.5
        
        delay = base_delay * (backoff_factor ** (attempt_count - 1))
        return min(delay, max_delay)
    
    async def _check_circuit_breaker(self, context: RecoveryContext) -> bool:
        """检查熔断器状态"""
        tool_name = context.tool_name
        
        if tool_name not in self._circuit_breakers:
            self._circuit_breakers[tool_name] = {
                'failure_count': 0,
                'last_failure_time': None,
                'state': 'closed',  # closed, open, half_open
                'threshold': 5,
                'timeout': 60  # 秒
            }
        
        circuit = self._circuit_breakers[tool_name]
        
        # 更新失败计数
        circuit['failure_count'] += 1
        circuit['last_failure_time'] = datetime.now()
        
        # 检查是否需要开启熔断器
        if circuit['failure_count'] >= circuit['threshold']:
            if circuit['state'] == 'closed':
                circuit['state'] = 'open'
                self.logger.warning(f"熔断器开启: {tool_name}")
                return True
        
        # 检查是否可以半开
        if circuit['state'] == 'open':
            if circuit['last_failure_time']:
                elapsed = (datetime.now() - circuit['last_failure_time']).total_seconds()
                if elapsed >= circuit['timeout']:
                    circuit['state'] = 'half_open'
                    self.logger.info(f"熔断器半开: {tool_name}")
                    return False
            return True
        
        return False
    
    def _record_error(self, context: RecoveryContext) -> None:
        """记录错误信息"""
        task_id = context.task_id
        
        if task_id not in self._recovery_history:
            self._recovery_history[task_id] = []
        
        self._recovery_history[task_id].append(context)
        
        # 更新错误类型统计
        error_type = context.error_type.value
        if error_type not in self._error_stats['error_types']:
            self._error_stats['error_types'][error_type] = 0
        self._error_stats['error_types'][error_type] += 1
    
    def _get_manual_suggestions(self, context: RecoveryContext) -> List[str]:
        """获取手动处理建议"""
        suggestions = []
        
        if context.error_type == ErrorType.PERMISSION_ERROR:
            suggestions.extend([
                "检查文件或目录权限",
                "确认用户具有必要的访问权限",
                "尝试以管理员身份运行"
            ])
        
        elif context.error_type == ErrorType.FILE_ERROR:
            suggestions.extend([
                "检查文件是否存在",
                "确认文件路径正确",
                "检查磁盘空间是否充足"
            ])
        
        elif context.error_type == ErrorType.NETWORK_ERROR:
            suggestions.extend([
                "检查网络连接",
                "确认目标服务可用",
                "检查防火墙设置"
            ])
        
        elif context.error_type == ErrorType.TIMEOUT_ERROR:
            suggestions.extend([
                "增加超时时间",
                "检查系统资源使用情况",
                "优化处理逻辑"
            ])
        
        else:
            suggestions.extend([
                "查看详细错误日志",
                "检查输入参数",
                "联系技术支持"
            ])
        
        return suggestions
    
    def _init_error_patterns(self) -> List[ErrorPattern]:
        """初始化错误模式"""
        return [
            ErrorPattern(
                error_type=ErrorType.TIMEOUT_ERROR,
                keywords=['timeout', 'timed out', '超时'],
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                backoff_factor=2.0
            ),
            ErrorPattern(
                error_type=ErrorType.NETWORK_ERROR,
                keywords=['connection', 'network', 'unreachable', '网络'],
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=2,
                backoff_factor=1.5
            ),
            ErrorPattern(
                error_type=ErrorType.PERMISSION_ERROR,
                keywords=['permission', 'access denied', 'forbidden', '权限'],
                recovery_strategy=RecoveryStrategy.MANUAL,
                max_retries=1
            ),
            ErrorPattern(
                error_type=ErrorType.FILE_ERROR,
                keywords=['file not found', 'no such file', '文件不存在'],
                recovery_strategy=RecoveryStrategy.FALLBACK,
                max_retries=1,
                fallback_action='create_default_file'
            ),
            ErrorPattern(
                error_type=ErrorType.VALIDATION_ERROR,
                keywords=['validation', 'invalid', '无效', '验证失败'],
                recovery_strategy=RecoveryStrategy.ABORT,
                max_retries=0
            )
        ]
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        return {
            **self._error_stats,
            'success_rate': (
                self._error_stats['recovered_errors'] / 
                max(self._error_stats['total_errors'], 1) * 100
            ),
            'active_circuit_breakers': len([
                name for name, circuit in self._circuit_breakers.items()
                if circuit['state'] != 'closed'
            ])
        }
    
    def reset_circuit_breaker(self, tool_name: str) -> bool:
        """重置熔断器"""
        if tool_name in self._circuit_breakers:
            self._circuit_breakers[tool_name].update({
                'failure_count': 0,
                'state': 'closed',
                'last_failure_time': None
            })
            self.logger.info(f"熔断器已重置: {tool_name}")
            return True
        return False


# 全局错误恢复管理器实例
_global_error_recovery_manager = None

def get_error_recovery_manager() -> ErrorRecoveryManager:
    """获取全局错误恢复管理器"""
    global _global_error_recovery_manager
    if _global_error_recovery_manager is None:
        _global_error_recovery_manager = ErrorRecoveryManager()
    return _global_error_recovery_manager
