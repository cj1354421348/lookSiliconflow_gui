"""
LogManager优化版本
使用更细粒度的锁策略，避免过度同步导致的性能问题
"""

import threading
import time
from typing import Dict, Optional, List, Any

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
    使用优化的锁策略，避免死锁和过度同步
    """
    
    def __init__(self):
        """初始化日志管理器"""
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 日志器字典
        self._loggers: Dict[str, Logger] = {}
        self._loggers_lock = threading.RLock()  # 使用可重入锁
        
        # 日志配置
        self._config: Optional[LogConfig] = None
        self._config_lock = threading.RLock()  # 使用可重入锁
        
        # 配置更新标志，用于避免频繁的配置更新
        self._config_updating = False
        self._config_update_lock = threading.Lock()
        
        # 日志器工厂
        self._factory: Optional[LoggerFactory] = None
        
        # 根日志器
        self._root_logger: Optional[Logger] = None
        
        # 初始化标志
        self._initialized = False
        self._initialization_lock = threading.Lock()
    
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
            
            # 使用配置锁保护配置设置
            with self._config_lock:
                self._config = config
                
                # 设置工厂
                if factory is None:
                    factory = get_logger_factory()
                
                self._factory = factory
                
                # 创建根日志器
                self._root_logger = self._factory.create_logger("root", config)
                
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
        
        # 如果请求根日志器
        if name == "root" or name == "":
            return self._root_logger
        
        # 使用日志器锁保护日志器访问
        with self._loggers_lock:
            # 检查是否已存在
            if name in self._loggers:
                return self._loggers[name]
            
            # 创建新日志器
            logger = self._factory.create_logger(name, self._config)
            self._loggers[name] = logger
            
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
        
        return self._root_logger
    
    def has_logger(self, name: str) -> bool:
        """检查是否存在指定名称的日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            bool: 是否存在
        """
        if not self._initialized:
            return False
        
        with self._loggers_lock:
            return name in self._loggers
    
    def remove_logger(self, name: str) -> bool:
        """移除日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            bool: 是否成功移除
        """
        if not self._initialized:
            return False
        
        with self._loggers_lock:
            if name in self._loggers:
                logger = self._loggers.pop(name)
                logger.shutdown()
                return True
        
        return False
    
    def get_logger_names(self) -> List[str]:
        """获取所有日志器名称
        
        Returns:
            List[str]: 日志器名称列表
        """
        if not self._initialized:
            return []
        
        with self._loggers_lock:
            return list(self._loggers.keys())
    
    def get_config(self) -> Optional[LogConfig]:
        """获取日志配置
        
        Returns:
            Optional[LogConfig]: 日志配置，如果未初始化则返回None
        """
        return self._config
    
    def update_config(self, config: LogConfig) -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 使用配置更新锁避免并发配置更新
        with self._config_update_lock:
            # 如果已经在更新配置，直接返回
            if self._config_updating:
                return
            
            self._config_updating = True
        
        try:
            # 先更新配置
            with self._config_lock:
                self._config = config
            
            # 然后更新根日志器（不需要锁，因为根日志器是线程安全的）
            self._root_logger.update_config(config)
            
            # 最后更新所有日志器（使用日志器锁，但避免长时间持有）
            loggers_to_update = []
            with self._loggers_lock:
                loggers_to_update = list(self._loggers.values())
            
            # 在锁外更新日志器，避免长时间持有锁
            for logger in loggers_to_update:
                try:
                    logger.update_config(config)
                except Exception as e:
                    # 单个日志器更新失败不影响其他日志器
                    import logging
                    logging.error(f"更新日志器 {logger} 配置失败: {e}")
                    
        finally:
            # 重置配置更新标志
            with self._config_update_lock:
                self._config_updating = False
    
    def shutdown(self) -> None:
        """关闭日志管理器"""
        if not self._initialized:
            return
        
        # 使用配置更新锁确保没有正在进行的配置更新
        with self._config_update_lock:
            # 关闭所有日志器
            with self._loggers_lock:
                for logger in self._loggers.values():
                    logger.shutdown()
                self._loggers.clear()
            
            # 关闭根日志器
            if self._root_logger:
                self._root_logger.shutdown()
                self._root_logger = None
            
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
        
        # 向根日志器添加观察者（不需要锁）
        self._root_logger.add_observer(observer)
        
        # 向所有日志器添加观察者（使用日志器锁，但避免长时间持有）
        loggers_to_update = []
        with self._loggers_lock:
            loggers_to_update = list(self._loggers.values())
        
        # 在锁外添加观察者，避免长时间持有锁
        for logger in loggers_to_update:
            try:
                logger.add_observer(observer)
            except Exception as e:
                # 单个日志器添加观察者失败不影响其他日志器
                import logging
                logging.error(f"向日志器 {logger} 添加观察者失败: {e}")
    
    def remove_observer_from_all(self, observer: LogObserver) -> None:
        """从所有日志器移除观察者
        
        Args:
            observer: 日志观察者
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 从根日志器移除观察者（不需要锁）
        self._root_logger.remove_observer(observer)
        
        # 从所有日志器移除观察者（使用日志器锁，但避免长时间持有）
        loggers_to_update = []
        with self._loggers_lock:
            loggers_to_update = list(self._loggers.values())
        
        # 在锁外移除观察者，避免长时间持有锁
        for logger in loggers_to_update:
            try:
                logger.remove_observer(observer)
            except Exception as e:
                # 单个日志器移除观察者失败不影响其他日志器
                import logging
                logging.error(f"从日志器 {logger} 移除观察者失败: {e}")
    
    def flush_all(self) -> None:
        """刷新所有日志器
        
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 刷新根日志器（不需要锁）
        self._root_logger.flush()
        
        # 刷新所有日志器（使用日志器锁，但避免长时间持有）
        loggers_to_update = []
        with self._loggers_lock:
            loggers_to_update = list(self._loggers.values())
        
        # 在锁外刷新日志器，避免长时间持有锁
        for logger in loggers_to_update:
            try:
                logger.flush()
            except Exception as e:
                # 单个日志器刷新失败不影响其他日志器
                import logging
                logging.error(f"刷新日志器 {logger} 失败: {e}")
    
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
            return self._root_logger.get_logger_info()
        
        with self._loggers_lock:
            if name in self._loggers:
                return self._loggers[name].get_logger_info()
        
        return None
    
    def get_all_loggers_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有日志器信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有日志器信息的字典
        """
        if not self._initialized:
            return {}
        
        result = {}
        
        # 添加根日志器信息（不需要锁）
        result["root"] = self._root_logger.get_logger_info()
        
        # 添加所有日志器信息（使用日志器锁，但避免长时间持有）
        loggers_info = {}
        with self._loggers_lock:
            for name, logger in self._loggers.items():
                loggers_info[name] = logger.get_logger_info()
        
        # 在锁外合并结果
        result.update(loggers_info)
        
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
        
        with self._config_lock:
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
        
        with self._loggers_lock:
            return len(self._loggers)
    
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