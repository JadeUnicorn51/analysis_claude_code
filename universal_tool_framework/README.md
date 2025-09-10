# Universal Tool Framework (UTF)

## 🎯 项目概述

Universal Tool Framework (UTF) 是一个基于Claude Code架构精华提取的通用工具调用框架。它实现了"问题→规划→工具执行→结果"的完整闭环流程，支持用户中断、任务分解、智能工具选择和并发执行。

## 🏗️ 核心特性

- **智能任务分解**: 自动将复杂任务分解为可执行的Todo步骤
- **工具智能选择**: 基于任务需求自动选择最适合的工具
- **用户交互控制**: 支持实时中断、修改计划、进度查看
- **并发执行优化**: 智能识别可并发工具，优化执行效率
- **事件驱动架构**: 基于异步生成器的流式处理
- **可扩展设计**: 标准化工具接口，易于添加新工具

## 📁 项目结构

```
universal_tool_framework/
├── README.md                    # 项目说明
├── requirements.txt             # 依赖包
├── main.py                     # 示例运行文件
├── utf/                        # 核心框架
│   ├── __init__.py
│   ├── core/                   # 核心引擎
│   │   ├── __init__.py
│   │   ├── engine.py          # 主执行引擎
│   │   ├── task_decomposer.py # 任务分解器
│   │   ├── tool_orchestrator.py # 工具编排器
│   │   └── interaction_manager.py # 交互管理器
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── task.py            # 任务相关模型
│   │   ├── tool.py            # 工具相关模型
│   │   └── execution.py       # 执行相关模型
│   ├── tools/                  # 工具实现
│   │   ├── __init__.py
│   │   ├── base.py            # 工具基类
│   │   ├── file_tools/        # 文件操作工具
│   │   ├── system_tools/      # 系统工具
│   │   └── ai_tools/          # AI相关工具
│   ├── utils/                  # 工具函数
│   │   ├── __init__.py
│   │   ├── logging.py         # 日志工具
│   │   ├── validation.py      # 验证工具
│   │   └── concurrency.py     # 并发控制
│   └── config/                 # 配置管理
│       ├── __init__.py
│       ├── settings.py        # 配置类
│       └── default.yaml       # 默认配置
├── tests/                      # 测试文件
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_tools.py
│   └── test_integration.py
└── examples/                   # 示例代码
    ├── basic_usage.py
    ├── custom_tools.py
    └── advanced_scenarios.py
```

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools import FileReadTool, FileWriteTool, WebSearchTool

# 配置框架
config = FrameworkConfig(
    tools=[FileReadTool(), FileWriteTool(), WebSearchTool()],
    max_parallel_tools=3,
    allow_user_interruption=True
)

# 创建引擎
engine = UniversalTaskEngine(config)

# 执行任务
async def main():
    user_query = "分析项目文件，生成技术文档，并搜索相关技术资料"
    
    async for result in engine.execute_task(user_query):
        print(f"[{result['type']}] {result['data']}")

# 运行
import asyncio
asyncio.run(main())
```

## 🎯 设计理念

UTF框架基于以下核心理念设计：

1. **任务驱动**: 一切从用户任务开始，自动分解为可执行步骤
2. **工具抽象**: 统一的工具接口，支持任意类型的工具扩展
3. **用户中心**: 用户可随时介入、修改、控制执行流程
4. **智能调度**: AI驱动的工具选择和执行优化
5. **异步优先**: 基于async/await的高性能异步架构

## 📖 核心概念

### Task (任务)
用户提出的原始需求，可以是简单任务或复杂任务

### TodoItem (待办项)
复杂任务分解后的单个执行步骤

### Tool (工具)
实现特定功能的可执行组件，如文件操作、网络请求等

### Execution Plan (执行计划)
基于TodoList和可用工具生成的具体执行策略

### User Interaction (用户交互)
框架与用户的实时交互机制，支持中断、修改、确认等

## 🔧 扩展开发

### 添加新工具

```python
from utf.tools.base import BaseTool
from utf.models.tool import ToolResult

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "自定义工具示例"
    
    async def execute(self, params: dict) -> ToolResult:
        # 实现工具逻辑
        return ToolResult(
            success=True,
            data={"message": "执行成功"},
            metadata={"execution_time": 0.1}
        )
    
    def is_concurrency_safe(self, params: dict) -> bool:
        return True  # 是否支持并发执行
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

## 🔄 版本规划

### v0.1.0 (当前)
- 基础架构和核心引擎
- 基本工具实现
- 任务分解和执行流程

### v0.2.0
- 用户交互界面
- 更多内置工具
- 性能优化

### v0.3.0
- Web界面
- 工具市场
- 插件系统

### v1.0.0
- 企业级特性
- 分布式支持
- 完整生态

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**基于Claude Code架构精华，打造下一代AI工具框架**
