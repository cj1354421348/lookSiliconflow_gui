"""
LogManager最终修复版本
使用完全无锁的读取策略和最小化锁的写入策略
"""

import threading
import time
from typing import Dict, Optional, List, Any
from collections import defaultdict

from ..core.interfaces import Logger, LogConfig, LogObserver
from ..core.types import LogLevel
from ..config.log_config import LogConfigData
from ..factories.logger_factory import LoggerFactory, get_logger_factory, set_logger_factory


class LogManagerMeta(type):
    """日志管理器元类
    
    实现线程安全的单例模式
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class LogManager(metaclass=LogManagerMeta):
    """日志管理器
    
    线程安全的单例日志管理器，提供统一的日志管理入口
    使用完全无锁的读取策略和最小化锁的写入策略
    """
    
    def __init__(self):
        """初始化日志管理器"""
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 使用线程本地存储来避免锁竞争
        self._thread_local = threading.local()
        
        # 日志器字典 - 使用不可变字典进行无锁读取
        self._loggers_immutable = {}
        self._loggers_lock = threading.Lock()
        
        # 日志配置 - 使用原子引用进行无锁读取
        self._config_ref = None
        self._config_lock = threading.Lock()
        
        # 配置版本号，用于检测配置变更
        self._config_version = 0
        self._config_version_lock = threading.Lock()
        
        # 日志器工厂
        self._factory: Optional[LoggerFactory] = None
        
        # 根日志器 - 使用原子引用进行无锁读取
        self._root_logger_ref = None
        
        # 初始化标志
        self._initialized = False
        self._initialization_lock = threading.Lock()
        
        # 错误统计
        self._error_stats = defaultdict(int)
        self._error_stats_lock = threading.Lock()
    
    def initialize(self, config: Optional[LogConfig] = None, factory: Optional[LoggerFactory] = None) -> None:
        """初始化日志管理器
        
        Args:
            config: 日志配置，如果为None则使用默认配置
            factory: 日志器工厂，如果为None则使用默认工厂
        """
        if self._initialized:
            return
        
        with self._initialization_lock:
            if self._initialized:
                return
            
            # 设置配置
            if config is None:
                from ..builders.config_builder import create_config_builder
                config = create_config_builder().build()
            
            # 设置工厂
            if factory is None:
                factory = get_logger_factory()
            
            self._factory = factory
            
            # 创建根日志器
            root_logger = self._factory.create_logger("root", config)
            
            # 原子更新配置和根日志器引用
            with self._config_lock:
                self._config_ref = config
                self._root_logger_ref = root_logger
            
            # 原子更新配置版本号
            with self._config_version_lock:
                self._config_version += 1
            
            # 设置初始化标志
            self._initialized = True
    
    def get_logger(self, name: str) -> Logger:
        """获取日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            Logger: 日志器实例
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 如果请求根日志器，直接返回原子引用
        if name == "root" or name == "":
            return self._root_logger_ref
        
        # 检查线程本地缓存
        if hasattr(self._thread_local, 'logger_cache'):
            cached_logger = self._thread_local.logger_cache.get(name)
            if cached_logger is not None:
                return cached_logger
        
        # 无锁读取不可变日志器字典
        logger = self._loggers_immutable.get(name)
        if logger is not None:
            # 缓存到线程本地
            if not hasattr(self._thread_local, 'logger_cache'):
                self._thread_local.logger_cache = {}
            self._thread_local.logger_cache[name] = logger
            return logger
        
        # 需要创建新日志器，获取锁
        with self._loggers_lock:
            # 双重检查，可能在等待锁时已被其他线程创建
            logger = self._loggers_immutable.get(name)
            if logger is not None:
                # 缓存到线程本地
                if not hasattr(self._thread_local, 'logger_cache'):
                    self._thread_local.logger_cache = {}
                self._thread_local.logger_cache[name] = logger
                return logger
            
            # 创建新日志器
            config = self._config_ref  # 无锁读取配置
            logger = self._factory.create_logger(name, config)
            
            # 创建新的不可变字典
            new_loggers = dict(self._loggers_immutable)
            new_loggers[name] = logger
            
            # 原子更新不可变字典
            self._loggers_immutable = new_loggers
            
            # 缓存到线程本地
            if not hasattr(self._thread_local, 'logger_cache'):
                self._thread_local.logger_cache = {}
            self._thread_local.logger_cache[name] = logger
            
            return logger
    
    def get_root_logger(self) -> Logger:
        """获取根日志器
        
        Returns:
            Logger: 根日志器实例
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        return self._root_logger_ref
    
    def has_logger(self, name: str) -> bool:
        """检查是否存在指定名称的日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            bool: 是否存在
        """
        if not self._initialized:
            return False
        
        # 无锁检查不可变字典
        return name in self._loggers_immutable
    
    def remove_logger(self, name: str) -> bool:
        """移除日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            bool: 是否成功移除
        """
        if not self._initialized:
            return False
        
        # 获取锁进行修改
        with self._loggers_lock:
            if name not in self._loggers_immutable:
                return False
            
            # 创建新的不可变字典
            new_loggers = dict(self._loggers_immutable)
            logger = new_loggers.pop(name)
            
            # 原子更新不可变字典
            self._loggers_immutable = new_loggers
            
            # 关闭日志器
            logger.shutdown()
            
            # 清除线程本地缓存
            if hasattr(self._thread_local, 'logger_cache'):
                self._thread_local.logger_cache.pop(name, None)
            
            return True
    
    def get_logger_names(self) -> List[str]:
        """获取所有日志器名称
        
        Returns:
            List[str]: 日志器名称列表
        """
        if not self._initialized:
            return []
        
        # 无锁读取不可变字典的键
        return list(self._loggers_immutable.keys())
    
    def get_config(self) -> Optional[LogConfig]:
        """获取日志配置
        
        Returns:
            Optional[LogConfig]: 日志配置，如果未初始化则返回None
        """
        # 无锁读取配置引用
        return self._config_ref
    
    def update_config(self, config: LogConfig) -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 原子更新配置引用
        with self._config_lock:
            self._config_ref = config
        
        # 原子更新配置版本号
        with self._config_version_lock:
            self._config_version += 1
        
        # 更新根日志器
        self._root_logger_ref.update_config(config)
        
        # 异步更新所有日志器，避免阻塞
        loggers_to_update = list(self._loggers_immutable.values())
        
        # 使用后台线程更新，避免阻塞调用者
        def update_loggers():
            for logger in loggers_to_update:
                try:
                    logger.update_config(config)
                except Exception as e:
                    # 记录错误但不中断其他日志器的更新
                    with self._error_stats_lock:
                        self._error_stats['config_update_failures'] += 1
                    import logging
                    logging.error(f"更新日志器 {logger} 配置失败: {e}")
        
        # 启动后台线程
        update_thread = threading.Thread(target=update_loggers, daemon=True)
        update_thread.start()
    
    def shutdown(self) -> None:
        """关闭日志管理器"""
        if not self._initialized:
            return
        
        # 获取锁进行修改
        with self._loggers_lock:
            # 关闭所有日志器
            for logger in self._loggers_immutable.values():
                try:
                    logger.shutdown()
                except Exception as e:
                    # 记录错误但不中断关闭过程
                    with self._error_stats_lock:
                        self._error_stats['shutdown_failures'] += 1
                    import logging
                    logging.error(f"关闭日志器 {logger} 失败: {e}")
            
            # 清空日志器字典
            self._loggers_immutable = {}
            
            # 关闭根日志器
            if self._root_logger_ref is not None:
                try:
                    self._root_logger_ref.shutdown()
                except Exception as e:
                    with self._error_stats_lock:
                        self._error_stats['shutdown_failures'] += 1
                    import logging
                    logging.error(f"关闭根日志器失败: {e}")
                self._root_logger_ref = None
            
            # 重置初始化标志
            self._initialized = False
    
    def add_observer_to_all(self, observer: LogObserver) -> None:
        """向所有日志器添加观察者
        
        Args:
            observer: 日志观察者
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 向根日志器添加观察者
        self._root_logger_ref.add_observer(observer)
        
        # 异步向所有日志器添加观察者，避免阻塞
        loggers_to_update = list(self._loggers_immutable.values())
        
        def add_observers():
            for logger in loggers_to_update:
                try:
                    logger.add_observer(observer)
                except Exception as e:
                    # 记录错误但不中断其他日志器的添加
                    with self._error_stats_lock:
                        self._error_stats['add_observer_failures'] += 1
                    import logging
                    logging.error(f"向日志器 {logger} 添加观察者失败: {e}")
        
        # 启动后台线程
        add_thread = threading.Thread(target=add_observers, daemon=True)
        add_thread.start()
    
    def remove_observer_from_all(self, observer: LogObserver) -> None:
        """从所有日志器移除观察者
        
        Args:
            observer: 日志观察者
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 从根日志器移除观察者
        self._root_logger_ref.remove_observer(observer)
        
        # 异步从所有日志器移除观察者，避免阻塞
        loggers_to_update = list(self._loggers_immutable.values())
        
        def remove_observers():
            for logger in loggers_to_update:
                try:
                    logger.remove_observer(observer)
                except Exception as e:
                    # 记录错误但不中断其他日志器的移除
                    with self._error_stats_lock:
                        self._error_stats['remove_observer_failures'] += 1
                    import logging
                    logging.error(f"从日志器 {logger} 移除观察者失败: {e}")
        
        # 启动后台线程
        remove_thread = threading.Thread(target=remove_observers, daemon=True)
        remove_thread.start()
    
    def flush_all(self) -> None:
        """刷新所有日志器
        
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 刷新根日志器
        self._root_logger_ref.flush()
        
        # 异步刷新所有日志器，避免阻塞
        loggers_to_update = list(self._loggers_immutable.values())
        
        def flush_loggers():
            for logger in loggers_to_update:
                try:
                    logger.flush()
                except Exception as e:
                    # 记录错误但不中断其他日志器的刷新
                    with self._error_stats_lock:
                        self._error_stats['flush_failures'] += 1
                    import logging
                    logging.error(f"刷新日志器 {logger} 失败: {e}")
        
        # 启动后台线程
        flush_thread = threading.Thread(target=flush_loggers, daemon=True)
        flush_thread.start()
    
    def get_logger_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取日志器信息
        
        Args:
            name: 日志器名称
            
        Returns:
            Optional[Dict[str, Any]]: 日志器信息，如果不存在则返回None
        """
        if not self._initialized:
            return None
        
        if name == "root" or name == "":
            return self._root_logger_ref.get_logger_info()
        
        # 无锁读取不可变字典
        logger = self._loggers_immutable.get(name)
        if logger is not None:
            return logger.get_logger_info()
        
        return None
    
    def get_all_loggers_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有日志器信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有日志器信息的字典
        """
        if not self._initialized:
            return {}
        
        result = {}
        
        # 添加根日志器信息
        result["root"] = self._root_logger_ref.get_logger_info()
        
        # 无锁读取不可变字典并添加所有日志器信息
        for name, logger in self._loggers_immutable.items():
            result[name] = logger.get_logger_info()
        
        return result
    
    def get_factory(self) -> Optional[LoggerFactory]:
        """获取日志器工厂
        
        Returns:
            Optional[LoggerFactory]: 日志器工厂，如果未初始化则返回None
        """
        return self._factory
    
    def set_factory(self, factory: LoggerFactory) -> None:
        """设置日志器工厂
        
        Args:
            factory: 日志器工厂
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        self._factory = factory
    
    def is_initialized(self) -> bool:
        """检查日志管理器是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._initialized
    
    def get_loggers_count(self) -> int:
        """获取日志器数量
        
        Returns:
            int: 日志器数量
        """
        if not self._initialized:
            return 0
        
        # 无锁读取不可变字典的长度
        return len(self._loggers_immutable)
    
    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计信息
        
        Returns:
            Dict[str, int]: 错误统计信息
        """
        with self._error_stats_lock:
            return dict(self._error_stats)
    
    def __del__(self):
        """析构函数"""
        # 确保资源被释放
        if hasattr(self, '_initialized') and self._initialized:
            self.shutdown()


# 便捷函数
def get_log_manager() -> LogManager:
    """获取日志管理器实例
    
    Returns:
        LogManager: 日志管理器实例
    """
    return LogManager()


def get_logger(name: str) -> Logger:
    """获取日志器的便捷函数
    
    Args:
        name: 日志器名称
        
    Returns:
        Logger: 日志器实例
    """
    manager = get_log_manager()
    return manager.get_logger(name)


def get_root_logger() -> Logger:
    """获取根日志器的便捷函数
    
    Returns:
        Logger: 根日志器实例
    """
    manager = get_log_manager()
    return manager.get_root_logger()


def initialize_logging(config: Optional[LogConfig] = None, factory: Optional[LoggerFactory] = None) -> LogManager:
    """初始化日志系统的便捷函数
    
    Args:
        config: 日志配置，如果为None则使用默认配置
        factory: 日志器工厂，如果为None则使用默认工厂
        
    Returns:
        LogManager: 日志管理器实例
    """
    manager = get_log_manager()
    manager.initialize(config, factory)
    return manager