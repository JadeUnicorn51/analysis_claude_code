#!/usr/bin/env python3
"""
Universal Tool Framework 增强版启动脚本

展示框架的高级功能：错误恢复、性能监控、状态持久化、工具生命周期管理等
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import time

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileReadTool, FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool
from utf.utils.logging import setup_logging
from utf.models.task import TaskStatus


class EnhancedUTFCli:
    """增强版UTF命令行界面"""
    
    def __init__(self):
        # 创建增强配置
        self.config = FrameworkConfig.create_default()
        
        # 启用高级功能
        self.config.debug = True
        self.config.interaction.allow_user_interruption = True
        self.config.task.retry_failed_todos = True
        self.config.security.enable_permission_check = True
        
        # 添加所有可用工具
        self.config.add_tool(GeneralProcessorTool())
        self.config.add_tool(FileReadTool())
        self.config.add_tool(FileWriteTool())
        
        # 设置日志
        setup_logging(self.config.logging)
        
        # 创建引擎
        self.engine = UniversalTaskEngine(self.config)
        
        print("🚀 Universal Tool Framework - 增强版")
        print("=" * 50)
        print("✨ 高级功能已启用:")
        print("  - 错误恢复和故障转移")
        print("  - 性能监控和指标收集")
        print("  - 状态持久化和任务恢复")
        print("  - 工具生命周期管理")
        print("  - 熔断器保护")
        print()
        print("📋 可用命令:")
        print("  task <描述>     - 执行任务")
        print("  resume <ID>     - 恢复任务")
        print("  status          - 系统状态")
        print("  tools           - 工具状态")
        print("  metrics         - 性能指标")
        print("  recovery        - 恢复统计")
        print("  history         - 任务历史")
        print("  help            - 显示帮助")
        print("  quit            - 退出程序")
        print("=" * 50)
    
    async def run(self):
        """运行CLI"""
        while True:
            try:
                # 获取用户输入
                user_input = input("\n💬 请输入命令: ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if command in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break
                
                elif command in ['help', 'h']:
                    await self.show_help()
                
                elif command == 'task':
                    if args:
                        await self.execute_task(args)
                    else:
                        print("❌ 请提供任务描述")
                
                elif command == 'resume':
                    if args:
                        await self.resume_task(args)
                    else:
                        print("❌ 请提供任务ID")
                
                elif command == 'status':
                    await self.show_system_status()
                
                elif command == 'tools':
                    await self.show_tool_status()
                
                elif command == 'metrics':
                    await self.show_performance_metrics()
                
                elif command == 'recovery':
                    await self.show_recovery_statistics()
                
                elif command == 'history':
                    await self.show_task_history()
                
                else:
                    print(f"❌ 未知命令: {command}，输入 'help' 查看帮助")
                
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
    
    async def execute_task(self, task_query: str):
        """执行任务"""
        print(f"\n🔄 执行任务: {task_query}")
        print("-" * 40)
        
        start_time = time.time()
        task_completed = False
        
        try:
            async for result in self.engine.execute_task(task_query):
                await self.display_task_result(result)
                
                if result.type == "task_completed":
                    task_completed = True
                    duration = time.time() - start_time
                    print(f"🎉 任务完成! 总耗时: {duration:.2f}秒")
                    break
                elif result.type == "task_failed":
                    task_completed = True
                    print(f"💥 任务失败")
                    break
        
        except Exception as e:
            print(f"💥 执行异常: {e}")
    
    async def resume_task(self, task_id: str):
        """恢复任务"""
        print(f"\n🔄 恢复任务: {task_id}")
        print("-" * 40)
        
        try:
            async for result in self.engine.resume_task(task_id):
                await self.display_task_result(result)
                
                if result.type in ["task_completed", "task_resume_failed"]:
                    break
        
        except Exception as e:
            print(f"💥 恢复异常: {e}")
    
    async def show_system_status(self):
        """显示系统状态"""
        print("\n📊 系统状态")
        print("-" * 30)
        
        try:
            status = await self.engine.get_system_status()
            
            # 引擎状态
            engine_status = status.get('engine', {})
            print(f"🔧 引擎状态:")
            print(f"   活跃任务: {engine_status.get('active_tasks', 0)}")
            
            # 工具状态
            available_tools = status.get('available_tools', [])
            print(f"🛠️  可用工具: {len(available_tools)}")
            for tool in available_tools:
                print(f"   - {tool}")
            
            # 错误恢复统计
            recovery_stats = status.get('error_recovery', {})
            if recovery_stats:
                print(f"🔄 错误恢复:")
                print(f"   总错误数: {recovery_stats.get('total_errors', 0)}")
                print(f"   恢复成功: {recovery_stats.get('recovered_errors', 0)}")
                print(f"   成功率: {recovery_stats.get('success_rate', 0):.1f}%")
            
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")
    
    async def show_tool_status(self):
        """显示工具状态"""
        print("\n🛠️ 工具状态")
        print("-" * 30)
        
        try:
            lifecycle_stats = self.engine.tool_lifecycle_manager.get_lifecycle_statistics()
            
            print("📈 状态统计:")
            tool_states = lifecycle_stats.get('tool_states', {})
            for state, count in tool_states.items():
                if count > 0:
                    print(f"   {state}: {count}")
            
            print("🏥 健康状态:")
            health_summary = lifecycle_stats.get('health_summary', {})
            print(f"   总工具数: {health_summary.get('total_tools', 0)}")
            print(f"   健康工具: {health_summary.get('healthy_tools', 0)}")
            print(f"   总检查数: {health_summary.get('total_health_checks', 0)}")
            print(f"   错误次数: {health_summary.get('total_errors', 0)}")
            
        except Exception as e:
            print(f"❌ 获取工具状态失败: {e}")
    
    async def show_performance_metrics(self):
        """显示性能指标"""
        print("\n📊 性能指标")
        print("-" * 30)
        
        try:
            performance_report = self.engine.performance_monitor.get_performance_report(hours=1)
            
            # 时间范围
            time_range = performance_report.get('time_range', {})
            print(f"⏰ 时间范围: 最近 {time_range.get('hours', 1)} 小时")
            
            # 任务指标
            task_metrics = performance_report.get('task_metrics', {})
            if task_metrics:
                print("📋 任务指标:")
                print(f"   总执行次数: {task_metrics.get('total_executions', 0)}")
                print(f"   平均执行时间: {task_metrics.get('avg_duration', 0):.2f}秒")
                print(f"   95%执行时间: {task_metrics.get('p95_duration', 0):.2f}秒")
                print(f"   最大执行时间: {task_metrics.get('max_duration', 0):.2f}秒")
            
            # 工具指标
            tool_metrics = performance_report.get('tool_metrics', {})
            if tool_metrics:
                print("🔧 工具指标:")
                print(f"   总执行次数: {tool_metrics.get('total_executions', 0)}")
                print(f"   平均执行时间: {tool_metrics.get('avg_duration', 0):.2f}秒")
                print(f"   95%执行时间: {tool_metrics.get('p95_duration', 0):.2f}秒")
            
            # 系统指标
            system_metrics = performance_report.get('system_metrics', {})
            if system_metrics and 'cpu' in system_metrics:
                cpu_info = system_metrics['cpu']
                memory_info = system_metrics.get('memory', {})
                print("💻 系统指标:")
                print(f"   CPU使用率: {cpu_info.get('percent', 0):.1f}%")
                print(f"   内存使用率: {memory_info.get('percent', 0):.1f}%")
            
        except Exception as e:
            print(f"❌ 获取性能指标失败: {e}")
    
    async def show_recovery_statistics(self):
        """显示恢复统计"""
        print("\n🔄 错误恢复统计")
        print("-" * 30)
        
        try:
            stats = self.engine.error_recovery_manager.get_recovery_statistics()
            
            print(f"📊 总体统计:")
            print(f"   总错误数: {stats.get('total_errors', 0)}")
            print(f"   恢复成功: {stats.get('recovered_errors', 0)}")
            print(f"   恢复失败: {stats.get('failed_recoveries', 0)}")
            print(f"   成功率: {stats.get('success_rate', 0):.1f}%")
            
            # 错误类型统计
            error_types = stats.get('error_types', {})
            if error_types:
                print("\n🎯 错误类型:")
                for error_type, count in error_types.items():
                    print(f"   {error_type}: {count}")
            
            # 熔断器状态
            active_breakers = stats.get('active_circuit_breakers', 0)
            if active_breakers > 0:
                print(f"\n⚡ 活跃熔断器: {active_breakers}")
            
        except Exception as e:
            print(f"❌ 获取恢复统计失败: {e}")
    
    async def show_task_history(self):
        """显示任务历史"""
        print("\n📋 任务历史")
        print("-" * 30)
        
        try:
            # 获取所有任务
            all_tasks = await self.engine.state_manager.list_tasks(limit=10)
            
            if not all_tasks:
                print("📝 暂无任务历史")
                return
            
            print(f"📝 最近 {len(all_tasks)} 个任务:")
            
            for task_id in all_tasks:
                task = await self.engine.state_manager.load_task(task_id)
                if task:
                    status_icon = {
                        TaskStatus.COMPLETED: "✅",
                        TaskStatus.FAILED: "❌", 
                        TaskStatus.IN_PROGRESS: "🔄",
                        TaskStatus.PENDING: "⏳",
                        TaskStatus.CANCELLED: "🚫"
                    }.get(task.status, "❓")
                    
                    print(f"   {status_icon} {task_id[:8]}... - {task.query[:30]}... ({task.status.value})")
                    
                    # 显示恢复信息
                    recovery_info = await self.engine.state_manager.get_task_recovery_info(task_id)
                    if recovery_info and recovery_info.get('can_resume'):
                        print(f"      💡 可恢复 (进度: {recovery_info.get('progress', 0):.1f}%)")
            
        except Exception as e:
            print(f"❌ 获取任务历史失败: {e}")
    
    async def show_help(self):
        """显示帮助信息"""
        print("\n📚 增强版UTF帮助")
        print("-" * 30)
        print("🎯 任务管理:")
        print("   task <描述>     - 执行新任务")
        print("   resume <ID>     - 恢复指定任务")
        print("   history         - 查看任务历史")
        print()
        print("📊 监控命令:")
        print("   status          - 显示系统整体状态")
        print("   tools           - 显示工具生命周期状态")
        print("   metrics         - 显示性能监控指标")
        print("   recovery        - 显示错误恢复统计")
        print()
        print("🔧 示例任务:")
        print("   task 获取当前时间")
        print("   task 创建一个包含系统信息的文件")
        print("   task 分析项目结构并生成报告")
        print("   task 读取配置文件并验证格式")
        print()
        print("💡 高级功能:")
        print("   - 任务执行过程中按 Ctrl+C 可以优雅中断")
        print("   - 失败的任务会自动尝试恢复")
        print("   - 所有任务状态都会自动保存")
        print("   - 可以随时恢复未完成的任务")
    
    async def display_task_result(self, result):
        """显示任务结果"""
        result_type = result.type
        result_data = result.data
        
        if result_type == "task_analysis_started":
            print("🔍 开始分析任务...")
        
        elif result_type == "complexity_analysis_completed":
            complexity = result_data
            print(f"📊 复杂度分析: 评分={complexity['score']}/10")
            print(f"   需要分解: {'是' if complexity['needs_todo_list'] else '否'}")
            print(f"   预估步骤: {complexity['estimated_steps']} 步")
            print(f"   分析原因: {complexity['reasoning']}")
        
        elif result_type == "todo_list_generated":
            todo_count = result_data.get('todo_count', 0)
            print(f"📝 生成了 {todo_count} 个执行步骤:")
            
            todos = result_data.get('todos', [])
            for i, todo in enumerate(todos, 1):
                print(f"   {i}. {todo['content']}")
        
        elif result_type == "todo_started":
            todo = result_data.get('todo', {})
            print(f"▶️  执行步骤: {todo.get('content', 'Unknown')}")
        
        elif result_type == "tool_execution_result":
            tool_result = result_data
            if tool_result.get('success', False):
                print(f"✅ 工具执行成功")
                # 显示详细结果
                data = tool_result.get('data', {})
                if isinstance(data, dict) and 'message' in data:
                    print(f"   💬 {data['message']}")
            else:
                print(f"❌ 工具执行失败: {tool_result.get('error', 'Unknown error')}")
                
                # 显示错误恢复信息
                recovery_result = result_data.get('recovery_result')
                if recovery_result:
                    print(f"   🔄 恢复尝试: {recovery_result.get('action', 'unknown')}")
        
        elif result_type == "todo_completed":
            progress = result_data.get('progress', 0)
            print(f"✅ 步骤完成 (进度: {progress:.1f}%)")
        
        elif result_type == "task_completed":
            duration = result_data.get('duration', 0)
            resumed = result_data.get('resumed', False)
            resume_text = " (恢复任务)" if resumed else ""
            print(f"🎉 任务完成{resume_text}! 耗时: {duration:.2f}秒")
        
        elif result_type == "task_resumed":
            progress = result_data.get('progress', 0)
            remaining = result_data.get('remaining_todos', 0)
            print(f"🔄 任务已恢复 (进度: {progress:.1f}%, 剩余步骤: {remaining})")
        
        elif result_type == "task_failed":
            error = result_data.get('error', 'Unknown error')
            recovery_attempted = result_data.get('recovery_attempted', False)
            print(f"💥 任务失败: {error}")
            if recovery_attempted:
                recovery_result = result_data.get('recovery_result', {})
                print(f"   🔄 已尝试恢复: {recovery_result.get('action', 'unknown')}")
        
        elif result_type == "user_interaction_required":
            event = result_data
            print(f"🤝 需要用户交互: {event.get('type', 'unknown')}")
            
            # 自动处理交互（演示用）
            self.engine.interaction_manager.submit_user_response(
                event['id'], 
                'continue'
            )
            print("   ✅ 自动选择继续")


async def main():
    """主函数"""
    cli = EnhancedUTFCli()
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
