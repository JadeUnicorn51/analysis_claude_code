# Universal Tool Framework (UTF) - 快速开始指南

## 🎯 项目简介

Universal Tool Framework (UTF) 是基于Claude Code架构精华提取的通用工具调用框架。它实现了完整的"问题→规划→工具执行→结果"闭环流程，支持用户中断、任务分解、智能工具选择和并发执行。

### 核心特性

- ✨ **智能任务分解**: 自动将复杂任务分解为可执行的Todo步骤
- 🔧 **工具智能选择**: 基于任务需求自动选择最适合的工具
- 🤝 **用户交互控制**: 支持实时中断、修改计划、进度查看
- ⚡ **并发执行优化**: 智能识别可并发工具，优化执行效率
- 🌊 **事件驱动架构**: 基于异步生成器的流式处理
- 🔌 **可扩展设计**: 标准化工具接口，易于添加新工具

## 🚀 快速开始

### 1. 环境准备

确保您的Python版本 >= 3.8：

```bash
python --version
```

### 2. 安装依赖

```bash
cd universal_tool_framework
pip install -r requirements.txt
```

### 3. 运行示例

#### 方式一：快速演示
```bash
python run_example.py
```

#### 方式二：交互式CLI
```bash
python start.py
```

#### 方式三：完整示例
```bash
python main.py
```

## 📋 使用示例

### 基本用法

```python
import asyncio
from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool

async def simple_example():
    # 创建配置
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    config.add_tool(FileWriteTool())
    
    # 创建引擎
    engine = UniversalTaskEngine(config)
    
    # 执行任务
    async for result in engine.execute_task("创建一个Hello World文件"):
        if result.type == "task_completed":
            print("任务完成!")
            break

# 运行示例
asyncio.run(simple_example())
```

### 任务示例

您可以尝试以下任务：

#### 简单任务
- "获取当前时间"
- "问候用户"
- "创建一个Hello World文件"

#### 复杂任务
- "分析项目结构并生成说明文档"
- "读取配置文件，处理数据，然后写入结果"
- "创建多个测试文件，分析内容，生成报告"

## 🔧 框架架构

### 核心组件

```
UTF Framework
├── 🧠 UniversalTaskEngine     # 核心任务执行引擎
├── 📊 TaskDecomposer          # 任务分解器
├── 🔧 ToolOrchestrator        # 工具编排器
├── 🤝 InteractionManager      # 交互管理器
└── ⚙️ FrameworkConfig         # 框架配置
```

### 内置工具

1. **GeneralProcessorTool** - 通用处理器
   - 处理一般性任务
   - 提供时间信息、问候等基础功能

2. **FileReadTool** - 文件读取工具
   - 安全的文件读取
   - 支持大文件分段读取
   - 自动编码检测

3. **FileWriteTool** - 文件写入工具
   - 安全的文件写入
   - 原子性操作
   - 自动目录创建

## 🎮 交互式使用

启动交互式CLI：

```bash
python start.py
```

### 可用命令

- `help` - 显示帮助信息
- `status` - 显示系统状态
- `quit` - 退出程序

### 任务执行流程

1. **输入任务**: 输入自然语言任务描述
2. **任务分析**: 系统自动分析任务复杂度
3. **计划生成**: 复杂任务自动分解为步骤
4. **工具选择**: 智能选择合适的工具
5. **执行监控**: 实时显示执行进度
6. **结果展示**: 格式化显示执行结果

## 🔌 扩展开发

### 创建自定义工具

```python
from utf.tools.base import BaseTool
from utf.models.tool import ToolDefinition, ToolResult

class CustomTool(BaseTool):
    def _create_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="custom_tool",
            description="自定义工具描述",
            parameters={
                "input": {
                    "type": "string",
                    "description": "输入参数",
                    "required": True
                }
            },
            is_concurrent_safe=True,
            required_permissions=[],
            tags=["custom"],
            version="1.0.0"
        )
    
    async def _execute_core(self, parameters, context=None):
        # 实现工具逻辑
        yield self._create_success_result(
            context.get('call_id', 'unknown'),
            {"message": "执行成功"},
            0.1
        )

# 使用自定义工具
config = FrameworkConfig()
config.add_tool(CustomTool())
```

### 配置框架

```python
from utf.config.settings import FrameworkConfig

config = FrameworkConfig()

# 安全配置
config.security.sandbox_mode = True
config.security.max_execution_time = 300

# 并发配置
config.concurrency.max_parallel_tools = 5

# 交互配置
config.interaction.allow_user_interruption = True
config.interaction.confirmation_required = False

# 日志配置
config.logging.level = "INFO"
config.logging.enable_file_logging = True
```

## 📊 性能特性

- **并发执行**: 支持最多10个工具同时执行
- **智能调度**: 自动识别可并发和串行工具
- **流式处理**: 基于AsyncGenerator的流式结果输出
- **内存优化**: 增量处理，避免大量数据缓存
- **错误恢复**: 完善的错误处理和恢复机制

## 🛡️ 安全特性

- **权限控制**: 细粒度的工具执行权限管理
- **参数验证**: 基于Pydantic的严格参数验证
- **沙箱模式**: 可选的安全沙箱执行环境
- **审计日志**: 完整的执行过程记录

## 📝 注意事项

1. **文件操作**: 默认在当前目录下进行，注意文件路径安全
2. **并发限制**: 默认最多10个工具并发执行
3. **任务超时**: 单个任务默认最大执行时间为5分钟
4. **内存使用**: 大文件处理时注意内存使用

## 🤝 开发贡献

UTF框架采用模块化设计，欢迎贡献：

1. **工具开发**: 实现新的工具类型
2. **功能改进**: 优化现有功能
3. **文档完善**: 改进文档和示例
4. **测试用例**: 添加测试覆盖

## 📚 更多资源

- [README.md](README.md) - 完整项目说明
- [examples/](examples/) - 更多示例代码
- [tests/](tests/) - 测试用例
- [utf/](utf/) - 框架源代码

---

**基于Claude Code架构精华，打造下一代AI工具框架**
