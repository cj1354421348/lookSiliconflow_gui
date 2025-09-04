import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import Dict, Any

class SettingsDialog:
    """设置对话框"""
    
    def __init__(self, parent, config_manager, log_manager=None):
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.result = None
        
        # 创建对话框窗口，先隐藏
        self.dialog = tk.Toplevel(parent)
        self.dialog.withdraw()  # 隐藏窗口，直到完全准备好
        self.dialog.title("设置")
        self.dialog.geometry("600x500")
        self.dialog.minsize(500, 400)
        
        # 设置对话框图标
        try:
            self._set_dialog_icon(parent)
        except:
            pass
        
        # 模态对话框
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建设置界面
        self.create_widgets()
        
        # 加载当前设置
        self.load_settings()
        
        # 居中显示
        self.center_dialog()
        
        # 现在显示窗口
        self.dialog.deiconify()
    
    def center_dialog(self):
        """将对话框居中显示"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """创建设置界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建笔记本控件
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建各个设置页面
        self.create_api_tab(notebook)
        self.create_threshold_tab(notebook)
        self.create_threading_tab(notebook)
        self.create_ui_tab(notebook)
        self.create_export_tab(notebook)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="重置", command=self.reset_settings).pack(side=tk.LEFT)
    
    def create_api_tab(self, notebook):
        """创建API设置页面"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="API设置")
        
        # API端点
        ttk.Label(frame, text="API端点:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.api_endpoint_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.api_endpoint_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 超时时间
        ttk.Label(frame, text="超时时间(秒):").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.api_timeout_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.api_timeout_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=(10, 5))
        
        frame.columnconfigure(1, weight=1)
    
    def create_threshold_tab(self, notebook):
        """创建余额阈值设置页面"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="余额阈值")
        
        # 有效令牌阈值
        ttk.Label(frame, text="有效令牌阈值:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.valid_threshold_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.valid_threshold_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        ttk.Label(frame, text="(≥此值为有效)").grid(row=0, column=2, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # 低余额阈值
        ttk.Label(frame, text="低余额阈值:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.low_balance_threshold_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.low_balance_threshold_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=(10, 5))
        ttk.Label(frame, text="(≥此值为低余额)").grid(row=1, column=2, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        
        frame.columnconfigure(1, weight=0)
    
    def create_threading_tab(self, notebook):
        """创建线程设置页面"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="线程设置")
        
        # 启用多线程
        self.threading_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启用多线程处理", variable=self.threading_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # 最大线程数
        ttk.Label(frame, text="最大线程数:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.max_workers_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.max_workers_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=(10, 5))
        
        # 批处理大小
        ttk.Label(frame, text="批处理大小:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        self.batch_size_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.batch_size_var, width=20).grid(row=2, column=1, sticky=tk.W, pady=(10, 5))
        
        # 说明
        ttk.Label(frame, text="说明: 批处理大小用于进度显示，建议20-50", 
                 foreground="gray").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        frame.columnconfigure(1, weight=0)
    
    def create_ui_tab(self, notebook):
        """创建UI设置页面"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="界面设置")
        
        # 主题选择
        ttk.Label(frame, text="主题:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(frame, textvariable=self.theme_var, values=["light", "dark"], width=20)
        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # 窗口大小
        ttk.Label(frame, text="窗口宽度:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.window_width_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.window_width_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=(10, 5))
        
        ttk.Label(frame, text="窗口高度:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        self.window_height_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.window_height_var, width=20).grid(row=2, column=1, sticky=tk.W, pady=(10, 5))
        
        # 自动刷新
        self.auto_refresh_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启用自动刷新", variable=self.auto_refresh_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # 刷新间隔
        ttk.Label(frame, text="刷新间隔(秒):").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        self.refresh_interval_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.refresh_interval_var, width=20).grid(row=4, column=1, sticky=tk.W, pady=(10, 5))
        
        # 调试模式
        self.debug_mode_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启用调试模式", variable=self.debug_mode_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        frame.columnconfigure(1, weight=0)
    
    def create_export_tab(self, notebook):
        """创建导出设置页面"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="导出设置")
        
        # 默认导出目录
        ttk.Label(frame, text="默认导出目录:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.export_dir_var = tk.StringVar()
        export_dir_frame = ttk.Frame(frame)
        export_dir_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Entry(export_dir_frame, textvariable=self.export_dir_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(export_dir_frame, text="浏览", command=self.browse_export_dir).pack(side=tk.LEFT, padx=(5, 0))
        
        # 文件名模板
        ttk.Label(frame, text="文件名模板:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.filename_template_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.filename_template_var, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 5))
        
        # 模板说明
        template_help = ttk.Label(frame, text="可用变量: {status}, {date}, {time}", foreground="gray")
        template_help.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        frame.columnconfigure(1, weight=1)
    
    def browse_export_dir(self):
        """浏览导出目录"""
        import tkinter.filedialog as filedialog
        directory = filedialog.askdirectory(title="选择导出目录")
        if directory:
            self.export_dir_var.set(directory)
    
    def load_settings(self):
        """加载当前设置"""
        # API设置
        self.api_endpoint_var.set(self.config_manager.get_api_endpoint())
        self.api_timeout_var.set(str(self.config_manager.get_api_timeout()))
        
        # 阈值设置
        self.valid_threshold_var.set(str(self.config_manager.get_valid_threshold()))
        self.low_balance_threshold_var.set(str(self.config_manager.get_low_balance_threshold()))
        
        # 线程设置
        self.threading_enabled_var.set(self.config_manager.is_threading_enabled())
        self.max_workers_var.set(str(self.config_manager.get_max_workers()))
        self.batch_size_var.set(str(self.config_manager.get_batch_size()))
        
        # UI设置
        self.theme_var.set(self.config_manager.get_ui_theme())
        window_size = self.config_manager.get_window_size()
        self.window_width_var.set(str(window_size['width']))
        self.window_height_var.set(str(window_size['height']))
        self.auto_refresh_var.set(self.config_manager.is_auto_refresh_enabled())
        self.refresh_interval_var.set(str(self.config_manager.get_refresh_interval()))
        self.debug_mode_var.set(self.config_manager.is_debug_mode_enabled())
        
        # 导出设置
        self.export_dir_var.set(self.config_manager.get_export_directory())
        self.filename_template_var.set(self.config_manager.get_filename_template())
    
    def save_settings(self):
        """保存设置"""
        try:
            # API设置
            self.config_manager.set("api.endpoint", self.api_endpoint_var.get())
            self.config_manager.set("api.timeout", int(self.api_timeout_var.get()))
            
            # 阈值设置
            self.config_manager.set("balance_threshold.valid", float(self.valid_threshold_var.get()))
            self.config_manager.set("balance_threshold.low_balance", float(self.low_balance_threshold_var.get()))
            
            # 线程设置
            self.config_manager.set("threading.enabled", self.threading_enabled_var.get())
            self.config_manager.set("threading.max_workers", int(self.max_workers_var.get()))
            self.config_manager.set("threading.batch_size", int(self.batch_size_var.get()))
            
            # UI设置
            self.config_manager.set("ui.theme", self.theme_var.get())
            self.config_manager.set("ui.window_size", {
                'width': int(self.window_width_var.get()),
                'height': int(self.window_height_var.get())
            })
            self.config_manager.set("ui.auto_refresh", self.auto_refresh_var.get())
            self.config_manager.set("ui.refresh_interval", int(self.refresh_interval_var.get()))
            self.config_manager.set("ui.debug_mode", self.debug_mode_var.get())
            
            # 导出设置
            self.config_manager.set("export.default_directory", self.export_dir_var.get())
            self.config_manager.set("export.filename_template", self.filename_template_var.get())
            
            messagebox.showinfo("成功", "设置已保存")
            self.result = True
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("错误", f"设置值格式错误: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")
    
    def reset_settings(self):
        """重置设置为默认值"""
        if messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
            # 重置为默认值
            default_config = {
                "api.endpoint": "https://api.siliconflow.cn/v1/user/info",
                "api.timeout": 10,
                "balance_threshold.valid": 0.1,
                "balance_threshold.low_balance": 0.0,
                "threading.enabled": True,
                "threading.max_workers": 10,
                "threading.batch_size": 20,
                "ui.theme": "light",
                "ui.window_size": {"width": 1000, "height": 700},
                "ui.auto_refresh": True,
                "ui.refresh_interval": 5,
                "export.default_directory": "exports",
                "export.filename_template": "{status}_tokens_{date}.txt"
            }
            
            for key, value in default_config.items():
                self.config_manager.set(key, value)
            
            self.load_settings()
            messagebox.showinfo("成功", "设置已重置为默认值")
    
    def cancel(self):
        """取消设置"""
        self.result = False
        self.dialog.destroy()
    
    def _set_dialog_icon(self, parent):
        """设置对话框图标，继承父窗口的图标"""
        try:
            # 如果父窗口有图标，继承它
            if hasattr(parent, 'iconbitmap'):
                # 尝试使用父窗口的图标
                parent_icon = parent.iconbitmap()
                if parent_icon:
                    self.dialog.iconbitmap(parent_icon)
                else:
                    # 尝试从项目目录加载图标
                    icon_paths = ["icon.ico", "assets/icon.ico", "images/icon.ico"]
                    for icon_path in icon_paths:
                        if os.path.exists(icon_path):
                            try:
                                self.dialog.iconbitmap(icon_path)
                                break
                            except:
                                continue
        except:
            pass
    
    def show(self):
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result