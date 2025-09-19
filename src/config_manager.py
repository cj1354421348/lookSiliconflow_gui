import json
import os
from typing import Dict, Any, Optional
from src.database_manager import DatabaseManager

class ConfigManager:
    """配置管理器 - 从旧配置文件迁移到新数据库系统"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.default_config = self._get_default_config()
        self._ensure_config_exists()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api": {
                "endpoint": "https://api.siliconflow.cn/v1/user/info",
                "timeout": 10
            },
            "balance_threshold": {
                "valid": 0.1,
                "low_balance": 0.0
            },
            "threading": {
                "enabled": True,
                "max_workers": 10,
                "batch_size": 20
            },
            "ui": {
                "theme": "light",
                "window_size": {"width": 1000, "height": 700},
                "auto_refresh": True,
                "refresh_interval": 5,
                "debug_mode": False
            },
            "export": {
                "default_directory": "exports",
                "filename_template": "{status}_tokens_{date}.txt"
            },
            "proxy": {
                "port": 8080,
                "timeout": 30,
                "max_failures": 3,
                "enabled": False,
                "pool_type": "non_blacklist",
                "key_debounce_interval": 600,
                "max_small_retries": 3,
                "max_big_retries": 5,
                "request_timeout_minutes": 15
            }
        }
    
    def _ensure_config_exists(self):
        """确保配置存在，如果不存在则创建默认配置"""
        for key, value in self.default_config.items():
            if self.db_manager.get_config(key) is None:
                self.db_manager.set_config(key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 支持嵌套键，如 "api.endpoint"
        if '.' in key:
            keys = key.split('.')
            value = self.db_manager.get_config(keys[0])
            if value and isinstance(value, dict):
                for k in keys[1:]:
                    if k in value:
                        value = value[k]
                    else:
                        return default
                return value
            return default
        else:
            return self.db_manager.get_config(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        self.db_manager.set_config(key, value)
    
    def get_api_endpoint(self) -> str:
        """获取API端点"""
        return self.get("api.endpoint", self.default_config["api"]["endpoint"])
    
    def get_api_timeout(self) -> int:
        """获取API超时时间"""
        return self.get("api.timeout", self.default_config["api"]["timeout"])
    
    def get_valid_threshold(self) -> float:
        """获取有效令牌余额阈值"""
        return self.get("balance_threshold.valid", self.default_config["balance_threshold"]["valid"])
    
    def get_low_balance_threshold(self) -> float:
        """获取低余额令牌阈值"""
        return self.get("balance_threshold.low_balance", self.default_config["balance_threshold"]["low_balance"])
    
    def is_threading_enabled(self) -> bool:
        """是否启用多线程"""
        return self.get("threading.enabled", self.default_config["threading"]["enabled"])
    
    def get_max_workers(self) -> int:
        """获取最大线程数"""
        return self.get("threading.max_workers", self.default_config["threading"]["max_workers"])
    
    def get_batch_size(self) -> int:
        """获取批处理大小"""
        return self.get("threading.batch_size", self.default_config["threading"]["batch_size"])
    
    def get_ui_theme(self) -> str:
        """获取UI主题"""
        return self.get("ui.theme", self.default_config["ui"]["theme"])
    
    def get_window_size(self) -> Dict[str, int]:
        """获取窗口大小"""
        return self.get("ui.window_size", self.default_config["ui"]["window_size"])
    
    def is_auto_refresh_enabled(self) -> bool:
        """是否启用自动刷新"""
        return self.get("ui.auto_refresh", self.default_config["ui"]["auto_refresh"])
    
    def get_refresh_interval(self) -> int:
        """获取刷新间隔（秒）"""
        return self.get("ui.refresh_interval", self.default_config["ui"]["refresh_interval"])
    
    def is_debug_mode_enabled(self) -> bool:
        """是否启用调试模式"""
        return self.get("ui.debug_mode", self.default_config["ui"]["debug_mode"])
    
    def get_export_directory(self) -> str:
        """获取导出目录"""
        return self.get("export.default_directory", self.default_config["export"]["default_directory"])
    
    def get_filename_template(self) -> str:
        """获取文件名模板"""
        return self.get("export.filename_template", self.default_config["export"]["filename_template"])
    
    def migrate_from_file(self, config_file_path: str):
        """从旧的配置文件迁移配置"""
        if not os.path.exists(config_file_path):
            print(f"配置文件 {config_file_path} 不存在，跳过迁移")
            return
        
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                old_config = json.load(f)
            
            # 迁移API配置
            if "api" in old_config:
                self.set("api.endpoint", old_config["api"].get("endpoint", self.default_config["api"]["endpoint"]))
                self.set("api.timeout", old_config["api"].get("timeout", self.default_config["api"]["timeout"]))
            
            # 迁移余额阈值
            if "balance_threshold" in old_config:
                self.set("balance_threshold.valid", old_config["balance_threshold"].get("valid", self.default_config["balance_threshold"]["valid"]))
                self.set("balance_threshold.low_balance", old_config["balance_threshold"].get("low_balance", self.default_config["balance_threshold"]["low_balance"]))
            
            # 迁移线程配置
            if "threading" in old_config:
                self.set("threading.enabled", old_config["threading"].get("enabled", self.default_config["threading"]["enabled"]))
                self.set("threading.max_workers", old_config["threading"].get("max_workers", self.default_config["threading"]["max_workers"]))
                self.set("threading.batch_size", old_config["threading"].get("batch_size", self.default_config["threading"]["batch_size"]))
            
            print(f"配置迁移完成: {config_file_path}")
            
        except Exception as e:
            print(f"配置迁移失败: {e}")

    # 代理配置方法
    def get_proxy_port(self) -> int:
        """获取代理端口"""
        return self.get("proxy.port", self.default_config["proxy"]["port"])

    def get_proxy_timeout(self) -> int:
        """获取代理超时时间"""
        return self.get("proxy.timeout", self.default_config["proxy"]["timeout"])

    def get_proxy_max_failures(self) -> int:
        """获取密钥最大失败次数"""
        return self.get("proxy.max_failures", self.default_config["proxy"]["max_failures"])

    def is_proxy_enabled(self) -> bool:
        """是否启用代理"""
        return self.get("proxy.enabled", self.default_config["proxy"]["enabled"])

    def set_proxy_enabled(self, enabled: bool):
        """设置代理启用状态"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["enabled"] = enabled
        self.set("proxy", proxy_config)

    def set_proxy_port(self, port: int):
        """设置代理端口"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["port"] = port
        self.set("proxy", proxy_config)

    def set_proxy_timeout(self, timeout: int):
        """设置代理超时时间"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["timeout"] = timeout
        self.set("proxy", proxy_config)

    def set_proxy_max_failures(self, max_failures: int):
        """设置密钥最大失败次数"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["max_failures"] = max_failures
        self.set("proxy", proxy_config)

    def get_proxy_pool_type(self) -> str:
        """获取代理密钥池类型"""
        return self.get("proxy.pool_type", self.default_config["proxy"]["pool_type"])

    def set_proxy_pool_type(self, pool_type: str):
        """设置代理密钥池类型"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["pool_type"] = pool_type
        self.set("proxy", proxy_config)

    def get_proxy_key_debounce_interval(self) -> int:
        """获取代理密钥防抖间隔（秒）"""
        return self.get("proxy.key_debounce_interval", self.default_config["proxy"]["key_debounce_interval"])

    def set_proxy_key_debounce_interval(self, interval: int):
        """设置代理密钥防抖间隔（秒）"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["key_debounce_interval"] = interval
        self.set("proxy", proxy_config)

    def get_proxy_max_small_retries(self) -> int:
        """获取代理小重试最大次数"""
        return self.get("proxy.max_small_retries", self.default_config["proxy"]["max_small_retries"])

    def set_proxy_max_small_retries(self, max_retries: int):
        """设置代理小重试最大次数"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["max_small_retries"] = max_retries
        self.set("proxy", proxy_config)

    def get_proxy_max_big_retries(self) -> int:
        """获取代理大重试最大次数"""
        return self.get("proxy.max_big_retries", self.default_config["proxy"]["max_big_retries"])

    def set_proxy_max_big_retries(self, max_retries: int):
        """设置代理大重试最大次数"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["max_big_retries"] = max_retries
        self.set("proxy", proxy_config)

    def get_proxy_request_timeout_minutes(self) -> int:
        """获取代理请求超时时间（分钟）"""
        return self.get("proxy.request_timeout_minutes", self.default_config["proxy"]["request_timeout_minutes"])

    def set_proxy_request_timeout_minutes(self, timeout_minutes: int):
        """设置代理请求超时时间（分钟）"""
        proxy_config = self.get("proxy", self.default_config["proxy"])
        proxy_config["request_timeout_minutes"] = timeout_minutes
        self.set("proxy", proxy_config)

    def get_proxy_max_total_retries(self) -> int:
        """计算代理总重试次数（小重试 * 大重试）"""
        small_retries = self.get_proxy_max_small_retries()
        big_retries = self.get_proxy_max_big_retries()
        return small_retries + (big_retries * (small_retries + 1))
        # 计算逻辑：(小重试次数 + 1) * 大重试次数
        # +1是因为第一次正常请求不算重试，后续每次大重试最多可以有小重试次数+1次尝试
    
    def export_to_file(self, config_file_path: str):
        """导出配置到文件"""
        config_data = {
            "api": {
                "endpoint": self.get_api_endpoint(),
                "timeout": self.get_api_timeout()
            },
            "balance_threshold": {
                "valid": self.get_valid_threshold(),
                "low_balance": self.get_low_balance_threshold()
            },
            "threading": {
                "enabled": self.is_threading_enabled(),
                "max_workers": self.get_max_workers(),
                "batch_size": self.get_batch_size()
            },
            "ui": {
                "theme": self.get_ui_theme(),
                "window_size": self.get_window_size(),
                "auto_refresh": self.is_auto_refresh_enabled(),
                "refresh_interval": self.get_refresh_interval(),
                "debug_mode": self.is_debug_mode_enabled()
            },
            "export": {
                "default_directory": self.get_export_directory(),
                "filename_template": self.get_filename_template()
            },
            "proxy": {
                "port": self.get_proxy_port(),
                "timeout": self.get_proxy_timeout(),
                "max_failures": self.get_proxy_max_failures(),
                "enabled": self.is_proxy_enabled(),
                "pool_type": self.get_proxy_pool_type(),
                "key_debounce_interval": self.get_proxy_key_debounce_interval(),
                "max_small_retries": self.get_proxy_max_small_retries(),
                "max_big_retries": self.get_proxy_max_big_retries(),
                "request_timeout_minutes": self.get_proxy_request_timeout_minutes()
            }
        }
        
        try:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            print(f"配置导出成功: {config_file_path}")
        except Exception as e:
            print(f"配置导出失败: {e}")