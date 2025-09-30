"""
兼容性适配器模块

实现了日志系统的兼容性适配器，使新日志系统能够兼容旧的使用方式。
包括与Python标准logging模块的兼容性、旧API的适配等功能。
"""

import logging
import sys
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime

from ..core.interfaces import Logger, LogConfig, LogObserver, LogOutputStrategy
from ..core.types import LogLevel, LogEntry, ExceptionInfo
from ..singleton.log_manager import LogManager, get_log_manager
from ..config.log_config import LogConfigData
from ..strategies.output_strategies import ConsoleOutputStrategy
from ..observers.log_observers import ConsoleLogObserver
from ..formatters.log_formatters import StandardLogFormatter


class LoggingHandlerAdapter(logging.Handler):
    """标准logging模块处理器适配器
    
    将Python标准logging模块的日志记录转发到新日志系统
    """
    
    def __init__(self, logger_name: str = "adapter"):
        """初始化适配器
        
        Args:
            logger_name: 日志器名称
        """
        super().__init__()
        self.logger_name = logger_name
        self._logger: Optional[Logger] = None
        self._lock = threading.Lock()
    
    def emit(self, record: logging.LogRecord) -> None:
        """转发日志记录
        
        Args:
            record: 标准logging模块的日志记录
        """
        try:
            # 获取或创建日志器
            logger = self._get_logger()
            
            if logger is None:
                return
            
            # 转换日志级别
            level = self._convert_level(record.levelno)
            
            # 创建异常信息
            exception_info = None
            if record.exc_info:
                exception_info = ExceptionInfo.from_exception(
                    record.exc_info[1], 
                    include_traceback=True
                )
            
            # 创建上下文
            context = {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "pathname": record.pathname
            }
            
            # 记录日志
            logger.log(
                level=level,
                message=record.getMessage(),
                exception_info=exception_info,
                context=context
            )
            
        except Exception:
            # 静默处理适配器错误，避免影响主程序
            pass
    
    def _get_logger(self) -> Optional[Logger]:
        """获取日志器
        
        Returns:
            Optional[Logger]: 日志器实例，如果获取失败则返回None
        """
        if self._logger is None:
            with self._lock:
                if self._logger is None:
                    try:
                        manager = get_log_manager()
                        if manager.is_initialized():
                            self._logger = manager.get_logger(self.logger_name)
                    except Exception:
                        pass
        
        return self._logger
    
    def _convert_level(self, levelno: int) -> LogLevel:
        """转换日志级别
        
        Args:
            levelno: 标准logging模块的日志级别值
            
        Returns:
            LogLevel: 新日志系统的日志级别
        """
        if levelno >= logging.CRITICAL:
            return LogLevel.CRITICAL
        elif levelno >= logging.ERROR:
            return LogLevel.ERROR
        elif levelno >= logging.WARNING:
            return LogLevel.WARNING
        elif levelno >= logging.INFO:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG


class LoggerAdapter:
    """日志器适配器
    
    提供与旧API兼容的接口，使现有代码能够无缝迁移到新日志系统
    """
    
    def __init__(self, name: str):
        """初始化日志器适配器
        
        Args:
            name: 日志器名称
        """
        self.name = name
        self._logger: Optional[Logger] = None
        self._lock = threading.Lock()
    
    def _get_logger(self) -> Optional[Logger]:
        """获取日志器
        
        Returns:
            Optional[Logger]: 日志器实例，如果获取失败则返回None
        """
        if self._logger is None:
            with self._lock:
                if self._logger is None:
                    try:
                        manager = get_log_manager()
                        if manager.is_initialized():
                            self._logger = manager.get_logger(self.name)
                    except Exception:
                        # 如果无法获取日志器，返回None
                        pass
        
        return self._logger
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """记录调试级别日志
        
        Args:
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            logger.debug(msg, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """记录信息级别日志
        
        Args:
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            logger.info(msg, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """记录警告级别日志
        
        Args:
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            logger.warning(msg, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """记录错误级别日志
        
        Args:
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            logger.error(msg, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """记录严重错误级别日志
        
        Args:
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            logger.critical(msg, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """记录异常日志
        
        Args:
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            logger.exception(msg, **kwargs)
    
    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """记录指定级别的日志
        
        Args:
            level: 日志级别
            msg: 日志消息
            *args: 消息格式化参数
            **kwargs: 其他参数
        """
        logger = self._get_logger()
        if logger:
            if args:
                msg = msg % args
            
            # 转换日志级别
            log_level = self._convert_level(level)
            
            logger.log(log_level, msg, **kwargs)
    
    def setLevel(self, level: int) -> None:
        """设置日志级别（兼容标准logging模块）
        
        Args:
            level: 日志级别
        """
        # 新日志系统的级别是通过配置设置的，这里不做处理
        pass
    
    def addHandler(self, handler: logging.Handler) -> None:
        """添加处理器（兼容标准logging模块）
        
        Args:
            handler: 处理器
        """
        # 新日志系统使用输出策略，这里不做处理
        pass
    
    def removeHandler(self, handler: logging.Handler) -> None:
        """移除处理器（兼容标准logging模块）
        
        Args:
            handler: 处理器
        """
        # 新日志系统使用输出策略，这里不做处理
        pass
    
    def _convert_level(self, level: int) -> LogLevel:
        """转换日志级别
        
        Args:
            level: 标准logging模块的日志级别值
            
        Returns:
            LogLevel: 新日志系统的日志级别
        """
        if level >= logging.CRITICAL:
            return LogLevel.CRITICAL
        elif level >= logging.ERROR:
            return LogLevel.ERROR
        elif level >= logging.WARNING:
            return LogLevel.WARNING
        elif level >= logging.INFO:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG


class LoggingManagerAdapter:
    """日志管理器适配器
    
    提供与标准logging模块兼容的接口，使现有代码能够无缝迁移到新日志系统
    """
    
    def __init__(self):
        """初始化日志管理器适配器"""
        self._loggers: Dict[str, LoggerAdapter] = {}
        self._lock = threading.Lock()
    
    def getLogger(self, name: str) -> LoggerAdapter:
        """获取日志器（兼容标准logging模块）
        
        Args:
            name: 日志器名称
            
        Returns:
            LoggerAdapter: 日志器适配器
        """
        with self._lock:
            if name not in self._loggers:
                self._loggers[name] = LoggerAdapter(name)
            
            return self._loggers[name]
    
    def basicConfig(self, **kwargs) -> None:
        """基本配置（兼容标准logging模块）
        
        Args:
            **kwargs: 配置参数
        """
        try:
            # 解析配置参数
            level = kwargs.get('level', logging.INFO)
            format_str = kwargs.get('format', None)
            filename = kwargs.get('filename', None)
            filemode = kwargs.get('filemode', 'a')
            
            # 转换日志级别
            log_level = self._convert_level(level)
            
            # 创建配置
            from ..builders.config_builder import LogConfigBuilder
            builder = LogConfigBuilder()
            builder.set_level(log_level)
            
            # 设置格式字符串
            if format_str:
                builder.set_format(format_str)
            
            # 添加文件输出策略
            if filename:
                from ..strategies.output_strategies import FileOutputStrategy
                builder.add_file_output(filename)
            
            # 获取配置并初始化日志管理器
            config = builder.build()
            manager = get_log_manager()
            manager.initialize(config)
            
        except Exception:
            # 如果配置失败，使用默认配置
            self._default_config()
    
    def _default_config(self) -> None:
        """默认配置"""
        try:
            from ..builders.config_builder import LogConfigBuilder
            builder = LogConfigBuilder()
            config = builder.build()
            
            manager = get_log_manager()
            manager.initialize(config)
        except Exception:
            # 如果默认配置也失败，静默处理
            pass
    
    def _convert_level(self, level: int) -> LogLevel:
        """转换日志级别
        
        Args:
            level: 标准logging模块的日志级别值
            
        Returns:
            LogLevel: 新日志系统的日志级别
        """
        if level >= logging.CRITICAL:
            return LogLevel.CRITICAL
        elif level >= logging.ERROR:
            return LogLevel.ERROR
        elif level >= logging.WARNING:
            return LogLevel.WARNING
        elif level >= logging.INFO:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG
    
    def shutdown(self) -> None:
        """关闭日志管理器（兼容标准logging模块）"""
        try:
            manager = get_log_manager()
            manager.shutdown()
        except Exception:
            # 静默处理关闭错误
            pass


class CompatibilityLayer:
    """兼容性层
    
    提供完整的兼容性支持，包括全局函数和类
    """
    
    def __init__(self):
        """初始化兼容性层"""
        self._manager_adapter = LoggingManagerAdapter()
        self._installed = False
        self._lock = threading.Lock()
    
    def install(self) -> None:
        """安装兼容性层
        
        将标准logging模块的函数替换为兼容性函数
        """
        if self._installed:
            return
        
        with self._lock:
            if self._installed:
                return
            
            # 保存原始函数
            self._original_getLogger = logging.getLogger
            self._original_basicConfig = logging.basicConfig
            self._original_shutdown = logging.shutdown
            
            # 替换函数
            logging.getLogger = self.getLogger
            logging.basicConfig = self.basicConfig
            logging.shutdown = self.shutdown
            
            # 标记已安装
            self._installed = True
    
    def uninstall(self) -> None:
        """卸载兼容性层
        
        恢复标准logging模块的原始函数
        """
        if not self._installed:
            return
        
        with self._lock:
            if not self._installed:
                return
            
            # 恢复原始函数
            logging.getLogger = self._original_getLogger
            logging.basicConfig = self._original_basicConfig
            logging.shutdown = self._original_shutdown
            
            # 标记已卸载
            self._installed = False
    
    def getLogger(self, name: str) -> LoggerAdapter:
        """获取日志器（兼容标准logging模块）
        
        Args:
            name: 日志器名称
            
        Returns:
            LoggerAdapter: 日志器适配器
        """
        return self._manager_adapter.getLogger(name)
    
    def basicConfig(self, **kwargs) -> None:
        """基本配置（兼容标准logging模块）
        
        Args:
            **kwargs: 配置参数
        """
        self._manager_adapter.basicConfig(**kwargs)
    
    def shutdown(self) -> None:
        """关闭日志管理器（兼容标准logging模块）"""
        self._manager_adapter.shutdown()
    
    def is_installed(self) -> bool:
        """检查兼容性层是否已安装
        
        Returns:
            bool: 是否已安装
        """
        return self._installed


# 全局兼容性层实例
_global_compatibility_layer = None


def get_compatibility_layer() -> CompatibilityLayer:
    """获取全局兼容性层实例
    
    Returns:
        CompatibilityLayer: 全局兼容性层实例
    """
    global _global_compatibility_layer
    if _global_compatibility_layer is None:
        _global_compatibility_layer = CompatibilityLayer()
    return _global_compatibility_layer


def install_compatibility() -> None:
    """安装兼容性层的便捷函数"""
    layer = get_compatibility_layer()
    layer.install()


def uninstall_compatibility() -> None:
    """卸载兼容性层的便捷函数"""
    layer = get_compatibility_layer()
    layer.uninstall()


# 便捷函数
def getLogger(name: str) -> LoggerAdapter:
    """获取日志器的便捷函数（兼容标准logging模块）
    
    Args:
        name: 日志器名称
        
    Returns:
        LoggerAdapter: 日志器适配器
    """
    layer = get_compatibility_layer()
    return layer.getLogger(name)


def basicConfig(**kwargs) -> None:
    """基本配置的便捷函数（兼容标准logging模块）
    
    Args:
        **kwargs: 配置参数
    """
    layer = get_compatibility_layer()
    layer.basicConfig(**kwargs)


def shutdown() -> None:
    """关闭日志管理器的便捷函数（兼容标准logging模块）"""
    layer = get_compatibility_layer()
    layer.shutdown()


def add_logging_handler_to_standard_logger(logger_name: str, handler: logging.Handler) -> None:
    """向标准logging模块的日志器添加处理器
    
    Args:
        logger_name: 日志器名称
        handler: 处理器
    """
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)


def setup_standard_logging_adapter(logger_name: str = "adapter") -> LoggingHandlerAdapter:
    """设置标准logging模块的适配器
    
    Args:
        logger_name: 适配器使用的日志器名称
        
    Returns:
        LoggingHandlerAdapter: 适配器实例
    """
    # 创建适配器
    adapter = LoggingHandlerAdapter(logger_name)
    
    # 获取根日志器
    root_logger = logging.getLogger()
    
    # 添加适配器到根日志器
    root_logger.addHandler(adapter)
    
    # 设置根日志器级别
    root_logger.setLevel(logging.DEBUG)
    
    return adapter