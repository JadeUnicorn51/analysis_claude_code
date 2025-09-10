"""
并发控制工具
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass
from contextlib import asynccontextmanager

from ..utils.logging import get_logger


@dataclass
class ConcurrencyLimits:
    """并发限制配置"""
    max_concurrent: int = 10
    timeout_seconds: float = 120.0
    backoff_factor: float = 1.5
    max_retries: int = 3


class ConcurrencyManager:
    """
    并发控制管理器
    
    提供智能的并发控制、超时管理、重试机制等功能
    """
    
    def __init__(self, limits: ConcurrencyLimits):
        self.limits = limits
        self.logger = get_logger(__name__)
        
        # 信号量控制并发数
        self.semaphore = asyncio.Semaphore(limits.max_concurrent)
        
        # 活跃任务跟踪
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # 性能统计
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'timeout_tasks': 0,
            'average_execution_time': 0.0
        }
    
    @asynccontextmanager
    async def controlled_execution(self, task_id: str):
        """
        受控执行上下文管理器
        
        Args:
            task_id: 任务ID
        """
        async with self.semaphore:
            start_time = time.time()
            self.stats['total_tasks'] += 1
            
            try:
                self.logger.debug(f"开始执行任务: {task_id}")
                yield
                
                execution_time = time.time() - start_time
                self.stats['completed_tasks'] += 1
                self._update_average_time(execution_time)
                
                self.logger.debug(f"任务执行完成: {task_id}, 耗时: {execution_time:.2f}秒")
                
            except asyncio.TimeoutError:
                self.stats['timeout_tasks'] += 1
                self.logger.warning(f"任务执行超时: {task_id}")
                raise
                
            except Exception as e:
                self.stats['failed_tasks'] += 1
                self.logger.error(f"任务执行失败: {task_id}, 错误: {str(e)}")
                raise
                
            finally:
                self.active_tasks.pop(task_id, None)
    
    async def execute_with_timeout(
        self,
        coro: Awaitable,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None
    ):
        """
        带超时的执行
        
        Args:
            coro: 协程对象
            timeout: 超时时间(秒)
            task_id: 任务ID
            
        Returns:
            执行结果
            
        Raises:
            asyncio.TimeoutError: 执行超时
        """
        timeout = timeout or self.limits.timeout_seconds
        task_id = task_id or f"task_{int(time.time() * 1000)}"
        
        async with self.controlled_execution(task_id):
            try:
                result = await asyncio.wait_for(coro, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                self.logger.warning(f"任务超时: {task_id}, 超时时间: {timeout}秒")
                raise
    
    async def execute_with_retry(
        self,
        coro_factory: Callable[[], Awaitable],
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        task_id: Optional[str] = None
    ):
        """
        带重试的执行
        
        Args:
            coro_factory: 协程工厂函数
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            task_id: 任务ID
            
        Returns:
            执行结果
            
        Raises:
            Exception: 重试次数用尽后的最后异常
        """
        max_retries = max_retries or self.limits.max_retries
        backoff_factor = backoff_factor or self.limits.backoff_factor
        task_id = task_id or f"retry_task_{int(time.time() * 1000)}"
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                coro = coro_factory()
                result = await self.execute_with_timeout(coro, task_id=f"{task_id}_attempt_{attempt}")
                
                if attempt > 0:
                    self.logger.info(f"任务重试成功: {task_id}, 重试次数: {attempt}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    delay = backoff_factor ** attempt
                    self.logger.warning(
                        f"任务执行失败，将重试: {task_id}, "
                        f"尝试次数: {attempt + 1}/{max_retries + 1}, "
                        f"错误: {str(e)}, "
                        f"延迟: {delay:.2f}秒"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"任务重试次数用尽: {task_id}, 最终错误: {str(e)}")
        
        raise last_exception
    
    async def execute_batch_parallel(
        self,
        coro_list: List[Awaitable],
        max_concurrent: Optional[int] = None,
        return_exceptions: bool = True
    ) -> List[Any]:
        """
        并发执行批量任务
        
        Args:
            coro_list: 协程列表
            max_concurrent: 最大并发数(可覆盖全局设置)
            return_exceptions: 是否返回异常而不是抛出
            
        Returns:
            List[Any]: 执行结果列表
        """
        if max_concurrent and max_concurrent != self.limits.max_concurrent:
            # 创建临时信号量
            temp_semaphore = asyncio.Semaphore(max_concurrent)
            
            async def controlled_coro(coro, idx):
                async with temp_semaphore:
                    task_id = f"batch_task_{idx}"
                    return await self.execute_with_timeout(coro, task_id=task_id)
            
            controlled_coros = [
                controlled_coro(coro, i) for i, coro in enumerate(coro_list)
            ]
        else:
            controlled_coros = [
                self.execute_with_timeout(coro, task_id=f"batch_task_{i}")
                for i, coro in enumerate(coro_list)
            ]
        
        self.logger.info(f"开始并发执行批量任务: {len(controlled_coros)} 个任务")
        
        if return_exceptions:
            results = await asyncio.gather(*controlled_coros, return_exceptions=True)
        else:
            results = await asyncio.gather(*controlled_coros)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        self.logger.info(f"批量任务执行完成: 成功 {success_count}/{len(results)}")
        
        return results
    
    async def execute_batch_sequential(
        self,
        coro_list: List[Awaitable],
        stop_on_error: bool = False
    ) -> List[Any]:
        """
        顺序执行批量任务
        
        Args:
            coro_list: 协程列表
            stop_on_error: 遇到错误是否停止
            
        Returns:
            List[Any]: 执行结果列表
        """
        results = []
        
        self.logger.info(f"开始顺序执行批量任务: {len(coro_list)} 个任务")
        
        for i, coro in enumerate(coro_list):
            try:
                task_id = f"sequential_task_{i}"
                result = await self.execute_with_timeout(coro, task_id=task_id)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"顺序任务执行失败: {i}, 错误: {str(e)}")
                
                if stop_on_error:
                    self.logger.info(f"因错误停止执行，已完成: {i}/{len(coro_list)}")
                    break
                else:
                    results.append(e)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        self.logger.info(f"顺序任务执行完成: 成功 {success_count}/{len(results)}")
        
        return results
    
    def cancel_all_tasks(self) -> int:
        """
        取消所有活跃任务
        
        Returns:
            int: 取消的任务数量
        """
        cancelled_count = 0
        
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()
                cancelled_count += 1
                self.logger.info(f"任务已取消: {task_id}")
        
        self.active_tasks.clear()
        self.logger.info(f"取消了 {cancelled_count} 个活跃任务")
        
        return cancelled_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            'active_tasks': len(self.active_tasks),
            'available_slots': self.semaphore._value,
            'success_rate': (
                self.stats['completed_tasks'] / max(self.stats['total_tasks'], 1) * 100
            )
        }
    
    def _update_average_time(self, execution_time: float) -> None:
        """更新平均执行时间"""
        completed = self.stats['completed_tasks']
        if completed == 1:
            self.stats['average_execution_time'] = execution_time
        else:
            # 移动平均
            current_avg = self.stats['average_execution_time']
            self.stats['average_execution_time'] = (
                (current_avg * (completed - 1) + execution_time) / completed
            )


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        初始化速率限制器
        
        Args:
            max_calls: 时间窗口内最大调用次数
            time_window: 时间窗口(秒)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        获取执行许可
        
        如果超过速率限制，会等待直到可以执行
        """
        async with self.lock:
            now = time.time()
            
            # 移除过期的调用记录
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.time_window]
            
            # 如果达到限制，等待
            if len(self.calls) >= self.max_calls:
                oldest_call = min(self.calls)
                wait_time = self.time_window - (now - oldest_call)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # 记录当前调用
            self.calls.append(now)
    
    @asynccontextmanager
    async def limit(self):
        """速率限制上下文管理器"""
        await self.acquire()
        yield
