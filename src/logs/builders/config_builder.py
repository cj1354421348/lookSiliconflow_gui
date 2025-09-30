"""
配置构建器模块

实现了日志配置的建造者模式，提供了流式API来构建复杂的日志配置。
支持链式调用、配置验证和预设模板等功能。
"""

from typing import List, Dict, Any, Optional, Callable
import copy

from ..core.interfaces import LogConfig, LogOutputStrategy
from ..core.types import LogLevel
from ..config.log_config import LogConfigData
from ..strategies.output_strategies import (
    ConsoleOutputStrategy, 
    FileOutputStrategy, 
    GuiOutputStrategy, 
    RemoteOutputStrategy
)


class LogConfigBuilder:
    """日志配置构建器
    
    提供流式API来构建日志配置，支持链式调用和配置验证
    """
    
    def __init__(self):
        """初始化日志配置构建器"""
        self._config = LogConfigData()
        self._validation_rules: List[Callable[[LogConfigData], bool]] = []
    
    def set_level(self, level: LogLevel) -> 'LogConfigBuilder':
        """设置日志级别
        
        Args:
            level: 日志级别
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.min_level = level
        return self
    
    def set_format(self, format_string: str) -> 'LogConfigBuilder':
        """设置日志格式字符串
        
        Args:
            format_string: 格式字符串
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.format_string = format_string
        return self
    
    def add_file_output(self, 
                       file_path: str, 
                       encoding: str = 'utf-8',
                       max_file_size: Optional[int] = None,
                       backup_count: Optional[int] = None) -> 'LogConfigBuilder':
        """添加文件输出策略
        
        Args:
            file_path: 日志文件路径
            encoding: 文件编码
            max_file_size: 最大文件大小
            backup_count: 备份文件数量
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        strategy = FileLogStrategy(
            file_path=file_path,
            encoding=encoding,
            max_file_size=max_file_size or self._config.max_file_size,
            backup_count=backup_count or self._config.backup_count
        )
        self._config.output_strategies.append(strategy)
        return self
    
    def add_console_output(self, use_colors: bool = True) -> 'LogConfigBuilder':
        """添加控制台输出策略
        
        Args:
            use_colors: 是否使用颜色输出
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        strategy = ConsoleOutputStrategy(use_colors=use_colors)
        self._config.output_strategies.append(strategy)
        return self
    
    def add_gui_output(self, callback: Callable[[str], None]) -> 'LogConfigBuilder':
        """添加GUI输出策略
        
        Args:
            callback: GUI回调函数
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        strategy = GuiOutputStrategy(callback=callback)
        self._config.output_strategies.append(strategy)
        return self
    
    def add_remote_output(self,
                         endpoint: str,
                         method: str = "POST",
                         headers: Optional[Dict[str, str]] = None,
                         timeout: int = 5,
                         batch_size: int = 10,
                         max_retries: int = 3) -> 'LogConfigBuilder':
        """添加远程输出策略
        
        Args:
            endpoint: 远程日志服务端点
            method: HTTP方法
            headers: HTTP头
            timeout: 超时时间（秒）
            batch_size: 批量发送大小
            max_retries: 最大重试次数
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        strategy = RemoteOutputStrategy(
            endpoint=endpoint,
            method=method,
            headers=headers,
            timeout=timeout,
            batch_size=batch_size,
            max_retries=max_retries
        )
        self._config.output_strategies.append(strategy)
        return self
    
    def set_max_file_size(self, size_bytes: int) -> 'LogConfigBuilder':
        """设置最大文件大小
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.max_file_size = size_bytes
        return self
    
    def set_backup_count(self, count: int) -> 'LogConfigBuilder':
        """设置备份文件数量
        
        Args:
            count: 备份文件数量
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.backup_count = count
        return self
    
    def enable_async(self, enabled: bool = True) -> 'LogConfigBuilder':
        """启用或禁用异步日志
        
        Args:
            enabled: 是否启用异步日志
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.enable_async = enabled
        return self
    
    def set_queue_size(self, size: int) -> 'LogConfigBuilder':
        """设置异步队列大小
        
        Args:
            size: 队列大小
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.queue_size = size
        return self
    
    def set_flush_interval(self, interval_seconds: float) -> 'LogConfigBuilder':
        """设置刷新间隔
        
        Args:
            interval_seconds: 刷新间隔（秒）
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.flush_interval = interval_seconds
        return self
    
    def add_custom_property(self, key: str, value: Any) -> 'LogConfigBuilder':
        """添加自定义属性
        
        Args:
            key: 属性键
            value: 属性值
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config.custom_properties[key] = value
        return self
    
    def add_validation_rule(self, rule: Callable[[LogConfigData], bool]) -> 'LogConfigBuilder':
        """添加验证规则
        
        Args:
            rule: 验证规则函数
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._validation_rules.append(rule)
        return self
    
    def build(self) -> LogConfigData:
        """构建日志配置
        
        Returns:
            LogConfigData: 日志配置实例
            
        Raises:
            ValueError: 配置验证失败
        """
        # 创建配置的深拷贝，避免后续修改影响构建的配置
        config = copy.deepcopy(self._config)
        
        # 验证配置
        self._validate_config(config)
        
        # 如果没有输出策略，默认添加控制台输出
        if not config.output_strategies:
            config.output_strategies.append(ConsoleOutputStrategy())
        
        return config
    
    def _validate_config(self, config: LogConfigData) -> None:
        """验证配置
        
        Args:
            config: 日志配置
            
        Raises:
            ValueError: 配置验证失败
        """
        # 基本验证
        config.validate()
        
        # 应用自定义验证规则
        for rule in self._validation_rules:
            if not rule(config):
                raise ValueError("配置验证失败")
    
    def reset(self) -> 'LogConfigBuilder':
        """重置构建器
        
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config = LogConfigData()
        self._validation_rules.clear()
        return self
    
    def from_config(self, config: LogConfigData) -> 'LogConfigBuilder':
        """从现有配置初始化构建器
        
        Args:
            config: 现有配置
            
        Returns:
            LogConfigBuilder: 构建器实例，支持链式调用
        """
        self._config = copy.deepcopy(config)
        return self


class LogConfigTemplate:
    """日志配置模板
    
    提供常用的配置模板，简化配置创建过程
    """
    
    @staticmethod
    def development() -> LogConfigBuilder:
        """开发环境配置模板"""
        return (LogConfigBuilder()
                .set_level(LogLevel.DEBUG)
                .add_console_output(use_colors=True)
                .add_file_output("logs/development.log")
                .set_format("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))
    
    @staticmethod
    def production() -> LogConfigBuilder:
        """生产环境配置模板"""
        return (LogConfigBuilder()
                .set_level(LogLevel.INFO)
                .add_file_output("logs/production.log", max_file_size=50*1024*1024, backup_count=10)
                .add_remote_output("https://log.example.com/api/logs", timeout=10)
                .enable_async()
                .set_queue_size(5000)
                .set_flush_interval(5.0))
    
    @staticmethod
    def testing() -> LogConfigBuilder:
        """测试环境配置模板"""
        return (LogConfigBuilder()
                .set_level(LogLevel.WARNING)
                .add_console_output(use_colors=False)
                .add_file_output("logs/testing.log"))
    
    @staticmethod
    def gui_application(callback: Callable[[str], None]) -> LogConfigBuilder:
        """GUI应用程序配置模板"""
        return (LogConfigBuilder()
                .set_level(LogLevel.INFO)
                .add_gui_output(callback)
                .add_file_output("logs/application.log")
                .set_format("%(asctime)s [%(levelname)s] %(message)s"))


class LogConfigPreset:
    """日志配置预设
    
    管理和提供配置预设，支持注册和获取预设
    """
    
    _presets = {
        "development": LogConfigTemplate.development,
        "production": LogConfigTemplate.production,
        "testing": LogConfigTemplate.testing,
    }
    
    @classmethod
    def register_preset(cls, name: str, preset_factory: Callable[[], LogConfigBuilder]) -> None:
        """注册配置预设
        
        Args:
            name: 预设名称
            preset_factory: 预设工厂函数
            
        Raises:
            ValueError: 预设名称已存在
        """
        if name in cls._presets:
            raise ValueError(f"预设名称已存在: {name}")
        
        cls._presets[name] = preset_factory
    
    @classmethod
    def unregister_preset(cls, name: str) -> bool:
        """注销配置预设
        
        Args:
            name: 预设名称
            
        Returns:
            bool: 是否成功注销
        """
        if name in cls._presets:
            del cls._presets[name]
            return True
        return False
    
    @classmethod
    def get_preset(cls, name: str, **kwargs) -> LogConfigBuilder:
        """获取配置预设
        
        Args:
            name: 预设名称
            **kwargs: 预设参数
            
        Returns:
            LogConfigBuilder: 配置构建器
            
        Raises:
            ValueError: 不支持的预设名称
        """
        if name not in cls._presets:
            raise ValueError(f"不支持的配置预设: {name}")
        
        return cls._presets[name](**kwargs)
    
    @classmethod
    def list_presets(cls) -> List[str]:
        """列出所有可用的预设名称
        
        Returns:
            List[str]: 预设名称列表
        """
        return list(cls._presets.keys())
    
    @classmethod
    def has_preset(cls, name: str) -> bool:
        """检查是否存在指定的预设
        
        Args:
            name: 预设名称
            
        Returns:
            bool: 是否存在
        """
        return name in cls._presets


class LogConfigValidator:
    """日志配置验证器
    
    提供常用的配置验证规则
    """
    
    @staticmethod
    def min_level_at_least(min_level: LogLevel) -> Callable[[LogConfigData], bool]:
        """创建验证规则：最低日志级别至少为指定级别
        
        Args:
            min_level: 最低日志级别
            
        Returns:
            Callable[[LogConfigData], bool]: 验证规则函数
        """
        def rule(config: LogConfigData) -> bool:
            return config.min_level.value >= min_level.value
        return rule
    
    @staticmethod
    def queue_size_at_least(min_size: int) -> Callable[[LogConfigData], bool]:
        """创建验证规则：队列大小至少为指定大小
        
        Args:
            min_size: 最小队列大小
            
        Returns:
            Callable[[LogConfigData], bool]: 验证规则函数
        """
        def rule(config: LogConfigData) -> bool:
            return config.queue_size >= min_size
        return rule
    
    @staticmethod
    def has_output_strategy(strategy_type: type) -> Callable[[LogConfigData], bool]:
        """创建验证规则：必须包含指定类型的输出策略
        
        Args:
            strategy_type: 输出策略类型
            
        Returns:
            Callable[[LogConfigData], bool]: 验证规则函数
        """
        def rule(config: LogConfigData) -> bool:
            return any(isinstance(strategy, strategy_type) for strategy in config.output_strategies)
        return rule
    
    @staticmethod
    def has_custom_property(key: str) -> Callable[[LogConfigData], bool]:
        """创建验证规则：必须包含指定的自定义属性
        
        Args:
            key: 属性键
            
        Returns:
            Callable[[LogConfigData], bool]: 验证规则函数
        """
        def rule(config: LogConfigData) -> bool:
            return key in config.custom_properties
        return rule


# 便捷函数
def create_config_builder() -> LogConfigBuilder:
    """创建配置构建器的便捷函数
    
    Returns:
        LogConfigBuilder: 配置构建器实例
    """
    return LogConfigBuilder()


def create_config_from_preset(preset_name: str, **kwargs) -> LogConfigData:
    """从预设创建配置的便捷函数
    
    Args:
        preset_name: 预设名称
        **kwargs: 预设参数
        
    Returns:
        LogConfigData: 日志配置实例
    """
    builder = LogConfigPreset.get_preset(preset_name, **kwargs)
    return builder.build()