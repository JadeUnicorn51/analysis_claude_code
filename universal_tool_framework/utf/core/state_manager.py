"""
状态管理和持久化系统

提供任务状态的持久化、恢复和迁移功能
"""

import json
import pickle
import sqlite3
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import asdict
from contextlib import asynccontextmanager

from utf.models.task import Task, TodoItem, TaskStatus
from utf.models.execution import ExecutionContext, ExecutionResult
from utf.models.tool import ToolResult

def datetime_serializer(obj):
    """自定义datetime序列化器"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
from utf.utils.logging import get_logger


class StateStorage:
    """状态存储接口"""
    
    async def save_task_state(self, task: Task) -> None:
        """保存任务状态"""
        raise NotImplementedError
    
    async def load_task_state(self, task_id: str) -> Optional[Task]:
        """加载任务状态"""
        raise NotImplementedError
    
    async def delete_task_state(self, task_id: str) -> bool:
        """删除任务状态"""
        raise NotImplementedError
    
    async def list_task_states(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """列出任务状态"""
        raise NotImplementedError


class FileSystemStateStorage(StateStorage):
    """基于文件系统的状态存储"""
    
    def __init__(self, storage_dir: str = "./utf_state"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__)
        
        # 创建子目录
        (self.storage_dir / "tasks").mkdir(exist_ok=True)
        (self.storage_dir / "contexts").mkdir(exist_ok=True)
        (self.storage_dir / "results").mkdir(exist_ok=True)
        
        self.logger.info(f"FileSystemStateStorage initialized: {self.storage_dir}")
    
    async def save_task_state(self, task: Task) -> None:
        """保存任务状态到文件"""
        task_file = self.storage_dir / "tasks" / f"{task.id}.json"
        
        # 序列化任务数据
        task_data = {
            'id': task.id,
            'query': task.query,
            'description': task.description,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'complexity': task.complexity.model_dump() if task.complexity else None,
            'todo_list': [todo.model_dump() for todo in task.todo_list],
            'metadata': task.metadata
        }
        
        async with aiofiles.open(task_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(task_data, indent=2, ensure_ascii=False, default=datetime_serializer))
        
        self.logger.debug(f"任务状态已保存: {task.id}")
    
    async def load_task_state(self, task_id: str) -> Optional[Task]:
        """从文件加载任务状态"""
        task_file = self.storage_dir / "tasks" / f"{task_id}.json"
        
        if not task_file.exists():
            return None
        
        try:
            async with aiofiles.open(task_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                task_data = json.loads(content)
            
            # 反序列化任务
            task = Task(
                id=task_data['id'],
                query=task_data['query'],
                description=task_data['description'],
                status=TaskStatus(task_data['status']),
                created_at=datetime.fromisoformat(task_data['created_at']),
                started_at=datetime.fromisoformat(task_data['started_at']) if task_data['started_at'] else None,
                completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data['completed_at'] else None,
                metadata=task_data.get('metadata', {})
            )
            
            # 反序列化复杂度
            if task_data.get('complexity'):
                from utf.models.task import TaskComplexity
                task.complexity = TaskComplexity(**task_data['complexity'])
            
            # 反序列化TodoList
            task.todo_list = []
            for todo_data in task_data.get('todo_list', []):
                todo = TodoItem(
                    id=todo_data['id'],
                    content=todo_data['content'],
                    status=TaskStatus(todo_data['status']),
                    tools_needed=todo_data.get('tools_needed', []),
                    dependencies=todo_data.get('dependencies', []),
                    priority=todo_data.get('priority', 0),
                    estimated_duration=todo_data.get('estimated_duration'),
                    created_at=datetime.fromisoformat(todo_data['created_at']),
                    started_at=datetime.fromisoformat(todo_data['started_at']) if todo_data['started_at'] else None,
                    completed_at=datetime.fromisoformat(todo_data['completed_at']) if todo_data['completed_at'] else None,
                    metadata=todo_data.get('metadata', {})
                )
                task.todo_list.append(todo)
            
            self.logger.debug(f"任务状态已加载: {task_id}")
            return task
            
        except Exception as e:
            self.logger.error(f"加载任务状态失败: {task_id}, 错误: {e}")
            return None
    
    async def delete_task_state(self, task_id: str) -> bool:
        """删除任务状态文件"""
        task_file = self.storage_dir / "tasks" / f"{task_id}.json"
        
        try:
            if task_file.exists():
                task_file.unlink()
                self.logger.debug(f"任务状态已删除: {task_id}")
                return True
        except Exception as e:
            self.logger.error(f"删除任务状态失败: {task_id}, 错误: {e}")
        
        return False
    
    async def list_task_states(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """列出任务状态文件"""
        task_ids = []
        tasks_dir = self.storage_dir / "tasks"
        
        try:
            for task_file in tasks_dir.glob("*.json"):
                task_id = task_file.stem
                
                # 如果指定了状态过滤
                if status:
                    task = await self.load_task_state(task_id)
                    if not task or task.status != status:
                        continue
                
                task_ids.append(task_id)
                
                if limit and len(task_ids) >= limit:
                    break
            
        except Exception as e:
            self.logger.error(f"列出任务状态失败: {e}")
        
        return task_ids
    
    async def save_execution_context(self, context: ExecutionContext) -> None:
        """保存执行上下文"""
        context_file = self.storage_dir / "contexts" / f"{context.task_id}.json"
        
        context_data = {
            'session_id': context.session_id,
            'task_id': context.task_id,
            'user_id': context.user_id,
            'working_directory': context.working_directory,
            'environment_variables': context.environment_variables,
            'permissions': context.permissions,
            'max_execution_time': context.max_execution_time,
            'allow_network_access': context.allow_network_access,
            'allow_file_write': context.allow_file_write,
            'metadata': context.metadata
        }
        
        async with aiofiles.open(context_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(context_data, indent=2, ensure_ascii=False))


class DatabaseStateStorage(StateStorage):
    """基于数据库的状态存储"""
    
    def __init__(self, db_path: str = "./utf_state.db"):
        self.db_path = db_path
        self.logger = get_logger(__name__)
        self._init_database()
        
        self.logger.info(f"DatabaseStateStorage initialized: {db_path}")
    
    def _init_database(self) -> None:
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    complexity_data TEXT,
                    todo_list_data TEXT,
                    metadata_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建执行上下文表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_contexts (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    working_directory TEXT,
                    context_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建执行结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_results (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    todo_id TEXT,
                    tool_name TEXT,
                    success BOOLEAN NOT NULL,
                    result_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    async def save_task_state(self, task: Task) -> None:
        """保存任务状态到数据库"""
        await asyncio.get_event_loop().run_in_executor(
            None, self._save_task_state_sync, task
        )
    
    def _save_task_state_sync(self, task: Task) -> None:
        """同步保存任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 序列化复杂数据
            complexity_data = json.dumps(task.complexity.model_dump()) if task.complexity else None
            todo_list_data = json.dumps([todo.model_dump() for todo in task.todo_list])
            metadata_data = json.dumps(task.metadata)
            
            cursor.execute('''
                INSERT OR REPLACE INTO tasks 
                (id, query, description, status, created_at, started_at, completed_at,
                 complexity_data, todo_list_data, metadata_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                task.id,
                task.query,
                task.description,
                task.status.value,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                complexity_data,
                todo_list_data,
                metadata_data
            ))
            
            conn.commit()
    
    async def load_task_state(self, task_id: str) -> Optional[Task]:
        """从数据库加载任务状态"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._load_task_state_sync, task_id
        )
    
    def _load_task_state_sync(self, task_id: str) -> Optional[Task]:
        """同步加载任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, query, description, status, created_at, started_at, completed_at,
                       complexity_data, todo_list_data, metadata_data
                FROM tasks WHERE id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            try:
                # 反序列化任务
                task = Task(
                    id=row[0],
                    query=row[1],
                    description=row[2],
                    status=TaskStatus(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    started_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    metadata=json.loads(row[9]) if row[9] else {}
                )
                
                # 反序列化复杂度
                if row[7]:
                    from utf.models.task import TaskComplexity
                    complexity_data = json.loads(row[7])
                    task.complexity = TaskComplexity(**complexity_data)
                
                # 反序列化TodoList
                if row[8]:
                    todo_list_data = json.loads(row[8])
                    task.todo_list = []
                    for todo_data in todo_list_data:
                        todo = TodoItem(
                            id=todo_data['id'],
                            content=todo_data['content'],
                            status=TaskStatus(todo_data['status']),
                            tools_needed=todo_data.get('tools_needed', []),
                            dependencies=todo_data.get('dependencies', []),
                            priority=todo_data.get('priority', 0),
                            estimated_duration=todo_data.get('estimated_duration'),
                            created_at=datetime.fromisoformat(todo_data['created_at']),
                            started_at=datetime.fromisoformat(todo_data['started_at']) if todo_data['started_at'] else None,
                            completed_at=datetime.fromisoformat(todo_data['completed_at']) if todo_data['completed_at'] else None,
                            metadata=todo_data.get('metadata', {})
                        )
                        task.todo_list.append(todo)
                
                return task
                
            except Exception as e:
                self.logger.error(f"反序列化任务失败: {task_id}, 错误: {e}")
                return None
    
    async def delete_task_state(self, task_id: str) -> bool:
        """删除数据库中的任务状态"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._delete_task_state_sync, task_id
        )
    
    def _delete_task_state_sync(self, task_id: str) -> bool:
        """同步删除任务状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                cursor.execute('DELETE FROM execution_contexts WHERE task_id = ?', (task_id,))
                cursor.execute('DELETE FROM execution_results WHERE task_id = ?', (task_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"删除任务状态失败: {task_id}, 错误: {e}")
            return False
    
    async def list_task_states(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """列出数据库中的任务状态"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._list_task_states_sync, status, limit
        )
    
    def _list_task_states_sync(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """同步列出任务状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT id FROM tasks'
                params = []
                
                if status:
                    query += ' WHERE status = ?'
                    params.append(status.value)
                
                query += ' ORDER BY created_at DESC'
                
                if limit:
                    query += ' LIMIT ?'
                    params.append(limit)
                
                cursor.execute(query, params)
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"列出任务状态失败: {e}")
            return []


class StateManager:
    """
    状态管理器
    
    提供统一的状态管理接口和自动持久化功能
    """
    
    def __init__(
        self,
        storage: Optional[StateStorage] = None,
        auto_save_interval: int = 30  # 自动保存间隔(秒)
    ):
        self.logger = get_logger(__name__)
        self.storage = storage or FileSystemStateStorage()
        self.auto_save_interval = auto_save_interval
        
        # 内存缓存
        self._cached_tasks: Dict[str, Task] = {}
        self._cached_contexts: Dict[str, ExecutionContext] = {}
        
        # 自动保存任务
        self._auto_save_task: Optional[asyncio.Task] = None
        self._dirty_tasks: set = set()  # 需要保存的任务ID
        
        self.logger.info("StateManager initialized")
    
    async def start_auto_save(self) -> None:
        """启动自动保存"""
        if self._auto_save_task and not self._auto_save_task.done():
            return
        
        self._auto_save_task = asyncio.create_task(self._auto_save_loop())
        self.logger.info("自动保存已启动")
    
    async def stop_auto_save(self) -> None:
        """停止自动保存"""
        if self._auto_save_task and not self._auto_save_task.done():
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
        
        # 保存剩余的脏数据
        await self._save_dirty_tasks()
        self.logger.info("自动保存已停止")
    
    async def save_task(self, task: Task, force: bool = False) -> None:
        """保存任务状态"""
        self._cached_tasks[task.id] = task
        
        if force:
            await self.storage.save_task_state(task)
            self._dirty_tasks.discard(task.id)
        else:
            self._dirty_tasks.add(task.id)
    
    async def load_task(self, task_id: str) -> Optional[Task]:
        """加载任务状态"""
        # 先检查缓存
        if task_id in self._cached_tasks:
            return self._cached_tasks[task_id]
        
        # 从存储加载
        task = await self.storage.load_task_state(task_id)
        if task:
            self._cached_tasks[task_id] = task
        
        return task
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务状态"""
        # 从缓存删除
        self._cached_tasks.pop(task_id, None)
        self._dirty_tasks.discard(task_id)
        
        # 从存储删除
        return await self.storage.delete_task_state(task_id)
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """列出任务"""
        return await self.storage.list_task_states(status, limit)
    
    async def get_task_recovery_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务恢复信息"""
        task = await self.load_task(task_id)
        if not task:
            return None
        
        # 分析任务状态
        pending_todos = [todo for todo in task.todo_list if todo.status == TaskStatus.PENDING]
        in_progress_todos = [todo for todo in task.todo_list if todo.status == TaskStatus.IN_PROGRESS]
        
        recovery_info = {
            'task_id': task.id,
            'current_status': task.status.value,
            'progress': task.progress_percentage,
            'can_resume': task.status in [TaskStatus.IN_PROGRESS, TaskStatus.PENDING],
            'pending_todos': len(pending_todos),
            'in_progress_todos': len(in_progress_todos),
            'last_update': task.completed_at or task.started_at or task.created_at,
            'recovery_suggestions': self._get_recovery_suggestions(task)
        }
        
        return recovery_info
    
    def _get_recovery_suggestions(self, task: Task) -> List[str]:
        """获取恢复建议"""
        suggestions = []
        
        if task.status == TaskStatus.IN_PROGRESS:
            suggestions.append("任务正在执行中，可以直接恢复")
            
            # 检查是否有失败的TodoItem
            failed_todos = [todo for todo in task.todo_list if todo.status == TaskStatus.FAILED]
            if failed_todos:
                suggestions.append(f"有 {len(failed_todos)} 个步骤执行失败，建议检查错误原因")
        
        elif task.status == TaskStatus.PENDING:
            suggestions.append("任务尚未开始，可以重新执行")
        
        elif task.status == TaskStatus.FAILED:
            suggestions.append("任务执行失败，建议分析失败原因后重试")
        
        elif task.status == TaskStatus.COMPLETED:
            suggestions.append("任务已完成，无需恢复")
        
        return suggestions
    
    async def _auto_save_loop(self) -> None:
        """自动保存循环"""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)
                await self._save_dirty_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"自动保存失败: {e}")
    
    async def _save_dirty_tasks(self) -> None:
        """保存脏任务"""
        if not self._dirty_tasks:
            return
        
        dirty_task_ids = list(self._dirty_tasks)
        self._dirty_tasks.clear()
        
        for task_id in dirty_task_ids:
            if task_id in self._cached_tasks:
                try:
                    await self.storage.save_task_state(self._cached_tasks[task_id])
                except Exception as e:
                    self.logger.error(f"保存任务失败: {task_id}, 错误: {e}")
                    # 重新标记为脏数据
                    self._dirty_tasks.add(task_id)
        
        if dirty_task_ids:
            self.logger.debug(f"自动保存了 {len(dirty_task_ids)} 个任务")


# 全局状态管理器实例
_global_state_manager = None

def get_state_manager() -> StateManager:
    """获取全局状态管理器"""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager()
    return _global_state_manager
