# Gemini 上下文：Claude Code 逆向工程分析项目

## 目录概述

这是一个用于研究和逆向工程 **Claude Code v1.0.33** 的资料库。其核心目标是通过对 `@anthropic-ai/claude-code` npm 包中混淆的 `cli.mjs` 文件进行系统性分析，以揭示其内部架构、核心机制和实现逻辑。

本项目不是一个传统的软件开发项目，而是一个深度分析和文档化的研究项目。主要产出是大量的技术分析文档，而非可执行程序。

## 关键文件和目录

理解本项目的关键在于阅读其分析过程和产出的文档。

- **`README.md`**: 提供了项目的高级概述，包括核心技术发现、系统架构图和仓库结构。这是了解本项目的最佳起点。

- **`work_doc_for_this/`**: 此目录包含了项目研究的“标准作业程序”（SOP）。
    - **`CLAUDE_CODE_REVERSE_SOP.md`**: 详细描述了从代码预处理、分割、LLM辅助分析到最终问答的完整逆向工程流程。它解释了 `scripts/` 目录中各个脚本的目的和用法。

- **`claude_code_v_1.0.33/stage1_analysis_workspace/`**: 这是主要的工作空间，包含了分析过程中的所有产物。
    - **`docs/`**: **（最重要）** 此目录包含了对 Claude Code 架构最详尽的分析文档。如果你想理解 Claude Code 的技术细节，应该从这里开始。关键文档包括：
        - `Claude_Code_Agent系统完整技术解析.md`: 对 Agent 系统架构的完整解析。
        - `实时Steering机制完整技术文档.md`: 对核心的实时消息处理机制的深度分析。
        - `分层多Agent架构完整技术文档.md`: 对其多 Agent 协作模式的分析。
        - 其他 `*.md` 文件分别深入探讨了沙箱、工具、UI等特定模块。
    - **`scripts/`**: 包含一系列 Node.js 脚本，用于自动化分析流程，例如代码美化 (`beautify.js`)、分割 (`split.js`) 和合并 (`merge-again.js`)。
    - **`chunks/`**: 存放从 `cli.beautify.mjs` 文件中分割出来的代码块。
    - **`analysis_results/merged-chunks/`**: 存放根据开源库或功能合并后的代码块。

## 如何使用这个目录

1.  **从 `README.md` 开始**：快速了解项目的目标和主要发现。
2.  **阅读 `work_doc_for_this/CLAUDE_CODE_REVERSE_SOP.md`**：理解整个逆向分析工作的流程和方法论。
3.  **深入 `claude_code_v_1.0.33/stage1_analysis_workspace/docs/`**：根据你的兴趣点，选择相应的技术文档进行深入阅读，以了解 Claude Code 的具体实现细节。

简而言之，这个目录是一个关于 Claude Code 的逆向工程知识库。与我交互时，你可以直接提出关于 Claude Code 架构或特定机制的问题，我将利用这些分析文档为你提供答案。
