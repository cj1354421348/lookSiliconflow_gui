"""
业务常量和魔法数字定义
集中管理所有硬编码值，便于维护和配置
"""

# API 相关常量
class APIConstants:
    """API 相关常量"""
    DEFAULT_ENDPOINT = "https://api.siliconflow.cn/v1/user/info"
    DEFAULT_TIMEOUT = 10  # 秒
    
    # 余额阈值
    VALID_BALANCE_THRESHOLD = 0.1
    LOW_BALANCE_THRESHOLD = 0.0

# 线程配置常量
class ThreadingConstants:
    """线程配置常量"""
    DEFAULT_MAX_WORKERS = 10
    DEFAULT_BATCH_SIZE = 20

# UI 配置常量
class UIConstants:
    """UI 配置常量"""
    DEFAULT_THEME = "light"
    DEFAULT_WINDOW_WIDTH = 1000
    DEFAULT_WINDOW_HEIGHT = 700
    DEFAULT_REFRESH_INTERVAL = 5  # 秒
    
    # 显示相关
    TOKEN_DISPLAY_LENGTH = 12  # 令牌显示长度（保护隐私）
    MAX_ERROR_MESSAGE_LENGTH = 500  # 错误消息最大显示长度
    MAX_LOG_DISPLAY_ITEMS = 5  # 日志显示最大项目数

# 导出配置常量
class ExportConstants:
    """导出配置常量"""
    DEFAULT_DIRECTORY = "exports"
    DEFAULT_FILENAME_TEMPLATE = "{status}_tokens_{date}.txt"

# 代理配置常量
class ProxyConstants:
    """代理配置常量"""
    DEFAULT_PORT = 8080
    DEFAULT_TIMEOUT = 30  # 秒
    DEFAULT_MAX_FAILURES = 3
    DEFAULT_POOL_TYPE = "non_blacklist"
    DEFAULT_KEY_DEBOUNCE_INTERVAL = 600  # 秒
    DEFAULT_MAX_SMALL_RETRIES = 3
    DEFAULT_MAX_BIG_RETRIES = 5
    DEFAULT_REQUEST_TIMEOUT_MINUTES = 15  # 分钟

# 数据库配置常量
class DatabaseConstants:
    """数据库配置常量"""
    DEFAULT_DB_PATH = "database/token_manager.db"
    DEFAULT_LOG_RETENTION_DAYS = 30  # 日志保留天数
    
    # 表名
    CONFIG_TABLE = "config"
    TOKENS_TABLE = "tokens"
    BATCHES_TABLE = "batches"
    EXPORTS_TABLE = "exports"
    PROXY_REQUEST_LOGS_TABLE = "proxy_request_logs"

# 令牌状态常量
class TokenStatus:
    """令牌状态常量"""
    PENDING = "pending"
    VALID = "valid"
    LOW_BALANCE = "low_balance"
    CHARGE_BALANCE = "charge_balance"
    INVALID = "invalid"
    
    # 所有有效状态列表
    VALID_STATUSES = [PENDING, VALID, LOW_BALANCE, CHARGE_BALANCE, INVALID]

# 代理请求状态常量
class ProxyRequestStatus:
    """代理请求状态常量"""
    PENDING = "请求中"
    SUCCESS = "成功"
    FAILED = "失败"

# 响应类型常量
class ResponseType:
    """响应类型常量"""
    STREAMING = "流式响应"
    NORMAL = "普通响应"

# 重试类型常量
class RetryType:
    """重试类型常量"""
    INITIAL = "initial"
    SMALL_RETRY = "small_retry"
    BIG_RETRY = "big_retry"

# HTTP 状态码常量
class HTTPStatus:
    """HTTP 状态码常量"""
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

# 时间相关常量
class TimeConstants:
    """时间相关常量"""
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    
    # UI 更新延迟
    STATUS_RESET_DELAY = 3000  # 毫秒
    ICON_SET_DELAY = 200  # 毫秒

# 文件相关常量
class FileConstants:
    """文件相关常量"""
    ICON_PATHS = [
        "icon.ico",
        "assets/icon.ico", 
        "images/icon.ico"
    ]
    
    # 文件类型
    TEXT_FILES = [("文本文件", "*.txt")]
    ALL_FILES = [("所有文件", "*.*")]

# 窗口相关常量
class WindowConstants:
    """窗口相关常量"""
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    
    # 对话框尺寸
    CLEANUP_DIALOG_WIDTH = 400
    CLEANUP_DIALOG_HEIGHT = 300
    CLEANUP_DIALOG_MIN_WIDTH = 350
    CLEANUP_DIALOG_MIN_HEIGHT = 250

# 日志相关常量
class LogConstants:
    """日志相关常量"""
    DEFAULT_LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    GUI_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 密钥池类型常量
class KeyPoolTypes:
    """密钥池类型常量"""
    NON_BLACKLIST = "non_blacklist"
    AVAILABLE_BALANCE = "available_balance"
    GIFT_BALANCE = "gift_balance"
    UNAVAILABLE_BALANCE = "unavailable_balance"
    
    # 所有池子类型
    ALL_TYPES = [NON_BLACKLIST, AVAILABLE_BALANCE, GIFT_BALANCE, UNAVAILABLE_BALANCE]

# 排序相关常量
class SortConstants:
    """排序相关常量"""
    DEFAULT_SORT_COLUMN = "最后检查"
    DEFAULT_SORT_DIRECTION = True  # True 为降序
    
    # 列映射
    COLUMN_MAPPING = {
        "令牌": "token_value",
        "余额": "total_balance", 
        "充值余额": "charge_balance",
        "最后检查": "last_checked",
        "创建时间": "created_at"
    }

# 网络相关常量
class NetworkConstants:
    """网络相关常量"""
    CHUNK_SIZE = 1024  # 流式响应块大小
    MAX_RETRY_ATTEMPTS = 10  # 最大重试尝试次数
    FAILURE_RATE_THRESHOLD = 0.5  # 失败率警告阈值

# 错误消息常量
class ErrorMessages:
    """错误消息常量"""
    NO_AVAILABLE_KEYS = "No available API keys"
    ALL_RETRIES_FAILED = "所有重试都失败了"
    CONFIG_FILE_NOT_FOUND = "配置文件不存在，跳过迁移"
    CONFIG_MIGRATION_FAILED = "配置迁移失败"
    CONFIG_EXPORT_FAILED = "配置导出失败"
    PROXY_SERVER_UNAVAILABLE = "代理服务器不可用，请安装Flask依赖"
    INVALID_POOL_TYPE = "不支持的池子类型"
    NO_TOKENS_SELECTED = "没有选中的令牌"
    NO_VALID_TOKENS = "没有有效的令牌可复制"