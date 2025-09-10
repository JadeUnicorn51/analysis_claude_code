"""
文件读取工具

基于Claude Code的Read工具实现，支持多种文件类型和安全检查
"""

import time
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator

from utf.tools.base import BaseTool
from utf.models.tool import ToolDefinition, ToolResult
from utf.utils.validation import ValidationError


class FileReadTool(BaseTool):
    """
    文件读取工具
    
    功能：
    - 读取文本文件内容
    - 支持大文件分段读取
    - 自动检测文件编码
    - 安全性检查
    """
    
    def _create_definition(self) -> ToolDefinition:
        """创建工具定义"""
        return ToolDefinition(
            name="file_read",
            description="读取文件内容，支持文本文件的安全读取",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径",
                    "required": True
                },
                "offset": {
                    "type": "integer", 
                    "description": "读取起始行号(可选)",
                    "required": False,
                    "default": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "读取行数限制(可选，默认2000行)",
                    "required": False,
                    "default": 2000
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码(可选，默认自动检测)",
                    "required": False,
                    "default": "utf-8"
                }
            },
            is_concurrent_safe=True,
            is_read_only=True,
            required_permissions=["file_read"],
            tags=["file", "read", "text"],
            version="1.0.0"
        )
    
    def _get_required_parameters(self) -> list:
        """获取必需参数"""
        return ["file_path"]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        try:
            # 验证文件路径
            file_path = parameters.get("file_path")
            if not file_path:
                return False
            
            # 检查路径安全性
            path = Path(file_path)
            if not self._is_safe_path(path):
                return False
            
            # 验证数值参数
            offset = parameters.get("offset", 0)
            limit = parameters.get("limit", 2000)
            
            if not isinstance(offset, int) or offset < 0:
                return False
            
            if not isinstance(limit, int) or limit <= 0 or limit > 10000:
                return False
            
            return True
            
        except Exception:
            return False
    
    def check_permissions(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """权限检查"""
        if not super().check_permissions(parameters, context):
            return False
        
        # 检查文件扩展名
        file_path = parameters.get("file_path")
        if file_path:
            path = Path(file_path)
            
            # 允许的文件扩展名
            allowed_extensions = {
                '.txt', '.md', '.json', '.yaml', '.yml', 
                '.py', '.js', '.ts', '.html', '.css',
                '.xml', '.csv', '.log', '.conf', '.ini'
            }
            
            if path.suffix.lower() not in allowed_extensions:
                return False
        
        return True
    
    async def _execute_core(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolResult, None]:
        """核心执行逻辑"""
        start_time = time.time()
        tool_call_id = context.get('call_id', 'unknown') if context else 'unknown'
        
        file_path = parameters["file_path"]
        offset = parameters.get("offset", 0)
        limit = parameters.get("limit", 2000)
        encoding = parameters.get("encoding", "utf-8")
        
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                execution_time = time.time() - start_time
                yield self._create_error_result(
                    tool_call_id,
                    f"文件不存在: {file_path}",
                    execution_time
                )
                return
            
            # 检查是否为文件
            if not path.is_file():
                execution_time = time.time() - start_time
                yield self._create_error_result(
                    tool_call_id,
                    f"路径不是文件: {file_path}",
                    execution_time
                )
                return
            
            # 获取文件信息
            file_stat = path.stat()
            file_size = file_stat.st_size
            
            # 如果文件过大，警告用户
            if file_size > 10 * 1024 * 1024:  # 10MB
                yield self._create_success_result(
                    tool_call_id,
                    {
                        "type": "warning",
                        "message": f"文件较大 ({file_size / 1024 / 1024:.1f}MB)，建议使用分段读取"
                    },
                    time.time() - start_time
                )
            
            # 读取文件内容
            content = await self._read_file_content(path, offset, limit, encoding)
            
            execution_time = time.time() - start_time
            
            # 构建结果
            result_data = {
                "file_path": str(path.absolute()),
                "content": content["text"],
                "lines_read": content["lines_count"],
                "total_lines": content["total_lines"],
                "file_size": file_size,
                "encoding": encoding,
                "offset": offset,
                "limit": limit,
                "is_truncated": content["is_truncated"]
            }
            
            # 添加安全警告（如果需要）
            if self._should_add_security_warning(content["text"]):
                result_data["security_warning"] = "检测到可能的安全敏感内容，请谨慎处理"
            
            yield self._create_success_result(
                tool_call_id,
                result_data,
                execution_time,
                metadata={
                    "file_type": path.suffix,
                    "read_mode": "partial" if offset > 0 or content["is_truncated"] else "full"
                }
            )
            
        except UnicodeDecodeError as e:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"文件编码错误: {str(e)}，请尝试其他编码",
                execution_time
            )
            
        except PermissionError:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"没有权限读取文件: {file_path}",
                execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"读取文件失败: {str(e)}",
                execution_time
            )
    
    async def _read_file_content(
        self,
        path: Path,
        offset: int,
        limit: int,
        encoding: str
    ) -> Dict[str, Any]:
        """读取文件内容"""
        
        lines = []
        total_lines = 0
        current_line = 0
        is_truncated = False
        
        try:
            async with aiofiles.open(path, 'r', encoding=encoding) as f:
                async for line in f:
                    total_lines += 1
                    
                    # 跳过offset之前的行
                    if current_line < offset:
                        current_line += 1
                        continue
                    
                    # 检查是否达到限制
                    if len(lines) >= limit:
                        is_truncated = True
                        break
                    
                    # 添加行号
                    line_with_number = f"{current_line + 1:6d}|{line.rstrip()}"
                    lines.append(line_with_number)
                    current_line += 1
                    
        except UnicodeDecodeError:
            # 尝试其他常见编码
            for fallback_encoding in ['gbk', 'gb2312', 'latin1']:
                try:
                    async with aiofiles.open(path, 'r', encoding=fallback_encoding) as f:
                        lines = []
                        total_lines = 0
                        current_line = 0
                        
                        async for line in f:
                            total_lines += 1
                            
                            if current_line < offset:
                                current_line += 1
                                continue
                            
                            if len(lines) >= limit:
                                is_truncated = True
                                break
                            
                            line_with_number = f"{current_line + 1:6d}|{line.rstrip()}"
                            lines.append(line_with_number)
                            current_line += 1
                    
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise UnicodeDecodeError(encoding, b'', 0, 1, "无法解码文件内容")
        
        return {
            "text": "\n".join(lines),
            "lines_count": len(lines),
            "total_lines": total_lines,
            "is_truncated": is_truncated
        }
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径安全性"""
        try:
            # 解析路径
            resolved_path = path.resolve()
            
            # 检查是否包含危险的路径遍历
            path_str = str(resolved_path)
            if '..' in path_str or path_str.startswith('/etc') or path_str.startswith('/proc'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _should_add_security_warning(self, content: str) -> bool:
        """检查是否需要添加安全警告"""
        # 检查是否包含敏感信息
        sensitive_patterns = [
            'password', 'secret', 'token', 'key', 'credential',
            'private_key', 'api_key', 'access_token'
        ]
        
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in sensitive_patterns)
    
    def estimate_execution_time(self, parameters: Dict[str, Any]) -> float:
        """估算执行时间"""
        file_path = parameters.get("file_path", "")
        limit = parameters.get("limit", 2000)
        
        try:
            path = Path(file_path)
            if path.exists():
                file_size = path.stat().st_size
                # 基于文件大小和读取行数估算
                base_time = min(file_size / (1024 * 1024), 2.0)  # 最多2秒
                line_time = limit / 10000  # 每10000行约1秒
                return base_time + line_time
        except Exception:
            pass
        
        return 1.0  # 默认1秒
