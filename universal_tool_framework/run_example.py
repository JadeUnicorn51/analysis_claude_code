#!/usr/bin/env python3
"""
Universal Tool Framework 快速运行示例

这是一个最简化的示例，展示UTF框架的基本用法
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool


async def quick_demo():
    """快速演示"""
    print("🚀 UTF框架快速演示")
    print("=" * 30)
    
    # 创建配置
    config = FrameworkConfig.create_default()
    
    # 添加基础工具
    config.add_tool(GeneralProcessorTool())
    config.add_tool(FileWriteTool())
    
    # 创建引擎
    engine = UniversalTaskEngine(config)
    
    # 简单任务
    tasks = [
        "问候用户",
        "获取当前时间",
        "创建一个测试文件"
    ]
    
    for task in tasks:
        print(f"\n📋 任务: {task}")
        print("-" * 20)
        
        async for result in engine.execute_task(task):
            if result.type == "task_completed":
                print("✅ 完成")
                break
            elif result.type == "task_failed":
                print(f"❌ 失败: {result.data.get('error', 'Unknown')}")
                break
            elif result.type == "tool_execution_result":
                tool_result = result.data
                if tool_result.get('success'):
                    data = tool_result.get('data', {})
                    if isinstance(data, dict) and 'message' in data:
                        print(f"💬 {data['message']}")


if __name__ == "__main__":
    try:
        asyncio.run(quick_demo())
        print("\n🎉 演示完成!")
    except KeyboardInterrupt:
        print("\n👋 用户中断")
    except Exception as e:
        print(f"\n💥 错误: {e}")
        import traceback
        traceback.print_exc()
