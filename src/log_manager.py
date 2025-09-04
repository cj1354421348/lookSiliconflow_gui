import logging
import os
from datetime import datetime
from typing import Optional
from pathlib import Path


class LogManager:
    """统一日志管理器 - 按级别分发日志到不同目标"""
    
    def __init__(self, debug_mode: bool = False, log_dir: str = "logs"):
        self.debug_mode = debug_mode
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志级别定义
        self.LEVEL_USER = "USER"
        self.LEVEL_PROCESS = "PROCESS" 
        self.LEVEL_DEBUG = "DEBUG"
        
        # 设置日志文件
        self.log_file = self.log_dir / f"token_manager_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 初始化日志系统
        self._setup_logger()
        
        # GUI回调函数
        self.gui_callback = None
    
    def _setup_logger(self):
        """设置Python logging系统"""
        self.logger = logging.getLogger("TokenManager")
        self.logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 文件处理器 - 记录所有日志
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器 - 仅记录用户级别日志
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # 只显示INFO及以上级别
        console_formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def set_gui_callback(self, callback):
        """设置GUI日志回调函数"""
        self.gui_callback = callback
    
    def log_user(self, message: str):
        """用户级别日志 - 显示在GUI和日志文件中"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # 输出到日志文件
        self.logger.info(f"USER: {message}")
        
        # 输出到GUI
        if self.gui_callback:
            self.gui_callback(formatted_message)
    
    def log_process(self, message: str):
        """处理过程日志 - 仅在调试模式时输出到日志文件"""
        if self.debug_mode:
            self.logger.info(f"PROCESS: {message}")
    
    def log_debug(self, message: str):
        """调试日志 - 仅在调试模式时输出到日志文件"""
        if self.debug_mode:
            self.logger.debug(f"DEBUG: {message}")
    
    def log_error(self, message: str):
        """错误日志 - 显示在GUI和日志文件中"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] 错误: {message}"
        
        # 输出到日志文件
        self.logger.error(f"USER_ERROR: {message}")
        
        # 输出到GUI
        if self.gui_callback:
            self.gui_callback(formatted_message)
    
    def set_debug_mode(self, enabled: bool):
        """设置调试模式"""
        self.debug_mode = enabled
        if enabled:
            self.log_user("调试模式已启用")
        else:
            self.log_user("调试模式已禁用")
    
    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)
    
    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            for log_file in self.log_dir.glob("token_manager_*.log"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    self.log_process(f"已删除旧日志文件: {log_file.name}")
        except Exception as e:
            self.log_error(f"清理旧日志文件失败: {e}")