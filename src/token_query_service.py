import requests
import json
import logging
import threading
import time
import os
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from src.database_manager import DatabaseManager
from src.config_manager import ConfigManager

class TokenQueryService:
    """令牌查询服务 - 处理所有令牌查询和分类逻辑"""
    
    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.logger = self._setup_logger()
        self.is_processing = False
        self.processing_lock = threading.Lock()