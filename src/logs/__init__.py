"""
日志系统模块

提供了一个灵活、可扩展、高性能的日志系统，支持多种设计模式和配置选项。
包括核心数据类型、接口、抽象类、具体实现和兼容性适配器等。
"""

# 核心数据类型
from .core.types import LogLevel, ExceptionInfo, LogEntry

# 核心接口
from .core.interfaces import (
    LogOutputStrategy,
    LogObserver,
    Logger,
    LogConfig,
    LogFormatter,
    LogFilter,
    CompositeLogFilter
)

# 抽象基类
from .core.abstracts import (
    AbstractLogger,
    AbstractLogOutputStrategy,
    AbstractLogFormatter
)

# 输出策略
from .strategies.output_strategies import (
    ConsoleOutputStrategy,
    FileOutputStrategy,
    GuiOutputStrategy,
    RemoteOutputStrategy
)

# 日志格式化器
from .formatters.log_formatters import (
    StandardLogFormatter,
    JsonLogFormatter,
    ColoredLogFormatter,
    SimpleLogFormatter,
    DetailedLogFormatter,
    StructuredLogFormatter
)

# 日志观察者
from .observers.log_observers import (
    GuiLogObserver,
    FileLogObserver,
    NetworkLogObserver,
    FilteredLogObserver,
    CompositeLogObserver,
    ConsoleLogObserver,
    MemoryLogObserver,
    JsonFileLogObserver
)

# 日志配置
from .config.log_config import (
    LogConfigData,
    LogConfigManager,
    LogConfigTemplate
)

# 日志器
from .loggers.observable_logger import ObservableLogger
from .loggers.async_logger import AsyncLogger

# 日志器工厂
from .factories.logger_factory import (
    LoggerFactory,
    DefaultLoggerFactory,
    ConfigAwareLoggerFactory,
    CachedLoggerFactory,
    get_logger_factory,
    set_logger_factory,
    create_logger
)

# 配置构建器
from .builders.config_builder import (
    LogConfigBuilder,
    LogConfigTemplate,
    LogConfigPreset,
    LogConfigValidator,
    create_config_builder,
    create_config_from_preset
)

# 日志管理器（单例）
from .singleton.log_manager import (
    LogManager,
    get_log_manager,
    get_logger,
    get_root_logger,
    initialize_logging
)

# 错误处理
from .error_handling.error_handler import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    PrintErrorHandler,
    FallbackErrorHandler,
    CompositeErrorHandler,
    ConditionalErrorHandler,
    ErrorHandlingManager,
    FallbackStrategy,
    get_error_manager,
    set_error_manager,
    handle_error,
    setup_default_error_handling
)

# 性能优化
from .performance.performance_optimization import (
    ObjectPool,
    LogEntryPool,
    BatchProcessor,
    AsyncBatchProcessor,
    PerformanceMonitor,
    get_performance_monitor,
    set_performance_monitor,
    create_log_entry_pool,
    create_batch_processor,
    create_async_batch_processor
)

# 兼容性适配器
from .compatibility.compatibility_adapter import (
    LoggingHandlerAdapter,
    LoggerAdapter,
    LoggingManagerAdapter,
    CompatibilityLayer,
    get_compatibility_layer,
    install_compatibility,
    uninstall_compatibility,
    getLogger as compatGetLogger,
    basicConfig,
    shutdown,
    add_logging_handler_to_standard_logger,
    setup_standard_logging_adapter
)

# 版本信息
__version__ = "1.0.0"
__author__ = "Log System Team"
__email__ = "logsystem@example.com"

# 默认配置
def create_default_config():
    """创建默认配置
    
    Returns:
        LogConfigData: 默认配置
    """
    return LogConfigTemplate.development().build()

# 初始化函数
def init_logging(config=None, install_compat=True):
    """初始化日志系统
    
    Args:
        config: 日志配置，如果为None则使用默认配置
        install_compat: 是否安装兼容性层
        
    Returns:
        LogManager: 日志管理器实例
    """
    if config is None:
        config = create_default_config()
    
    manager = initialize_logging(config)
    
    if install_compat:
        install_compatibility()
    
    return manager

# 获取日志器的便捷函数
def get_logger(name):
    """获取日志器的便捷函数
    
    Args:
        name: 日志器名称
        
    Returns:
        Logger: 日志器实例
    """
    return get_log_manager().get_logger(name)

# 获取根日志器的便捷函数
def get_root_logger():
    """获取根日志器的便捷函数
    
    Returns:
        Logger: 根日志器实例
    """
    return get_log_manager().get_root_logger()

# 导出所有公共类和函数
__all__ = [
    # 核心数据类型
    'LogLevel',
    'ExceptionInfo',
    'LogEntry',
    
    # 核心接口
    'LogOutputStrategy',
    'LogObserver',
    'Logger',
    'LogConfig',
    'LogFormatter',
    'LogFilter',
    'CompositeLogFilter',
    
    # 抽象基类
    'AbstractLogger',
    'AbstractLogOutputStrategy',
    'AbstractLogFormatter',
    
    # 输出策略
    'ConsoleOutputStrategy',
    'FileOutputStrategy',
    'GuiOutputStrategy',
    'RemoteOutputStrategy',
    
    # 日志格式化器
    'StandardLogFormatter',
    'JsonLogFormatter',
    'ColoredLogFormatter',
    'SimpleLogFormatter',
    'DetailedLogFormatter',
    'StructuredLogFormatter',
    
    # 日志观察者
    'GuiLogObserver',
    'FileLogObserver',
    'NetworkLogObserver',
    'FilteredLogObserver',
    'CompositeLogObserver',
    'ConsoleLogObserver',
    'MemoryLogObserver',
    'JsonFileLogObserver',
    
    # 日志配置
    'LogConfigData',
    'LogConfigManager',
    'LogConfigTemplate',
    
    # 日志器
    'ObservableLogger',
    'AsyncLogger',
    
    # 日志器工厂
    'LoggerFactory',
    'DefaultLoggerFactory',
    'ConfigAwareLoggerFactory',
    'CachedLoggerFactory',
    'get_logger_factory',
    'set_logger_factory',
    'create_logger',
    
    # 配置构建器
    'LogConfigBuilder',
    'LogConfigTemplate',
    'LogConfigPreset',
    'LogConfigValidator',
    'create_config_builder',
    'create_config_from_preset',
    
    # 日志管理器（单例）
    'LogManager',
    'get_log_manager',
    'get_logger',
    'get_root_logger',
    'initialize_logging',
    
    # 错误处理
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorContext',
    'ErrorHandler',
    'PrintErrorHandler',
    'FallbackErrorHandler',
    'CompositeErrorHandler',
    'ConditionalErrorHandler',
    'ErrorHandlingManager',
    'FallbackStrategy',
    'get_error_manager',
    'set_error_manager',
    'handle_error',
    'setup_default_error_handling',
    
    # 性能优化
    'ObjectPool',
    'LogEntryPool',
    'BatchProcessor',
    'AsyncBatchProcessor',
    'PerformanceMonitor',
    'get_performance_monitor',
    'set_performance_monitor',
    'create_log_entry_pool',
    'create_batch_processor',
    'create_async_batch_processor',
    
    # 兼容性适配器
    'LoggingHandlerAdapter',
    'LoggerAdapter',
    'LoggingManagerAdapter',
    'CompatibilityLayer',
    'get_compatibility_layer',
    'install_compatibility',
    'uninstall_compatibility',
    'compatGetLogger',
    'basicConfig',
    'shutdown',
    'add_logging_handler_to_standard_logger',
    'setup_standard_logging_adapter',
    
    # 便捷函数
    'create_default_config',
    'init_logging',
    'get_logger',
    'get_root_logger',
    
    # 版本信息
    '__version__',
    '__author__',
    '__email__'
]