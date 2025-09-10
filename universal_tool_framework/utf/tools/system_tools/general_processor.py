"""
通用处理器工具

处理一般性任务的通用工具
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator

from ...tools.base import BaseTool
from ...models.tool import ToolDefinition, ToolResult


class GeneralProcessorTool(BaseTool):
    """
    通用处理器工具
    
    用于处理不需要特定工具的一般性任务
    """
    
    def _create_definition(self) -> ToolDefinition:
        """创建工具定义"""
        return ToolDefinition(
            name="general_processor",
            description="处理一般性任务，提供基础的文本处理和信息生成功能",
            parameters={
                "task": {
                    "type": "string",
                    "description": "要处理的任务描述",
                    "required": True
                },
                "context": {
                    "type": "string",
                    "description": "任务上下文信息",
                    "required": False,
                    "default": ""
                }
            },
            is_concurrent_safe=True,
            is_read_only=True,
            required_permissions=[],
            tags=["general", "processor", "text"],
            version="1.0.0"
        )
    
    def _get_required_parameters(self) -> list:
        """获取必需参数"""
        return ["task"]
    
    async def _execute_core(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolResult, None]:
        """核心执行逻辑"""
        start_time = time.time()
        tool_call_id = context.get('call_id', 'unknown') if context else 'unknown'
        
        task = parameters["task"]
        task_context = parameters.get("context", "")
        
        try:
            # 模拟处理过程
            await self._sleep_if_needed(0.5)  # 模拟处理时间
            
            # 生成处理结果
            result = self._process_task(task, task_context)
            
            execution_time = time.time() - start_time
            
            yield self._create_success_result(
                tool_call_id,
                result,
                execution_time,
                metadata={
                    "task_type": self._classify_task(task),
                    "processing_time": execution_time
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"处理任务失败: {str(e)}",
                execution_time
            )
    
    def _process_task(self, task: str, task_context: str) -> Dict[str, Any]:
        """处理任务"""
        task_lower = task.lower()
        
        # 根据任务类型生成不同的结果
        if any(keyword in task_lower for keyword in ['时间', '日期', 'time', 'date']):
            return self._generate_time_info()
        
        elif any(keyword in task_lower for keyword in ['hello', '你好', '问候']):
            return self._generate_greeting()
        
        elif any(keyword in task_lower for keyword in ['分析', '研究', 'analyze']):
            return self._generate_analysis_result(task, task_context)
        
        elif any(keyword in task_lower for keyword in ['创建', '生成', 'create', 'generate']):
            return self._generate_creation_result(task, task_context)
        
        else:
            return self._generate_general_result(task, task_context)
    
    def _generate_time_info(self) -> Dict[str, Any]:
        """生成时间信息"""
        now = datetime.now()
        return {
            "type": "time_info",
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": now.timestamp(),
            "weekday": now.strftime("%A"),
            "message": f"当前时间是 {now.strftime('%Y年%m月%d日 %H:%M:%S')}"
        }
    
    def _generate_greeting(self) -> Dict[str, Any]:
        """生成问候信息"""
        return {
            "type": "greeting",
            "message": "你好！我是Universal Tool Framework，很高兴为您服务！",
            "features": [
                "智能任务分解",
                "工具自动选择", 
                "用户交互控制",
                "并发执行优化"
            ]
        }
    
    def _generate_analysis_result(self, task: str, context: str) -> Dict[str, Any]:
        """生成分析结果"""
        return {
            "type": "analysis",
            "task": task,
            "analysis": {
                "summary": f"已分析任务: {task}",
                "key_points": [
                    "任务内容已理解",
                    "分析框架已建立",
                    "待进一步深入研究"
                ],
                "recommendations": [
                    "收集更多相关信息",
                    "建立详细分析模型",
                    "生成具体行动计划"
                ]
            },
            "context": context if context else "无额外上下文"
        }
    
    def _generate_creation_result(self, task: str, context: str) -> Dict[str, Any]:
        """生成创建结果"""
        return {
            "type": "creation",
            "task": task,
            "creation_plan": {
                "objective": f"创建目标: {task}",
                "steps": [
                    "确定创建规格",
                    "设计基础结构", 
                    "实现核心功能",
                    "测试和优化"
                ],
                "timeline": "预计完成时间: 根据复杂度而定",
                "resources": [
                    "需要文件写入权限",
                    "可能需要外部工具支持"
                ]
            },
            "context": context if context else "无额外上下文"
        }
    
    def _generate_general_result(self, task: str, context: str) -> Dict[str, Any]:
        """生成通用结果"""
        return {
            "type": "general",
            "task": task,
            "processing_result": {
                "status": "processed",
                "message": f"已处理任务: {task}",
                "suggestions": [
                    "任务已被通用处理器处理",
                    "如需更专业的处理，请使用专用工具",
                    "可以提供更具体的指令以获得更好的结果"
                ]
            },
            "context": context if context else "无额外上下文",
            "next_steps": [
                "根据任务类型选择合适的专用工具",
                "提供更详细的任务描述",
                "指定具体的输出要求"
            ]
        }
    
    def _classify_task(self, task: str) -> str:
        """分类任务"""
        task_lower = task.lower()
        
        if any(keyword in task_lower for keyword in ['时间', '日期', 'time']):
            return "time_related"
        elif any(keyword in task_lower for keyword in ['hello', '你好', '问候']):
            return "greeting"
        elif any(keyword in task_lower for keyword in ['分析', 'analyze']):
            return "analysis"
        elif any(keyword in task_lower for keyword in ['创建', '生成', 'create']):
            return "creation"
        else:
            return "general"
    
    def estimate_execution_time(self, parameters: Dict[str, Any]) -> float:
        """估算执行时间"""
        return 0.5  # 通用处理器通常很快
