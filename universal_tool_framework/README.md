# Universal Tool Framework (UTF)

## 🎯 项目概述

Universal Tool Framework (UTF) 是一个**AI驱动的智能工具调用框架**，基于Claude Code架构精华提取。它实现了完整的"**AI理解→智能规划→工具执行→结果总结**"闭环流程，支持LLM驱动的任务分析、智能分解、上下文记忆和自适应执行。

### 🤖 AI智能核心
- **LLM驱动**: 使用大语言模型进行任务理解和智能决策
- **智能规划**: AI自动分析任务复杂度并生成最优执行计划  
- **上下文记忆**: 智能管理对话历史和任务状态，支持语义搜索
- **自适应执行**: 根据执行结果动态调整策略，智能错误恢复

## 🏗️ 核心特性

### 🧠 AI智能特性
- **LLM任务理解**: 深度理解自然语言任务描述，智能提取执行意图
- **智能复杂度分析**: AI评估任务难度并自动选择最优分解策略
- **智能规划生成**: 根据可用工具和上下文自动生成最优执行计划
- **上下文感知**: 基于对话历史和任务状态进行智能决策
- **语义工具匹配**: 智能分析工具能力并选择最适合的工具组合
- **执行结果总结**: AI生成友好的任务完成总结和建议

### 🎯 基础功能
- **智能任务分解**: AI驱动的任务分解，比规则引擎更智能
- **工具智能选择**: 基于语义理解的工具选择和参数生成
- **用户交互控制**: 支持实时中断、修改计划、进度查看
- **并发执行优化**: 智能识别可并发工具，优化执行效率
- **事件驱动架构**: 基于异步生成器的流式处理
- **可扩展设计**: 标准化工具接口，易于添加新工具

### 🚀 高级功能
- **错误恢复系统**: AI驱动的错误分析、智能重试、故障转移
- **性能监控**: 实时性能指标收集、告警、趋势分析
- **状态持久化**: 任务状态自动保存、断点恢复、迁移支持
- **工具生命周期**: 工具注册、健康检查、版本管理、热重载
- **熔断器保护**: 防止级联故障、自动熔断、优雅降级
- **增强安全**: 细粒度权限控制、安全审计、沙箱模式

## 📁 项目结构

```
universal_tool_framework/
├── README.md                    # 项目说明
├── requirements.txt             # 依赖包
├── main.py                     # 完整示例程序
├── run_example.py              # 快速演示程序
├── start.py                    # 基础交互CLI
├── start_enhanced.py           # 增强版CLI (展示高级功能)
├── utf/                        # 核心框架
│   ├── __init__.py
│   ├── core/                   # 核心引擎
│   │   ├── __init__.py
│   │   ├── engine.py          # 主执行引擎
│   │   ├── task_decomposer.py # 任务分解器
│   │   ├── tool_orchestrator.py # 工具编排器
│   │   ├── interaction_manager.py # 交互管理器
│   │   ├── error_recovery.py  # 错误恢复系统
│   │   ├── state_manager.py   # 状态持久化
│   │   └── tool_lifecycle.py  # 工具生命周期管理
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
│   │   ├── concurrency.py     # 并发控制
│   │   └── metrics.py         # 性能监控
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
cd universal_tool_framework
pip install -r requirements.txt
```

### 快速体验

#### 方式一：快速演示
```bash
python run_example.py
```

#### 方式二：基础交互
```bash
python start.py
```

#### 方式三：增强版体验 (推荐)
```bash
python start_enhanced.py
```

### 编程使用

#### 基础用法
```python
from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileReadTool, FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool

# 配置框架
config = FrameworkConfig()
config.add_tool(GeneralProcessorTool())
config.add_tool(FileReadTool())
config.add_tool(FileWriteTool())

# 创建引擎
engine = UniversalTaskEngine(config)

# 执行任务
async def main():
    user_query = "分析项目文件，生成技术文档"
    
    async for result in engine.execute_task(user_query):
        if result.type == "task_completed":
            print("任务完成!")
            break

import asyncio
asyncio.run(main())
```

#### 高级用法 (错误恢复、状态持久化)
```python
from utf import UniversalTaskEngine, FrameworkConfig

# 创建配置
config = FrameworkConfig()
config.task.retry_failed_todos = True  # 启用重试
config.security.enable_permission_check = True  # 启用权限检查

engine = UniversalTaskEngine(config)

# 执行任务
async def advanced_example():
    # 执行复杂任务
    task_id = None
    async for result in engine.execute_task("复杂的数据分析任务"):
        if result.type == "task_analysis_started":
            task_id = result.data["task_id"]
        elif result.type == "task_failed":
            print(f"任务失败，ID: {task_id}")
            break
    
    # 稍后恢复任务
    if task_id:
        async for result in engine.resume_task(task_id):
            if result.type == "task_completed":
                print("任务恢复并完成!")
                break

asyncio.run(advanced_example())
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
