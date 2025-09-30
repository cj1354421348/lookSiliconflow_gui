"""
日志格式化器模块

实现了各种日志格式化器，包括标准文本格式化器和JSON格式化器。
这些格式化器类继承自抽象基类，提供了具体的格式化实现。
"""

import json
import re
from typing import List, Dict, Any
from datetime import datetime

from ..core.abstracts import AbstractLogFormatter
from ..core.types import LogEntry


class StandardLogFormatter(AbstractLogFormatter):
    """标准日志格式化器
    
    支持类似Python标准logging模块的格式字符串
    """
    
    def __init__(self, format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
        """初始化标准日志格式化器
        
        Args:
            format_string: 格式字符串
        """
        super().__init__(format_string)
    
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        # 使用正则表达式替换所有字段
        result = self._field_pattern.sub(
            lambda match: self._format_field(record, match),
            self._format_string
        )
        return result
    
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
        elif field_name == "threadName":
            return f"Thread-{record.thread_id}"
        elif field_name == "timestamp":
            return record.timestamp.isoformat()
        elif field_name == "created":
            return record.timestamp.timestamp()
        elif field_name == "msecs":
            return record.timestamp.microsecond // 1000
        
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


class JsonLogFormatter(AbstractLogFormatter):
    """JSON日志格式化器
    
    将日志记录格式化为JSON格式，便于结构化日志处理和分析
    """
    
    def __init__(self, 
                 format_string: str = None,
                 include_timestamp: bool = True,
                 include_level: bool = True,
                 include_logger_name: bool = True,
                 include_thread_id: bool = True,
                 include_exception: bool = True,
                 include_context: bool = True,
                 ensure_ascii: bool = False):
        """初始化JSON日志格式化器
        
        Args:
            format_string: 格式字符串（在JSON格式中不使用）
            include_timestamp: 是否包含时间戳
            include_level: 是否包含日志级别
            include_logger_name: 是否包含日志器名称
            include_thread_id: 是否包含线程ID
            include_exception: 是否包含异常信息
            include_context: 是否包含上下文信息
            ensure_ascii: 是否确保ASCII编码
        """
        super().__init__(format_string or "%(message)s")
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger_name = include_logger_name
        self.include_thread_id = include_thread_id
        self.include_exception = include_exception
        self.include_context = include_context
        self.ensure_ascii = ensure_ascii
    
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的JSON字符串
        """
        # 构建JSON对象
        json_obj = {}
        
        # 添加基本字段
        if self.include_timestamp:
            json_obj["timestamp"] = record.timestamp.isoformat()
        
        if self.include_level:
            json_obj["level"] = record.level.name
            json_obj["level_value"] = record.level.value
        
        if self.include_logger_name:
            json_obj["logger_name"] = record.logger_name
        
        if self.include_thread_id:
            json_obj["thread_id"] = record.thread_id
        
        # 添加消息
        json_obj["message"] = record.message
        
        # 添加异常信息
        if self.include_exception and record.has_exception:
            json_obj["exception"] = {
                "type": record.exception_info.exception_type,
                "message": record.exception_info.exception_message
            }
            if record.exception_info.traceback_text:
                json_obj["exception"]["traceback"] = record.exception_info.traceback_text
            if record.exception_info.context:
                json_obj["exception"]["context"] = record.exception_info.context
        
        # 添加上下文信息
        if self.include_context and record.context:
            json_obj["context"] = record.context
        
        # 转换为JSON字符串
        return json.dumps(json_obj, ensure_ascii=self.ensure_ascii, separators=(',', ':'))
    
    def supports_field(self, field_name: str) -> bool:
        """检查是否支持指定字段
        
        Args:
            field_name: 字段名称
            
        Returns:
            bool: 是否支持
        """
        # JSON格式化器支持所有字段
        return True
    
    def get_supported_fields(self) -> List[str]:
        """获取支持的字段列表
        
        Returns:
            List[str]: 支持的字段列表
        """
        return [
            "timestamp", "level", "level_value", "logger_name", "thread_id",
            "message", "exception", "context"
        ]


class ColoredLogFormatter(AbstractLogFormatter):
    """彩色日志格式化器
    
    为控制台输出添加颜色，提高可读性
    """
    
    def __init__(self, format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
        """初始化彩色日志格式化器
        
        Args:
            format_string: 格式字符串
        """
        super().__init__(format_string)
        self._colors = {
            "DEBUG": "\033[36m",    # 青色
            "INFO": "\033[32m",     # 绿色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",    # 红色
            "CRITICAL": "\033[35m", # 紫色
        }
        self._reset_color = "\033[0m"
    
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的彩色字符串
        """
        # 先使用标准格式化
        formatted = super().format(record)
        
        # 添加颜色
        if record.level.name in self._colors:
            color_code = self._colors[record.level.name]
            formatted = f"{color_code}{formatted}{self._reset_color}"
        
        return formatted


class SimpleLogFormatter(AbstractLogFormatter):
    """简单日志格式化器
    
    提供简洁的日志格式，适合生产环境使用
    """
    
    def __init__(self, format_string: str = "%(asctime)s [%(levelname)s] %(message)s"):
        """初始化简单日志格式化器
        
        Args:
            format_string: 格式字符串
        """
        super().__init__(format_string)
    
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        # 使用父类的格式化方法
        return super().format(record)


class DetailedLogFormatter(AbstractLogFormatter):
    """详细日志格式化器
    
    提供详细的日志格式，包含文件名、行号等信息，适合开发环境使用
    """
    
    def __init__(self, format_string: str = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"):
        """初始化详细日志格式化器
        
        Args:
            format_string: 格式字符串
        """
        super().__init__(format_string)
    
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        # 使用父类的格式化方法
        return super().format(record)
    
    def _get_field_value(self, record: LogEntry, field_name: str) -> Any:
        """获取字段值
        
        Args:
            record: 日志记录
            field_name: 字段名称
            
        Returns:
            Any: 字段值
        """
        # 先尝试父类的方法
        value = super()._get_field_value(record, field_name)
        
        # 如果是未知字段，尝试从上下文中获取
        if value == f"%({field_name})" and record.context:
            return record.context.get(field_name, f"%({field_name})")
        
        return value


class StructuredLogFormatter(AbstractLogFormatter):
    """结构化日志格式化器
    
    提供键值对格式的日志，便于解析和处理
    """
    
    def __init__(self, format_string: str = None):
        """初始化结构化日志格式化器
        
        Args:
            format_string: 格式字符串（在结构化格式中不使用）
        """
        super().__init__(format_string or "%(message)s")
    
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的结构化字符串
        """
        # 构建键值对
        parts = []
        
        # 添加时间戳
        parts.append(f"timestamp={record.timestamp.isoformat()}")
        
        # 添加级别
        parts.append(f"level={record.level.name}")
        
        # 添加日志器名称
        parts.append(f"logger={record.logger_name}")
        
        # 添加线程ID
        parts.append(f"thread_id={record.thread_id}")
        
        # 添加消息
        parts.append(f"message={self._escape_value(record.message)}")
        
        # 添加异常信息
        if record.has_exception:
            parts.append(f"exception_type={record.exception_info.exception_type}")
            parts.append(f"exception_message={self._escape_value(record.exception_info.exception_message)}")
            if record.exception_info.traceback_text:
                parts.append(f"exception_traceback={self._escape_value(record.exception_info.traceback_text)}")
        
        # 添加上下文信息
        if record.context:
            for key, value in record.context.items():
                parts.append(f"{key}={self._escape_value(str(value))}")
        
        # 组合所有部分
        return " ".join(parts)
    
    def _escape_value(self, value: str) -> str:
        """转义值中的特殊字符
        
        Args:
            value: 要转义的值
            
        Returns:
            str: 转义后的值
        """
        # 替换空格和特殊字符
        value = value.replace("\\", "\\\\")
        value = value.replace(" ", "\\ ")
        value = value.replace("=", "\\=")
        value = value.replace("\"", "\\\"")
        value = value.replace("'", "\\'")
        
        # 如果值包含空格，用引号包围
        if " " in value:
            value = f'"{value}"'
        
        return value
    
    def supports_field(self, field_name: str) -> bool:
        """检查是否支持指定字段
        
        Args:
            field_name: 字段名称
            
        Returns:
            bool: 是否支持
        """
        # 结构化格式化器支持所有字段
        return True
    
    def get_supported_fields(self) -> List[str]:
        """获取支持的字段列表
        
        Returns:
            List[str]: 支持的字段列表
        """
        return [
            "timestamp", "level", "logger", "thread_id", "message",
            "exception_type", "exception_message", "exception_traceback"
        ]