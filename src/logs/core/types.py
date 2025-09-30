"""
核心数据类型模块

定义了日志系统的核心数据类型，包括日志级别枚举、日志记录数据类等。
这些数据类型是整个日志系统的基础。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import traceback


class LogLevel(Enum):
    """日志级别枚举
    
    定义了标准的日志级别，与Python标准logging模块兼容
    """
    DEBUG = 10      # 调试信息，用于问题诊断
    INFO = 20       # 一般信息，记录程序运行状态
    WARNING = 30    # 警告信息，表示可能的问题
    ERROR = 40      # 错误信息，表示发生了错误
    CRITICAL = 50   # 严重错误，表示可能导致程序终止的错误
    
    @classmethod
    def from_name(cls, name: str) -> 'LogLevel':
        """从名称获取日志级别
        
        Args:
            name: 日志级别名称
            
        Returns:
            LogLevel: 日志级别
            
        Raises:
            ValueError: 不支持的日志级别名称
        """
        try:
            return cls[name.upper()]
        except KeyError:
            raise ValueError(f"不支持的日志级别: {name}")
    
    @property
    def is_debug(self) -> bool:
        """是否为调试级别"""
        return self == LogLevel.DEBUG
    
    @property
    def is_info(self) -> bool:
        """是否为信息级别"""
        return self == LogLevel.INFO
    
    @property
    def is_warning(self) -> bool:
        """是否为警告级别"""
        return self == LogLevel.WARNING
    
    @property
    def is_error(self) -> bool:
        """是否为错误级别"""
        return self == LogLevel.ERROR
    
    @property
    def is_critical(self) -> bool:
        """是否为严重错误级别"""
        return self == LogLevel.CRITICAL


@dataclass
class ExceptionInfo:
    """异常信息数据类
    
    封装了异常的详细信息，便于日志记录和分析
    """
    exception_type: str
    exception_message: str
    traceback_text: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """后初始化处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @classmethod
    def from_exception(cls, 
                      exception: Exception, 
                      include_traceback: bool = True,
                      context: Optional[Dict[str, Any]] = None) -> 'ExceptionInfo':
        """从异常对象创建异常信息
        
        Args:
            exception: 异常对象
            include_traceback: 是否包含堆栈跟踪
            context: 异常上下文信息
            
        Returns:
            ExceptionInfo: 异常信息实例
        """
        traceback_text = None
        if include_traceback:
            traceback_text = traceback.format_exc()
        
        return cls(
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback_text=traceback_text,
            context=context
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的异常信息
        """
        result = {
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
        
        if self.traceback_text:
            result["traceback_text"] = self.traceback_text
        
        if self.context:
            result["context"] = self.context
        
        return result


@dataclass
class LogEntry:
    """日志条目数据类
    
    封装了单条日志记录的所有信息，是日志系统的核心数据结构
    """
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str
    thread_id: int
    exception_info: Optional[ExceptionInfo] = None
    context: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """后初始化处理"""
        # 确保时间戳有时区信息
        if self.timestamp.tzinfo is None:
            import datetime as dt
            self.timestamp = self.timestamp.replace(tzinfo=dt.timezone.utc)
    
    @property
    def level_name(self) -> str:
        """获取日志级别名称"""
        return self.level.name
    
    @property
    def has_exception(self) -> bool:
        """是否包含异常信息"""
        return self.exception_info is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的日志记录
        """
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "level_value": self.level.value,
            "message": self.message,
            "logger_name": self.logger_name,
            "thread_id": self.thread_id
        }
        
        if self.exception_info:
            result["exception_info"] = self.exception_info.to_dict()
        
        if self.context:
            result["context"] = self.context
        
        return result
    
    def copy_with(self, **changes) -> 'LogEntry':
        """创建带有指定更改的副本
        
        Args:
            **changes: 要更改的字段
            
        Returns:
            LogEntry: 新的日志记录实例
        """
        # 创建当前字段的字典
        field_values = {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "logger_name": self.logger_name,
            "thread_id": self.thread_id,
            "exception_info": self.exception_info,
            "context": self.context.copy() if self.context else {}
        }
        
        # 应用更改
        field_values.update(changes)
        
        # 创建新实例
        return LogEntry(**field_values)