"""
代理设置对话框
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional


class ProxySettingsDialog:
    """代理设置对话框"""

    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None

        # 获取实际代理运行状态，优先使用数据库中的持久化配置
        proxy_running_from_config = self.config_manager.is_proxy_enabled()

        # 检查实际运行状态作为参考
        proxy_running_actual = False
        if hasattr(parent, 'proxy_server') and parent.proxy_server and hasattr(parent.proxy_server, 'is_running'):
            proxy_running_actual = parent.proxy_server.is_running

        # 加载当前配置（优先使用持久化配置，但显示实际运行状态作为参考）
        self.current_config = {
            'enabled': proxy_running_from_config,  # 使用持久化配置而非实际运行状态
            'port': self.config_manager.get_proxy_port(),
            'timeout': self.config_manager.get_proxy_timeout(),
            'max_failures': self.config_manager.get_proxy_max_failures(),
            'pool_type': self.config_manager.get_proxy_pool_type(),
            'key_debounce_interval': self.config_manager.get_proxy_key_debounce_interval(),
            'max_small_retries': self.config_manager.get_proxy_max_small_retries(),
            'max_big_retries': self.config_manager.get_proxy_max_big_retries(),
            'request_timeout_minutes': self.config_manager.get_proxy_request_timeout_minutes()
        }

        # 池子类型选项
        self.pool_types = [
            ('非黑名单密钥池', 'non_blacklist', '包含有效和充值余额的密钥'),
            ('可用余额密钥池', 'available_balance', '包含有可用余额的密钥'),
            ('赠金密钥池', 'gift_balance', '包含有赠金的密钥'),
            ('不可用余额密钥池', 'unavailable_balance', '包含无余额或余额不足的密钥（调试用）')
        ]

        self.create_dialog()

    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent.root)
        self.dialog.title("代理设置")
        self.dialog.geometry("520x520")
        self.dialog.resizable(False, False)

        # 设置模态
        self.dialog.transient(self.parent.root)
        self.dialog.grab_set()

        # 创建主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 基本设置
        self.create_basic_settings(main_frame)

        # 密钥池设置
        self.create_key_pool_settings(main_frame)

        # 重试策略设置
        self.create_retry_settings(main_frame)

        # 按钮
        self.create_buttons(main_frame)

        # 居中对话框
        self.center_dialog()

    def create_basic_settings(self, parent):
        """创建基本设置区域"""
        basic_frame = ttk.LabelFrame(parent, text="基本设置", padding="15")
        basic_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 启用代理
        self.enabled_var = tk.BooleanVar(value=self.current_config['enabled'])
        ttk.Checkbutton(
            basic_frame,
            text="启用代理服务器",
            variable=self.enabled_var
        ).grid(row=0, column=0, sticky=tk.W, columnspan=2)

        # 端口
        ttk.Label(basic_frame, text="端口:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.port_var = tk.IntVar(value=self.current_config['port'])
        port_spinbox = ttk.Spinbox(
            basic_frame,
            from_=1024,
            to=65535,
            textvariable=self.port_var,
            width=10
        )
        port_spinbox.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(10, 0))

        # 超时时间和最大失败次数（隐藏变量，不显示UI）
        self.timeout_var = tk.IntVar(value=self.current_config['timeout'])
        self.max_failures_var = tk.IntVar(value=self.current_config['max_failures'])





    def create_buttons(self, parent):
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(15, 0))

        # 确定按钮
        ttk.Button(
            button_frame,
            text="确定",
            command=self.on_ok
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 取消按钮
        ttk.Button(
            button_frame,
            text="取消",
            command=self.on_cancel
        ).pack(side=tk.LEFT)

        # 重置按钮
        ttk.Button(
            button_frame,
            text="重置为默认",
            command=self.on_reset
        ).pack(side=tk.RIGHT)

    def on_ok(self):
        """确定按钮点击事件"""
        try:
            port = self.port_var.get()
            if port < 1024 or port > 65535:
                messagebox.showwarning("输入错误", "端口号必须在1024-65535之间")
                return

            timeout = self.timeout_var.get()
            if timeout < 5 or timeout > 300:
                messagebox.showwarning("输入错误", "超时时间必须在5-300秒之间")
                return

            max_failures = self.max_failures_var.get()
            if max_failures < 1 or max_failures > 10:
                messagebox.showwarning("输入错误", "最大失败次数必须在1-10之间")
                return

            debounce_interval = self.debounce_interval_var.get()
            if debounce_interval < 0 or debounce_interval > 3600:
                messagebox.showwarning("输入错误", "防抖时间必须在0-3600秒之间")
                return

            small_retries = self.small_retries_var.get()
            if small_retries < 0 or small_retries > 10:
                messagebox.showwarning("输入错误", "小重试次数必须在0-10之间")
                return

            big_retries = self.big_retries_var.get()
            if big_retries < 1 or big_retries > 20:
                messagebox.showwarning("输入错误", "大重试次数必须在1-20之间")
                return

            # 验证重试次数的合理性
            if small_retries == 0 and big_retries == 0:
                messagebox.showwarning("输入错误", "小重试和大重试不能同时为0")
                return

            request_timeout = self.request_timeout_var.get()
            if request_timeout < 1 or request_timeout > 60:
                messagebox.showwarning("输入错误", "请求超时时间必须在1-60分钟之间")
                return

            pool_type = self.pool_type_var.get()
            if pool_type not in [pt[1] for pt in self.pool_types]:
                messagebox.showwarning("输入错误", "请选择有效的密钥池类型")
                return

            # 构建结果配置
            self.result = {
                'enabled': self.enabled_var.get(),
                'port': port,
                'timeout': timeout,
                'max_failures': max_failures,
                'pool_type': pool_type,
                'key_debounce_interval': debounce_interval,
                'max_small_retries': small_retries,
                'max_big_retries': big_retries,
                'request_timeout_minutes': request_timeout
            }

            # 关闭对话框
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("错误", f"保存设置时发生错误: {e}")

    def on_cancel(self):
        """取消按钮点击事件"""
        self.result = None
        self.dialog.destroy()

    def on_reset(self):
        """重置为默认值"""
        if messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
            # 恢复默认值
            self.enabled_var.set(False)
            self.port_var.set(8080)
            self.timeout_var.set(30)
            self.max_failures_var.set(3)
            self.pool_type_var.set('non_blacklist')
            self.debounce_interval_var.set(600)
            self.small_retries_var.set(3)
            self.big_retries_var.set(5)
            self.request_timeout_var.set(15)
            self.update_pool_description()
            self.update_total_retries_display()

    def center_dialog(self):
        """居中对话框"""
        self.dialog.update_idletasks()

        # 获取父窗口和对话框的几何信息
        parent_x = self.parent.root.winfo_x()
        parent_y = self.parent.root.winfo_y()
        parent_width = self.parent.root.winfo_width()
        parent_height = self.parent.root.winfo_height()

        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()

        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # 确保对话框在屏幕范围内
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + dialog_width > screen_width:
            x = screen_width - dialog_width
        if y + dialog_height > screen_height:
            y = screen_height - dialog_height

        self.dialog.geometry(f"+{x}+{y}")

    def show(self) -> Optional[Dict[str, Any]]:
        """显示对话框并返回结果"""
        # 等待对话框关闭
        self.parent.root.wait_window(self.dialog)
        return self.result

    def create_key_pool_settings(self, parent):
        """创建密钥池设置区域"""
        pool_frame = ttk.LabelFrame(parent, text="密钥池设置", padding="15")
        pool_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 池子类型选择
        ttk.Label(pool_frame, text="选择密钥池类型:").grid(row=0, column=0, sticky=tk.W)

        # 创建池子类型下拉框
        self.pool_type_var = tk.StringVar(value=self.current_config['pool_type'])
        pool_type_combo = ttk.Combobox(
            pool_frame,
            textvariable=self.pool_type_var,
            values=[pool_type[1] for pool_type in self.pool_types],
            state="readonly",
            width=20
        )
        pool_type_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 添加选择事件，显示池子类型说明
        pool_type_combo.bind('<<ComboboxSelected>>', self.on_pool_type_selected)

        # 池子类型说明
        self.pool_description_var = tk.StringVar(value="")
        pool_description_label = ttk.Label(
            pool_frame,
            textvariable=self.pool_description_var,
            font=("TkDefaultFont", 9),
            foreground="#666666",
            wraplength=450
        )
        pool_description_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(15, 0))

        # 设置初始说明
        self.update_pool_description()

    def create_retry_settings(self, parent):
        """创建重试策略设置区域"""
        retry_frame = ttk.LabelFrame(parent, text="重试策略设置", padding="15")
        retry_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 防抖时间（节流时间）
        ttk.Label(retry_frame, text="防抖时间 (秒):").grid(row=0, column=0, sticky=tk.W)
        self.debounce_interval_var = tk.IntVar(value=self.current_config['key_debounce_interval'])
        debounce_spinbox = ttk.Spinbox(
            retry_frame,
            from_=0,
            to=3600,
            increment=60,
            textvariable=self.debounce_interval_var,
            width=10
        )
        debounce_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(retry_frame, text="0=立即切换", font=("TkDefaultFont", 8)).grid(row=0, column=2, sticky=tk.W, padx=(5, 0))

        # 小重试次数
        ttk.Label(retry_frame, text="小重试次数:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.small_retries_var = tk.IntVar(value=self.current_config['max_small_retries'])
        small_retries_spinbox = ttk.Spinbox(
            retry_frame,
            from_=0,
            to=10,
            textvariable=self.small_retries_var,
            width=10
        )
        small_retries_spinbox.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(10, 0))
        ttk.Label(retry_frame, text="当前密钥重试", font=("TkDefaultFont", 8)).grid(row=1, column=2, sticky=tk.W, padx=(5, 0))

        # 大重试次数
        ttk.Label(retry_frame, text="大重试次数:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.big_retries_var = tk.IntVar(value=self.current_config['max_big_retries'])
        big_retries_spinbox = ttk.Spinbox(
            retry_frame,
            from_=1,
            to=20,
            textvariable=self.big_retries_var,
            width=10
        )
        big_retries_spinbox.grid(row=2, column=1, sticky=tk.W, pady=(10, 0), padx=(10, 0))
        ttk.Label(retry_frame, text="可换密钥的次数", font=("TkDefaultFont", 8)).grid(row=2, column=2, sticky=tk.W, padx=(5, 0))

        # 请求超时时间（分钟）
        ttk.Label(retry_frame, text="请求超时时间 (分钟):").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.request_timeout_var = tk.IntVar(value=self.current_config['request_timeout_minutes'])
        timeout_spinbox = ttk.Spinbox(
            retry_frame,
            from_=1,
            to=60,
            textvariable=self.request_timeout_var,
            width=10
        )
        timeout_spinbox.grid(row=3, column=1, sticky=tk.W, pady=(10, 0), padx=(10, 0))
        ttk.Label(retry_frame, text="上游API响应超时", font=("TkDefaultFont", 8)).grid(row=3, column=2, sticky=tk.W, padx=(5, 0))

        # 总重试次数计算（显示用）
        self.total_retries_display_var = tk.StringVar(value="")
        total_display_label = ttk.Label(
            retry_frame,
            textvariable=self.total_retries_display_var,
            font=("TkDefaultFont", 9),
            foreground="#006600"
        )
        total_display_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(15, 0))

        # 绑定变化事件，实时更新总重试次数显示
        self.small_retries_var.trace('w', self.update_total_retries_display)
        self.big_retries_var.trace('w', self.update_total_retries_display)

        # 重试策略说明
        retry_info_text = "策略：小重试失败后→大重试（换密钥）→小重试清零→继续直到大重试次数用完"
        ttk.Label(retry_frame, text=retry_info_text, font=("TkDefaultFont", 8), foreground="#0066cc").grid(
            row=4, column=0, columnspan=3, sticky=tk.W, pady=(15, 0)
        )

    def on_pool_type_selected(self, event):
        """池子类型选择改变事件"""
        self.update_pool_description()

    def update_pool_description(self):
        """更新池子类型说明"""
        selected_type = self.pool_type_var.get()
        for name, pool_type, description in self.pool_types:
            if pool_type == selected_type:
                self.pool_description_var.set(f"{name}: {description}")
                break

    def update_total_retries_display(self, *args):
        """更新总重试次数显示"""
        try:
            small_retries = self.small_retries_var.get()
            big_retries = self.big_retries_var.get()
            # 计算总重试次数：(小重试次数 + 1) * 大重试次数
            total_retries = (small_retries + 1) * big_retries
            self.total_retries_display_var.set(f"总重试次数计算: ({small_retries} + 1) × {big_retries} = {total_retries} 次")
        except:
            self.total_retries_display_var.set("")