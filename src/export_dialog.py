import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime
from typing import List, Dict, Any

class ExportDialog:
    """导出对话框"""
    
    def __init__(self, parent, db_manager, config_manager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.result = None
        
        # 创建对话框窗口，先隐藏
        self.dialog = tk.Toplevel(parent)
        self.dialog.withdraw()  # 隐藏窗口，直到完全准备好
        self.dialog.title("导出令牌")
        self.dialog.geometry("500x450")  # 增加高度
        self.dialog.minsize(450, 400)    # 增加最小尺寸
        
        # 设置对话框图标
        try:
            self._set_dialog_icon(parent)
        except:
            pass
        
        # 模态对话框
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建导出界面
        self.create_widgets()
        
        # 加载统计数据
        self.load_statistics()
        
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
        """创建导出界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置主框架的网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # 预览框架具有权重
        
        # 状态选择框架
        status_frame = ttk.LabelFrame(main_frame, text="选择要导出的令牌状态", padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 状态复选框
        self.status_vars = {}
        
        # 第一行：待处理、有效、余额不足
        # 待处理
        var = tk.BooleanVar()
        self.status_vars["pending"] = var
        pending_cb = ttk.Checkbutton(status_frame, text="待处理", variable=var)
        pending_cb.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # 有效
        var = tk.BooleanVar()
        self.status_vars["valid"] = var
        valid_cb = ttk.Checkbutton(status_frame, text="有效", variable=var)
        valid_cb.grid(row=0, column=1, sticky=tk.W, padx=(40, 0), pady=2)
        
        # 余额不足 - 放置在有效的右边
        var = tk.BooleanVar()
        self.status_vars["low_balance"] = var
        low_balance_cb = ttk.Checkbutton(status_frame, text="余额不足", variable=var)
        low_balance_cb.grid(row=0, column=2, sticky=tk.W, padx=(40, 0), pady=2)
        
        # 第二行：充值余额、无效
        # 充值余额
        var = tk.BooleanVar()
        self.status_vars["charge_balance"] = var
        charge_balance_cb = ttk.Checkbutton(status_frame, text="充值余额", variable=var)
        charge_balance_cb.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # 无效
        var = tk.BooleanVar()
        self.status_vars["invalid"] = var
        invalid_cb = ttk.Checkbutton(status_frame, text="无效", variable=var)
        invalid_cb.grid(row=1, column=1, sticky=tk.W, padx=(40, 0), pady=2)
        
        # 全选/取消全选按钮
        button_frame = ttk.Frame(status_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(button_frame, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="取消全选", command=self.deselect_all).pack(side=tk.LEFT)
        
        # 导出选项框架
        options_frame = ttk.LabelFrame(main_frame, text="导出选项", padding="10")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)
        
        # 导出方式
        ttk.Label(options_frame, text="导出方式:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.export_method_var = tk.StringVar(value="file")
        ttk.Radiobutton(options_frame, text="导出到文件", variable=self.export_method_var, value="file", command=self.show_file_options).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        ttk.Radiobutton(options_frame, text="导出到剪贴板", variable=self.export_method_var, value="clipboard", command=self.show_clipboard_options).grid(row=0, column=2, sticky=tk.W, pady=(0, 5), padx=(20, 0))
        
        # 文件选项
        self.file_options_frame = ttk.Frame(options_frame)
        self.file_options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.file_options_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.file_options_frame, text="文件名:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.filename_var = tk.StringVar()
        self.filename_entry = ttk.Entry(self.file_options_frame, textvariable=self.filename_var, width=40)
        self.filename_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.browse_button = ttk.Button(self.file_options_frame, text="浏览", command=self.browse_file)
        self.browse_button.grid(row=0, column=2, padx=(5, 0), pady=(0, 5))
        
        # 剪贴板选项
        self.clipboard_options_frame = ttk.Frame(options_frame)
        self.clipboard_options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.clipboard_options_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.clipboard_options_frame, text="每行令牌数:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.tokens_per_line_var = tk.StringVar(value="1")
        ttk.Combobox(self.clipboard_options_frame, textvariable=self.tokens_per_line_var, values=["1", "5", "10", "20"], width=10, state="readonly").grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # 预览框架
        preview_frame = ttk.LabelFrame(main_frame, text="预览", padding="10")
        preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.preview_text = tk.Text(preview_frame, height=8, width=50)
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        preview_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        # 按钮框架
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        buttons_frame.columnconfigure(1, weight=1)
        
        # 预览按钮 (左对齐)
        ttk.Button(buttons_frame, text="预览", command=self.update_preview).grid(row=0, column=0, padx=(0, 5))
        
        # 导出和取消按钮 (右对齐)
        ttk.Button(buttons_frame, text="取消", command=self.cancel).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(buttons_frame, text="导出", command=self.export_tokens).grid(row=0, column=3, padx=(5, 0))
        
        # 初始化界面状态
        self.show_file_options()
    
    def load_statistics(self):
        """加载统计数据"""
        try:
            stats = self.db_manager.get_token_statistics()
            self.statistics = stats
        except Exception as e:
            messagebox.showerror("错误", f"加载统计数据失败: {e}")
            self.statistics = {"by_status": {}, "total_count": 0}
    
    def show_file_options(self):
        """显示文件选项"""
        self.file_options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.clipboard_options_frame.grid_forget()
    
    def show_clipboard_options(self):
        """显示剪贴板选项"""
        self.clipboard_options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.file_options_frame.grid_forget()
    
    def select_all(self):
        """全选所有状态"""
        for var in self.status_vars.values():
            var.set(True)
        self.update_preview()
    
    def deselect_all(self):
        """取消全选"""
        for var in self.status_vars.values():
            var.set(False)
        self.update_preview()
    
    def browse_file(self):
        """浏览文件保存位置"""
        initial_filename = self.generate_filename()
        file_path = filedialog.asksaveasfilename(
            title="保存导出文件",
            initialfile=initial_filename,
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.filename_var.set(file_path)
    
    def generate_filename(self):
        """生成默认文件名"""
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        # 获取选中的状态
        selected_statuses = self.get_selected_statuses()
        if len(selected_statuses) == 1:
            status_part = selected_statuses[0]
        else:
            status_part = "all_tokens"
        
        template = self.config_manager.get_filename_template()
        filename = template.format(
            status=status_part,
            date=date_str,
            time=time_str
        )
        
        return filename
    
    def get_selected_statuses(self):
        """获取选中的状态列表"""
        return [status for status, var in self.status_vars.items() if var.get()]
    
    def get_tokens_for_export(self):
        """获取要导出的令牌"""
        statuses = self.get_selected_statuses()
        if not statuses:
            return []
        
        tokens = []
        for status in statuses:
            tokens.extend(self.db_manager.get_tokens_by_status(status))
        
        return tokens
    
    def update_preview(self):
        """更新预览"""
        statuses = self.get_selected_statuses()
        if not statuses:
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", "请选择要导出的令牌状态")
            return
        
        tokens = self.get_tokens_for_export()
        if not tokens:
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", "选中的状态下没有令牌")
            return
        
        # 生成预览内容（显示前10个）
        preview_tokens = tokens[:10]
        preview_content = []
        
        for token in preview_tokens:
            preview_content.append(token["token_value"])
        
        preview_text = "\n".join(preview_content)
        if len(tokens) > 10:
            preview_text += f"\n\n... 还有 {len(tokens) - 10} 个令牌"
        
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview_text)
    
    def export_tokens(self):
        """执行导出操作"""
        statuses = self.get_selected_statuses()
        if not statuses:
            messagebox.showwarning("警告", "请选择要导出的令牌状态")
            return
        
        tokens = self.get_tokens_for_export()
        if not tokens:
            messagebox.showwarning("警告", "选中的状态下没有令牌")
            return
        
        export_method = self.export_method_var.get()
        
        if export_method == "file":
            self.export_to_file(tokens)
        else:
            self.export_to_clipboard(tokens)
    
    def export_to_file(self, tokens):
        """导出到文件"""
        file_path = self.filename_var.get()
        if not file_path:
            messagebox.showwarning("警告", "请选择保存位置")
            return
        
        try:
            # 确保目录存在
            export_dir = os.path.dirname(file_path)
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                for token in tokens:
                    f.write(f"{token['token_value']}\n")
            
            # 记录导出
            self.db_manager.export_tokens_to_file(file_path, self.get_selected_statuses())
            
            total_count = len(tokens)
            messagebox.showinfo("成功", f"已成功导出 {total_count} 个令牌到文件:\n{file_path}")
            self.result = True
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"导出到文件失败: {e}")
    
    def export_to_clipboard(self, tokens):
        """导出到剪贴板"""
        try:
            tokens_per_line = int(self.tokens_per_line_var.get())
            
            # 格式化令牌
            token_values = [token["token_value"] for token in tokens]
            
            if tokens_per_line == 1:
                clipboard_content = "\n".join(token_values)
            else:
                lines = []
                for i in range(0, len(token_values), tokens_per_line):
                    line_tokens = token_values[i:i + tokens_per_line]
                    lines.append(", ".join(line_tokens))
                clipboard_content = "\n".join(lines)
            
            # 复制到剪贴板
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(clipboard_content)
            
            total_count = len(tokens)
            messagebox.showinfo("成功", f"已成功复制 {total_count} 个令牌到剪贴板")
            self.result = True
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"导出到剪贴板失败: {e}")
    
    def cancel(self):
        """取消导出"""
        self.result = None
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
        self.update_preview()
        self.dialog.wait_window()
        return self.result