#!/usr/bin/env python3
"""
深度功能能力检查 - 检查核心AI组件的实际工作能力
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from utf import UniversalTaskEngine, FrameworkConfig
from utf.tools.file_tools import FileReadTool, FileWriteTool
from utf.tools.system_tools import GeneralProcessorTool
from utf.ai.llm_client import LLMMessage

async def test_llm_core_capabilities():
    """测试LLM核心能力"""
    print("🧠 测试LLM核心能力")
    print("-" * 40)
    
    # 创建配置
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    # 测试1: 基础对话能力
    print("1. 测试基础对话能力...")
    try:
        messages = [
            LLMMessage(role="user", content="你好，请简单自我介绍")
        ]
        response = await engine.llm_client.chat_completion(messages)
        print(f"   ✅ 基础对话: {response.content[:100]}...")
        print(f"   📊 Token使用: {response.usage}")
    except Exception as e:
        print(f"   ❌ 基础对话失败: {e}")
    
    # 测试2: JSON结构化输出能力
    print("\n2. 测试JSON结构化输出...")
    try:
        messages = [
            LLMMessage(role="system", content="你必须以JSON格式回复，包含name和description字段"),
            LLMMessage(role="user", content="描述一个简单的文件操作工具")
        ]
        response = await engine.llm_client.chat_completion(messages)
        print(f"   📝 原始响应: {response.content}")
        
        # 尝试解析JSON
        try:
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response.content[json_start:json_end]
                parsed = json.loads(json_str)
                print(f"   ✅ JSON解析成功: {parsed}")
            else:
                print(f"   ⚠️ 未找到有效JSON结构")
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON解析失败: {e}")
    except Exception as e:
        print(f"   ❌ 结构化输出失败: {e}")
    
    # 测试3: 任务分析能力
    print("\n3. 测试任务分析能力...")
    try:
        complexity = await engine.intelligent_planner.analyze_task_complexity(
            "分析一个Python项目的代码结构，生成技术文档，并创建测试用例"
        )
        print(f"   ✅ 复杂度分析: {complexity.score}/10")
        print(f"   📝 分析理由: {complexity.reasoning}")
        print(f"   🔧 推荐工具: {complexity.required_tools}")
    except Exception as e:
        print(f"   ❌ 任务分析失败: {e}")
    
    return True

async def test_task_decomposition_quality():
    """测试任务分解质量"""
    print("\n🧩 测试任务分解质量")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    config.add_tool(FileReadTool())
    config.add_tool(FileWriteTool())
    engine = UniversalTaskEngine(config)
    
    # 测试复杂任务分解
    test_tasks = [
        "创建一个简单的Python web服务器",
        "分析项目代码并生成API文档", 
        "实现用户认证系统",
        "获取当前时间",
        "读取配置文件"
    ]
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n{i}. 分解任务: {task}")
        try:
            # 分析复杂度
            complexity = await engine.intelligent_planner.analyze_task_complexity(task)
            print(f"   📊 复杂度: {complexity.score}/10 ({'复杂' if complexity.needs_todo_list else '简单'})")
            
            if complexity.needs_todo_list:
                # 创建虚拟任务对象
                from utf.models.task import Task
                from utf.models.execution import ExecutionContext
                
                virtual_task = Task(
                    id=f"test_{i}",
                    query=task,
                    description=task,
                    complexity=complexity
                )
                
                execution_context = ExecutionContext(
                    session_id="test",
                    task_id=f"test_{i}"
                )
                
                # 分解任务
                available_tools = [tool.definition.name for tool in config.tools]
                todo_list = await engine.intelligent_planner.decompose_task_intelligently(
                    virtual_task, available_tools, execution_context
                )
                
                print(f"   📝 分解步骤 ({len(todo_list)}个):")
                for j, todo in enumerate(todo_list, 1):
                    print(f"      {j}. {todo.content}")
                    print(f"         🔧 工具: {', '.join(todo.tools_needed)}")
                    print(f"         ⭐ 优先级: {todo.priority}")
            else:
                print("   📝 简单任务，无需分解")
                
        except Exception as e:
            print(f"   ❌ 分解失败: {e}")
            import traceback
            traceback.print_exc()

async def test_context_management():
    """测试上下文管理能力"""
    print("\n💭 测试上下文管理能力")
    print("-" * 40)
    
    config = FrameworkConfig()
    engine = UniversalTaskEngine(config)
    
    task_id = "test_context"
    
    # 测试1: 添加不同类型的上下文
    print("1. 测试上下文添加...")
    try:
        await engine.context_manager.add_user_message(task_id, "我想要创建一个Web应用")
        await engine.context_manager.add_assistant_message(task_id, "我将帮您创建Web应用，首先分析需求")
        await engine.context_manager.add_user_message(task_id, "需要用户登录功能")
        await engine.context_manager.add_assistant_message(task_id, "好的，我将添加用户认证系统")
        
        stats = engine.context_manager.get_conversation_stats(task_id)
        print(f"   ✅ 上下文条目: {stats.get('total_entries', 0)}")
        print(f"   📊 条目类型: {stats.get('entry_types', {})}")
    except Exception as e:
        print(f"   ❌ 上下文添加失败: {e}")
    
    # 测试2: 上下文检索
    print("\n2. 测试上下文检索...")
    try:
        relevant_context = await engine.context_manager.get_relevant_context(
            task_id, "用户认证", max_tokens=1000
        )
        print(f"   ✅ 检索到相关上下文: {len(relevant_context)} 条消息")
        for msg in relevant_context[:3]:  # 显示前3条
            print(f"      {msg.role}: {msg.content[:50]}...")
    except Exception as e:
        print(f"   ❌ 上下文检索失败: {e}")
    
    # 测试3: 上下文总结
    print("\n3. 测试上下文总结...")
    try:
        summary = await engine.context_manager.summarize_conversation(task_id)
        print(f"   ✅ 对话总结: {summary[:100]}...")
    except Exception as e:
        print(f"   ❌ 上下文总结失败: {e}")

async def test_tool_execution_quality():
    """测试工具执行质量"""
    print("\n🔧 测试工具执行质量")  
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    config.add_tool(FileWriteTool())
    config.add_tool(FileReadTool())
    engine = UniversalTaskEngine(config)
    
    # 测试实际任务执行
    test_scenarios = [
        "获取当前时间并保存到文件",
        "创建一个包含系统信息的报告文件",
        "读取项目README文件的内容"
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. 测试场景: {scenario}")
        
        try:
            task_started = False
            tools_executed = 0
            task_completed = False
            errors = []
            
            async for result in engine.execute_task(scenario):
                if result.type == "task_analysis_started":
                    task_started = True
                elif result.type == "tool_execution_result":
                    tools_executed += 1
                    if not result.data.get('success', False):
                        errors.append(result.data.get('error', 'Unknown error'))
                elif result.type == "task_completed":
                    task_completed = True
                    ai_summary = result.data.get('ai_summary', '')
                    print(f"   ✅ 任务完成")
                    print(f"   🤖 AI总结: {ai_summary[:80]}...")
                    break
                elif result.type == "task_failed":
                    errors.append(result.data.get('error', 'Task failed'))
                    break
            
            print(f"   📊 执行统计:")
            print(f"      任务启动: {'✅' if task_started else '❌'}")
            print(f"      工具执行: {tools_executed} 次")
            print(f"      任务完成: {'✅' if task_completed else '❌'}")
            if errors:
                print(f"      错误数量: {len(errors)}")
                for error in errors:
                    print(f"         - {error}")
                    
        except Exception as e:
            print(f"   ❌ 执行异常: {e}")

async def test_error_handling():
    """测试错误处理能力"""
    print("\n🚨 测试错误处理能力")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    # 测试1: 故意触发错误
    print("1. 测试错误恢复机制...")
    try:
        # 模拟错误情况
        error_context = {
            'task_id': 'test_error',
            'error_source': 'test',
            'attempt_count': 1,
            'max_attempts': 3
        }
        
        test_error = RuntimeError("测试错误")
        recovery_result = await engine.error_recovery_manager.handle_error(
            test_error, error_context
        )
        
        print(f"   ✅ 错误恢复结果: {recovery_result.get('action', 'unknown')}")
        print(f"   📝 恢复消息: {recovery_result.get('message', 'No message')}")
        
        # 检查错误统计
        stats = engine.error_recovery_manager.get_recovery_statistics()
        print(f"   📊 错误统计: {stats}")
        
    except Exception as e:
        print(f"   ❌ 错误处理测试失败: {e}")

async def test_performance_monitoring():
    """测试性能监控能力"""
    print("\n📊 测试性能监控能力")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    # 测试性能监控
    print("1. 测试性能指标收集...")
    try:
        # 记录一些测试指标
        engine.performance_monitor.record_user_interaction("command_input", 0.1)
        engine.performance_monitor.record_concurrency_metrics(1, 1, 0)
        engine.performance_monitor.record_resource_usage()
        
        # 获取性能报告
        report = engine.performance_monitor.get_performance_report()
        print(f"   ✅ 性能报告生成成功")
        print(f"   📊 系统指标: {report.get('system_metrics', {}).keys()}")
        
        # 获取指标收集器统计
        all_metrics = engine.performance_monitor.collector.get_all_metrics()
        print(f"   📈 收集的指标类型: {list(all_metrics.keys())}")
        
    except Exception as e:
        print(f"   ❌ 性能监控测试失败: {e}")

async def main():
    """主测试函数"""
    print("🔍 深度功能能力检查")
    print("=" * 60)
    
    test_functions = [
        test_llm_core_capabilities,
        test_task_decomposition_quality,
        test_context_management,
        test_tool_execution_quality,
        test_error_handling,
        test_performance_monitoring
    ]
    
    results = {}
    
    for test_func in test_functions:
        try:
            result = await test_func()
            results[test_func.__name__] = True
        except Exception as e:
            print(f"\n❌ {test_func.__name__} 测试失败: {e}")
            results[test_func.__name__] = False
    
    print("\n" + "=" * 60)
    print("📋 测试结果汇总:")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        test_display = test_name.replace('test_', '').replace('_', ' ').title()
        print(f"   {status} - {test_display}")
    
    success_rate = (passed / total) * 100
    print(f"\n🎯 总体通过率: {success_rate:.1f}% ({passed}/{total})")
    
    if success_rate >= 80:
        print("✅ 核心功能运行良好！")
    elif success_rate >= 60:
        print("🟡 核心功能基本可用，有改进空间")
    else:
        print("🔴 存在重大问题，需要修复")
    
    return success_rate >= 60

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 测试中断")
        sys.exit(1)
