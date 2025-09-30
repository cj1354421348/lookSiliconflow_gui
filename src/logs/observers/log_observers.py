"""
日志观察者模块

实现了各种日志观察者，包括GUI观察者、文件观察者和网络观察者。
这些观察者类实现了LogObserver接口，可以监听日志事件并执行相应操作。
"""

import os
import threading
import json
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

from ..core.interfaces import LogObserver
from ..core.types import LogEntry
from ..strategies.output_strategies import ThreadSafeCallback


class GuiLogObserver(LogObserver):
    """GUI日志观察者
    
    将日志事件转发到GUI回调函数，支持线程安全的GUI更新
    """
    
    def __init__(self, callback: Callable[[str], None]):
        """初始化GUI日志观察者
        
        Args:
            callback: GUI回调函数
        """
        self.callback = callback
        self._thread_safe_callback = ThreadSafeCallback(callback)
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        formatted_message = self._format_record(record)
        self._thread_safe_callback.safe_call(formatted_message)
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "GuiLogObserver"
    
    def _format_record(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        timestamp_str = record.timestamp.strftime("%H:%M:%S")
        level_str = record.level.name
        return f"[{timestamp_str}] [{level_str}] {record.message}"


class FileLogObserver(LogObserver):
    """文件日志观察者
    
    将日志事件写入到指定文件中
    """
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """初始化文件日志观察者
        
        Args:
            file_path: 日志文件路径
            encoding: 文件编码
        """
        self.file_path = file_path
        self.encoding = encoding
        self._file_lock = threading.Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """确保日志文件存在"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding=self.encoding):
                pass
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        with self._file_lock:
            with open(self.file_path, 'a', encoding=self.encoding) as f:
                f.write(self._format_record(record) + '\n')
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "FileLogObserver"
    
    def _format_record(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        timestamp_str = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_str = record.level.name
        return f"[{timestamp_str}] [{level_str}] [{record.logger_name}] {record.message}"


class NetworkLogObserver(LogObserver):
    """网络日志观察者
    
    将日志事件发送到远程日志服务
    """
    
    def __init__(self, 
                 endpoint: str,
                 method: str = "POST",
                 headers: Optional[Dict[str, str]] = None,
                 timeout: int = 5,
                 max_retries: int = 3):
        """初始化网络日志观察者
        
        Args:
            endpoint: 远程日志服务端点
            method: HTTP方法
            headers: HTTP头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        self.endpoint = endpoint
        self.method = method.upper()
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = None  # 延迟初始化
    
    @property
    def session(self):
        """获取HTTP会话"""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        # 准备发送数据
        log_data = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "logger_name": record.logger_name,
            "thread_id": record.thread_id
        }
        
        # 发送数据（带重试）
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=self.method,
                    url=self.endpoint,
                    headers=self.headers,
                    json=log_data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败，记录到本地
                    print(f"网络日志发送失败: {e}")
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "NetworkLogObserver"


class FilteredLogObserver(LogObserver):
    """过滤日志观察者 - 装饰器模式
    
    对其他观察者进行过滤，只处理符合条件的日志记录
    """
    
    def __init__(self, 
                 observer: LogObserver, 
                 level_filter=None,
                 logger_name_filter: Optional[str] = None,
                 message_filter: Optional[Callable[[str], bool]] = None):
        """初始化过滤日志观察者
        
        Args:
            observer: 被装饰的观察者
            level_filter: 日志级别过滤器
            logger_name_filter: 日志器名称过滤器
            message_filter: 消息过滤器
        """
        self._observer = observer
        self._level_filter = level_filter
        self._logger_name_filter = logger_name_filter
        self._message_filter = message_filter
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件（带过滤）"""
        if self._should_process(record):
            self._observer.on_log_record(record)
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return f"Filtered({self._observer.get_observer_name()})"
    
    def _should_process(self, record: LogEntry) -> bool:
        """判断是否应该处理该日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            bool: 是否应该处理
        """
        # 级别过滤
        if self._level_filter and record.level.value < self._level_filter.value:
            return False
        
        # 日志器名称过滤
        if self._logger_name_filter and self._logger_name_filter not in record.logger_name:
            return False
        
        # 消息过滤
        if self._message_filter and not self._message_filter(record.message):
            return False
        
        return True


class CompositeLogObserver(LogObserver):
    """复合日志观察者
    
    可以组合多个观察者，实现多个观察者的协同工作
    """
    
    def __init__(self, observers: Optional[List[LogObserver]] = None):
        """初始化复合日志观察者
        
        Args:
            observers: 观察者列表
        """
        self._observers = observers or []
    
    def add_observer(self, observer: LogObserver) -> None:
        """添加观察者
        
        Args:
            observer: 日志观察者
        """
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: LogObserver) -> None:
        """移除观察者
        
        Args:
            observer: 日志观察者
        """
        if observer in self._observers:
            self._observers.remove(observer)
    
    def clear_observers(self) -> None:
        """清空所有观察者"""
        self._observers.clear()
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        for observer in self._observers:
            try:
                observer.on_log_record(record)
            except Exception as e:
                observer.on_error(e, {"record": record})
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "CompositeLogObserver"
    
    def on_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """处理错误事件
        
        Args:
            error: 异常对象
            context: 错误上下文
        """
        # 通知所有观察者
        for observer in self._observers:
            observer.on_error(error, context)


class ConsoleLogObserver(LogObserver):
    """控制台日志观察者
    
    将日志事件输出到控制台，支持彩色输出
    """
    
    def __init__(self, use_colors: bool = True):
        """初始化控制台日志观察者
        
        Args:
            use_colors: 是否使用颜色输出
        """
        self.use_colors = use_colors
        self._color_map = {
            "DEBUG": "\033[36m",    # 青色
            "INFO": "\033[32m",     # 绿色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",    # 红色
            "CRITICAL": "\033[35m", # 紫色
        }
        self._reset_color = "\033[0m"
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        formatted_message = self._format_record(record)
        
        if self.use_colors and record.level.name in self._color_map:
            color_code = self._color_map[record.level.name]
            formatted_message = f"{color_code}{formatted_message}{self._reset_color}"
        
        print(formatted_message)
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "ConsoleLogObserver"
    
    def _format_record(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        timestamp_str = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_str = record.level.name
        return f"[{timestamp_str}] [{level_str}] [{record.logger_name}] {record.message}"


class MemoryLogObserver(LogObserver):
    """内存日志观察者
    
    将日志事件存储在内存中，适合测试和调试使用
    """
    
    def __init__(self, max_records: int = 1000):
        """初始化内存日志观察者
        
        Args:
            max_records: 最大记录数
        """
        self.max_records = max_records
        self._records = []
        self._lock = threading.Lock()
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        with self._lock:
            self._records.append(record)
            
            # 如果超过最大记录数，删除最旧的记录
            if len(self._records) > self.max_records:
                self._records.pop(0)
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "MemoryLogObserver"
    
    def get_records(self) -> List[LogEntry]:
        """获取所有日志记录
        
        Returns:
            List[LogEntry]: 日志记录列表
        """
        with self._lock:
            return self._records.copy()
    
    def clear_records(self) -> None:
        """清空所有日志记录"""
        with self._lock:
            self._records.clear()
    
    def get_records_count(self) -> int:
        """获取日志记录数量
        
        Returns:
            int: 记录数量
        """
        with self._lock:
            return len(self._records)


class JsonFileLogObserver(LogObserver):
    """JSON文件日志观察者
    
    将日志事件以JSON格式写入到文件中
    """
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """初始化JSON文件日志观察者
        
        Args:
            file_path: 日志文件路径
            encoding: 文件编码
        """
        self.file_path = file_path
        self.encoding = encoding
        self._file_lock = threading.Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """确保日志文件存在"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding=self.encoding):
                pass
    
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        with self._file_lock:
            with open(self.file_path, 'a', encoding=self.encoding) as f:
                json_line = json.dumps(self._record_to_dict(record), ensure_ascii=False)
                f.write(json_line + '\n')
    
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        return "JsonFileLogObserver"
    
    def _record_to_dict(self, record: LogEntry) -> Dict[str, Any]:
        """将日志记录转换为字典
        
        Args:
            record: 日志记录
            
        Returns:
            Dict[str, Any]: 字典格式的日志记录
        """
        result = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "level_value": record.level.value,
            "message": record.message,
            "logger_name": record.logger_name,
            "thread_id": record.thread_id
        }
        
        if record.has_exception:
            result["exception"] = {
                "type": record.exception_info.exception_type,
                "message": record.exception_info.exception_message
            }
            if record.exception_info.traceback_text:
                result["exception"]["traceback"] = record.exception_info.traceback_text
        
        if record.context:
            result["context"] = record.context
        
        return result