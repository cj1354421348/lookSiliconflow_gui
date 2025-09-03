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