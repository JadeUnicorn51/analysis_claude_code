"""
文件写入工具

基于Claude Code的Write工具实现，支持安全的文件创建和写入
"""

import time
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator

from ...tools.base import BaseTool
from ...models.tool import ToolDefinition, ToolResult


class FileWriteTool(BaseTool):
    """
    文件写入工具
    
    功能：
    - 安全的文件写入
    - 自动创建目录
    - 支持多种编码
    - 原子性写入操作
    """
    
    def _create_definition(self) -> ToolDefinition:
        """创建工具定义"""
        return ToolDefinition(
            name="file_write",
            description="写入内容到文件，支持创建新文件和覆盖现有文件",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件路径",
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                    "required": True
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码(默认utf-8)",
                    "required": False,
                    "default": "utf-8"
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式(默认false，覆盖写入)",
                    "required": False,
                    "default": False
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "是否自动创建目录(默认true)",
                    "required": False,
                    "default": True
                }
            },
            is_concurrent_safe=False,  # 文件写入不是并发安全的
            is_read_only=False,
            required_permissions=["file_write"],
            tags=["file", "write", "create"],
            version="1.0.0"
        )
    
    def _get_required_parameters(self) -> list:
        """获取必需参数"""
        return ["file_path", "content"]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        try:
            # 验证文件路径
            file_path = parameters.get("file_path")
            if not file_path or not isinstance(file_path, str):
                return False
            
            # 验证内容
            content = parameters.get("content")
            if content is None:  # 允许空字符串
                return False
            
            # 检查路径安全性
            path = Path(file_path)
            if not self._is_safe_path(path):
                return False
            
            # 验证布尔参数
            append = parameters.get("append", False)
            create_dirs = parameters.get("create_dirs", True)
            
            if not isinstance(append, bool) or not isinstance(create_dirs, bool):
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
                '.xml', '.csv', '.log', '.conf', '.ini',
                '.sql', '.sh', '.bat'
            }
            
            # 如果有扩展名，检查是否在允许列表中
            if path.suffix and path.suffix.lower() not in allowed_extensions:
                return False
        
        # 检查是否在安全目录内
        context = context or {}
        working_dir = context.get('working_directory')
        if working_dir:
            try:
                working_path = Path(working_dir).resolve()
                file_path_resolved = Path(file_path).resolve()
                
                # 检查文件是否在工作目录内
                if not str(file_path_resolved).startswith(str(working_path)):
                    return False
            except Exception:
                return False
        
        return True
    
    def is_concurrency_safe(self, parameters: Dict[str, Any]) -> bool:
        """检查并发安全性"""
        # 写入相同文件时不安全
        return False
    
    async def _execute_core(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolResult, None]:
        """核心执行逻辑"""
        start_time = time.time()
        tool_call_id = context.get('call_id', 'unknown') if context else 'unknown'
        
        file_path = parameters["file_path"]
        content = parameters["content"]
        encoding = parameters.get("encoding", "utf-8")
        append = parameters.get("append", False)
        create_dirs = parameters.get("create_dirs", True)
        
        try:
            path = Path(file_path)
            
            # 检查父目录
            parent_dir = path.parent
            if not parent_dir.exists():
                if create_dirs:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    yield self._create_success_result(
                        tool_call_id,
                        {
                            "type": "info",
                            "message": f"创建目录: {parent_dir}"
                        },
                        time.time() - start_time
                    )
                else:
                    execution_time = time.time() - start_time
                    yield self._create_error_result(
                        tool_call_id,
                        f"父目录不存在: {parent_dir}",
                        execution_time
                    )
                    return
            
            # 检查现有文件
            file_existed = path.exists()
            original_size = 0
            if file_existed:
                try:
                    original_size = path.stat().st_size
                except Exception:
                    original_size = 0
            
            # 写入文件
            mode = 'a' if append else 'w'
            
            # 原子性写入：先写入临时文件，然后重命名
            if not append:
                temp_path = path.with_suffix(path.suffix + '.tmp')
                
                async with aiofiles.open(temp_path, 'w', encoding=encoding) as f:
                    await f.write(content)
                
                # 原子性重命名
                temp_path.replace(path)
            else:
                # 追加模式直接写入
                async with aiofiles.open(path, mode, encoding=encoding) as f:
                    await f.write(content)
            
            # 获取最终文件信息
            final_stat = path.stat()
            final_size = final_stat.st_size
            
            execution_time = time.time() - start_time
            
            # 构建结果
            result_data = {
                "file_path": str(path.absolute()),
                "operation": "append" if append else ("overwrite" if file_existed else "create"),
                "content_length": len(content),
                "file_size": final_size,
                "encoding": encoding,
                "lines_written": content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            }
            
            if file_existed:
                result_data["original_size"] = original_size
                result_data["size_change"] = final_size - original_size
            
            yield self._create_success_result(
                tool_call_id,
                result_data,
                execution_time,
                metadata={
                    "file_type": path.suffix,
                    "write_mode": mode,
                    "atomic_write": not append
                }
            )
            
        except PermissionError:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"没有权限写入文件: {file_path}",
                execution_time
            )
            
        except UnicodeEncodeError as e:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"编码错误: {str(e)}，请检查内容或更换编码",
                execution_time
            )
            
        except OSError as e:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"文件系统错误: {str(e)}",
                execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            yield self._create_error_result(
                tool_call_id,
                f"写入文件失败: {str(e)}",
                execution_time
            )
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径安全性"""
        try:
            # 解析路径
            resolved_path = path.resolve()
            path_str = str(resolved_path)
            
            # 检查危险路径
            dangerous_paths = [
                '/etc', '/proc', '/sys', '/dev', '/boot',
                '/bin', '/sbin', '/usr/bin', '/usr/sbin'
            ]
            
            for dangerous in dangerous_paths:
                if path_str.startswith(dangerous):
                    return False
            
            # 检查路径遍历
            if '..' in str(path) or path_str.count('/') > 10:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _before_execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """执行前检查"""
        file_path = parameters["file_path"]
        path = Path(file_path)
        
        # 如果文件存在且不是追加模式，记录警告
        if path.exists() and not parameters.get("append", False):
            self.logger.warning(f"将覆盖现有文件: {file_path}")
    
    def estimate_execution_time(self, parameters: Dict[str, Any]) -> float:
        """估算执行时间"""
        content = parameters.get("content", "")
        content_size = len(content.encode('utf-8'))
        
        # 基于内容大小估算时间
        if content_size < 1024:  # < 1KB
            return 0.1
        elif content_size < 1024 * 1024:  # < 1MB
            return 0.5
        else:  # >= 1MB
            return min(content_size / (1024 * 1024), 5.0)  # 最多5秒
