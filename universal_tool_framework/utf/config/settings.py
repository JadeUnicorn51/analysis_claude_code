"""
框架配置管理
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from utf.models.tool import Tool


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="mock", description="LLM提供商")
    model: str = Field(default="mock-gpt-4", description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大tokens")
    timeout: float = Field(default=30.0, description="请求超时时间")


class SecurityConfig(BaseModel):
    """安全配置"""
    enable_permission_check: bool = Field(default=True, description="启用权限检查")
    enable_parameter_validation: bool = Field(default=True, description="启用参数验证")
    sandbox_mode: bool = Field(default=False, description="沙箱模式")
    max_execution_time: int = Field(default=300, description="最大执行时间(秒)")
    allowed_file_extensions: List[str] = Field(
        default=[".txt", ".json", ".yaml", ".yml", ".md", ".py"],
        description="允许的文件扩展名"
    )
    blocked_commands: List[str] = Field(
        default=["rm", "del", "format", "fdisk"],
        description="禁止的命令"
    )
    audit_level: str = Field(default="basic", description="审计级别: basic, detailed, full")


class ConcurrencyConfig(BaseModel):
    """并发配置"""
    max_parallel_tools: int = Field(default=10, description="最大并发工具数")
    max_parallel_batches: int = Field(default=3, description="最大并发批次数")
    tool_timeout_seconds: int = Field(default=120, description="单个工具超时时间")
    batch_timeout_seconds: int = Field(default=600, description="批次超时时间")
    enable_smart_scheduling: bool = Field(default=True, description="启用智能调度")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    enable_file_logging: bool = Field(default=True, description="启用文件日志")
    log_file: str = Field(default="utf.log", description="日志文件路径")
    max_file_size: int = Field(default=10485760, description="日志文件最大大小(字节)")
    backup_count: int = Field(default=5, description="日志文件备份数量")
    enable_structured_logging: bool = Field(default=True, description="启用结构化日志")


class InteractionConfig(BaseModel):
    """交互配置"""
    allow_user_interruption: bool = Field(default=True, description="允许用户中断")
    progress_update_interval: float = Field(default=1.0, description="进度更新间隔(秒)")
    confirmation_required: bool = Field(default=False, description="需要用户确认")
    auto_continue_simple_tasks: bool = Field(default=True, description="简单任务自动继续")
    user_response_timeout: int = Field(default=300, description="用户响应超时(秒)")


class TaskConfig(BaseModel):
    """任务配置"""
    complexity_threshold: int = Field(default=3, description="复杂度阈值")
    max_todo_items: int = Field(default=20, description="最大TodoItem数量")
    enable_auto_decomposition: bool = Field(default=True, description="启用自动分解")
    enable_dependency_analysis: bool = Field(default=True, description="启用依赖分析")
    retry_failed_todos: bool = Field(default=True, description="重试失败的TodoItem")
    max_retry_attempts: int = Field(default=3, description="最大重试次数")


class FrameworkConfig(BaseSettings):
    """框架主配置类"""
    
    # 基础配置
    name: str = Field(default="UTF", description="框架名称")
    version: str = Field(default="0.1.0", description="框架版本")
    debug: bool = Field(default=False, description="调试模式")
    
    # 工具配置
    tools: List[Tool] = Field(default=[], description="可用工具列表")
    enable_mcp_tools: bool = Field(default=False, description="启用MCP工具")
    
    # AI配置
    llm_config: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    
    # 子配置
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="安全配置")
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig, description="并发配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")
    interaction: InteractionConfig = Field(default_factory=InteractionConfig, description="交互配置")
    task: TaskConfig = Field(default_factory=TaskConfig, description="任务配置")
    
    # 扩展配置
    extensions: Dict[str, Any] = Field(default={}, description="扩展配置")
    
    class Config:
        """Pydantic配置"""
        env_prefix = "UTF_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"
    
    def add_tool(self, tool: Tool) -> None:
        """添加工具"""
        if tool not in self.tools:
            self.tools.append(tool)
    
    def remove_tool(self, tool_name: str) -> None:
        """移除工具"""
        self.tools = [tool for tool in self.tools if tool.definition.name != tool_name]
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        for tool in self.tools:
            if tool.definition.name == tool_name:
                return tool
        return None
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return [tool.definition.name for tool in self.tools]
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        # 验证工具名称唯一性
        tool_names = self.get_tool_names()
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("工具名称必须唯一")
        
        # 验证并发配置
        if self.concurrency.max_parallel_tools <= 0:
            raise ValueError("最大并发工具数必须大于0")
        
        # 验证超时配置
        if self.security.max_execution_time <= 0:
            raise ValueError("最大执行时间必须大于0")
        
        return True
    
    @classmethod
    def create_default(cls) -> "FrameworkConfig":
        """创建默认配置"""
        return cls()
    
    @classmethod
    def from_file(cls, file_path: str) -> "FrameworkConfig":
        """从文件加载配置"""
        import yaml
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def save_to_file(self, file_path: str) -> None:
        """保存配置到文件"""
        import yaml
        
        config_dict = self.to_dict()
        # 移除不可序列化的对象
        config_dict.pop('tools', None)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
