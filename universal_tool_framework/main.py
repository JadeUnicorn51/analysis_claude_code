"""
Universal Tool Framework 示例程序

演示如何使用UTF框架执行任务
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from universal_tool_framework.utf import UniversalTaskEngine, FrameworkConfig
from universal_tool_framework.utf.tools.file_tools import FileReadTool, FileWriteTool
from universal_tool_framework.utf.tools.system_tools import GeneralProcessorTool
from universal_tool_framework.utf.utils.logging import setup_logging


async def main():
    """主函数"""
    print("🚀 Universal Tool Framework 示例程序")
    print("=" * 50)
    
    # 创建工具实例
    file_read_tool = FileReadTool()
    file_write_tool = FileWriteTool()
    general_processor = GeneralProcessorTool()
    
    # 配置框架
    config = FrameworkConfig()
    config.add_tool(file_read_tool)
    config.add_tool(file_write_tool)
    config.add_tool(general_processor)
    
    # 设置日志
    setup_logging(config.logging)
    
    # 创建引擎
    engine = UniversalTaskEngine(config)
    
    # 示例任务
    tasks = [
        "创建一个包含当前时间的文本文件",
        "读取刚创建的文件内容",
        "分析项目结构并生成说明文档"
    ]
    
    for i, task_query in enumerate(tasks, 1):
        print(f"\n📋 任务 {i}: {task_query}")
        print("-" * 40)
        
        try:
            # 执行任务
            async for result in engine.execute_task(task_query):
                result_type = result.type
                result_data = result.data
                
                # 美化输出
                if result_type == "task_analysis_started":
                    print(f"🔍 开始分析任务...")
                
                elif result_type == "complexity_analysis_completed":
                    complexity = result_data
                    print(f"📊 复杂度分析: 评分={complexity['score']}/10")
                    print(f"   需要分解: {'是' if complexity['needs_todo_list'] else '否'}")
                    print(f"   预估步骤: {complexity['estimated_steps']} 步")
                
                elif result_type == "todo_list_generated":
                    todo_count = result_data.get('todo_count', 0)
                    print(f"📝 生成了 {todo_count} 个执行步骤")
                    
                    # 显示TodoList
                    todos = result_data.get('todos', [])
                    for j, todo in enumerate(todos, 1):
                        print(f"   {j}. {todo['content']}")
                
                elif result_type == "todo_started":
                    todo = result_data.get('todo', {})
                    print(f"▶️  执行步骤: {todo.get('content', 'Unknown')}")
                
                elif result_type == "tool_execution_result":
                    tool_result = result_data
                    if tool_result.get('success', False):
                        print(f"✅ 工具执行成功")
                    else:
                        print(f"❌ 工具执行失败: {tool_result.get('error', 'Unknown error')}")
                
                elif result_type == "todo_completed":
                    progress = result_data.get('progress', 0)
                    print(f"✅ 步骤完成 (进度: {progress:.1f}%)")
                
                elif result_type == "task_completed":
                    duration = result_data.get('duration', 0)
                    print(f"🎉 任务完成! 耗时: {duration:.2f}秒")
                
                elif result_type == "task_failed":
                    error = result_data.get('error', 'Unknown error')
                    print(f"💥 任务失败: {error}")
                
                elif result_type == "user_interaction_required":
                    # 自动处理用户交互（示例）
                    event = result_data
                    print(f"🤝 需要用户交互: {event.get('type', 'unknown')}")
                    
                    # 这里可以实现真实的用户交互逻辑
                    # 现在简单地选择"continue"
                    engine.interaction_manager.submit_user_response(
                        event['id'], 
                        'continue'
                    )
        
        except Exception as e:
            print(f"💥 执行异常: {str(e)}")
        
        print()
    
    print("🏁 所有示例任务执行完成!")


async def simple_demo():
    """简单演示"""
    print("\n🎯 简单演示模式")
    print("=" * 30)
    
    # 最小配置
    config = FrameworkConfig()
    config.add_tool(FileWriteTool())
    config.add_tool(GeneralProcessorTool())
    
    engine = UniversalTaskEngine(config)
    
    # 执行简单任务
    simple_task = "创建一个Hello World文件"
    
    print(f"任务: {simple_task}")
    
    async for result in engine.execute_task(simple_task):
        if result.type == "task_completed":
            print("✅ 任务完成!")
            break
        elif result.type == "task_failed":
            print(f"❌ 任务失败: {result.data.get('error')}")
            break


if __name__ == "__main__":
    try:
        # 运行主演示
        asyncio.run(main())
        
        # 运行简单演示
        asyncio.run(simple_demo())
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n💥 程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
