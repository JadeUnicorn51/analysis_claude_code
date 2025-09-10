#!/usr/bin/env python3
"""
Universal Tool Framework 启动脚本

提供交互式命令行界面
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileReadTool, FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool
from utf.utils.logging import setup_logging


class UTFCli:
    """UTF命令行界面"""
    
    def __init__(self):
        # 创建配置
        self.config = FrameworkConfig.create_default()
        
        # 添加所有可用工具
        self.config.add_tool(GeneralProcessorTool())
        self.config.add_tool(FileReadTool())
        self.config.add_tool(FileWriteTool())
        
        # 设置日志
        setup_logging(self.config.logging)
        
        # 创建引擎
        self.engine = UniversalTaskEngine(self.config)
        
        print("🚀 Universal Tool Framework")
        print("=" * 40)
        print("可用工具:")
        for tool_name in self.config.get_tool_names():
            print(f"  - {tool_name}")
        print()
        print("输入任务描述，或输入 'help' 查看帮助，'quit' 退出")
        print("=" * 40)
    
    async def run(self):
        """运行CLI"""
        while True:
            try:
                # 获取用户输入
                user_input = input("\n💬 请输入任务: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break
                
                if user_input.lower() in ['help', 'h']:
                    self.show_help()
                    continue
                
                if user_input.lower() in ['status', 's']:
                    self.show_status()
                    continue
                
                # 执行任务
                await self.execute_task(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 用户中断，退出程序")
                break
            except EOFError:
                print("\n👋 输入结束，退出程序")
                break
            except Exception as e:
                print(f"\n💥 错误: {e}")
    
    async def execute_task(self, task_query: str):
        """执行任务"""
        print(f"\n🔄 执行任务: {task_query}")
        print("-" * 30)
        
        try:
            task_completed = False
            
            async for result in self.engine.execute_task(task_query):
                result_type = result.type
                result_data = result.data
                
                if result_type == "complexity_analysis_completed":
                    complexity = result_data
                    print(f"📊 复杂度: {complexity['score']}/10, 需要分解: {'是' if complexity['needs_todo_list'] else '否'}")
                
                elif result_type == "todo_list_generated":
                    todos = result_data.get('todos', [])
                    print(f"📝 生成 {len(todos)} 个步骤:")
                    for i, todo in enumerate(todos, 1):
                        print(f"   {i}. {todo['content']}")
                
                elif result_type == "todo_started":
                    todo = result_data.get('todo', {})
                    print(f"▶️  执行: {todo.get('content')}")
                
                elif result_type == "tool_execution_result":
                    tool_result = result_data
                    if tool_result.get('success'):
                        data = tool_result.get('data', {})
                        self.display_tool_result(data)
                    else:
                        print(f"❌ 工具错误: {tool_result.get('error')}")
                
                elif result_type == "todo_completed":
                    progress = result_data.get('progress', 0)
                    print(f"✅ 步骤完成 ({progress:.1f}%)")
                
                elif result_type == "task_completed":
                    duration = result_data.get('duration', 0)
                    print(f"🎉 任务完成! 耗时: {duration:.2f}秒")
                    task_completed = True
                
                elif result_type == "task_failed":
                    error = result_data.get('error')
                    print(f"💥 任务失败: {error}")
                    task_completed = True
            
            if not task_completed:
                print("⚠️  任务执行可能未完成")
                
        except Exception as e:
            print(f"💥 执行异常: {e}")
    
    def display_tool_result(self, data):
        """显示工具结果"""
        if isinstance(data, dict):
            if 'message' in data:
                print(f"💬 {data['message']}")
            
            if 'file_path' in data:
                print(f"📁 文件: {data['file_path']}")
            
            if 'content' in data and len(str(data['content'])) < 200:
                print(f"📄 内容预览: {str(data['content'])[:100]}...")
        else:
            print(f"📋 结果: {str(data)[:200]}...")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n📚 帮助信息")
        print("-" * 20)
        print("命令:")
        print("  help/h     - 显示此帮助")
        print("  status/s   - 显示系统状态") 
        print("  quit/q     - 退出程序")
        print()
        print("任务示例:")
        print("  创建一个Hello World文件")
        print("  获取当前时间")
        print("  分析项目结构")
        print("  读取README.md文件")
    
    def show_status(self):
        """显示状态信息"""
        print("\n📊 系统状态")
        print("-" * 20)
        print(f"可用工具: {len(self.config.tools)}")
        print(f"活跃任务: {len(self.engine.get_active_tasks())}")
        print(f"并发限制: {self.config.concurrency.max_parallel_tools}")
        print(f"调试模式: {'开启' if self.config.debug else '关闭'}")


async def main():
    """主函数"""
    cli = UTFCli()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n💥 启动失败: {e}")
        import traceback
        traceback.print_exc()
