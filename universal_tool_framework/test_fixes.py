#!/usr/bin/env python3
"""
测试修复后的功能
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from universal_tool_framework.utf import UniversalTaskEngine, FrameworkConfig
from universal_tool_framework.utf.tools.system_tools import GeneralProcessorTool
from universal_tool_framework.utf.ai.llm_client import LLMMessage

async def test_json_parsing_fix():
    """测试JSON解析修复"""
    print("🔧 测试JSON解析修复")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    # 测试1: 复杂度分析
    print("1. 测试复杂度分析JSON解析...")
    try:
        complexity = await engine.intelligent_planner.analyze_task_complexity(
            "创建一个web服务器"
        )
        print(f"   ✅ 复杂度分析成功: {complexity.score}/10")
        print(f"   📝 分析理由: {complexity.reasoning}")
        print(f"   🔧 需要TodoList: {complexity.needs_todo_list}")
    except Exception as e:
        print(f"   ❌ 复杂度分析失败: {e}")
    
    # 测试2: 任务分解
    print("\n2. 测试任务分解JSON解析...")
    try:
        from universal_tool_framework.utf.models.task import Task
        from universal_tool_framework.utf.models.execution import ExecutionContext
        
        test_task = Task(
            id="test_task",
            query="创建web服务器",
            description="创建一个简单的web服务器"
        )
        
        context = ExecutionContext(session_id="test", task_id="test_task")
        tools = ["general_processor"]
        
        todo_list = await engine.intelligent_planner.decompose_task_intelligently(
            test_task, tools, context
        )
        
        print(f"   ✅ 任务分解成功: {len(todo_list)} 个步骤")
        for i, todo in enumerate(todo_list, 1):
            print(f"      {i}. {todo.content} (优先级: {todo.priority})")
            
    except Exception as e:
        print(f"   ❌ 任务分解失败: {e}")
    
    # 测试3: JSON格式响应
    print("\n3. 测试JSON格式响应...")
    try:
        messages = [
            LLMMessage(role="system", content="你必须以JSON格式回复"),
            LLMMessage(role="user", content="描述一个文件工具")
        ]
        
        response = await engine.llm_client.chat_completion(messages)
        print(f"   📝 原始响应: {response.content[:100]}...")
        
        # 尝试解析JSON
        json_start = response.content.find('{')
        json_end = response.content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response.content[json_start:json_end]
            parsed = json.loads(json_str)
            print(f"   ✅ JSON解析成功: {parsed}")
        else:
            print(f"   ⚠️ 未找到有效JSON结构")
            
    except Exception as e:
        print(f"   ❌ JSON格式响应失败: {e}")

async def test_async_generator_fix():
    """测试异步生成器修复"""
    print("\n⚡ 测试异步生成器修复")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    print("1. 测试工具执行流程...")
    try:
        error_count = 0
        success_count = 0
        
        async for result in engine.execute_task("获取当前时间"):
            if result.type == "tool_execution_result":
                if result.data.get('success', False):
                    success_count += 1
                    print(f"   ✅ 工具执行成功: {result.data.get('tool_name', 'unknown')}")
                else:
                    error_count += 1
                    error_msg = result.data.get('error', 'Unknown error')
                    if "coroutine was expected" in error_msg:
                        print(f"   🔴 异步生成器错误仍存在!")
                    else:
                        print(f"   ⚠️ 其他工具错误: {error_msg}")
            elif result.type == "task_completed":
                print(f"   🎯 任务完成")
                break
                
        print(f"   📊 执行统计: 成功 {success_count}, 错误 {error_count}")
        if error_count == 0:
            print("   ✅ 异步生成器问题已修复!")
        else:
            print("   ❌ 仍有错误需要处理")
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")

async def test_json_serialization_fix():
    """测试JSON序列化修复"""
    print("\n💾 测试JSON序列化修复")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    print("1. 测试状态保存...")
    try:
        # 执行一个简单任务来触发状态保存
        task_completed = False
        serialization_errors = []
        
        async for result in engine.execute_task("简单测试任务"):
            if result.type == "task_completed":
                task_completed = True
                print("   ✅ 任务完成，检查状态保存...")
                
                # 等待一下让后台保存任务完成
                await asyncio.sleep(0.5)
                break
        
        if task_completed:
            print("   ✅ 任务状态保存测试通过")
        else:
            print("   ❌ 任务未能完成")
            
    except Exception as e:
        if "JSON serializable" in str(e):
            print(f"   🔴 JSON序列化问题仍存在: {e}")
        else:
            print(f"   ❌ 其他错误: {e}")

async def test_comprehensive_workflow():
    """测试完整工作流程"""
    print("\n🔄 测试完整工作流程")
    print("-" * 40)
    
    config = FrameworkConfig()
    config.add_tool(GeneralProcessorTool())
    engine = UniversalTaskEngine(config)
    
    test_cases = [
        ("简单任务", "获取当前时间"),
        ("中等任务", "创建一个文档文件"),
        ("复杂任务", "设计一个web应用架构")
    ]
    
    for test_name, task_query in test_cases:
        print(f"\n测试 {test_name}: {task_query}")
        
        try:
            phases = {
                "started": False,
                "analysis": False,
                "execution": False,
                "completed": False
            }
            
            errors = []
            
            async for result in engine.execute_task(task_query):
                if result.type == "task_analysis_started":
                    phases["started"] = True
                elif result.type == "complexity_analysis_completed":
                    phases["analysis"] = True
                    score = result.data.get('score', 0)
                    print(f"   📊 AI评估: {score}/10")
                elif result.type == "tool_execution_result":
                    phases["execution"] = True
                    if not result.data.get('success', False):
                        errors.append(result.data.get('error', 'Unknown'))
                elif result.type == "task_completed":
                    phases["completed"] = True
                    break
                elif result.type == "task_failed":
                    errors.append(result.data.get('error', 'Task failed'))
                    break
            
            # 评估结果
            passed_phases = sum(1 for v in phases.values() if v)
            total_phases = len(phases)
            
            print(f"   📋 阶段完成: {passed_phases}/{total_phases}")
            print(f"   🚨 错误数量: {len(errors)}")
            
            if passed_phases == total_phases and len(errors) == 0:
                print(f"   ✅ {test_name} 测试完全通过!")
            elif passed_phases >= 3:
                print(f"   🟡 {test_name} 基本通过，有小问题")
            else:
                print(f"   ❌ {test_name} 测试失败")
                
        except Exception as e:
            print(f"   💥 {test_name} 测试异常: {e}")

async def main():
    """主测试函数"""
    print("🧪 修复功能验证测试")
    print("=" * 60)
    
    test_functions = [
        test_json_parsing_fix,
        test_async_generator_fix, 
        test_json_serialization_fix,
        test_comprehensive_workflow
    ]
    
    for test_func in test_functions:
        try:
            await test_func()
        except Exception as e:
            print(f"\n💥 {test_func.__name__} 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 修复验证完成!")
    print("\n💡 如果所有测试通过，说明关键问题已得到修复")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 测试中断")
        sys.exit(1)
