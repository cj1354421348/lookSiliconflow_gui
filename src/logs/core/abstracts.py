"""
抽象基类模块

定义了日志系统的抽象基类，提供了部分默认实现，减少了具体实现类的工作量。
这些抽象基类实现了相应的接口，并提供了通用的功能实现。
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import sys
import re

from .interfaces import Logger, LogOutputStrategy, LogFormatter, LogObserver, LogFilter
from .types import LogLevel, LogEntry, ExceptionInfo


class AbstractLogger(Logger, ABC):
    """抽象日志器基类
    
    提供了Logger接口的部分默认实现，减少了具体实现类的工作量
    """
    
    def __init__(self, name: str):
        """初始化抽象日志器
        
        Args:
            name: 日志器名称
        """
        self.name = name
        self._observers: List[LogObserver] = []
        self._observers_lock = None  # 延迟初始化
        self._filters: List[LogFilter] = []
        self._filters_lock = None  # 延迟初始化
    
    def debug(self, message: str, **kwargs) -> None:
        """记录调试级别日志"""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """记录信息级别日志"""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录警告级别日志"""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """记录错误级别日志"""
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误级别日志"""
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """记录异常日志"""
        exc_info = kwargs.pop('exc_info', sys.exc_info())
        if exc_info and exc_info[0] is not None:
            exception_info = ExceptionInfo.from_exception(
                exc_info[1], 
                include_traceback=True,
                context=kwargs.get('context')
            )
            kwargs['exception_info'] = exception_info
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def add_observer(self, observer: LogObserver) -> None:
        """添加日志观察者"""
        if self._observers_lock is None:
            import threading
            self._observers_lock = threading.Lock()
        
        with self._observers_lock:
            if observer not in self._observers:
                self._observers.append(observer)
    
    def remove_observer(self, observer: LogObserver) -> None:
        """移除日志观察者"""
        if self._observers_lock is None:
            import threading
            self._observers_lock = threading.Lock()
        
        with self._observers_lock:
            if observer in self._observers:
                self._observers.remove(observer)
    
    def add_filter(self, filter_instance: LogFilter) -> None:
        """添加日志过滤器"""
        if self._filters_lock is None:
            import threading
            self._filters_lock = threading.Lock()
        
        with self._filters_lock:
            if filter_instance not in self._filters:
                self._filters.append(filter_instance)
    
    def remove_filter(self, filter_instance: LogFilter) -> None:
        """移除日志过滤器"""
        if self._filters_lock is None:
            import threading
            self._filters_lock = threading.Lock()
        
        with self._filters_lock:
            if filter_instance in self._filters:
                self._filters.remove(filter_instance)
    
    def clear_filters(self) -> None:
        """清空所有日志过滤器"""
        if self._filters_lock is None:
            import threading
            self._filters_lock = threading.Lock()
        
        with self._filters_lock:
            self._filters.clear()
    
    def _notify_observers(self, record: LogEntry) -> None:
        """通知所有观察者
        
        Args:
            record: 日志记录
        """
        if self._observers_lock is None:
            import threading
            self._observers_lock = threading.Lock()
        
        with self._observers_lock:
            for observer in self._observers:
                try:
                    observer.on_log_record(record)
                except Exception as e:
                    observer.on_error(e, {"record": record})
    
    def _should_log(self, record: LogEntry) -> bool:
        """检查是否应该记录日志
        
        Args:
            record: 日志记录
            
        Returns:
            bool: 是否应该记录
        """
        # 检查级别
        if not self.is_enabled_for(record.level):
            return False
        
        # 检查过滤器
        if self._filters_lock is None:
            import threading
            self._filters_lock = threading.Lock()
        
        with self._filters_lock:
            for filter_instance in self._filters:
                if not filter_instance.filter(record):
                    return False
        
        return True
    
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """记录日志（抽象方法实现）
        
        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 其他参数
        """
        # 默认实现：创建日志条目并处理
        from datetime import datetime
        import threading
        
        # 创建日志条目
        record = LogEntry(
            timestamp=datetime.now(),
            level=level,
            logger_name=self.name,
            message=message,
            thread_id=threading.get_ident(),
            context=kwargs.get('context'),
            exception_info=kwargs.get('exception_info')
        )
        
        # 检查是否应该记录
        if self._should_log(record):
            # 通知观察者
            self._notify_observers(record)
    
    def flush(self) -> None:
        """刷新日志缓冲区（抽象方法实现）"""
        # 默认实现：什么都不做
        pass
    
    def shutdown(self) -> None:
        """关闭日志器（抽象方法实现）"""
        # 默认实现：清空观察者和过滤器
        if self._observers_lock is not None:
            with self._observers_lock:
                self._observers.clear()
        
        if self._filters_lock is not None:
            with self._filters_lock:
                self._filters.clear()
    
    def update_config(self, config: 'LogConfig') -> None:
        """更新日志配置（抽象方法实现）
        
        Args:
            config: 新的日志配置
        """
        # 默认实现：什么都不做，子类可以覆盖
        pass
    
    def get_logger_info(self) -> Dict[str, Any]:
        """获取日志器信息"""
        return {
            "logger_name": self.name,
            "logger_type": self.__class__.__name__,
            "observers_count": len(self._observers),
            "filters_count": len(self._filters)
        }


class AbstractLogOutputStrategy(LogOutputStrategy, ABC):
    """抽象日志输出策略基类
    
    提供了LogOutputStrategy接口的部分默认实现，减少了具体实现类的工作量
    """
    
    def __init__(self, formatter: Optional[LogFormatter] = None):
        """初始化抽象日志输出策略
        
        Args:
            formatter: 日志格式化器
        """
        self._formatter = formatter
        self._closed = False
    
    def set_formatter(self, formatter: LogFormatter) -> None:
        """设置日志格式化器
        
        Args:
            formatter: 日志格式化器
        """
        self._formatter = formatter
    
    def get_formatter(self) -> Optional[LogFormatter]:
        """获取日志格式化器
        
        Returns:
            Optional[LogFormatter]: 日志格式化器
        """
        return self._formatter
    
    def _format_record(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        if self._formatter:
            return self._formatter.format(record)
        
        # 默认格式化
        timestamp_str = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_str = record.level.name
        return f"[{timestamp_str}] [{level_str}] [{record.logger_name}] {record.message}"
    
    def close(self) -> None:
        """关闭输出策略"""
        self._closed = True
    
    @property
    def is_closed(self) -> bool:
        """检查输出策略是否已关闭
        
        Returns:
            bool: 是否已关闭
        """
        return self._closed
    
    def _ensure_not_closed(self) -> None:
        """确保输出策略未关闭
        
        Raises:
            RuntimeError: 输出策略已关闭
        """
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} 已关闭")
    
    def flush(self) -> None:
        """刷新输出缓冲区"""
        # 默认实现：什么都不做
        pass
    
    def is_thread_safe(self) -> bool:
        """检查输出策略是否线程安全
        
        Returns:
            bool: 是否线程安全
        """
        # 默认实现：不保证线程安全
        return False
    
    def supports_formatting(self) -> bool:
        """检查输出策略是否支持自定义格式
        
        Returns:
            bool: 是否支持自定义格式
        """
        # 默认实现：支持格式化
        return True


class AbstractLogFormatter(LogFormatter, ABC):
    """抽象日志格式化器基类
    
    提供了LogFormatter接口的部分默认实现，减少了具体实现类的工作量
    """
    
    def __init__(self, format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
        """初始化抽象日志格式化器
        
        Args:
            format_string: 格式字符串
        """
        self._format_string = format_string
        self._field_pattern = re.compile(r'%\((\w+)\)')
        self._supported_fields = self._extract_supported_fields()
    
    def _extract_supported_fields(self) -> List[str]:
        """从格式字符串中提取支持的字段
        
        Returns:
            List[str]: 支持的字段列表
        """
        return self._field_pattern.findall(self._format_string)
    
    def set_format_string(self, format_string: str) -> None:
        """设置格式字符串
        
        Args:
            format_string: 格式字符串
        """
        self._format_string = format_string
        self._supported_fields = self._extract_supported_fields()
    
    def get_format_string(self) -> str:
        """获取格式字符串
        
        Returns:
            str: 格式字符串
        """
        return self._format_string
    
    def supports_field(self, field_name: str) -> bool:
        """检查是否支持指定字段
        
        Args:
            field_name: 字段名称
            
        Returns:
            bool: 是否支持
        """
        return field_name in self._supported_fields
    
    def get_supported_fields(self) -> List[str]:
        """获取支持的字段列表
        
        Returns:
            List[str]: 支持的字段列表
        """
        return self._supported_fields.copy()
    
    def _get_field_value(self, record: LogEntry, field_name: str) -> Any:
        """获取字段值
        
        Args:
            record: 日志记录
            field_name: 字段名称
            
        Returns:
            Any: 字段值
        """
        # 标准字段
        if field_name == "asctime":
            return record.timestamp.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        elif field_name == "name":
            return record.logger_name
        elif field_name == "levelname":
            return record.level.name
        elif field_name == "levelno":
            return record.level.value
        elif field_name == "message":
            return record.message
        elif field_name == "thread":
            return record.thread_id
        elif field_name == "timestamp":
            return record.timestamp.isoformat()
        
        # 异常信息字段
        if record.has_exception:
            if field_name == "exc_info":
                return record.exception_info.exception_message
            elif field_name == "exc_text":
                return record.exception_info.traceback_text or ""
        
        # 上下文字段
        if record.context and field_name in record.context:
            return record.context[field_name]
        
        # 未知字段
        return f"%({field_name})"
    
    def _format_field(self, record: LogEntry, field_match) -> str:
        """格式化单个字段
        
        Args:
            record: 日志记录
            field_match: 字段匹配对象
            
        Returns:
            str: 格式化后的字段值
        """
        field_name = field_match.group(1)
        value = self._get_field_value(record, field_name)
        return str(value)
    
    def clone(self) -> 'AbstractLogFormatter':
        """克隆格式化器
        
        Returns:
            AbstractLogFormatter: 格式化器的克隆
        """
        return self.__class__(self._format_string)