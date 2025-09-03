import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import Dict, Any
from src.config_manager import ConfigManager

class SettingsDialog:
    """设置对话框"""
    
    def __init__(self, parent, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.result = None