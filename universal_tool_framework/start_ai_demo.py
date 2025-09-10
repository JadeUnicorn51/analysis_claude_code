#!/usr/bin/env python3
"""
Universal Tool Framework AI智能演示

展示框架的AI智能核心：LLM驱动的任务分析、智能规划、上下文管理等
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileReadTool, FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool
from utf.utils.logging import setup_logging
from utf.models.task import TaskStatus
from utf.ai.llm_client import LLMConfig, LLMProvider


class AIIntelligenceCLI:
    """AI智能演示CLI"""
    
    def __init__(self):
        # 创建AI增强配置
        self.config = FrameworkConfig.create_default()
        
        # 配置LLM (默认使用Mock，可以切换到真实LLM)
        self.config.llm_config = LLMConfig(
            provider="mock",  # 可以改为 "openai" 如果有API密钥
            model="mock-gpt-4",
            temperature=0.7,
            max_tokens=2000
        )
        
        # 添加工具
        self.config.add_tool(GeneralProcessorTool())
        self.config.add_tool(FileReadTool())
        self.config.add_tool(FileWriteTool())
        
        # 启用AI相关功能
        self.config.debug = True
        self.config.interaction.allow_user_interruption = True
        self.config.task.enable_auto_decomposition = True
        
        # 设置日志
        setup_logging(self.config.logging)
        
        # 创建AI增强引擎
        self.engine = UniversalTaskEngine(self.config)
        
        print("🤖 Universal Tool Framework - AI智能演示")
        print("=" * 60)
        print("✨ AI智能特性:")
        print("  🧠 LLM驱动的任务分析和分解")
        print("  🎯 智能工具选择和执行规划")
        print("  💭 上下文记忆和语义理解")
        print("  🔄 智能错误恢复和重新规划")
        print("  📊 任务执行总结和建议")
        print()
        print(f"🔧 当前LLM: {self.config.llm_config.provider} ({self.config.llm_config.model})")
        print()
        print("📋 智能命令:")
        print("  ask <问题>      - AI对话和任务执行")
        print("  analyze <任务>  - 分析任务复杂度")
        print("  context <ID>    - 查看任务上下文")
        print("  memory          - 查看AI记忆使用")
        print("  resume <ID>     - 智能恢复任务")
        print("  chat            - 纯对话模式")
        print("  demo            - 运行AI演示")
        print("  help            - 显示帮助")
        print("  quit            - 退出程序")
        print("=" * 60)
    
    async def run(self):
        """运行AI演示CLI"""
        await self._run_startup_demo()
        
        while True:
            try:
                user_input = input("\n🤖 AI助手: ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if command in ['quit', 'exit', 'q']:
                    print("👋 AI助手: 再见！期待下次为您服务！")
                    break
                
                elif command in ['help', 'h']:
                    await self.show_help()
                
                elif command == 'ask':
                    if args:
                        await self.ai_task_execution(args)
                    else:
                        print("❌ 请提供您的问题或任务")
                
                elif command == 'analyze':
                    if args:
                        await self.analyze_task_complexity(args)
                    else:
                        print("❌ 请提供要分析的任务")
                
                elif command == 'context':
                    if args:
                        await self.show_task_context(args)
                    else:
                        print("❌ 请提供任务ID")
                
                elif command == 'memory':
                    await self.show_memory_usage()
                
                elif command == 'resume':
                    if args:
                        await self.intelligent_resume(args)
                    else:
                        print("❌ 请提供任务ID")
                
                elif command == 'chat':
                    await self.pure_chat_mode()
                
                elif command == 'demo':
                    await self.run_ai_demo()
                
                else:
                    # 默认当作AI对话处理
                    await self.ai_task_execution(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 用户中断，退出程序")
                break
            except EOFError:
                print("\n👋 输入结束，退出程序")
                break
            except Exception as e:
                print(f"\n💥 错误: {e}")
                import traceback
                traceback.print_exc()
    
    async def _run_startup_demo(self):
        """启动演示"""
        print("\n🚀 启动AI智能演示...")
        
        # 测试AI响应
        try:
            health_ok = await self.engine.llm_client.health_check()
            if health_ok:
                print("✅ AI智能引擎已就绪")
            else:
                print("⚠️  AI引擎启动中...")
        except Exception as e:
            print(f"⚠️  AI引擎初始化警告: {e}")
        
        print("💡 尝试说：'创建一个包含当前时间的文件' 或 '分析这个项目的结构'")
    
    async def ai_task_execution(self, user_query: str):
        """AI驱动的任务执行"""
        print(f"\n🧠 AI正在分析: {user_query}")
        print("-" * 50)
        
        start_time = time.time()
        task_completed = False
        ai_responses = []
        
        try:
            async for result in self.engine.execute_task(user_query):
                result_type = result.type
                result_data = result.data
                
                if result_type == "task_analysis_started":
                    print("🔍 AI开始智能分析任务...")
                
                elif result_type == "complexity_analysis_completed":
                    complexity = result_data
                    print(f"📊 AI复杂度分析:")
                    print(f"   🎯 智能评分: {complexity['score']}/10")
                    print(f"   🧩 需要分解: {'是' if complexity['needs_todo_list'] else '否'}")
                    print(f"   📝 预估步骤: {complexity['estimated_steps']} 步")
                    print(f"   🔧 推荐工具: {', '.join(complexity['required_tools'])}")
                    print(f"   💭 AI分析: {complexity['reasoning']}")
                
                elif result_type == "todo_list_generated":
                    todo_count = result_data.get('todo_count', 0)
                    print(f"\n🎯 AI智能规划 ({todo_count} 个步骤):")
                    
                    todos = result_data.get('todos', [])
                    for i, todo in enumerate(todos, 1):
                        tools = ', '.join(todo.get('tools_needed', []))
                        priority = todo.get('priority', 0)
                        print(f"   {i}. {todo['content']}")
                        print(f"      🔧 工具: {tools} | 优先级: {priority}")
                
                elif result_type == "todo_started":
                    todo = result_data.get('todo', {})
                    print(f"\n▶️  AI执行步骤: {todo.get('content', 'Unknown')}")
                
                elif result_type == "tool_execution_result":
                    tool_result = result_data
                    if tool_result.get('success', False):
                        print(f"   ✅ 工具执行成功")
                        
                        # 显示AI生成的结果
                        data = tool_result.get('data', {})
                        if isinstance(data, dict):
                            if 'message' in data:
                                print(f"   💬 AI结果: {data['message']}")
                            if 'file_path' in data:
                                print(f"   📁 文件: {data['file_path']}")
                    else:
                        error = tool_result.get('error', 'Unknown error')
                        print(f"   ❌ 工具执行失败: {error}")
                
                elif result_type == "todo_completed":
                    progress = result_data.get('progress', 0)
                    print(f"   ✅ 步骤完成 (AI进度: {progress:.1f}%)")
                
                elif result_type == "task_completed":
                    duration = time.time() - start_time
                    ai_summary = result_data.get('ai_summary', '')
                    task_completed = True
                    
                    print(f"\n🎉 任务完成! 耗时: {duration:.2f}秒")
                    if ai_summary:
                        print(f"🤖 AI总结: {ai_summary}")
                    break
                
                elif result_type == "task_failed":
                    error = result_data.get('error', 'Unknown error')
                    recovery_result = result_data.get('recovery_result', {})
                    task_completed = True
                    
                    print(f"\n💥 任务失败: {error}")
                    if recovery_result:
                        print(f"🔄 AI恢复尝试: {recovery_result.get('action', 'unknown')}")
                    break
            
            if not task_completed:
                print("⚠️  任务执行可能未完成")
                
        except Exception as e:
            print(f"💥 AI执行异常: {e}")
    
    async def analyze_task_complexity(self, task_query: str):
        """分析任务复杂度"""
        print(f"\n🔬 AI深度分析: {task_query}")
        print("-" * 40)
        
        try:
            complexity = await self.engine.intelligent_planner.analyze_task_complexity(task_query)
            
            print("📊 AI复杂度分析报告:")
            print(f"   🎯 复杂度评分: {complexity.score}/10")
            print(f"   🧩 是否需要分解: {'是' if complexity.needs_todo_list else '否'}")
            print(f"   📝 预估执行步骤: {complexity.estimated_steps}")
            print(f"   🔧 推荐工具类型: {', '.join(complexity.required_tools)}")
            print(f"   💭 AI分析理由: {complexity.reasoning}")
            
            # 分类建议
            if complexity.score <= 3:
                print("   💡 AI建议: 这是一个简单任务，可以直接执行")
            elif complexity.score <= 6:
                print("   💡 AI建议: 中等复杂度任务，建议分解为几个步骤")
            else:
                print("   💡 AI建议: 复杂任务，需要仔细规划和多步骤执行")
            
        except Exception as e:
            print(f"❌ AI分析失败: {e}")
    
    async def show_task_context(self, task_id: str):
        """显示任务上下文"""
        print(f"\n💭 AI上下文记忆: {task_id}")
        print("-" * 40)
        
        try:
            context_stats = self.engine.context_manager.get_conversation_stats(task_id)
            
            if not context_stats:
                print("📝 该任务暂无上下文记录")
                return
            
            print("📊 上下文统计:")
            print(f"   📝 总条目数: {context_stats.get('total_entries', 0)}")
            print(f"   📊 条目类型: {context_stats.get('entry_types', {})}")
            print(f"   📏 总长度: {context_stats.get('total_length', 0)} 字符")
            print(f"   💾 是否有摘要: {'是' if context_stats.get('has_summary') else '否'}")
            print(f"   🕒 最后更新: {context_stats.get('last_updated', 'N/A')}")
            
            # 生成上下文摘要
            summary = await self.engine.context_manager.summarize_conversation(task_id)
            if summary:
                print(f"\n📋 AI上下文摘要:")
                print(f"   {summary}")
            
        except Exception as e:
            print(f"❌ 获取上下文失败: {e}")
    
    async def show_memory_usage(self):
        """显示AI记忆使用情况"""
        print("\n🧠 AI记忆系统状态")
        print("-" * 30)
        
        try:
            memory_stats = self.engine.context_manager.get_memory_usage()
            
            print("📊 记忆统计:")
            print(f"   💬 活跃对话数: {memory_stats.get('conversations', 0)}")
            print(f"   📝 上下文条目: {memory_stats.get('context_entries', 0)}")
            print(f"   📚 知识库条目: {memory_stats.get('knowledge_entries', 0)}")
            print(f"   📏 总文本长度: {memory_stats.get('total_text_length', 0):,} 字符")
            print(f"   💾 预估内存: {memory_stats.get('estimated_memory_mb', 0):.2f} MB")
            
            # AI状态
            ai_status = (await self.engine.get_system_status()).get('ai_status', {})
            print(f"\n🤖 AI引擎状态:")
            print(f"   🔧 LLM提供商: {ai_status.get('llm_provider', 'Unknown')}")
            print(f"   🧠 LLM模型: {ai_status.get('llm_model', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ 获取记忆状态失败: {e}")
    
    async def intelligent_resume(self, task_id: str):
        """智能恢复任务"""
        print(f"\n🔄 AI智能恢复任务: {task_id}")
        print("-" * 40)
        
        try:
            async for result in self.engine.resume_task(task_id):
                await self.display_task_result(result)
                
                if result.type in ["task_completed", "task_resume_failed"]:
                    break
        
        except Exception as e:
            print(f"💥 智能恢复异常: {e}")
    
    async def pure_chat_mode(self):
        """纯对话模式"""
        print("\n💬 进入AI对话模式 (输入 'exit' 退出)")
        print("-" * 40)
        
        while True:
            try:
                user_input = input("你: ").strip()
                if user_input.lower() in ['exit', 'quit', '退出']:
                    print("AI: 对话结束，回到主菜单")
                    break
                
                if not user_input:
                    continue
                
                # 使用LLM进行对话
                from utf.ai.llm_client import LLMMessage
                messages = [
                    LLMMessage(role="system", content="你是Universal Tool Framework的AI助手，友好且专业。"),
                    LLMMessage(role="user", content=user_input)
                ]
                
                response = await self.engine.llm_client.chat_completion(messages)
                print(f"AI: {response.content}")
                
            except Exception as e:
                print(f"AI: 抱歉，我遇到了一个错误: {e}")
    
    async def run_ai_demo(self):
        """运行AI能力演示"""
        print("\n🎬 AI智能能力演示")
        print("=" * 40)
        
        demo_tasks = [
            "获取当前时间并问候用户",
            "创建一个包含系统信息的文件",
            "分析这个项目的结构"
        ]
        
        for i, task in enumerate(demo_tasks, 1):
            print(f"\n🎯 演示 {i}: {task}")
            print("-" * 30)
            
            await self.ai_task_execution(task)
            
            if i < len(demo_tasks):
                print("\n⏸️  按回车继续下一个演示...")
                input()
        
        print("\n🎊 AI演示完成！")
    
    async def show_help(self):
        """显示帮助"""
        print("\n📚 AI智能助手帮助")
        print("-" * 30)
        print("🎯 智能任务执行:")
        print("   ask <任务>      - AI分析并执行任务")
        print("   analyze <任务>  - 分析任务复杂度")
        print("   demo            - 运行AI能力演示")
        print()
        print("💭 上下文和记忆:")
        print("   context <ID>    - 查看任务上下文")
        print("   memory          - 查看AI记忆状态")
        print("   chat            - 纯AI对话模式")
        print()
        print("🔄 智能管理:")
        print("   resume <ID>     - 智能恢复任务")
        print()
        print("💡 示例任务:")
        print("   ask 创建一个包含当前日期的备忘录")
        print("   ask 分析这个文件夹中的所有Python文件")
        print("   ask 帮我整理项目文档")
        print()
        print("🤖 AI特性:")
        print("   - 基于LLM的智能任务理解")
        print("   - 自动任务分解和规划")
        print("   - 上下文记忆和语义理解")
        print("   - 智能工具选择和优化")
        print("   - 错误分析和恢复建议")
    
    async def display_task_result(self, result):
        """显示任务结果（简化版）"""
        result_type = result.type
        result_data = result.data
        
        if result_type == "task_resumed":
            progress = result_data.get('progress', 0)
            remaining = result_data.get('remaining_todos', 0)
            print(f"🔄 任务已恢复 (AI进度: {progress:.1f}%, 剩余: {remaining})")
        
        elif result_type == "task_completed":
            ai_summary = result_data.get('ai_summary', '')
            print(f"🎉 任务完成!")
            if ai_summary:
                print(f"🤖 AI总结: {ai_summary}")
        
        elif result_type == "task_resume_failed":
            error = result_data.get('error', 'Unknown')
            print(f"💥 恢复失败: {error}")


async def main():
    """主函数"""
    cli = AIIntelligenceCLI()
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
