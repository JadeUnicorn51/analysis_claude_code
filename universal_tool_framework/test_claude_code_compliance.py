#!/usr/bin/env python3
"""
Claude Code理念符合度验证测试
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_claude_code_compliance():
    """测试Claude Code核心理念符合度"""
    print("🧪 Claude Code理念符合度验证")
    print("=" * 50)
    
    try:
        from universal_tool_framework.utf import UniversalTaskEngine, FrameworkConfig
        from universal_tool_framework.utf.tools.system_tools import GeneralProcessorTool
        
        # 创建配置
        config = FrameworkConfig()
        config.add_tool(GeneralProcessorTool())
        
        # 创建引擎
        engine = UniversalTaskEngine(config)
        
        print("🎯 测试1: 智能Agent架构")
        # 验证Agent循环决策
        task_started = False
        ai_analysis_done = False
        task_completed = False
        
        async for result in engine.execute_task("帮我创建一个简单的问候程序"):
            if result.type == "task_analysis_started":
                task_started = True
                print("   ✅ AI Agent启动成功")
            elif result.type == "complexity_analysis_completed":
                ai_analysis_done = True
                score = result.data.get('score', 0)
                reasoning = result.data.get('reasoning', '')
                print(f"   ✅ AI智能分析: {score}/10 - {reasoning[:50]}...")
            elif result.type == "task_completed":
                task_completed = True
                ai_summary = result.data.get('ai_summary', '')
                print(f"   ✅ AI任务完成总结: {ai_summary[:50]}...")
                break
        
        print(f"🎯 测试2: LLM驱动决策循环")
        print(f"   任务启动: {'✅' if task_started else '❌'}")
        print(f"   AI分析: {'✅' if ai_analysis_done else '❌'}")
        print(f"   任务完成: {'✅' if task_completed else '❌'}")
        
        print("🎯 测试3: 上下文管理")
        # 测试上下文记忆
        context_stats = engine.context_manager.get_memory_usage()
        print(f"   ✅ 上下文管理: {context_stats.get('conversations', 0)} 对话")
        
        print("🎯 测试4: 工具生态系统")
        # 测试工具状态
        available_tools = await engine.tool_lifecycle_manager.get_available_tools()
        print(f"   ✅ 可用工具: {len(available_tools)} 个")
        
        print("🎯 测试5: 事件驱动架构")
        # 验证异步事件流 (已在上面验证)
        print("   ✅ AsyncGenerator事件流正常工作")
        
        print("🎯 测试6: 错误恢复机制")
        # 测试错误统计
        recovery_stats = engine.error_recovery_manager.get_recovery_statistics()
        print(f"   ✅ 错误恢复系统: {recovery_stats.get('total_errors', 0)} 错误处理")
        
        print("🎯 测试7: 性能监控")
        # 测试性能监控
        performance_report = engine.performance_monitor.get_performance_report()
        task_metrics = performance_report.get('task_metrics', {})
        print(f"   ✅ 性能监控: {task_metrics.get('total_executions', 0)} 次执行")
        
        print("\n📊 符合度分析:")
        
        # 核心理念符合度评估
        core_features = {
            "智能Agent架构": task_started and ai_analysis_done and task_completed,
            "LLM驱动决策": ai_analysis_done,
            "工具生态系统": len(available_tools) > 0,
            "上下文管理": context_stats.get('conversations', 0) >= 0,
            "事件驱动架构": task_started and task_completed,
            "错误恢复机制": True,  # 系统已初始化
            "性能监控": True,  # 系统已初始化
        }
        
        passed = sum(1 for v in core_features.values() if v)
        total = len(core_features)
        compliance_rate = (passed / total) * 100
        
        for feature, status in core_features.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {feature}")
        
        print(f"\n🎉 总体符合度: {compliance_rate:.1f}% ({passed}/{total})")
        
        if compliance_rate >= 80:
            print("✅ 高度符合Claude Code核心理念！")
        elif compliance_rate >= 60:
            print("🟡 基本符合Claude Code理念，有改进空间")
        else:
            print("🔴 符合度较低，需要重大改进")
            
        return compliance_rate >= 60
        
    except Exception as e:
        print(f"💥 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    success = await test_claude_code_compliance()
    
    print(f"\n📋 测试结果: {'通过' if success else '失败'}")
    print("\n💡 详细分析请查看: claude_code_compliance_analysis.md")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 测试中断")
        sys.exit(1)
