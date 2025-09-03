#!/usr/bin/env python3
"""
令牌管理系统主启动文件
GUI版本 - 基于SQLite数据库的令牌余额查询和分类管理工具
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from gui_main import main
    import tkinter as tk
    from tkinter import messagebox
except ImportError as e:
    print(f"导入错误: {e}")
    print("请检查是否缺少依赖包:")
    print("pip install requests")
    sys.exit(1)

def check_dependencies():
    """检查依赖包"""
    missing_dependencies = []
    
    try:
        import requests
    except ImportError:
        missing_dependencies.append("requests")
    
    # tkinter通常是Python标准库的一部分，但检查一下
    try:
        import tkinter
    except ImportError:
        missing_dependencies.append("tkinter")
    
    if missing_dependencies:
        print("缺少以下依赖包:")
        for dep in missing_dependencies:
            print(f"  - {dep}")
        
        if os.name == 'nt':  # Windows
            install_cmd = "pip install " + " ".join(missing_dependencies)
        else:  # Linux/Mac
            install_cmd = f"pip3 install {' '.join(missing_dependencies)}"
        
        print(f"\n请运行以下命令安装依赖:")
        print(install_cmd)
        return False
    
    return True

def main_entry():
    """主入口函数"""
    print("启动令牌管理系统...")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # 启动GUI应用
        main()
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_entry()