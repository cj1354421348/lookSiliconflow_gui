"""
可观察日志器模块

实现了可观察的日志器，支持观察者模式，可以动态添加和移除观察者。
当有日志记录产生时，会通知所有观察者。
"""

import threading
from typing import List, Dict, Any, Optional

from ..core.abstracts import AbstractLogger
from ..core.interfaces import LogObserver, LogOutputStrategy, LogConfig
from ..core.types import LogLevel, LogEntry, ExceptionInfo
from datetime import datetime


class ObservableLogger(AbstractLogger):
    """可观察的日志器
    
    实现了观察者模式，可以动态添加和移除观察者。
    当有日志记录产生时，会通知所有观察者。
    """
    
    def __init__(self, name: str, config: LogConfig):
        """初始化可观察日志器
        
        Args:
            name: 日志器名称
            config: 日志配置
        """
        super().__init__(name)
        self.config = config
        self._strategies: List[LogOutputStrategy] = []
        self._strategies_lock = None  # 延迟初始化
        self._initialize_strategies()
    
    def _initialize_strategies(self) -> None:
        """初始化输出策略"""
        for strategy in self.config.get_output_strategies():
            self._strategies.append(strategy)
    
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
        
        # 使用策略输出
        self._output_with_strategies(record)
    
    def flush(self) -> None:
        """刷新所有输出策略"""
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            for strategy in self._strategies:
                try:
                    strategy.flush()
                except Exception as e:
                    # 静默处理刷新异常
                    pass
    
    def shutdown(self) -> None:
        """关闭日志器"""
        # 刷新所有输出策略
        self.flush()
        
        # 关闭所有输出策略
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            for strategy in self._strategies:
                try:
                    strategy.close()
                except Exception as e:
                    # 静默处理关闭异常
                    pass
    
    def update_config(self, config: LogConfig) -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
        """
        # 关闭旧策略
        self.shutdown()
        
        # 更新配置
        self.config = config
        
        # 重新初始化策略
        self._strategies.clear()
        self._initialize_strategies()
    
    def is_enabled_for(self, level: LogLevel) -> bool:
        """检查是否启用指定级别
        
        Args:
            level: 日志级别
            
        Returns:
            bool: 是否启用
        """
        return level.value >= self.config.get_min_level().value
    
    def _output_with_strategies(self, record: LogEntry) -> None:
        """使用策略输出日志
        
        Args:
            record: 日志记录
        """
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            for strategy in self._strategies:
                try:
                    strategy.output(record)
                except Exception as e:
                    # 静默处理输出异常，避免影响主流程
                    pass
    
    def add_output_strategy(self, strategy: LogOutputStrategy) -> None:
        """添加输出策略
        
        Args:
            strategy: 输出策略
        """
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            if strategy not in self._strategies:
                self._strategies.append(strategy)
    
    def remove_output_strategy(self, strategy: LogOutputStrategy) -> None:
        """移除输出策略
        
        Args:
            strategy: 输出策略
        """
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            if strategy in self._strategies:
                self._strategies.remove(strategy)
    
    def clear_output_strategies(self) -> None:
        """清空所有输出策略"""
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            self._strategies.clear()
    
    def get_output_strategies(self) -> List[LogOutputStrategy]:
        """获取输出策略列表
        
        Returns:
            List[LogOutputStrategy]: 输出策略列表
        """
        if self._strategies_lock is None:
            import threading
            self._strategies_lock = threading.Lock()
        
        with self._strategies_lock:
            return self._strategies.copy()
    
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
            "strategies_count": len(self._strategies)
        })
        return info