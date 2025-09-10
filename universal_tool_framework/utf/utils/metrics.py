"""
性能监控和指标收集系统

提供全面的性能监控、指标收集和分析功能
"""

import time
import psutil
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager

from ..utils.logging import get_logger


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """指标摘要"""
    name: str
    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float
    recent_points: List[MetricPoint]


class MetricsCollector:
    """
    指标收集器
    
    收集和存储各种性能指标
    """
    
    def __init__(self, max_points_per_metric: int = 10000):
        self.logger = get_logger(__name__)
        self.max_points = max_points_per_metric
        
        # 指标存储
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_points))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        
        # 系统指标
        self._system_metrics = SystemMetricsCollector()
        
        # 指标锁
        self._lock = threading.RLock()
        
        self.logger.info("MetricsCollector initialized")
    
    def record_timing(
        self,
        name: str,
        duration: float,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录时间指标"""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=duration,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        with self._lock:
            self._metrics[f"timing.{name}"].append(point)
    
    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """增加计数器"""
        with self._lock:
            self._counters[name] += value
            
            # 同时记录为时间序列
            point = MetricPoint(
                timestamp=datetime.now(),
                value=self._counters[name],
                tags=tags or {}
            )
            self._metrics[f"counter.{name}"].append(point)
    
    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """设置仪表值"""
        with self._lock:
            self._gauges[name] = value
            
            point = MetricPoint(
                timestamp=datetime.now(),
                value=value,
                tags=tags or {}
            )
            self._metrics[f"gauge.{name}"].append(point)
    
    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """记录直方图数据"""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            tags=tags or {}
        )
        
        with self._lock:
            self._metrics[f"histogram.{name}"].append(point)
    
    def get_metric_summary(
        self,
        name: str,
        since: Optional[datetime] = None
    ) -> Optional[MetricSummary]:
        """获取指标摘要"""
        with self._lock:
            if name not in self._metrics:
                return None
            
            points = list(self._metrics[name])
            
            # 过滤时间范围
            if since:
                points = [p for p in points if p.timestamp >= since]
            
            if not points:
                return None
            
            values = [p.value for p in points]
            values.sort()
            
            count = len(values)
            sum_val = sum(values)
            min_val = min(values)
            max_val = max(values)
            avg_val = sum_val / count
            
            # 计算百分位数
            p50_idx = int(count * 0.50)
            p95_idx = int(count * 0.95)
            p99_idx = int(count * 0.99)
            
            p50 = values[min(p50_idx, count - 1)]
            p95 = values[min(p95_idx, count - 1)]
            p99 = values[min(p99_idx, count - 1)]
            
            return MetricSummary(
                name=name,
                count=count,
                sum=sum_val,
                min=min_val,
                max=max_val,
                avg=avg_val,
                p50=p50,
                p95=p95,
                p99=p99,
                recent_points=points[-100:]  # 最近100个点
            )
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'metrics_count': {name: len(points) for name, points in self._metrics.items()},
                'system_metrics': self._system_metrics.get_current_metrics()
            }
    
    def clear_metrics(self, older_than: Optional[datetime] = None) -> int:
        """清理旧指标"""
        if older_than is None:
            older_than = datetime.now() - timedelta(hours=24)
        
        cleared_count = 0
        
        with self._lock:
            for name, points in self._metrics.items():
                original_count = len(points)
                
                # 过滤掉旧数据
                filtered_points = deque(
                    [p for p in points if p.timestamp >= older_than],
                    maxlen=self.max_points
                )
                
                self._metrics[name] = filtered_points
                cleared_count += original_count - len(filtered_points)
        
        self.logger.info(f"清理了 {cleared_count} 个旧指标数据点")
        return cleared_count


class SystemMetricsCollector:
    """系统指标收集器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络统计
            network = psutil.net_io_counters()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            }
        
        except Exception as e:
            self.logger.error(f"获取系统指标失败: {e}")
            return {}


class PerformanceMonitor:
    """
    性能监控器
    
    提供性能监控的高级接口和自动化功能
    """
    
    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.logger = get_logger(__name__)
        self.collector = collector or MetricsCollector()
        
        # 性能阈值
        self.thresholds = {
            'task_execution_time': 30.0,  # 任务执行时间阈值(秒)
            'tool_execution_time': 10.0,  # 工具执行时间阈值(秒)
            'memory_usage_percent': 80.0,  # 内存使用率阈值
            'cpu_usage_percent': 80.0,     # CPU使用率阈值
        }
        
        # 告警回调
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        self.logger.info("PerformanceMonitor initialized")
    
    @contextmanager
    def measure_execution(
        self,
        operation_name: str,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """测量执行时间的上下文管理器"""
        start_time = time.time()
        operation_tags = tags or {}
        operation_metadata = metadata or {}
        
        try:
            yield
            
            # 记录成功执行
            self.collector.increment_counter(
                f"{operation_name}.success",
                tags=operation_tags
            )
            
        except Exception as e:
            # 记录失败执行
            self.collector.increment_counter(
                f"{operation_name}.error",
                tags={**operation_tags, 'error_type': type(e).__name__}
            )
            
            operation_metadata['error'] = str(e)
            raise
            
        finally:
            # 记录执行时间
            duration = time.time() - start_time
            self.collector.record_timing(
                operation_name,
                duration,
                tags=operation_tags,
                metadata=operation_metadata
            )
            
            # 检查性能阈值
            self._check_performance_threshold(operation_name, duration)
    
    def monitor_task_execution(
        self,
        task_id: str,
        task_type: str = "unknown"
    ):
        """监控任务执行"""
        return self.measure_execution(
            "task_execution",
            tags={
                'task_id': task_id,
                'task_type': task_type
            }
        )
    
    def monitor_tool_execution(
        self,
        tool_name: str,
        task_id: Optional[str] = None
    ):
        """监控工具执行"""
        tags = {'tool_name': tool_name}
        if task_id:
            tags['task_id'] = task_id
        
        return self.measure_execution(
            "tool_execution",
            tags=tags
        )
    
    def record_user_interaction(
        self,
        interaction_type: str,
        response_time: Optional[float] = None
    ) -> None:
        """记录用户交互"""
        self.collector.increment_counter(
            "user_interaction",
            tags={'type': interaction_type}
        )
        
        if response_time is not None:
            self.collector.record_timing(
                "user_response_time",
                response_time,
                tags={'type': interaction_type}
            )
    
    def record_concurrency_metrics(
        self,
        active_tasks: int,
        active_tools: int,
        queue_size: int
    ) -> None:
        """记录并发指标"""
        self.collector.set_gauge("active_tasks", active_tasks)
        self.collector.set_gauge("active_tools", active_tools)
        self.collector.set_gauge("queue_size", queue_size)
    
    def record_resource_usage(self) -> None:
        """记录资源使用情况"""
        system_metrics = self.collector._system_metrics.get_current_metrics()
        
        if system_metrics:
            # CPU指标
            if 'cpu' in system_metrics:
                cpu_percent = system_metrics['cpu'].get('percent', 0)
                self.collector.set_gauge("cpu_usage_percent", cpu_percent)
                self._check_resource_threshold("cpu_usage_percent", cpu_percent)
            
            # 内存指标
            if 'memory' in system_metrics:
                memory_percent = system_metrics['memory'].get('percent', 0)
                self.collector.set_gauge("memory_usage_percent", memory_percent)
                self._check_resource_threshold("memory_usage_percent", memory_percent)
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
    
    def _check_performance_threshold(self, operation: str, duration: float) -> None:
        """检查性能阈值"""
        threshold_key = f"{operation}_time"
        if threshold_key in self.thresholds:
            threshold = self.thresholds[threshold_key]
            if duration > threshold:
                self._trigger_alert(
                    f"performance_threshold_exceeded",
                    {
                        'operation': operation,
                        'duration': duration,
                        'threshold': threshold,
                        'severity': 'warning'
                    }
                )
    
    def _check_resource_threshold(self, resource: str, value: float) -> None:
        """检查资源使用阈值"""
        if resource in self.thresholds:
            threshold = self.thresholds[resource]
            if value > threshold:
                self._trigger_alert(
                    f"resource_threshold_exceeded",
                    {
                        'resource': resource,
                        'value': value,
                        'threshold': threshold,
                        'severity': 'warning'
                    }
                )
    
    def _trigger_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """触发告警"""
        self.logger.warning(f"性能告警: {alert_type}, 数据: {data}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, data)
            except Exception as e:
                self.logger.error(f"告警回调执行失败: {e}")
    
    def get_performance_report(self, hours: int = 1) -> Dict[str, Any]:
        """生成性能报告"""
        since = datetime.now() - timedelta(hours=hours)
        
        report = {
            'time_range': {
                'start': since.isoformat(),
                'end': datetime.now().isoformat(),
                'hours': hours
            },
            'task_metrics': {},
            'tool_metrics': {},
            'system_metrics': self.collector._system_metrics.get_current_metrics(),
            'resource_metrics': {}
        }
        
        # 任务执行指标
        task_summary = self.collector.get_metric_summary("timing.task_execution", since)
        if task_summary:
            report['task_metrics'] = {
                'total_executions': task_summary.count,
                'avg_duration': task_summary.avg,
                'p95_duration': task_summary.p95,
                'max_duration': task_summary.max
            }
        
        # 工具执行指标
        tool_summary = self.collector.get_metric_summary("timing.tool_execution", since)
        if tool_summary:
            report['tool_metrics'] = {
                'total_executions': tool_summary.count,
                'avg_duration': tool_summary.avg,
                'p95_duration': tool_summary.p95,
                'max_duration': tool_summary.max
            }
        
        return report


# 全局性能监控器实例
_global_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor
