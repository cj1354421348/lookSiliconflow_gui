"""
日志器工厂模块

实现了日志器工厂，负责创建和管理各种类型的日志器。
工厂模式解耦了日志器的创建和使用，支持灵活扩展。
"""

from typing import Dict, Type, Optional, Callable, Any

from ..core.interfaces import Logger, LogConfig
from ..core.types import LogLevel
from ..config.log_config import LogConfigData
from ..loggers.observable_logger import ObservableLogger
from ..loggers.async_logger import AsyncLogger


class LoggerFactory:
    """日志器工厂
    
    负责创建各种类型的日志器，支持注册新的日志器类型和自定义创建器
    """
    
    def __init__(self):
        """初始化日志器工厂"""
        self._logger_types: Dict[str, Type[Logger]] = {
            "default": ObservableLogger,
            "observable": ObservableLogger,
            "async": AsyncLogger,
        }
        self._custom_creators: Dict[str, Callable[[str, LogConfig], Logger]] = {}
    
    def register_logger_type(self, name: str, logger_type: Type[Logger]) -> None:
        """注册日志器类型
        
        Args:
            name: 日志器类型名称
            logger_type: 日志器类型
            
        Raises:
            ValueError: 类型名称已存在
        """
        if name in self._logger_types or name in self._custom_creators:
            raise ValueError(f"日志器类型名称已存在: {name}")
        
        self._logger_types[name] = logger_type
    
    def register_custom_creator(self, name: str, creator: Callable[[str, LogConfig], Logger]) -> None:
        """注册自定义日志器创建器
        
        Args:
            name: 日志器类型名称
            creator: 创建器函数
            
        Raises:
            ValueError: 类型名称已存在
        """
        if name in self._logger_types or name in self._custom_creators:
            raise ValueError(f"日志器类型名称已存在: {name}")
        
        self._custom_creators[name] = creator
    
    def unregister_logger_type(self, name: str) -> bool:
        """注销日志器类型
        
        Args:
            name: 日志器类型名称
            
        Returns:
            bool: 是否成功注销
        """
        if name in self._logger_types:
            del self._logger_types[name]
            return True
        elif name in self._custom_creators:
            del self._custom_creators[name]
            return True
        return False
    
    def create_logger(self, name: str, config: LogConfig, logger_type: str = "default") -> Logger:
        """创建日志器实例
        
        Args:
            name: 日志器名称
            config: 日志配置
            logger_type: 日志器类型
            
        Returns:
            Logger: 日志器实例
            
        Raises:
            ValueError: 不支持的日志器类型
        """
        # 检查自定义创建器
        if logger_type in self._custom_creators:
            return self._custom_creators[logger_type](name, config)
        
        # 检查注册的类型
        if logger_type not in self._logger_types:
            raise ValueError(f"不支持的日志器类型: {logger_type}")
        
        # 创建日志器
        logger_class = self._logger_types[logger_type]
        return logger_class(name, config)
    
    def get_available_types(self) -> list:
        """获取可用的日志器类型列表
        
        Returns:
            list: 日志器类型列表
        """
        return list(self._logger_types.keys()) + list(self._custom_creators.keys())
    
    def has_logger_type(self, name: str) -> bool:
        """检查是否存在指定的日志器类型
        
        Args:
            name: 日志器类型名称
            
        Returns:
            bool: 是否存在
        """
        return name in self._logger_types or name in self._custom_creators
    
    def get_logger_type_info(self, name: str) -> Dict[str, Any]:
        """获取日志器类型信息
        
        Args:
            name: 日志器类型名称
            
        Returns:
            Dict[str, Any]: 类型信息
            
        Raises:
            ValueError: 不支持的日志器类型
        """
        if name in self._logger_types:
            return {
                "type_name": name,
                "type_class": self._logger_types[name].__name__,
                "type_module": self._logger_types[name].__module__,
                "creator_type": "class"
            }
        elif name in self._custom_creators:
            return {
                "type_name": name,
                "type_class": "CustomCreator",
                "type_module": self._custom_creators[name].__module__,
                "creator_type": "function"
            }
        else:
            raise ValueError(f"不支持的日志器类型: {name}")
    
    def get_all_types_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有日志器类型的信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有类型的信息
        """
        result = {}
        for name in self.get_available_types():
            result[name] = self.get_logger_type_info(name)
        return result


class DefaultLoggerFactory(LoggerFactory):
    """默认日志器工厂
    
    提供默认的日志器创建功能，预注册了常用的日志器类型
    """
    
    def __init__(self):
        """初始化默认日志器工厂"""
        super().__init__()
        
        # 注册默认的日志器类型
        self._register_default_types()
    
    def _register_default_types(self) -> None:
        """注册默认的日志器类型"""
        # 默认类型已在父类中注册
        pass


class ConfigAwareLoggerFactory(LoggerFactory):
    """配置感知的日志器工厂
    
    根据配置自动选择合适的日志器类型
    """
    
    def __init__(self):
        """初始化配置感知的日志器工厂"""
        super().__init__()
    
    def create_logger(self, name: str, config: LogConfig, logger_type: str = None) -> Logger:
        """创建日志器实例（自动选择类型）
        
        Args:
            name: 日志器名称
            config: 日志配置
            logger_type: 日志器类型，如果为None则自动选择
            
        Returns:
            Logger: 日志器实例
        """
        # 如果没有指定类型，根据配置自动选择
        if logger_type is None:
            logger_type = self._select_logger_type(config)
        
        return super().create_logger(name, config, logger_type)
    
    def _select_logger_type(self, config: LogConfig) -> str:
        """根据配置选择日志器类型
        
        Args:
            config: 日志配置
            
        Returns:
            str: 日志器类型名称
        """
        # 如果启用异步，选择异步日志器
        if config.is_async_enabled():
            return "async"
        
        # 默认选择可观察日志器
        return "observable"


class CachedLoggerFactory(LoggerFactory):
    """缓存的日志器工厂
    
    缓存已创建的日志器，避免重复创建
    """
    
    def __init__(self):
        """初始化缓存的日志器工厂"""
        super().__init__()
        self._logger_cache: Dict[str, Logger] = {}
        self._cache_lock = None  # 延迟初始化
    
    def create_logger(self, name: str, config: LogConfig, logger_type: str = "default") -> Logger:
        """创建日志器实例（带缓存）
        
        Args:
            name: 日志器名称
            config: 日志配置
            logger_type: 日志器类型
            
        Returns:
            Logger: 日志器实例
        """
        # 生成缓存键
        cache_key = self._generate_cache_key(name, config, logger_type)
        
        # 检查缓存
        if self._has_lock():
            with self._get_lock():
                if cache_key in self._logger_cache:
                    return self._logger_cache[cache_key]
        else:
            if cache_key in self._logger_cache:
                return self._logger_cache[cache_key]
        
        # 创建日志器
        logger = super().create_logger(name, config, logger_type)
        
        # 缓存日志器
        if self._has_lock():
            with self._get_lock():
                self._logger_cache[cache_key] = logger
        else:
            self._logger_cache[cache_key] = logger
        
        return logger
    
    def _generate_cache_key(self, name: str, config: LogConfig, logger_type: str) -> str:
        """生成缓存键
        
        Args:
            name: 日志器名称
            config: 日志配置
            logger_type: 日志器类型
            
        Returns:
            str: 缓存键
        """
        # 简单的缓存键生成策略
        return f"{name}:{logger_type}:{id(config)}"
    
    def _has_lock(self) -> bool:
        """检查是否有锁"""
        return self._cache_lock is not None
    
    def _get_lock(self):
        """获取锁"""
        if self._cache_lock is None:
            import threading
            self._cache_lock = threading.Lock()
        return self._cache_lock
    
    def clear_cache(self) -> None:
        """清空缓存"""
        if self._has_lock():
            with self._get_lock():
                self._logger_cache.clear()
        else:
            self._logger_cache.clear()
    
    def get_cache_size(self) -> int:
        """获取缓存大小
        
        Returns:
            int: 缓存大小
        """
        return len(self._logger_cache)
    
    def is_cached(self, name: str, config: LogConfig, logger_type: str = "default") -> bool:
        """检查日志器是否已缓存
        
        Args:
            name: 日志器名称
            config: 日志配置
            logger_type: 日志器类型
            
        Returns:
            bool: 是否已缓存
        """
        cache_key = self._generate_cache_key(name, config, logger_type)
        return cache_key in self._logger_cache


# 全局日志器工厂实例
_global_logger_factory = None


def get_logger_factory() -> LoggerFactory:
    """获取全局日志器工厂实例
    
    Returns:
        LoggerFactory: 全局日志器工厂实例
    """
    global _global_logger_factory
    if _global_logger_factory is None:
        _global_logger_factory = ConfigAwareLoggerFactory()
    return _global_logger_factory


def set_logger_factory(factory: LoggerFactory) -> None:
    """设置全局日志器工厂实例
    
    Args:
        factory: 日志器工厂实例
    """
    global _global_logger_factory
    _global_logger_factory = factory


def create_logger(name: str, config: LogConfig, logger_type: str = "default") -> Logger:
    """创建日志器的便捷函数
    
    Args:
        name: 日志器名称
        config: 日志配置
        logger_type: 日志器类型
        
    Returns:
        Logger: 日志器实例
    """
    factory = get_logger_factory()
    return factory.create_logger(name, config, logger_type)