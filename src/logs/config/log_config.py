"""
日志配置模块

定义了日志配置的数据类和管理器，提供了灵活的配置管理功能。
包括配置数据类、配置管理器和配置验证等功能。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import copy
import json
import os

from ..core.interfaces import LogConfig, LogOutputStrategy
from ..core.types import LogLevel
from ..strategies.output_strategies import ConsoleOutputStrategy


@dataclass
class LogConfigData(LogConfig):
    """日志配置数据类
    
    封装了日志系统的所有配置信息，包括日志级别、输出策略、格式化等
    """
    min_level: LogLevel = LogLevel.INFO
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    output_strategies: List[LogOutputStrategy] = field(default_factory=list)
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_async: bool = True
    queue_size: int = 1000
    flush_interval: float = 1.0  # seconds
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def get_min_level(self) -> LogLevel:
        """获取最低日志级别
        
        Returns:
            LogLevel: 最低日志级别
        """
        return self.min_level
    
    def get_output_strategies(self) -> List[LogOutputStrategy]:
        """获取输出策略列表
        
        Returns:
            List[LogOutputStrategy]: 输出策略列表
        """
        return self.output_strategies.copy()
    
    def get_format_string(self) -> str:
        """获取格式字符串
        
        Returns:
            str: 格式字符串
        """
        return self.format_string
    
    def is_async_enabled(self) -> bool:
        """检查是否启用异步日志
        
        Returns:
            bool: 是否启用异步日志
        """
        return self.enable_async
    
    def get_queue_size(self) -> int:
        """获取异步队列大小
        
        Returns:
            int: 队列大小
        """
        return self.queue_size
    
    def get_flush_interval(self) -> float:
        """获取刷新间隔（秒）
        
        Returns:
            float: 刷新间隔
        """
        return self.flush_interval
    
    def get_custom_property(self, key: str, default_value: Any = None) -> Any:
        """获取自定义属性
        
        Args:
            key: 属性键
            default_value: 默认值
            
        Returns:
            Any: 属性值
        """
        return self.custom_properties.get(key, default_value)
    
    def set_custom_property(self, key: str, value: Any) -> None:
        """设置自定义属性
        
        Args:
            key: 属性键
            value: 属性值
        """
        self.custom_properties[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的配置
        """
        return {
            "min_level": self.min_level.name,
            "format_string": self.format_string,
            "max_file_size": self.max_file_size,
            "backup_count": self.backup_count,
            "enable_async": self.enable_async,
            "queue_size": self.queue_size,
            "flush_interval": self.flush_interval,
            "custom_properties": self.custom_properties
        }
    
    def validate(self) -> bool:
        """验证配置有效性
        
        Returns:
            bool: 配置是否有效
            
        Raises:
            ValueError: 配置验证失败
        """
        # 验证日志级别
        if not isinstance(self.min_level, LogLevel):
            raise ValueError("日志级别必须是LogLevel枚举值")
        
        # 验证刷新间隔
        if self.flush_interval <= 0:
            raise ValueError("刷新间隔必须大于0")
        
        # 验证队列大小
        if self.queue_size <= 0:
            raise ValueError("队列大小必须大于0")
        
        # 验证文件大小
        if self.max_file_size <= 0:
            raise ValueError("最大文件大小必须大于0")
        
        # 验证备份数量
        if self.backup_count < 0:
            raise ValueError("备份数量不能为负数")
        
        # 如果没有输出策略，默认添加控制台输出
        if not self.output_strategies:
            self.output_strategies.append(ConsoleOutputStrategy())
        
        return True
    
    def clone(self) -> 'LogConfigData':
        """克隆配置
        
        Returns:
            LogConfigData: 配置的克隆
        """
        # 创建配置的深拷贝
        return copy.deepcopy(self)


class LogConfigManager:
    """日志配置管理器
    
    负责日志配置的加载、保存和管理
    """
    
    def __init__(self):
        """初始化日志配置管理器"""
        self._config: Optional[LogConfigData] = None
        self._config_file_path: Optional[str] = None
        self._validation_rules: List[Callable[[LogConfigData], bool]] = []
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> LogConfigData:
        """从字典加载配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            LogConfigData: 日志配置实例
            
        Raises:
            ValueError: 配置加载失败
        """
        try:
            # 解析日志级别
            min_level = LogLevel.from_name(config_dict.get("min_level", "INFO"))
            
            # 创建配置对象
            config = LogConfigData(
                min_level=min_level,
                format_string=config_dict.get("format_string", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                max_file_size=config_dict.get("max_file_size", 10 * 1024 * 1024),
                backup_count=config_dict.get("backup_count", 5),
                enable_async=config_dict.get("enable_async", True),
                queue_size=config_dict.get("queue_size", 1000),
                flush_interval=config_dict.get("flush_interval", 1.0),
                custom_properties=config_dict.get("custom_properties", {})
            )
            
            # 验证配置
            self._validate_config(config)
            
            self._config = config
            return config
            
        except Exception as e:
            raise ValueError(f"配置加载失败: {e}")
    
    def load_from_file(self, file_path: str) -> LogConfigData:
        """从文件加载配置
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            LogConfigData: 日志配置实例
            
        Raises:
            ValueError: 配置加载失败
        """
        try:
            if not os.path.exists(file_path):
                raise ValueError(f"配置文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = self.load_from_dict(config_dict)
            self._config_file_path = file_path
            return config
            
        except Exception as e:
            raise ValueError(f"从文件加载配置失败: {e}")
    
    def save_to_file(self, file_path: str, config: Optional[LogConfigData] = None) -> None:
        """保存配置到文件
        
        Args:
            file_path: 配置文件路径
            config: 要保存的配置，如果为None则使用当前配置
        """
        if config is None:
            config = self._config
        
        if config is None:
            raise ValueError("没有可保存的配置")
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存配置
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._config_file_path = file_path
            
        except Exception as e:
            raise ValueError(f"保存配置到文件失败: {e}")
    
    def save_current_config(self) -> None:
        """保存当前配置到文件
        
        Raises:
            ValueError: 保存失败
        """
        if self._config_file_path is None:
            raise ValueError("没有配置文件路径")
        
        self.save_to_file(self._config_file_path, self._config)
    
    def get_config(self) -> Optional[LogConfigData]:
        """获取当前配置
        
        Returns:
            Optional[LogConfigData]: 当前配置，如果没有则返回None
        """
        return self._config
    
    def set_config(self, config: LogConfigData) -> None:
        """设置当前配置
        
        Args:
            config: 日志配置
            
        Raises:
            ValueError: 配置验证失败
        """
        self._validate_config(config)
        self._config = config
    
    def update_config(self, **kwargs) -> None:
        """更新当前配置
        
        Args:
            **kwargs: 要更新的配置项
            
        Raises:
            ValueError: 配置更新失败
        """
        if self._config is None:
            raise ValueError("没有当前配置")
        
        # 创建配置的副本
        new_config = self._config.clone()
        
        # 更新配置项
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
            else:
                new_config.set_custom_property(key, value)
        
        # 验证新配置
        self._validate_config(new_config)
        
        # 更新当前配置
        self._config = new_config
    
    def add_validation_rule(self, rule: Callable[[LogConfigData], bool]) -> None:
        """添加配置验证规则
        
        Args:
            rule: 验证规则函数
        """
        self._validation_rules.append(rule)
    
    def clear_validation_rules(self) -> None:
        """清空所有验证规则"""
        self._validation_rules.clear()
    
    def _validate_config(self, config: LogConfigData) -> None:
        """验证配置
        
        Args:
            config: 日志配置
            
        Raises:
            ValueError: 配置验证失败
        """
        # 基本验证
        config.validate()
        
        # 自定义验证规则
        for rule in self._validation_rules:
            if not rule(config):
                raise ValueError("配置验证失败")
    
    def create_default_config(self) -> LogConfigData:
        """创建默认配置
        
        Returns:
            LogConfigData: 默认配置
        """
        config = LogConfigData(
            min_level=LogLevel.INFO,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            output_strategies=[ConsoleOutputStrategy()],
            max_file_size=10 * 1024 * 1024,
            backup_count=5,
            enable_async=True,
            queue_size=1000,
            flush_interval=1.0
        )
        
        self._config = config
        return config
    
    def get_config_file_path(self) -> Optional[str]:
        """获取配置文件路径
        
        Returns:
            Optional[str]: 配置文件路径，如果没有则返回None
        """
        return self._config_file_path
    
    def set_config_file_path(self, file_path: str) -> None:
        """设置配置文件路径
        
        Args:
            file_path: 配置文件路径
        """
        self._config_file_path = file_path


class LogConfigTemplate:
    """日志配置模板
    
    提供常用的配置模板，简化配置创建过程
    """
    
    @staticmethod
    def development() -> LogConfigData:
        """开发环境配置模板"""
        from ..strategies.output_strategies import FileOutputStrategy
        
        config = LogConfigData(
            min_level=LogLevel.DEBUG,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            output_strategies=[
                ConsoleOutputStrategy(use_colors=True),
                FileOutputStrategy("logs/development.log")
            ],
            enable_async=False
        )
        
        return config
    
    @staticmethod
    def production() -> LogConfigData:
        """生产环境配置模板"""
        from ..strategies.output_strategies import FileOutputStrategy, RemoteOutputStrategy
        
        config = LogConfigData(
            min_level=LogLevel.INFO,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            output_strategies=[
                FileOutputStrategy("logs/production.log", max_file_size=50*1024*1024, backup_count=10),
                RemoteOutputStrategy("https://log.example.com/api/logs", timeout=10)
            ],
            enable_async=True,
            queue_size=5000,
            flush_interval=5.0
        )
        
        return config
    
    @staticmethod
    def testing() -> LogConfigData:
        """测试环境配置模板"""
        from ..strategies.output_strategies import FileOutputStrategy
        
        config = LogConfigData(
            min_level=LogLevel.WARNING,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            output_strategies=[
                ConsoleOutputStrategy(use_colors=False),
                FileOutputStrategy("logs/testing.log")
            ],
            enable_async=False
        )
        
        return config
    
    @staticmethod
    def gui_application(callback) -> LogConfigData:
        """GUI应用程序配置模板"""
        from ..strategies.output_strategies import GuiOutputStrategy, FileOutputStrategy
        
        config = LogConfigData(
            min_level=LogLevel.INFO,
            format_string="%(asctime)s [%(levelname)s] %(message)s",
            output_strategies=[
                GuiOutputStrategy(callback),
                FileOutputStrategy("logs/application.log")
            ],
            enable_async=True
        )
        
        return config