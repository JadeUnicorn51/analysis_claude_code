"""
Universal Tool Framework (UTF)
基于Claude Code架构精华的通用工具调用框架

主要组件:
- UniversalTaskEngine: 核心任务执行引擎
- FrameworkConfig: 框架配置类
- BaseTool: 工具基类
- TaskResult: 任务结果类
"""

from utf.core.engine import UniversalTaskEngine
from utf.config.settings import FrameworkConfig
from utf.models.task import Task, TodoItem, TaskStatus, TaskResult
from utf.models.tool import ToolResult, ToolCall
from utf.tools.base import BaseTool

__version__ = "0.1.0"
__author__ = "UTF Development Team"
__license__ = "MIT"

__all__ = [
    "UniversalTaskEngine",
    "FrameworkConfig", 
    "BaseTool",
    "Task",
    "TodoItem",
    "TaskStatus",
    "TaskResult",
    "ToolResult",
    "ToolCall",
]
