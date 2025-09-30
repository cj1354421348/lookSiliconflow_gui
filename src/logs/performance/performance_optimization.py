"""
性能优化模块

实现了日志系统的性能优化功能，包括对象池、异步处理、批量处理等。
这些优化措施可以提高日志系统的性能，减少对主线程的影响。
"""

import threading
import queue
import time
import weakref
from typing import Dict, Any, Optional, Callable, List, Generic, TypeVar
from abc import ABC, abstractmethod
from contextlib import contextmanager
from collections import deque

from ..core.types import LogLevel, LogEntry, ExceptionInfo
from ..error_handling.error_handler import ErrorHandlingManager, ErrorContext, ErrorCategory, ErrorSeverity


T = TypeVar('T')


class ObjectPool(Generic[T], ABC):
    """对象池抽象基类
    
    提供对象池的基本功能，减少对象创建和销毁的开销
    """
    
    def __init__(self, max_size: int = 100):
        """初始化对象池
        
        Args:
            max_size: 对象池最大大小
        """
        self.max_size = max_size
        self._pool = deque()
        self._lock = threading.Lock()
        self._created_count = 0
        self._borrowed_count = 0
    
    @abstractmethod
    def create_object(self) -> T:
        """创建新对象
        
        Returns:
            T: 新创建的对象
        """
        pass
    
    @abstractmethod
    def reset_object(self, obj: T) -> None:
        """重置对象状态
        
        Args:
            obj: 要重置的对象
        """
        pass
    
    def borrow_object(self) -> T:
        """从对象池借用对象
        
        Returns:
            T: 借用的对象
        """
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
            else:
                obj = self.create_object()
                self._created_count += 1
            
            self._borrowed_count += 1
            return obj
    
    def return_object(self, obj: T) -> None:
        """归还对象到对象池
        
        Args:
            obj: 要归还的对象
        """
        with self._lock:
            if len(self._pool) < self.max_size:
                self.reset_object(obj)
                self._pool.append(obj)
            
            self._borrowed_count -= 1
    
    @contextmanager
    def object(self) -> T:
        """上下文管理器，自动借用和归还对象
        
        Yields:
            T: 借用的对象
        """
        obj = self.borrow_object()
        try:
            yield obj
        finally:
            self.return_object(obj)
    
    def get_pool_size(self) -> int:
        """获取对象池大小
        
        Returns:
            int: 对象池大小
        """
        with self._lock:
            return len(self._pool)
    
    def get_created_count(self) -> int:
        """获取已创建对象数量
        
        Returns:
            int: 已创建对象数量
        """
        return self._created_count
    
    def get_borrowed_count(self) -> int:
        """获取已借用对象数量
        
        Returns:
            int: 已借用对象数量
        """
        return self._borrowed_count
    
    def clear(self) -> None:
        """清空对象池"""
        with self._lock:
            self._pool.clear()


class LogEntryPool(ObjectPool[LogEntry]):
    """日志条目对象池
    
    重用LogEntry对象，减少内存分配和垃圾回收的开销
    """
    
    def create_object(self) -> LogEntry:
        """创建新的LogEntry对象
        
        Returns:
            LogEntry: 新创建的LogEntry对象
        """
        return LogEntry(
            timestamp=None,
            level=None,
            message="",
            logger_name="",
            thread_id=0,
            exception_info=None,
            context={}
        )
    
    def reset_object(self, obj: LogEntry) -> None:
        """重置LogEntry对象状态
        
        Args:
            obj: 要重置的LogEntry对象
        """
        obj.timestamp = None
        obj.level = None
        obj.message = ""
        obj.logger_name = ""
        obj.thread_id = 0
        obj.exception_info = None
        obj.context.clear()


class BatchProcessor:
    """批量处理器
    
    将多个日志记录批量处理，减少I/O操作次数
    """
    
    def __init__(self, 
                 batch_size: int = 100, 
                 max_wait_time: float = 1.0,
                 processor: Callable[[List[LogEntry]], None] = None):
        """初始化批量处理器
        
        Args:
            batch_size: 批量大小
            max_wait_time: 最大等待时间（秒）
            processor: 处理函数
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.processor = processor
        
        self._batch = []
        self._lock = threading.Lock()
        self._last_process_time = time.time()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._process_batch, daemon=True)
        self._worker_thread.start()
    
    def add_entry(self, entry: LogEntry) -> None:
        """添加日志条目到批量处理器
        
        Args:
            entry: 日志条目
        """
        with self._lock:
            self._batch.append(entry)
            
            # 如果达到批量大小，触发处理
            if len(self._batch) >= self.batch_size:
                self._process_batch_now()
    
    def _process_batch(self) -> None:
        """处理批量日志的后台线程"""
        while not self._stop_event.is_set():
            time.sleep(0.1)  # 减少CPU使用率
            
            with self._lock:
                # 检查是否需要处理
                current_time = time.time()
                if (len(self._batch) > 0 and 
                    (len(self._batch) >= self.batch_size or 
                     current_time - self._last_process_time >= self.max_wait_time)):
                    self._process_batch_now()
    
    def _process_batch_now(self) -> None:
        """立即处理批量日志"""
        if not self._batch:
            return
        
        # 复制批量数据
        batch = self._batch.copy()
        self._batch.clear()
        self._last_process_time = time.time()
        
        # 处理批量数据
        if self.processor:
            try:
                self.processor(batch)
            except Exception as e:
                # 处理异常
                error_manager = ErrorHandlingManager()
                error_manager.handle_error(
                    error=e,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.OUTPUT_STRATEGY,
                    batch_size=len(batch)
                )
    
    def flush(self) -> None:
        """刷新批量处理器，立即处理所有日志"""
        self._process_batch_now()
    
    def stop(self) -> None:
        """停止批量处理器"""
        self._stop_event.set()
        self.flush()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
    
    def get_batch_size(self) -> int:
        """获取当前批量大小
        
        Returns:
            int: 当前批量大小
        """
        with self._lock:
            return len(self._batch)


class AsyncBatchProcessor(BatchProcessor):
    """异步批量处理器
    
    使用队列和后台线程实现异步批量处理
    """
    
    def __init__(self, 
                 batch_size: int = 100, 
                 max_wait_time: float = 1.0,
                 queue_size: int = 1000,
                 processor: Callable[[List[LogEntry]], None] = None):
        """初始化异步批量处理器
        
        Args:
            batch_size: 批量大小
            max_wait_time: 最大等待时间（秒）
            queue_size: 队列大小
            processor: 处理函数
        """
        super().__init__(batch_size, max_wait_time, processor)
        self.queue_size = queue_size
        self._queue = queue.Queue(maxsize=queue_size)
        self._queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._queue_thread.start()
    
    def add_entry(self, entry: LogEntry) -> bool:
        """添加日志条目到异步批量处理器
        
        Args:
            entry: 日志条目
            
        Returns:
            bool: 是否成功添加
        """
        try:
            self._queue.put_nowait(entry)
            return True
        except queue.Full:
            # 队列满，丢弃日志条目
            return False
    
    def _process_queue(self) -> None:
        """处理队列的后台线程"""
        while not self._stop_event.is_set():
            try:
                # 从队列中获取日志条目，带超时
                entry = self._queue.get(timeout=0.1)
                
                # 添加到批量处理器
                super().add_entry(entry)
                
                # 标记任务完成
                self._queue.task_done()
                
            except queue.Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                # 处理异常
                error_manager = ErrorHandlingManager()
                error_manager.handle_error(
                    error=e,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.OUTPUT_STRATEGY
                )
    
    def flush(self) -> None:
        """刷新异步批量处理器"""
        # 等待队列处理完成
        while not self._queue.empty():
            time.sleep(0.01)
        
        # 刷新批量处理器
        super().flush()
    
    def stop(self) -> None:
        """停止异步批量处理器"""
        super().stop()
        
        # 等待队列线程结束
        if self._queue_thread.is_alive():
            self._queue_thread.join(timeout=1.0)
    
    def get_queue_size(self) -> int:
        """获取当前队列大小
        
        Returns:
            int: 当前队列大小
        """
        return self._queue.qsize()


class PerformanceMonitor:
    """性能监控器
    
    监控日志系统的性能指标，提供性能统计信息
    """
    
    def __init__(self):
        """初始化性能监控器"""
        self._lock = threading.Lock()
        self._stats = {
            "log_count": 0,
            "error_count": 0,
            "total_processing_time": 0.0,
            "min_processing_time": float('inf'),
            "max_processing_time": 0.0,
            "start_time": time.time(),
            "last_reset_time": time.time()
        }
    
    def record_log(self, processing_time: float) -> None:
        """记录日志处理时间和统计信息
        
        Args:
            processing_time: 处理时间（秒）
        """
        with self._lock:
            self._stats["log_count"] += 1
            self._stats["total_processing_time"] += processing_time
            self._stats["min_processing_time"] = min(self._stats["min_processing_time"], processing_time)
            self._stats["max_processing_time"] = max(self._stats["max_processing_time"], processing_time)
    
    def record_error(self) -> None:
        """记录错误统计信息"""
        with self._lock:
            self._stats["error_count"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计信息
        """
        with self._lock:
            stats = self._stats.copy()
            
            # 计算平均处理时间
            if stats["log_count"] > 0:
                stats["avg_processing_time"] = stats["total_processing_time"] / stats["log_count"]
            else:
                stats["avg_processing_time"] = 0.0
            
            # 计算吞吐量（每秒日志数）
            elapsed_time = time.time() - stats["last_reset_time"]
            if elapsed_time > 0:
                stats["throughput"] = stats["log_count"] / elapsed_time
            else:
                stats["throughput"] = 0.0
            
            # 计算错误率
            if stats["log_count"] > 0:
                stats["error_rate"] = stats["error_count"] / stats["log_count"]
            else:
                stats["error_rate"] = 0.0
            
            return stats
    
    def reset_stats(self) -> None:
        """重置性能统计信息"""
        with self._lock:
            self._stats.update({
                "log_count": 0,
                "error_count": 0,
                "total_processing_time": 0.0,
                "min_processing_time": float('inf'),
                "max_processing_time": 0.0,
                "last_reset_time": time.time()
            })
    
    def get_uptime(self) -> float:
        """获取运行时间（秒）
        
        Returns:
            float: 运行时间
        """
        with self._lock:
            return time.time() - self._stats["start_time"]


# 全局性能监控器实例
_global_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例
    
    Returns:
        PerformanceMonitor: 全局性能监控器实例
    """
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    """设置全局性能监控器实例
    
    Args:
        monitor: 性能监控器实例
    """
    global _global_performance_monitor
    _global_performance_monitor = monitor


# 性能优化的便捷函数
def create_log_entry_pool(max_size: int = 100) -> LogEntryPool:
    """创建日志条目对象池的便捷函数
    
    Args:
        max_size: 对象池最大大小
        
    Returns:
        LogEntryPool: 日志条目对象池
    """
    return LogEntryPool(max_size)


def create_batch_processor(batch_size: int = 100, 
                         max_wait_time: float = 1.0,
                         processor: Callable[[List[LogEntry]], None] = None) -> BatchProcessor:
    """创建批量处理器的便捷函数
    
    Args:
        batch_size: 批量大小
        max_wait_time: 最大等待时间（秒）
        processor: 处理函数
        
    Returns:
        BatchProcessor: 批量处理器
    """
    return BatchProcessor(batch_size, max_wait_time, processor)


def create_async_batch_processor(batch_size: int = 100, 
                                max_wait_time: float = 1.0,
                                queue_size: int = 1000,
                                processor: Callable[[List[LogEntry]], None] = None) -> AsyncBatchProcessor:
    """创建异步批量处理器的便捷函数
    
    Args:
        batch_size: 批量大小
        max_wait_time: 最大等待时间（秒）
        queue_size: 队列大小
        processor: 处理函数
        
    Returns:
        AsyncBatchProcessor: 异步批量处理器
    """
    return AsyncBatchProcessor(batch_size, max_wait_time, queue_size, processor)