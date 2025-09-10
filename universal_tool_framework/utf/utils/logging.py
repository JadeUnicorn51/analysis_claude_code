"""
日志工具模块
"""

import logging
import logging.handlers
import sys
from typing import Optional
from pathlib import Path

from utf.config.settings import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """
    设置日志系统
    
    Args:
        config: 日志配置
    """
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式器
    formatter = logging.Formatter(config.format)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if config.enable_file_logging:
        log_file_path = Path(config.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 结构化日志
    if config.enable_structured_logging:
        try:
            import structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        except ImportError:
            pass  # structlog not installed


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 日志器实例
    """
    return logging.getLogger(name)


class UTFLogger:
    """UTF框架专用日志器包装类"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.name = name
    
    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """错误日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """严重错误日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs) -> None:
        """内部日志方法"""
        extra = {}
        if kwargs:
            extra['extra_data'] = kwargs
        
        self.logger.log(level, f"[UTF] {message}", extra=extra)
    
    def log_tool_execution(
        self,
        tool_name: str,
        parameters: dict,
        execution_time: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """记录工具执行日志"""
        log_data = {
            'tool_name': tool_name,
            'parameters': parameters,
            'execution_time': execution_time,
            'success': success
        }
        
        if error:
            log_data['error'] = error
            self.error(f"工具执行失败: {tool_name}", **log_data)
        else:
            self.info(f"工具执行成功: {tool_name}", **log_data)
    
    def log_task_progress(
        self,
        task_id: str,
        todo_id: Optional[str],
        progress: float,
        message: str
    ) -> None:
        """记录任务进度日志"""
        self.info(
            f"任务进度更新: {message}",
            task_id=task_id,
            todo_id=todo_id,
            progress=progress
        )
    
    def log_user_interaction(
        self,
        event_type: str,
        task_id: str,
        action: Optional[str] = None,
        response_time: Optional[float] = None
    ) -> None:
        """记录用户交互日志"""
        self.info(
            f"用户交互: {event_type}",
            task_id=task_id,
            action=action,
            response_time=response_time
        )
