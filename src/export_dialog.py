import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime
from typing import List, Dict, Any
from src.database_manager import DatabaseManager
from src.config_manager import ConfigManager

class ExportDialog:
    """导出对话框"""
    
    def __init__(self, parent, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.result = None