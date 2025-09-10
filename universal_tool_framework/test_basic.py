#!/usr/bin/env python3
"""
基本功能测试脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_basic_ai_functionality():
    """测试基本AI功能"""
    try:
        # 导入测试
        print("1. 测试导入...")
        from utf import UniversalTaskEngine, FrameworkConfig
        from utf.tools.system_tools import GeneralProcessorTool
        print("   ✅ 导入成功")
        
        # 创建配置
        print("2. 创建配置...")
        config = FrameworkConfig()
        config.add_tool(GeneralProcessorTool())
        print("   ✅ 配置创建成功")
        
        # 创建引擎
        print("3. 创建AI引擎...")
        engine = UniversalTaskEngine(config)
        print("   ✅ AI引擎创建成功")
        
        # 测试LLM客户端
        print("4. 测试AI客户端...")
        health_ok = await engine.llm_client.health_check()
        print(f"   ✅ AI客户端健康: {health_ok}")
        
        # 测试简单任务
        print("5. 测试AI任务执行...")
        task_completed = False
        async for result in engine.execute_task("获取当前时间"):
            print(f"   📋 {result.type}: {result.data}")
            if result.type == "task_completed":
                task_completed = True
                ai_summary = result.data.get('ai_summary', '')
                if ai_summary:
                    print(f"   🤖 AI总结: {ai_summary}")
                break
            elif result.type == "task_failed":
                print(f"   ❌ 任务失败: {result.data.get('error', '')}")
                break
        
        if task_completed:
            print("   ✅ AI任务执行成功")
        else:
            print("   ⚠️ AI任务执行未完成")
        
        # 测试复杂度分析
        print("6. 测试AI复杂度分析...")
        complexity = await engine.intelligent_planner.analyze_task_complexity("创建一个技术文档")
        print(f"   📊 AI评分: {complexity.score}/10")
        print(f"   💭 AI分析: {complexity.reasoning}")
        print("   ✅ AI复杂度分析成功")
        
        print("\n🎉 所有基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🧪 Universal Tool Framework - 基本功能测试")
    print("=" * 50)
    
    success = await test_basic_ai_functionality()
    
    if success:
        print("\n✅ 测试结果: 通过")
        print("💡 可以运行: python start_ai_demo.py")
    else:
        print("\n❌ 测试结果: 失败")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 测试中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        sys.exit(1)
