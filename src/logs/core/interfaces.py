"""
核心接口模块

定义了日志系统的核心接口，包括日志器接口、输出策略接口、观察者接口和格式化器接口。
这些接口构成了整个日志系统的基础框架，实现了高内聚、低耦合的设计。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable

from .types import LogLevel, LogEntry


class LogOutputStrategy(ABC):
    """日志输出策略接口
    
    定义了日志输出策略的抽象接口，不同的输出方式（文件、控制台、GUI等）
    都可以实现此接口，从而实现策略模式
    """
    
    @abstractmethod
    def output(self, record: LogEntry) -> None:
        """输出日志记录
        
        Args:
            record: 日志记录
        """
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """刷新输出缓冲区
        
        确保所有缓冲的日志记录都已输出
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭输出策略
        
        释放资源，关闭文件、网络连接等
        """
        pass
    
    def is_thread_safe(self) -> bool:
        """检查输出策略是否线程安全
        
        Returns:
            bool: 是否线程安全
        """
        return False
    
    def supports_formatting(self) -> bool:
        """检查输出策略是否支持自定义格式
        
        Returns:
            bool: 是否支持自定义格式
        """
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息
        
        Returns:
            Dict[str, Any]: 策略信息字典
        """
        return {
            "strategy_name": self.__class__.__name__,
            "thread_safe": self.is_thread_safe(),
            "supports_formatting": self.supports_formatting()
        }


class LogObserver(ABC):
    """日志观察者接口
    
    定义了日志观察者的抽象接口，实现了观察者模式。
    观察者可以监听日志事件，并在日志记录产生时执行相应操作
    """
    
    @abstractmethod
    def on_log_record(self, record: LogEntry) -> None:
        """处理日志记录事件
        
        Args:
            record: 日志记录
        """
        pass
    
    @abstractmethod
    def get_observer_name(self) -> str:
        """获取观察者名称
        
        Returns:
            str: 观察者名称
        """
        pass
    
    def get_observer_info(self) -> Dict[str, Any]:
        """获取观察者信息
        
        Returns:
            Dict[str, Any]: 观察者信息字典
        """
        return {
            "observer_name": self.get_observer_name(),
            "observer_type": self.__class__.__name__
        }
    
    def on_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """处理错误事件
        
        Args:
            error: 异常对象
            context: 错误上下文
        """
        # 默认实现：静默处理错误
        pass


class Logger(ABC):
    """日志器接口
    
    定义了日志器的抽象接口，是整个日志系统的核心接口。
    不同的日志器实现（同步、异步、可观察等）都应实现此接口
    """
    
    @abstractmethod
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 其他参数，如exception_info, context等
        """
        pass
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """记录调试级别日志
        
        Args:
            message: 日志消息
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """记录信息级别日志
        
        Args:
            message: 日志消息
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """记录警告级别日志
        
        Args:
            message: 日志消息
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """记录错误级别日志
        
        Args:
            message: 日志消息
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误级别日志
        
        Args:
            message: 日志消息
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    def exception(self, message: str, **kwargs) -> None:
        """记录异常日志
        
        自动捕获当前异常并记录
        
        Args:
            message: 日志消息
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    def add_observer(self, observer: LogObserver) -> None:
        """添加日志观察者
        
        Args:
            observer: 日志观察者
        """
        pass
    
    @abstractmethod
    def remove_observer(self, observer: LogObserver) -> None:
        """移除日志观察者
        
        Args:
            observer: 日志观察者
        """
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """刷新日志缓冲区
        
        确保所有缓冲的日志记录都已输出
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭日志器
        
        释放资源，关闭文件、网络连接等
        """
        pass
    
    @abstractmethod
    def update_config(self, config: 'LogConfig') -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
        """
        pass
    
    @abstractmethod
    def get_logger_info(self) -> Dict[str, Any]:
        """获取日志器信息
        
        Returns:
            Dict[str, Any]: 日志器信息字典
        """
        pass
    
    def is_enabled_for(self, level: LogLevel) -> bool:
        """检查是否启用指定级别
        
        Args:
            level: 日志级别
            
        Returns:
            bool: 是否启用
        """
        # 默认实现，子类可以覆盖
        return True


class LogConfig(ABC):
    """日志配置接口
    
    定义了日志配置的抽象接口，不同的配置实现
    （如内存配置、文件配置、环境变量配置等）都应实现此接口
    """
    
    @abstractmethod
    def get_min_level(self) -> LogLevel:
        """获取最低日志级别
        
        Returns:
            LogLevel: 最低日志级别
        """
        pass
    
    @abstractmethod
    def get_output_strategies(self) -> List[LogOutputStrategy]:
        """获取输出策略列表
        
        Returns:
            List[LogOutputStrategy]: 输出策略列表
        """
        pass
    
    @abstractmethod
    def get_format_string(self) -> str:
        """获取格式字符串
        
        Returns:
            str: 格式字符串
        """
        pass
    
    @abstractmethod
    def is_async_enabled(self) -> bool:
        """检查是否启用异步日志
        
        Returns:
            bool: 是否启用异步日志
        """
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """获取异步队列大小
        
        Returns:
            int: 队列大小
        """
        pass
    
    @abstractmethod
    def get_flush_interval(self) -> float:
        """获取刷新间隔（秒）
        
        Returns:
            float: 刷新间隔
        """
        pass
    
    @abstractmethod
    def get_custom_property(self, key: str, default_value: Any = None) -> Any:
        """获取自定义属性
        
        Args:
            key: 属性键
            default_value: 默认值
            
        Returns:
            Any: 属性值
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的配置
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """验证配置有效性
        
        Returns:
            bool: 配置是否有效
        """
        pass
    
    @abstractmethod
    def clone(self) -> 'LogConfig':
        """克隆配置
        
        Returns:
            LogConfig: 配置的克隆
        """
        pass


class LogFormatter(ABC):
    """日志格式化器接口
    
    定义了日志格式化器的抽象接口，不同的格式化器实现
    （如文本格式化器、JSON格式化器、XML格式化器等）都应实现此接口
    """
    
    @abstractmethod
    def format(self, record: LogEntry) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的字符串
        """
        pass
    
    @abstractmethod
    def set_format_string(self, format_string: str) -> None:
        """设置格式字符串
        
        Args:
            format_string: 格式字符串
        """
        pass
    
    @abstractmethod
    def get_format_string(self) -> str:
        """获取格式字符串
        
        Returns:
            str: 格式字符串
        """
        pass
    
    @abstractmethod
    def supports_field(self, field_name: str) -> bool:
        """检查是否支持指定字段
        
        Args:
            field_name: 字段名称
            
        Returns:
            bool: 是否支持
        """
        pass
    
    @abstractmethod
    def get_supported_fields(self) -> List[str]:
        """获取支持的字段列表
        
        Returns:
            List[str]: 支持的字段列表
        """
        pass
    
    @abstractmethod
    def clone(self) -> 'LogFormatter':
        """克隆格式化器
        
        Returns:
            LogFormatter: 格式化器的克隆
        """
        pass


class LogFilter(ABC):
    """日志过滤器接口
    
    定义了日志过滤器的抽象接口，不同的过滤器实现
    （如级别过滤器、名称过滤器、消息过滤器等）都应实现此接口
    """
    
    @abstractmethod
    def filter(self, record: LogEntry) -> bool:
        """过滤日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            bool: 是否通过过滤
        """
        pass
    
    @abstractmethod
    def get_filter_info(self) -> Dict[str, Any]:
        """获取过滤器信息
        
        Returns:
            Dict[str, Any]: 过滤器信息字典
        """
        pass
    
    @abstractmethod
    def clone(self) -> 'LogFilter':
        """克隆过滤器
        
        Returns:
            LogFilter: 过滤器的克隆
        """
        pass


class CompositeLogFilter(LogFilter):
    """复合日志过滤器
    
    可以组合多个过滤器，实现复杂的过滤逻辑
    """
    
    def __init__(self, filters: Optional[List[LogFilter]] = None):
        """初始化复合过滤器
        
        Args:
            filters: 过滤器列表
        """
        self._filters = filters or []
    
    def add_filter(self, filter_instance: LogFilter) -> None:
        """添加过滤器
        
        Args:
            filter_instance: 过滤器实例
        """
        self._filters.append(filter_instance)
    
    def remove_filter(self, filter_instance: LogFilter) -> None:
        """移除过滤器
        
        Args:
            filter_instance: 过滤器实例
        """
        if filter_instance in self._filters:
            self._filters.remove(filter_instance)
    
    def clear_filters(self) -> None:
        """清空所有过滤器"""
        self._filters.clear()
    
    def filter(self, record: LogEntry) -> bool:
        """过滤日志记录
        
        所有子过滤器都必须返回True，记录才能通过过滤
        
        Args:
            record: 日志记录
            
        Returns:
            bool: 是否通过过滤
        """
        return all(f.filter(record) for f in self._filters)
    
    def get_filter_info(self) -> Dict[str, Any]:
        """获取过滤器信息
        
        Returns:
            Dict[str, Any]: 过滤器信息字典
        """
        return {
            "filter_type": "CompositeLogFilter",
            "sub_filters": [f.get_filter_info() for f in self._filters]
        }
    
    def clone(self) -> 'CompositeLogFilter':
        """克隆过滤器
        
        Returns:
            CompositeLogFilter: 过滤器的克隆
        """
        return CompositeLogFilter([f.clone() for f in self._filters])