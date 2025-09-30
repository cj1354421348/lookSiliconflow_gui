"""
错误处理模块

实现了日志系统的错误处理和降级机制，确保系统在异常情况下仍能正常工作。
包括错误处理器、降级策略和错误恢复等功能。
"""

import sys
import traceback
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime
from threading import Lock

from ..core.types import LogLevel, LogEntry, ExceptionInfo


class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = 1      # 低严重程度，可以忽略
    MEDIUM = 2   # 中等严重程度，需要记录
    HIGH = 3     # 高严重程度，需要处理
    CRITICAL = 4 # 严重错误，需要立即处理


class ErrorCategory(Enum):
    """错误类别枚举"""
    CONFIGURATION = "configuration"    # 配置错误
    OUTPUT_STRATEGY = "output_strategy"  # 输出策略错误
    FORMATTER = "formatter"            # 格式化器错误
    OBSERVER = "observer"              # 观察者错误
    LOGGER = "logger"                  # 日志器错误
    FACTORY = "factory"                # 工厂错误
    MANAGER = "manager"                # 管理器错误
    UNKNOWN = "unknown"                # 未知错误


class ErrorContext:
    """错误上下文类
    
    封装了错误的上下文信息，便于错误处理和分析
    """
    
    def __init__(self, 
                 error: Exception, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 **kwargs):
        """初始化错误上下文
        
        Args:
            error: 异常对象
            severity: 错误严重程度
            category: 错误类别
            **kwargs: 其他上下文信息
        """
        self.error = error
        self.severity = severity
        self.category = category
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
        self.context_data = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的错误上下文
        """
        return {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "severity": self.severity.name,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback,
            "context_data": self.context_data
        }


class ErrorHandler:
    """错误处理器接口
    
    定义了错误处理器的抽象接口，不同的错误处理方式
    都可以实现此接口，从而实现策略模式
    """
    
    def handle_error(self, context: ErrorContext) -> None:
        """处理错误
        
        Args:
            context: 错误上下文
        """
        pass
    
    def can_handle(self, context: ErrorContext) -> bool:
        """检查是否可以处理指定错误
        
        Args:
            context: 错误上下文
            
        Returns:
            bool: 是否可以处理
        """
        return True


class PrintErrorHandler(ErrorHandler):
    """打印错误处理器
    
    将错误信息打印到标准错误输出
    """
    
    def handle_error(self, context: ErrorContext) -> None:
        """处理错误
        
        Args:
            context: 错误上下文
        """
        error_info = (
            f"[{context.timestamp.isoformat()}] "
            f"[{context.category.value}] "
            f"[{context.severity.name}] "
            f"{type(context.error).__name__}: {context.error}"
        )
        print(error_info, file=sys.stderr)
        
        # 如果是高严重程度或严重错误，打印堆栈跟踪
        if context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            print(context.traceback, file=sys.stderr)


class FallbackErrorHandler(ErrorHandler):
    """降级错误处理器
    
    在发生错误时执行降级策略，确保系统继续运行
    """
    
    def __init__(self, fallback_strategy: Callable[[ErrorContext], None]):
        """初始化降级错误处理器
        
        Args:
            fallback_strategy: 降级策略函数
        """
        self.fallback_strategy = fallback_strategy
    
    def handle_error(self, context: ErrorContext) -> None:
        """处理错误
        
        Args:
            context: 错误上下文
        """
        try:
            self.fallback_strategy(context)
        except Exception as e:
            # 降级策略也失败了，使用打印错误处理器
            handler = PrintErrorHandler()
            handler.handle_error(ErrorContext(
                error=e,
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.UNKNOWN,
                original_error=context
            ))


class CompositeErrorHandler(ErrorHandler):
    """复合错误处理器
    
    可以组合多个错误处理器，实现多层次的错误处理
    """
    
    def __init__(self, handlers: Optional[List[ErrorHandler]] = None):
        """初始化复合错误处理器
        
        Args:
            handlers: 错误处理器列表
        """
        self.handlers = handlers or []
        self._lock = Lock()
    
    def add_handler(self, handler: ErrorHandler) -> None:
        """添加错误处理器
        
        Args:
            handler: 错误处理器
        """
        with self._lock:
            if handler not in self.handlers:
                self.handlers.append(handler)
    
    def remove_handler(self, handler: ErrorHandler) -> None:
        """移除错误处理器
        
        Args:
            handler: 错误处理器
        """
        with self._lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
    
    def clear_handlers(self) -> None:
        """清空所有错误处理器"""
        with self._lock:
            self.handlers.clear()
    
    def handle_error(self, context: ErrorContext) -> None:
        """处理错误
        
        Args:
            context: 错误上下文
        """
        with self._lock:
            for handler in self.handlers:
                try:
                    if handler.can_handle(context):
                        handler.handle_error(context)
                except Exception as e:
                    # 错误处理器本身也出错了，使用打印错误处理器
                    print_handler = PrintErrorHandler()
                    print_handler.handle_error(ErrorContext(
                        error=e,
                        severity=ErrorSeverity.CRITICAL,
                        category=ErrorCategory.UNKNOWN,
                        original_error=context
                    ))


class ConditionalErrorHandler(ErrorHandler):
    """条件错误处理器
    
    根据条件决定是否处理错误
    """
    
    def __init__(self, 
                 handler: ErrorHandler, 
                 condition: Callable[[ErrorContext], bool]):
        """初始化条件错误处理器
        
        Args:
            handler: 错误处理器
            condition: 条件函数
        """
        self.handler = handler
        self.condition = condition
    
    def handle_error(self, context: ErrorContext) -> None:
        """处理错误
        
        Args:
            context: 错误上下文
        """
        if self.condition(context):
            self.handler.handle_error(context)
    
    def can_handle(self, context: ErrorContext) -> bool:
        """检查是否可以处理指定错误
        
        Args:
            context: 错误上下文
            
        Returns:
            bool: 是否可以处理
        """
        return self.condition(context)


class ErrorHandlingManager:
    """错误处理管理器
    
    负责管理和协调各种错误处理器，提供统一的错误处理入口
    """
    
    def __init__(self):
        """初始化错误处理管理器"""
        self._handler = CompositeErrorHandler()
        self._lock = Lock()
        self._error_count = 0
        self._error_stats: Dict[str, int] = {}
    
    def add_handler(self, handler: ErrorHandler) -> None:
        """添加错误处理器
        
        Args:
            handler: 错误处理器
        """
        self._handler.add_handler(handler)
    
    def remove_handler(self, handler: ErrorHandler) -> None:
        """移除错误处理器
        
        Args:
            handler: 错误处理器
        """
        self._handler.remove_handler(handler)
    
    def handle_error(self, 
                   error: Exception, 
                   severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                   category: ErrorCategory = ErrorCategory.UNKNOWN,
                   **kwargs) -> None:
        """处理错误
        
        Args:
            error: 异常对象
            severity: 错误严重程度
            category: 错误类别
            **kwargs: 其他上下文信息
        """
        # 创建错误上下文
        context = ErrorContext(error, severity, category, **kwargs)
        
        # 更新错误统计
        with self._lock:
            self._error_count += 1
            category_key = category.value
            self._error_stats[category_key] = self._error_stats.get(category_key, 0) + 1
        
        # 处理错误
        self._handler.handle_error(context)
    
    def get_error_count(self) -> int:
        """获取错误总数
        
        Returns:
            int: 错误总数
        """
        with self._lock:
            return self._error_count
    
    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计信息
        
        Returns:
            Dict[str, int]: 错误统计信息
        """
        with self._lock:
            return self._error_stats.copy()
    
    def clear_stats(self) -> None:
        """清空错误统计信息"""
        with self._lock:
            self._error_count = 0
            self._error_stats.clear()


class FallbackStrategy:
    """降级策略类
    
    提供常用的降级策略，确保系统在异常情况下仍能正常工作
    """
    
    @staticmethod
    def silent_fallback(context: ErrorContext) -> None:
        """静默降级策略
        
        静默处理错误，不执行任何操作
        
        Args:
            context: 错误上下文
        """
        pass
    
    @staticmethod
    def print_fallback(context: ErrorContext) -> None:
        """打印降级策略
        
        将错误信息打印到标准错误输出
        
        Args:
            context: 错误上下文
        """
        handler = PrintErrorHandler()
        handler.handle_error(context)
    
    @staticmethod
    def log_fallback(context: ErrorContext) -> None:
        """日志降级策略
        
        将错误信息记录到日志文件
        
        Args:
            context: 错误上下文
        """
        try:
            # 创建简单的日志记录
            log_entry = LogEntry(
                timestamp=context.timestamp,
                level=LogLevel.ERROR,
                message=f"Error in {context.category.value}: {context.error}",
                logger_name="error_handler",
                thread_id=0,
                exception_info=ExceptionInfo.from_exception(context.error, include_traceback=False),
                context={"severity": context.severity.name, "category": context.category.value}
            )
            
            # 尝试写入到错误日志文件
            import os
            error_log_path = "logs/error.log"
            os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
            
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry.timestamp.isoformat()} [{log_entry.level.name}] {log_entry.message}\n")
                if log_entry.has_exception:
                    f.write(f"Exception: {log_entry.exception_info.exception_type}: {log_entry.exception_info.exception_message}\n")
        except Exception:
            # 如果日志记录也失败了，使用打印降级策略
            FallbackStrategy.print_fallback(context)
    
    @staticmethod
    def retry_fallback(max_retries: int = 3, delay: float = 1.0) -> Callable[[ErrorContext], None]:
        """重试降级策略
        
        创建一个重试降级策略函数
        
        Args:
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
            
        Returns:
            Callable[[ErrorContext], None]: 重试降级策略函数
        """
        def strategy(context: ErrorContext) -> None:
            # 这个策略需要在具体场景中实现，这里只是一个示例
            pass
        
        return strategy


# 全局错误处理管理器实例
_global_error_manager = None


def get_error_manager() -> ErrorHandlingManager:
    """获取全局错误处理管理器实例
    
    Returns:
        ErrorHandlingManager: 全局错误处理管理器实例
    """
    global _global_error_manager
    if _global_error_manager is None:
        _global_error_manager = ErrorHandlingManager()
        
        # 添加默认的错误处理器
        _global_error_manager.add_handler(PrintErrorHandler())
    
    return _global_error_manager


def set_error_manager(manager: ErrorHandlingManager) -> None:
    """设置全局错误处理管理器实例
    
    Args:
        manager: 错误处理管理器实例
    """
    global _global_error_manager
    _global_error_manager = manager


def handle_error(error: Exception, 
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                category: ErrorCategory = ErrorCategory.UNKNOWN,
                **kwargs) -> None:
    """处理错误的便捷函数
    
    Args:
        error: 异常对象
        severity: 错误严重程度
        category: 错误类别
        **kwargs: 其他上下文信息
    """
    manager = get_error_manager()
    manager.handle_error(error, severity, category, **kwargs)


def setup_default_error_handling() -> None:
    """设置默认错误处理"""
    manager = get_error_manager()
    
    # 清空现有处理器
    manager._handler.clear_handlers()
    
    # 添加默认的错误处理器
    manager.add_handler(PrintErrorHandler())
    
    # 添加降级错误处理器
    fallback_handler = FallbackErrorHandler(FallbackStrategy.log_fallback)
    manager.add_handler(fallback_handler)