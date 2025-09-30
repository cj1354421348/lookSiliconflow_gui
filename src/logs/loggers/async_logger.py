"""
异步日志器模块

实现了异步日志器，使用异步处理机制提高日志记录性能。
日志记录被放入队列中，由后台线程异步处理，减少对主线程的影响。
"""

import threading
import queue
import time
from typing import List, Dict, Any, Optional, Callable

from ..core.abstracts import AbstractLogger
from ..core.interfaces import LogObserver, LogOutputStrategy, LogConfig
from ..core.types import LogLevel, LogEntry, ExceptionInfo
from datetime import datetime


class AsyncLogHandler:
    """异步日志处理器
    
    负责异步处理日志记录，使用队列和后台线程
    """
    
    def __init__(self, 
                 queue_size: int = 1000, 
                 flush_interval: float = 1.0,
                 error_handler: Optional[Callable[[Exception, Dict[str, Any]], None]] = None):
        """初始化异步日志处理器
        
        Args:
            queue_size: 队列大小
            flush_interval: 刷新间隔（秒）
            error_handler: 错误处理函数
        """
        self.queue_size = queue_size
        self.flush_interval = flush_interval
        self.error_handler = error_handler
        
        # 创建队列
        self._queue = queue.Queue(maxsize=queue_size)
        
        # 创建锁和事件
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()
        
        # 创建后台线程
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        
        # 创建刷新线程
        self._flush_thread = threading.Thread(target=self _periodic_flush, daemon=True)
        self._flush_thread.start()
        
        # 输出策略列表
        self._strategies: List[LogOutputStrategy] = []
        self._strategies_lock = threading.Lock()
    
    def add_strategy(self, strategy: LogOutputStrategy) -> None:
        """添加输出策略
        
        Args:
            strategy: 输出策略
        """
        with self._strategies_lock:
            if strategy not in self._strategies:
                self._strategies.append(strategy)
    
    def remove_strategy(self, strategy: LogOutputStrategy) -> None:
        """移除输出策略
        
        Args:
            strategy: 输出策略
        """
        with self._strategies_lock:
            if strategy in self._strategies:
                self._strategies.remove(strategy)
    
    def clear_strategies(self) -> None:
        """清空所有输出策略"""
        with self._strategies_lock:
            self._strategies.clear()
    
    def enqueue(self, record: LogEntry) -> bool:
        """将日志记录加入队列
        
        Args:
            record: 日志记录
            
        Returns:
            bool: 是否成功加入队列
        """
        try:
            # 非阻塞方式加入队列
            self._queue.put_nowait(record)
            return True
        except queue.Full:
            # 队列满，丢弃日志记录
            if self.error_handler:
                self.error_handler(
                    queue.Full(), 
                    {"message": "日志队列已满，丢弃日志记录", "record": record}
                )
            return False
    
    def flush(self) -> None:
        """刷新队列，处理所有日志记录"""
        # 触发刷新事件
        self._flush_event.set()
        
        # 等待队列处理完成
        while not self._queue.empty():
            time.sleep(0.01)
    
    def stop(self) -> None:
        """停止异步处理器"""
        # 设置停止事件
        self._stop_event.set()
        
        # 触发刷新事件
        self._flush_event.set()
        
        # 等待线程结束
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        
        if self._flush_thread.is_alive():
            self._flush_thread.join(timeout=1.0)
    
    def _process_queue(self) -> None:
        """处理队列中的日志记录"""
        while not self._stop_event.is_set():
            try:
                # 从队列中获取日志记录，带超时
                record = self._queue.get(timeout=0.1)
                
                # 处理日志记录
                self._process_record(record)
                
                # 标记任务完成
                self._queue.task_done()
                
            except queue.Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                # 处理异常
                if self.error_handler:
                    self.error_handler(e, {"message": "处理日志记录时发生异常"})
    
    def _periodic_flush(self) -> None:
        """定期刷新队列"""
        while not self._stop_event.is_set():
            # 等待刷新事件或超时
            self._flush_event.wait(timeout=self.flush_interval)
            
            # 重置刷新事件
            self._flush_event.clear()
            
            # 如果没有停止事件，则刷新
            if not self._stop_event.is_set():
                self._flush_queue()
    
    def _flush_queue(self) -> None:
        """刷新队列，处理所有日志记录"""
        while not self._queue.empty():
            try:
                # 从队列中获取日志记录，非阻塞
                record = self._queue.get_nowait()
                
                # 处理日志记录
                self._process_record(record)
                
                # 标记任务完成
                self._queue.task_done()
                
            except queue.Empty:
                # 队列为空，结束刷新
                break
            except Exception as e:
                # 处理异常
                if self.error_handler:
                    self.error_handler(e, {"message": "刷新队列时发生异常"})
    
    def _process_record(self, record: LogEntry) -> None:
        """处理单个日志记录
        
        Args:
            record: 日志记录
        """
        with self._strategies_lock:
            for strategy in self._strategies:
                try:
                    strategy.output(record)
                except Exception as e:
                    # 处理异常
                    if self.error_handler:
                        self.error_handler(e, {
                            "message": "输出日志记录时发生异常",
                            "strategy": strategy.__class__.__name__,
                            "record": record
                        })
    
    def get_queue_size(self) -> int:
        """获取当前队列大小
        
        Returns:
            int: 队列大小
        """
        return self._queue.qsize()
    
    def is_alive(self) -> bool:
        """检查处理器是否活跃
        
        Returns:
            bool: 是否活跃
        """
        return (self._worker_thread.is_alive() and 
                self._flush_thread.is_alive() and 
                not self._stop_event.is_set())


class AsyncLogger(AbstractLogger):
    """异步日志器
    
    使用异步处理机制提高日志记录性能，减少对主线程的影响
    """
    
    def __init__(self, name: str, config: LogConfig):
        """初始化异步日志器
        
        Args:
            name: 日志器名称
            config: 日志配置
        """
        super().__init__(name)
        self.config = config
        
        # 创建异步处理器
        self._async_handler = AsyncLogHandler(
            queue_size=config.get_queue_size(),
            flush_interval=config.get_flush_interval(),
            error_handler=self._handle_error
        )
        
        # 初始化输出策略
        self._initialize_strategies()
    
    def _initialize_strategies(self) -> None:
        """初始化输出策略"""
        for strategy in self.config.get_output_strategies():
            self._async_handler.add_strategy(strategy)
    
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 其他参数，如exception_info, context等
        """
        # 检查是否应该记录此级别的日志
        if level.value < self.config.get_min_level().value:
            return
        
        # 创建日志记录
        record = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=self.name,
            thread_id=threading.get_ident(),
            exception_info=kwargs.get('exception_info'),
            context=kwargs.get('context', {})
        )
        
        # 检查过滤器
        if not self._should_log(record):
            return
        
        # 通知观察者
        self._notify_observers(record)
        
        # 将日志记录加入队列
        self._async_handler.enqueue(record)
    
    def flush(self) -> None:
        """刷新日志缓冲区"""
        self._async_handler.flush()
    
    def shutdown(self) -> None:
        """关闭日志器"""
        # 刷新所有日志记录
        self.flush()
        
        # 停止异步处理器
        self._async_handler.stop()
    
    def update_config(self, config: LogConfig) -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
        """
        # 停止旧的异步处理器
        self._async_handler.stop()
        
        # 更新配置
        self.config = config
        
        # 创建新的异步处理器
        self._async_handler = AsyncLogHandler(
            queue_size=config.get_queue_size(),
            flush_interval=config.get_flush_interval(),
            error_handler=self._handle_error
        )
        
        # 重新初始化策略
        self._initialize_strategies()
    
    def is_enabled_for(self, level: LogLevel) -> bool:
        """检查是否启用指定级别
        
        Args:
            level: 日志级别
            
        Returns:
            bool: 是否启用
        """
        return level.value >= self.config.get_min_level().value
    
    def add_output_strategy(self, strategy: LogOutputStrategy) -> None:
        """添加输出策略
        
        Args:
            strategy: 输出策略
        """
        self._async_handler.add_strategy(strategy)
    
    def remove_output_strategy(self, strategy: LogOutputStrategy) -> None:
        """移除输出策略
        
        Args:
            strategy: 输出策略
        """
        self._async_handler.remove_strategy(strategy)
    
    def clear_output_strategies(self) -> None:
        """清空所有输出策略"""
        self._async_handler.clear_strategies()
    
    def get_output_strategies(self) -> List[LogOutputStrategy]:
        """获取输出策略列表
        
        Returns:
            List[LogOutputStrategy]: 输出策略列表
        """
        return self._async_handler._strategies.copy()
    
    def get_queue_size(self) -> int:
        """获取当前队列大小
        
        Returns:
            int: 队列大小
        """
        return self._async_handler.get_queue_size()
    
    def is_async_handler_alive(self) -> bool:
        """检查异步处理器是否活跃
        
        Returns:
            bool: 是否活跃
        """
        return self._async_handler.is_alive()
    
    def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文
        """
        # 默认实现：静默处理错误
        pass
    
    def get_logger_info(self) -> Dict[str, Any]:
        """获取日志器信息
        
        Returns:
            Dict[str, Any]: 日志器信息字典
        """
        info = super().get_logger_info()
        info.update({
            "config": {
                "min_level": self.config.get_min_level().name,
                "format_string": self.config.get_format_string(),
                "async_enabled": self.config.is_async_enabled(),
                "queue_size": self.config.get_queue_size(),
                "flush_interval": self.config.get_flush_interval()
            },
            "async_handler": {
                "alive": self.is_async_handler_alive(),
                "queue_size": self.get_queue_size(),
                "max_queue_size": self.config.get_queue_size()
            },
            "strategies_count": len(self._async_handler._strategies)
        })
        return info