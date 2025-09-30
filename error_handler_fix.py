"""
错误处理器接口验证修复
确保所有错误处理器都实现了完整的接口
"""

import sys
import traceback
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime
from threading import Lock
import logging
import time

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
        
        # 添加错误链跟踪
        self.error_chain = [error]
        if 'original_error' in kwargs:
            if hasattr(kwargs['original_error'], 'error_chain'):
                # 如果原始错误也有错误链，合并它们
                self.error_chain = kwargs['original_error'].error_chain + self.error_chain
            else:
                # 否则将原始错误添加到错误链
                self.error_chain.insert(0, kwargs['original_error'])
        
        logging.debug(f"创建错误上下文，错误链长度: {len(self.error_chain)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的错误上下文
        """
        # 构建错误链信息
        error_chain_info = []
        for i, err in enumerate(self.error_chain):
            error_chain_info.append({
                "index": i,
                "type": type(err).__name__,
                "message": str(err)
            })
        
        return {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "severity": self.severity.name,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback,
            "context_data": self.context_data,
            "error_chain_length": len(self.error_chain),
            "error_chain": error_chain_info
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
            logging.debug(f"执行降级策略: {self.fallback_strategy.__name__}")
            self.fallback_strategy(context)
        except Exception as e:
            # 降级策略也失败了，使用打印错误处理器
            logging.error(f"降级策略 {self.fallback_strategy.__name__} 失败: {e}")
            logging.error(f"原始错误: {context.error}")
            
            # 创建新的错误上下文，包含原始错误信息
            error_context = ErrorContext(
                error=e,
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.UNKNOWN,
                original_error=context,
                failed_strategy=self.fallback_strategy.__name__
            )
            
            # 使用打印错误处理器作为最后的降级策略
            try:
                handler = PrintErrorHandler()
                handler.handle_error(error_context)
            except Exception as fallback_error:
                # 如果连打印错误处理器都失败了，直接输出到stderr
                logging.critical(f"降级策略的打印错误处理器也失败: {fallback_error}")
                print(f"CRITICAL: 降级策略完全失败", file=sys.stderr)
                print(f"原始错误: {context.error}", file=sys.stderr)
                print(f"降级策略错误: {e}", file=sys.stderr)
                print(f"降级错误: {fallback_error}", file=sys.stderr)


class CompositeErrorHandler(ErrorHandler):
    """复合错误处理器
    
    可以组合多个错误处理器，实现多层次的错误处理
    修复了接口验证问题
    """
    
    def __init__(self, handlers: Optional[List[ErrorHandler]] = None):
        """初始化复合错误处理器
        
        Args:
            handlers: 错误处理器列表
        """
        self.handlers = handlers or []
        self._lock = Lock()
        self._handler_priorities = {}  # 处理器优先级字典
        self._max_handlers = 50  # 最大处理器数量限制
        
        # 初始化处理器优先级
        for i, handler in enumerate(self.handlers):
            self._handler_priorities[handler] = i
    
    def _validate_handler(self, handler) -> None:
        """验证错误处理器是否实现了完整的接口
        
        Args:
            handler: 要验证的错误处理器
            
        Raises:
            TypeError: 如果处理器没有实现完整的接口
        """
        # 检查是否实现了必需的方法
        required_methods = ['handle_error', 'can_handle']
        
        for method_name in required_methods:
            if not hasattr(handler, method_name):
                raise TypeError(f"错误处理器必须实现 {method_name} 方法")
            
            method = getattr(handler, method_name)
            if not callable(method):
                raise TypeError(f"错误处理器的 {method_name} 必须是可调用的")
    
    def add_handler(self, handler: ErrorHandler) -> None:
        """添加错误处理器
        
        Args:
            handler: 错误处理器
            
        Raises:
            TypeError: 如果处理器没有实现完整的接口
            RuntimeError: 如果处理器数量超过限制
        """
        # 验证处理器接口
        self._validate_handler(handler)
        
        with self._lock:
            # 检查处理器数量限制
            if len(self.handlers) >= self._max_handlers:
                logging.error(f"错误处理器数量超过限制: {self._max_handlers}")
                raise RuntimeError(f"错误处理器数量超过限制: {self._max_handlers}")
            
            if handler not in self.handlers:
                self.handlers.append(handler)
                # 设置处理器优先级（后添加的优先级更高）
                self._handler_priorities[handler] = len(self.handlers) - 1
                logging.debug(f"添加错误处理器: {handler.__class__.__name__}, 优先级: {self._handler_priorities[handler]}")
    
    def remove_handler(self, handler: ErrorHandler) -> None:
        """移除错误处理器
        
        Args:
            handler: 错误处理器
        """
        with self._lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
                # 清理优先级信息
                if handler in self._handler_priorities:
                    del self._handler_priorities[handler]
                logging.debug(f"移除错误处理器: {handler.__class__.__name__}")
    
    def clear_handlers(self) -> None:
        """清空所有错误处理器"""
        with self._lock:
            self.handlers.clear()
            self._handler_priorities.clear()
            logging.debug("清空所有错误处理器")
    
    def handle_error(self, context: ErrorContext) -> None:
        """处理错误
        
        Args:
            context: 错误上下文
        """
        with self._lock:
            for i, handler in enumerate(self.handlers):
                try:
                    if handler.can_handle(context):
                        logging.debug(f"调用错误处理器 {i+1}/{len(self.handlers)}: {handler.__class__.__name__}")
                        handler.handle_error(context)
                except Exception as e:
                    # 错误处理器本身也出错了，使用打印错误处理器
                    logging.error(f"错误处理器 {handler.__class__.__name__} 本身出错: {e}")
                    logging.error(f"原始错误: {context.error}")
                    
                    # 创建新的错误上下文，包含原始错误信息
                    error_context = ErrorContext(
                        error=e,
                        severity=ErrorSeverity.CRITICAL,
                        category=ErrorCategory.UNKNOWN,
                        original_error=context,
                        failed_handler=handler.__class__.__name__,
                        handler_index=i
                    )
                    
                    # 使用打印错误处理器作为最后的降级策略
                    try:
                        print_handler = PrintErrorHandler()
                        print_handler.handle_error(error_context)
                    except Exception as fallback_error:
                        # 如果连打印错误处理器都失败了，直接输出到stderr
                        logging.critical(f"打印错误处理器也失败: {fallback_error}")
                        print(f"CRITICAL: 错误处理完全失败", file=sys.stderr)
                        print(f"原始错误: {context.error}", file=sys.stderr)
                        print(f"处理器错误: {e}", file=sys.stderr)
                        print(f"降级错误: {fallback_error}", file=sys.stderr)


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
    修复了接口验证问题
    """
    
    def __init__(self):
        """初始化错误处理管理器"""
        self._handler = CompositeErrorHandler()
        self._lock = Lock()
        self._error_count = 0
        self._error_stats: Dict[str, int] = {}
        self._recursion_depth = 0  # 递归深度计数器
        self._max_recursion_depth = 10  # 最大递归深度限制
        self._performance_stats = {
            'total_handling_time': 0.0,
            'max_handling_time': 0.0,
            'min_handling_time': float('inf'),
            'handling_count': 0
        }
        self._lock_acquisition_times = {}  # 锁获取时间跟踪
        self._lock_timeout = 5.0  # 锁超时时间（秒）
    
    def add_handler(self, handler: ErrorHandler) -> None:
        """添加错误处理器
        
        Args:
            handler: 错误处理器
            
        Raises:
            TypeError: 如果处理器没有实现完整的接口
        """
        self._handler.add_handler(handler)
    
    def remove_handler(self, handler: ErrorHandler) -> None:
        """移除错误处理器
        
        Args:
            handler: 错误处理器
        """
        self._handler.remove_handler(handler)
    
    def _safe_acquire_lock(self, lock_name: str = "main") -> bool:
        """安全获取锁，避免死锁
        
        Args:
            lock_name: 锁名称
            
        Returns:
            bool: 是否成功获取锁
        """
        current_time = time.time()
        
        # 检查是否已经持有该锁
        if lock_name in self._lock_acquisition_times:
            holding_time = current_time - self._lock_acquisition_times[lock_name]
            if holding_time > self._lock_timeout:
                logging.error(f"锁 {lock_name} 持有时间过长: {holding_time:.3f}秒，可能存在死锁")
                return False
        
        # 尝试获取锁
        if self._lock.acquire(blocking=False):
            self._lock_acquisition_times[lock_name] = current_time
            logging.debug(f"成功获取锁: {lock_name}")
            return True
        else:
            logging.warning(f"无法获取锁: {lock_name}，锁可能被其他线程持有")
            return False
    
    def _safe_release_lock(self, lock_name: str = "main") -> None:
        """安全释放锁
        
        Args:
            lock_name: 锁名称
        """
        if lock_name in self._lock_acquisition_times:
            del self._lock_acquisition_times[lock_name]
        
        try:
            self._lock.release()
            logging.debug(f"成功释放锁: {lock_name}")
        except RuntimeError:
            logging.warning(f"尝试释放未持有的锁: {lock_name}")
    
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
        # 检查递归深度
        with self._lock:
            self._recursion_depth += 1
            current_depth = self._recursion_depth
            
            # 记录递归深度警告
            if current_depth > 3:
                logging.warning(f"错误处理递归深度过深: {current_depth}")
            
            # 如果超过最大递归深度，强制终止递归
            if current_depth > self._max_recursion_depth:
                logging.error(f"错误处理递归深度超过限制: {current_depth}，强制终止递归")
                print(f"CRITICAL: 错误处理递归深度超过限制: {current_depth}，强制终止递归", file=sys.stderr)
                print(f"原始错误: {error}", file=sys.stderr)
                self._recursion_depth = 0  # 重置递归深度
                return
        
        start_time = time.time()
        try:
            # 创建错误上下文
            context = ErrorContext(error, severity, category, **kwargs)
            
            # 更新错误统计
            with self._lock:
                self._error_count += 1
                category_key = category.value
                self._error_stats[category_key] = self._error_stats.get(category_key, 0) + 1
            
            # 处理错误
            self._handler.handle_error(context)
            
        finally:
            # 减少递归深度
            with self._lock:
                self._recursion_depth -= 1
                if self._recursion_depth < 0:
                    self._recursion_depth = 0  # 防止负数
            
            # 更新性能统计
            handling_time = time.time() - start_time
            with self._lock:
                self._performance_stats['total_handling_time'] += handling_time
                self._performance_stats['max_handling_time'] = max(
                    self._performance_stats['max_handling_time'], handling_time
                )
                self._performance_stats['min_handling_time'] = min(
                    self._performance_stats['min_handling_time'], handling_time
                )
                self._performance_stats['handling_count'] += 1
            
            # 记录性能警告
            if handling_time > 1.0:  # 超过1秒
                logging.warning(f"错误处理耗时过长: {handling_time:.3f}秒")
    
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
            self._performance_stats = {
                'total_handling_time': 0.0,
                'max_handling_time': 0.0,
                'min_handling_time': float('inf'),
                'handling_count': 0
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计信息
        """
        with self._lock:
            if self._performance_stats['handling_count'] == 0:
                return {
                    'average_handling_time': 0.0,
                    'max_handling_time': 0.0,
                    'min_handling_time': 0.0,
                    'total_handling_time': 0.0,
                    'handling_count': 0
                }
            
            return {
                'average_handling_time': self._performance_stats['total_handling_time'] / self._performance_stats['handling_count'],
                'max_handling_time': self._performance_stats['max_handling_time'],
                'min_handling_time': self._performance_stats['min_handling_time'],
                'total_handling_time': self._performance_stats['total_handling_time'],
                'handling_count': self._performance_stats['handling_count']
            }


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
            logging.debug("尝试日志降级策略")
            
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
            
            logging.debug(f"日志降级策略成功，写入到: {error_log_path}")
            
        except Exception as e:
            # 如果日志记录也失败了，使用打印降级策略
            logging.error(f"日志降级策略失败: {e}")
            logging.error(f"原始错误: {context.error}")
            
            try:
                FallbackStrategy.print_fallback(context)
            except Exception as fallback_error:
                # 如果连打印降级策略都失败了，直接输出到stderr
                logging.critical(f"日志降级策略的打印降级也失败: {fallback_error}")
                print(f"CRITICAL: 日志降级策略完全失败", file=sys.stderr)
                print(f"原始错误: {context.error}", file=sys.stderr)
                print(f"日志错误: {e}", file=sys.stderr)
                print(f"降级错误: {fallback_error}", file=sys.stderr)
    
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
            import time
            logging.debug(f"开始重试降级策略，最大重试次数: {max_retries}")
            
            for attempt in range(max_retries):
                try:
                    # 尝试使用日志降级策略
                    FallbackStrategy.log_fallback(context)
                    logging.debug(f"重试降级策略在第 {attempt + 1} 次尝试成功")
                    return
                except Exception as e:
                    logging.warning(f"重试降级策略第 {attempt + 1} 次尝试失败: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    else:
                        logging.error(f"重试降级策略所有尝试都失败")
                        # 最后尝试打印降级策略
                        try:
                            FallbackStrategy.print_fallback(context)
                        except Exception as fallback_error:
                            logging.critical(f"重试降级策略的打印降级也失败: {fallback_error}")
                            print(f"CRITICAL: 重试降级策略完全失败", file=sys.stderr)
                            print(f"原始错误: {context.error}", file=sys.stderr)
                            print(f"重试错误: {e}", file=sys.stderr)
                            print(f"降级错误: {fallback_error}", file=sys.stderr)
        
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