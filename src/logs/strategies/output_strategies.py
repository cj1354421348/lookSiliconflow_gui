"""
输出策略模块

实现了各种日志输出策略，包括文件输出、控制台输出和GUI输出。
这些策略类继承自抽象基类，提供了具体的输出实现。
"""

import os
import threading
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from ..core.abstracts import AbstractLogOutputStrategy
from ..core.interfaces import LogFormatter
from ..core.types import LogEntry


class ConsoleOutputStrategy(AbstractLogOutputStrategy):
    """控制台输出策略"""
    
    def __init__(self, use_colors: bool = True, formatter: Optional[LogFormatter] = None):
        """初始化控制台输出策略
        
        Args:
            use_colors: 是否使用颜色输出
            formatter: 日志格式化器
        """
        super().__init__(formatter)
        self.use_colors = use_colors
        self._color_map = {
            "DEBUG": "\033[36m",    # 青色
            "INFO": "\033[32m",     # 绿色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",    # 红色
            "CRITICAL": "\033[35m", # 紫色
        }
        self._reset_color = "\033[0m"
    
    def output(self, record: LogEntry) -> None:
        """输出日志记录到控制台"""
        self._ensure_not_closed()
        
        formatted_message = self._format_record(record)
        
        if self.use_colors and record.level.name in self._color_map:
            color_code = self._color_map[record.level.name]
            formatted_message = f"{color_code}{formatted_message}{self._reset_color}"
        
        print(formatted_message)
    
    def flush(self) -> None:
        """刷新输出缓冲区"""
        # 控制台输出不需要刷新
        pass
    
    def close(self) -> None:
        """关闭输出策略"""
        super().close()
    
    def is_thread_safe(self) -> bool:
        """检查输出策略是否线程安全"""
        # 控制台输出是线程安全的
        return True


class FileOutputStrategy(AbstractLogOutputStrategy):
    """文件输出策略"""
    
    def __init__(self, 
                 file_path: str, 
                 encoding: str = 'utf-8',
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 formatter: Optional[LogFormatter] = None):
        """初始化文件输出策略
        
        Args:
            file_path: 日志文件路径
            encoding: 文件编码
            max_file_size: 最大文件大小
            backup_count: 备份文件数量
            formatter: 日志格式化器
        """
        super().__init__(formatter)
        self.file_path = file_path
        self.encoding = encoding
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self._file_lock = threading.Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """确保日志文件存在"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding=self.encoding):
                pass
    
    def output(self, record: LogEntry) -> None:
        """输出日志记录到文件"""
        self._ensure_not_closed()
        
        with self._file_lock:
            # 检查文件大小，如果超过限制则进行轮转
            if self._should_rotate():
                self._rotate_file()
            
            with open(self.file_path, 'a', encoding=self.encoding) as f:
                f.write(self._format_record(record) + '\n')
    
    def _should_rotate(self) -> bool:
        """检查是否需要轮转文件"""
        try:
            return os.path.getsize(self.file_path) >= self.max_file_size
        except OSError:
            return False
    
    def _rotate_file(self) -> None:
        """轮转日志文件"""
        # 删除最旧的备份文件
        oldest_backup = f"{self.file_path}.{self.backup_count}"
        if os.path.exists(oldest_backup):
            os.remove(oldest_backup)
        
        # 重命名现有备份文件
        for i in range(self.backup_count - 1, 0, -1):
            old_file = f"{self.file_path}.{i}"
            new_file = f"{self.file_path}.{i + 1}"
            if os.path.exists(old_file):
                os.rename(old_file, new_file)
        
        # 重命名当前日志文件
        if os.path.exists(self.file_path):
            os.rename(self.file_path, f"{self.file_path}.1")
    
    def flush(self) -> None:
        """刷新文件缓冲区"""
        # 文件输出是同步的，不需要刷新
        pass
    
    def close(self) -> None:
        """关闭输出策略"""
        super().close()
    
    def is_thread_safe(self) -> bool:
        """检查输出策略是否线程安全"""
        # 文件输出使用锁保护，是线程安全的
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = super().get_strategy_info()
        info.update({
            "file_path": self.file_path,
            "encoding": self.encoding,
            "max_file_size": self.max_file_size,
            "backup_count": self.backup_count
        })
        return info


class GuiOutputStrategy(AbstractLogOutputStrategy):
    """GUI输出策略"""
    
    def __init__(self, callback: Callable[[str], None], formatter: Optional[LogFormatter] = None):
        """初始化GUI输出策略
        
        Args:
            callback: GUI回调函数
            formatter: 日志格式化器
        """
        super().__init__(formatter)
        self.callback = callback
        self._thread_safe_callback = ThreadSafeCallback(callback)
    
    def output(self, record: LogEntry) -> None:
        """输出日志记录到GUI"""
        self._ensure_not_closed()
        
        formatted_message = self._format_record(record)
        self._thread_safe_callback.safe_call(formatted_message)
    
    def flush(self) -> None:
        """刷新输出缓冲区"""
        # GUI输出是同步的，不需要刷新
        pass
    
    def close(self) -> None:
        """关闭输出策略"""
        self._thread_safe_callback.stop()
        super().close()
    
    def is_thread_safe(self) -> bool:
        """检查输出策略是否线程安全"""
        # GUI输出使用线程安全回调，是线程安全的
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = super().get_strategy_info()
        info.update({
            "callback": str(self.callback),
            "thread_safe_callback": str(self._thread_safe_callback)
        })
        return info


class RemoteOutputStrategy(AbstractLogOutputStrategy):
    """远程输出策略"""
    
    def __init__(self, 
                 endpoint: str,
                 method: str = "POST",
                 headers: Optional[Dict[str, str]] = None,
                 timeout: int = 5,
                 batch_size: int = 10,
                 max_retries: int = 3,
                 formatter: Optional[LogFormatter] = None):
        """初始化远程输出策略
        
        Args:
            endpoint: 远程日志服务端点
            method: HTTP方法
            headers: HTTP头
            timeout: 超时时间（秒）
            batch_size: 批量发送大小
            max_retries: 最大重试次数
            formatter: 日志格式化器
        """
        super().__init__(formatter)
        self.endpoint = endpoint
        self.method = method.upper()
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._batch = []
        self._batch_lock = threading.Lock()
        self._session = None  # 延迟初始化
    
    @property
    def session(self):
        """获取HTTP会话"""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session
    
    def output(self, record: LogEntry) -> None:
        """输出日志记录到远程服务"""
        self._ensure_not_closed()
        
        with self._batch_lock:
            self._batch.append(record)
            
            # 如果达到批量大小，则发送
            if len(self._batch) >= self.batch_size:
                self._send_batch()
    
    def _send_batch(self) -> None:
        """发送批量日志"""
        if not self._batch:
            return
        
        # 准备发送数据
        logs_data = []
        for record in self._batch:
            logs_data.append({
                "timestamp": record.timestamp.isoformat(),
                "level": record.level.name,
                "message": record.message,
                "logger_name": record.logger_name,
                "thread_id": record.thread_id
            })
        
        # 清空当前批次
        self._batch.clear()
        
        # 发送数据（带重试）
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=self.method,
                    url=self.endpoint,
                    headers=self.headers,
                    json={"logs": logs_data},
                    timeout=self.timeout
                )
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败，记录到本地
                    print(f"远程日志发送失败: {e}")
    
    def flush(self) -> None:
        """刷新输出缓冲区"""
        # 发送剩余的日志
        with self._batch_lock:
            if self._batch:
                self._send_batch()
    
    def close(self) -> None:
        """关闭输出策略"""
        self.flush()
        if self._session:
            self._session.close()
        super().close()
    
    def is_thread_safe(self) -> bool:
        """检查输出策略是否线程安全"""
        # 远程输出使用锁保护，是线程安全的
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = super().get_strategy_info()
        info.update({
            "endpoint": self.endpoint,
            "method": self.method,
            "timeout": self.timeout,
            "batch_size": self.batch_size,
            "max_retries": self.max_retries
        })
        return info


class ThreadSafeCallback:
    """线程安全的回调执行器"""
    
    def __init__(self, callback: Callable[[str], None]):
        """初始化线程安全回调
        
        Args:
            callback: 回调函数
        """
        self.callback = callback
        self._lock = threading.Lock()
        self._main_thread_queue = None
        self._setup_main_thread_queue()
    
    def _setup_main_thread_queue(self) -> None:
        """设置主线程队列"""
        import queue
        self._main_thread_queue = queue.Queue()
        
        # 启动主线程处理器
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
    
    def _process_queue(self) -> None:
        """处理队列中的消息"""
        while not self._stop_event.is_set():
            try:
                message = self._main_thread_queue.get(timeout=0.1)
                with self._lock:
                    try:
                        self.callback(message)
                    except Exception:
                        # 静默处理GUI回调错误
                        pass
            except queue.Empty:
                continue
    
    def safe_call(self, message: str) -> None:
        """线程安全地调用回调函数
        
        Args:
            message: 日志消息
        """
        if threading.current_thread() is threading.main_thread():
            # 主线程直接调用
            with self._lock:
                try:
                    self.callback(message)
                except Exception:
                    # 静默处理GUI回调错误
                    pass
        else:
            # 子线程通过队列调用
            if self._main_thread_queue:
                try:
                    self._main_thread_queue.put_nowait(message)
                except queue.Full:
                    # 队列满，丢弃消息
                    pass
    
    def stop(self) -> None:
        """停止线程安全回调"""
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
        if hasattr(self, '_worker_thread'):
            self._worker_thread.join(timeout=1.0)