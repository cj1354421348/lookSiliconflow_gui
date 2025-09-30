"""
日志管理器模块

实现了线程安全的单例日志管理器，提供统一的日志管理入口。
支持多种日志器类型，可以动态配置和管理日志器。
"""

import threading
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
    """
    
    def __init__(self):
        """初始化日志管理器"""
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 日志器字典
        self._loggers: Dict[str, Logger] = {}
        self._loggers_lock = threading.Lock()
        
        # 日志配置
        self._config: Optional[LogConfig] = None
        self._config_lock = threading.Lock()
        
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
        
        # 检查是否已存在
        with self._loggers_lock:
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
        
        with self._config_lock:
            # 更新配置
            self._config = config
            
            # 更新根日志器
            self._root_logger.update_config(config)
            
            # 更新所有日志器
            with self._loggers_lock:
                for logger in self._loggers.values():
                    logger.update_config(config)
    
    def shutdown(self) -> None:
        """关闭日志管理器"""
        if not self._initialized:
            return
        
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
        
        # 向根日志器添加观察者
        self._root_logger.add_observer(observer)
        
        # 向所有日志器添加观察者
        with self._loggers_lock:
            for logger in self._loggers.values():
                logger.add_observer(observer)
    
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
        self._root_logger.remove_observer(observer)
        
        # 从所有日志器移除观察者
        with self._loggers_lock:
            for logger in self._loggers.values():
                logger.remove_observer(observer)
    
    def flush_all(self) -> None:
        """刷新所有日志器
        
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 刷新根日志器
        self._root_logger.flush()
        
        # 刷新所有日志器
        with self._loggers_lock:
            for logger in self._loggers.values():
                logger.flush()
    
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
        
        # 添加根日志器信息
        result["root"] = self._root_logger.get_logger_info()
        
        # 添加所有日志器信息
        with self._loggers_lock:
            for name, logger in self._loggers.items():
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