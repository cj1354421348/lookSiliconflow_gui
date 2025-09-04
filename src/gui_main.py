import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from functools import partial
import threading
import os
from typing import Dict, List, Optional
from datetime import datetime
import json
import hashlib

from database_manager import DatabaseManager
from config_manager import ConfigManager
from token_query_service import TokenQueryService
from settings_dialog import SettingsDialog
from export_dialog import ExportDialog
from log_manager import LogManager

class TokenManagerGUI:
    """令牌管理系统GUI主界面"""
    
    def __init__(self):
        # 初始化日志管理器
        self.log_manager = LogManager(debug_mode=False)
        
        # 初始化核心组件
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager(self.db_manager)
        self.query_service = TokenQueryService(self.db_manager, self.config_manager, self.log_manager)
        
        # 存储令牌数据用于右键菜单
        self.full_token_data = {}
        
        # 设置主窗口
        self.root = tk.Tk()
        self.root.title("令牌管理系统 v2.0")
        self.setup_window()
        
        # 创建界面组件
        self.create_widgets()
        
        # 排序状态
        self._sort_column = "最后检查"  # 默认按最后检查时间排序
        self._sort_direction = True  # True为降序 (新到旧)
        
        # 启动自动刷新
        self.auto_refresh_enabled = self.config_manager.is_auto_refresh_enabled()
        self.refresh_interval = self.config_manager.get_refresh_interval()
        
        # 初始化调试模式
        debug_enabled = self.config_manager.is_debug_mode_enabled()
        self.log_manager.set_debug_mode(debug_enabled)
        
        self.auto_refresh()
        
    def setup_window(self):
        """设置窗口属性"""
        window_size = self.config_manager.get_window_size()
        self.root.geometry(f"{window_size['width']}x{window_size['height']}")
        self.root.minsize(800, 600)
        
        # 设置窗口图标
        try:
            # 尝试设置自定义图标
            self._set_window_icon()
        except Exception as e:
            # 如果设置失败，忽略错误，使用默认图标
            pass
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 创建输入区域
        self.create_input_section(main_frame)
        
        # 创建控制面板
        self.create_control_panel(main_frame)
        
        # 创建状态显示区域
        self.create_status_section(main_frame)
        
        # 创建令牌列表区域
        self.create_token_list(main_frame)
        
        # 创建日志区域
        self.create_log_section(main_frame)
        
        # 设置GUI日志回调
        self.log_manager.set_gui_callback(self.log_message)
    
    def create_input_section(self, parent):
        """创建输入区域"""
        input_frame = ttk.LabelFrame(parent, text="令牌输入", padding="10")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        # 文件选择
        ttk.Label(input_frame, text="从文件导入:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.file_path_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.file_path_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(input_frame, text="浏览", command=self.select_input_file).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(input_frame, text="导入文件", command=self.import_from_file).grid(row=0, column=3, padx=(0, 10))
        
        # 文本输入
        ttk.Label(input_frame, text="直接输入:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.token_text = tk.Text(input_frame, height=3, width=50)
        self.token_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Button(input_frame, text="添加令牌", command=self.add_tokens_from_text).grid(row=1, column=2, pady=(5, 0), padx=(0, 10))
        ttk.Button(input_frame, text="清空", command=self.clear_input_text).grid(row=1, column=3, pady=(5, 0))
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding="10")
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 处理按钮
        self.process_button = ttk.Button(control_frame, text="开始处理", command=self.start_processing)
        self.process_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="停止处理", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        # 刷新按钮
        ttk.Button(control_frame, text="刷新", command=self.refresh_data).grid(row=0, column=2, padx=(0, 10))
        
        # 导出按钮
        ttk.Button(control_frame, text="导出", command=self.export_tokens).grid(row=0, column=3, padx=(0, 10))
        
        # 清理按钮
        ttk.Button(control_frame, text="清理", command=self.cleanup_tokens).grid(row=0, column=4, padx=(0, 10))
        
        # 设置按钮
        ttk.Button(control_frame, text="设置", command=self.open_settings).grid(row=0, column=5)
        
        # 重新请求所有令牌数据按钮
        ttk.Button(control_frame, text="重新请求", command=self.requery_all_tokens).grid(row=0, column=6, padx=(10, 0))
        
        # 移除测试复制按钮
    
    def create_status_section(self, parent):
        """创建状态显示区域"""
        status_frame = ttk.LabelFrame(parent, text="状态概览", padding="10")
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 统计标签
        self.status_labels = {}
        labels = [
            ("总计", "total"),
            ("待处理", "pending"),
            ("有效", "valid"),
            ("余额不足", "low_balance"),
            ("充值余额", "charge_balance"),
            ("无效", "invalid")
        ]
        
        for i, (label_text, key) in enumerate(labels):
            ttk.Label(status_frame, text=f"{label_text}:").grid(row=i//2, column=(i%2)*2, sticky=tk.W, padx=(0, 5), pady=2)
            count_label = ttk.Label(status_frame, text="0", font=("Arial", 10, "bold"))
            count_label.grid(row=i//2, column=(i%2)*2+1, sticky=tk.W, padx=(0, 20), pady=2)
            self.status_labels[key] = count_label
        
        # 添加余额总计和充值余额总计
        ttk.Label(status_frame, text="余额总计:").grid(row=(len(labels)+1)//2, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        self.total_balance_label = ttk.Label(status_frame, text="0.00", font=("Arial", 10, "bold"))
        self.total_balance_label.grid(row=(len(labels)+1)//2, column=1, sticky=tk.W, padx=(0, 20), pady=2)
        
        ttk.Label(status_frame, text="充值余额总计:").grid(row=(len(labels)+1)//2, column=2, sticky=tk.W, padx=(0, 5), pady=2)
        self.total_charge_balance_label = ttk.Label(status_frame, text="0.00", font=("Arial", 10, "bold"))
        self.total_charge_balance_label.grid(row=(len(labels)+1)//2, column=3, sticky=tk.W, padx=(0, 20), pady=2)
        
        # 处理状态
        self.processing_status_label = ttk.Label(status_frame, text="就绪", foreground="green")
        self.processing_status_label.grid(row=(len(labels)+1)//2 + 1, column=0, columnspan=4, pady=(10, 0))
    
    def create_token_list(self, parent):
        """创建令牌列表区域"""
        list_frame = ttk.LabelFrame(parent, text="令牌列表", padding="10")
        list_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)  # 修改为第1行（令牌树状视图所在行）具有权重
        
        # 状态选择
        ttk.Label(list_frame, text="状态筛选:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.status_filter = ttk.Combobox(list_frame, values=["全部", "pending", "valid", "low_balance", "charge_balance", "invalid"])
        self.status_filter.set("全部")
        self.status_filter.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.status_filter.bind("<<ComboboxSelected>>", self.filter_tokens)
        
        # 令牌树状视图
        columns = ("令牌", "余额", "充值余额", "最后检查")
        self.token_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        self.token_tree.configure(selectmode="extended")  # 单独设置多选模式
        
        # 设置列标题和点击事件
        for col in columns:
            self.token_tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.token_tree.column(col, width=120)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.token_tree.yview)
        self.token_tree.configure(yscrollcommand=scrollbar.set)
        
        self.token_tree.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=4, sticky=(tk.N, tk.S))
        
        # 绑定右键菜单事件
        self.token_tree.bind("<Button-3>", self.show_context_menu)
    
    def create_log_section(self, parent):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="日志", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 清空日志按钮
        ttk.Button(log_frame, text="清空日志", command=self.clear_log).grid(row=1, column=0, sticky=tk.E, pady=(5, 0))
    
    def select_input_file(self):
        """选择输入文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择令牌文件（可多选）",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_paths:
            # 如果选择了多个文件，用分号连接显示
            if len(file_paths) == 1:
                self.file_path_var.set(file_paths[0])
            else:
                self.file_path_var.set(f"; ".join(file_paths) + f" (共{len(file_paths)}个文件)")
    
    def import_from_file(self):
        """从文件导入令牌"""
        file_path_display = self.file_path_var.get()
        if not file_path_display:
            messagebox.showwarning("警告", "请先选择文件")
            return
        
        # 检查是否是多文件选择
        if "(共" in file_path_display and "个文件)" in file_path_display:
            # 提取实际文件路径（去掉显示文本）
            import re
            match = re.match(r"^(.*?) \(共\d+个文件\)$", file_path_display)
            if match:
                file_paths_str = match.group(1)
                file_paths = [fp.strip() for fp in file_paths_str.split(";") if fp.strip()]
            else:
                # 备用处理方式
                file_paths = file_path_display.split(" (共")[0].split(";")
        else:
            # 单文件
            file_paths = [file_path_display]
        
        # 处理所有文件
        total_added = 0
        total_duplicates = 0
        total_errors = 0
        error_messages = []
        
        for file_path in file_paths:
            result = self.query_service.add_tokens_from_file(file_path)
            if result["success"]:
                total_added += result.get("added_tokens", 0)
                total_duplicates += result.get("duplicates_skipped", 0)
            else:
                total_errors += 1
                error_messages.append(f"{os.path.basename(file_path)}: {result['message']}")
        
        # 显示汇总结果
        if total_errors == 0:
            message = f"成功导入 {len(file_paths)} 个文件\n"
            message += f"新增令牌: {total_added} 个\n"
            message += f"重复令牌: {total_duplicates} 个"
            messagebox.showinfo("成功", message)
            self.refresh_data()
        else:
            message = f"处理完成，但有 {total_errors} 个文件出错\n"
            message += f"成功文件: {len(file_paths) - total_errors} 个\n"
            message += f"新增令牌: {total_added} 个\n"
            message += f"重复令牌: {total_duplicates} 个\n\n"
            message += "错误详情:\n" + "\n".join(error_messages[:3])  # 只显示前3个错误
            if len(error_messages) > 3:
                message += f"\n... 还有 {len(error_messages) - 3} 个错误"
            messagebox.showwarning("部分成功", message)
            self.refresh_data()
    
    def add_tokens_from_text(self):
        """从文本添加令牌"""
        text = self.token_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入令牌")
            return
        
        result = self.query_service.add_tokens_from_text(text)
        
        if result["success"]:
            messagebox.showinfo("成功", result["message"])
            self.token_text.delete("1.0", tk.END)
            self.refresh_data()
        else:
            messagebox.showerror("失败", result["message"])
    
    def clear_input_text(self):
        """清空输入文本"""
        self.token_text.delete("1.0", tk.END)
    
    def start_processing(self):
        """开始处理令牌"""
        def process_async():
            self.process_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            result = self.query_service.process_pending_tokens()
            
            self.root.after(0, lambda: self.update_processing_result(result))
        
        threading.Thread(target=process_async, daemon=True).start()
    
    def stop_processing(self):
        """停止处理（这里简化处理）"""
        messagebox.showinfo("停止", "处理将在当前批次完成后停止")
        # 实际实现中需要更复杂的停止机制
    
    def update_processing_result(self, result):
        """更新处理结果"""
        self.process_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        if result["success"]:
            messagebox.showinfo("处理完成", 
                f"处理完成: 总计 {result.get('processed_count', 0)} 个令牌")
        else:
            messagebox.showerror("处理失败", result["message"])
        
        self.refresh_data()
    
    def update_requery_result(self, result):
        """更新重新请求结果"""
        self.process_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 统计结果
        processed_count = len(result) if isinstance(result, list) else 0
        successful_count = sum(1 for r in result if isinstance(r, dict) and r.get("success")) if isinstance(result, list) else 0
        failed_count = processed_count - successful_count
        
        if processed_count > 0:
            messagebox.showinfo("重新请求完成", 
                f"重新请求完成: 总计 {processed_count} 个令牌，成功 {successful_count} 个，失败 {failed_count} 个")
        else:
            messagebox.showinfo("重新请求完成", "没有令牌需要重新请求")
        
        self.refresh_data()
    
    def refresh_data(self):
        """刷新数据显示"""
        self.update_status_display()
        self.update_token_list()
        # 移除"数据已刷新"的日志输出，因为这是无效信息
    
    def update_status_display(self):
        """更新状态显示"""
        stats = self.db_manager.get_token_statistics()
        
        # 更新总数
        self.status_labels["total"].config(text=str(stats["total_count"]))
        
        # 更新各状态数量，如果没有该状态则显示0
        all_status_keys = ["pending", "valid", "low_balance", "charge_balance", "invalid"]
        for status_key in all_status_keys:
            if status_key in self.status_labels:
                count = stats["by_status"].get(status_key, {}).get("count", 0)
                self.status_labels[status_key].config(text=str(count))
        
        # 计算并更新余额总计和充值余额总计
        total_balance = 0.0
        total_charge_balance = 0.0
        
        # 遍历所有状态的令牌，累加余额
        for status in all_status_keys:
            tokens = self.db_manager.get_tokens_by_status(status)
            for token in tokens:
                # 累加总余额
                if token.get("total_balance") is not None:
                    try:
                        total_balance += float(token["total_balance"])
                    except (ValueError, TypeError):
                        pass  # 忽略无效值
                
                # 累加充值余额，只计算大于0的充值余额
                if token.get("charge_balance") is not None:
                    try:
                        charge_balance = float(token["charge_balance"])
                        if charge_balance > 0:  # 只累加大于0的充值余额
                            total_charge_balance += charge_balance
                    except (ValueError, TypeError):
                        pass  # 忽略无效值
        
        # 更新余额总计和充值余额总计显示
        self.total_balance_label.config(text=f"{total_balance:.2f}")
        self.total_charge_balance_label.config(text=f"{total_charge_balance:.2f}")
    
    def update_token_list(self):
        """更新令牌列表"""
        # 保存当前选中的令牌值
        selected_token_values = []
        selected_items = self.token_tree.selection()
        for item_id in selected_items:
            if item_id in self.full_token_data:
                token_data = self.full_token_data[item_id]
                selected_token_values.append(token_data["token_value"])
        
        # 清空现有列表
        for item in self.token_tree.get_children():
            self.token_tree.delete(item)
        
        # 获取筛选条件
        selected_status = self.status_filter.get()
        
        # 获取令牌数据
        if selected_status == "全部":
            tokens = []
            for status in ["pending", "valid", "low_balance", "charge_balance", "invalid"]:
                tokens.extend(self.db_manager.get_tokens_by_status(status))
        else:
            tokens = self.db_manager.get_tokens_by_status(selected_status)
        
        # 根据排序选项排序
        sort_column_map = {
            "令牌": "token_value",
            "余额": "total_balance",
            "充值余额": "charge_balance",
            "最后检查": "last_checked",
            "创建时间": "created_at" # 新增一个"创建时间"的排序键，以防后面需要
        }
        
        sort_key_name = sort_column_map.get(self._sort_column, "last_checked")

        def get_sort_key(token):
            key_value = token.get(sort_key_name)

            # 处理数值字段 (余额, 充值余额)
            if sort_key_name in ["total_balance", "charge_balance"]:
                if key_value is None:
                    return 0.0
                # 如果已经是数字类型，直接返回浮点数
                if isinstance(key_value, (int, float)):
                    return float(key_value)
                try:
                    # 尝试将字符串转换为浮点数
                    return float(key_value)
                except (ValueError, TypeError):
                    # 转换失败则返回默认值
                    return 0.0
            
            # 处理日期/字符串字段 (令牌, 最后检查, 创建时间)
            elif sort_key_name in ["token_value", "last_checked", "created_at"]:
                if key_value is None:
                    return ""
                return str(key_value)
            
            # 默认返回空字符串，以防 sort_key_name 不在已知列表中
            return ""

        tokens.sort(key=get_sort_key, reverse=self._sort_direction)
        
        # 清空完整令牌数据存储
        self.full_token_data.clear()
        
        # 创建映射以查找新的item_id
        new_item_ids = []
        
        # 添加到列表
        for token in tokens:  # 显示所有令牌
            token_value = token["token_value"]
            if len(token_value) > 20:
                display_token = token_value[:10] + "..." + token_value[-7:]
            else:
                display_token = token_value
            
            balance = token.get("total_balance", "-")
            charge_balance = token.get("charge_balance", "-")
            last_checked = token.get("last_checked", "-") or "未检查"
            
            item_id = self.token_tree.insert("", tk.END, values=(
                display_token, balance, charge_balance, last_checked[:19] if last_checked != "-" else "-"
            ))
            
            # 存储完整令牌数据
            self.full_token_data[item_id] = token
            
            # 如果这个令牌是之前选中的，记录新的item_id
            if token_value in selected_token_values:
                new_item_ids.append(item_id)
        
        # 恢复选中状态
        for item_id in new_item_ids:
            self.token_tree.selection_add(item_id)
        
        # 如果有恢复的选中项，滚动到第一个选中项
        if new_item_ids:
            self.token_tree.see(new_item_ids[0])
    
    def filter_tokens(self, event=None):
        """筛选令牌"""
        self.update_token_list()
    
    def sort_by_column(self, col):
        """按列排序"""
        if self._sort_column == col:
            self._sort_direction = not self._sort_direction  # 反转排序方向
        else:
            self._sort_column = col
            self._sort_direction = False  # 默认为降序
        
        self.update_token_list()
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 只依赖左键选中的项
        selected_items = self.token_tree.selection()
        
        # 调试信息
        self.log_manager.log_debug(f"右键调试: selected_items={selected_items}")
        
        # 只有在有左键选中的令牌时才显示菜单
        if selected_items:
            self.log_manager.log_debug("显示菜单：检测到左键选中项")
            
            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            
            # 使用第一个选中的令牌作为右键菜单的操作目标
            target_item = selected_items[0]
            if target_item in self.full_token_data:
                # 添加复制令牌选项
                context_menu.add_command(label="复制完整令牌", command=lambda: self.copy_full_token(target_item))
                context_menu.add_command(label="复制显示令牌", command=lambda: self.copy_display_token(target_item))
                
                # 添加分隔线
                context_menu.add_separator()
                
                # 添加复制状态选项
                context_menu.add_command(label="复制令牌状态", command=lambda: self.copy_token_status(target_item))
                
                # 添加多选支持
                if len(selected_items) > 1:
                    context_menu.add_separator()
                    context_menu.add_command(label="复制所有选中令牌", command=self.copy_selected_tokens)
                
                # 显示菜单
                context_menu.post(event.x_root, event.y_root)
            else:
                self.log_manager.log_debug(f"选中的项 {target_item} 不在 full_token_data 中")
        else:
            self.log_manager.log_debug("不显示菜单：没有左键选中的令牌")
    
    def copy_full_token(self, item):
        """复制完整令牌到剪贴板"""
        try:
            if item and item in self.full_token_data:
                token_data = self.full_token_data[item]
                full_token = token_data["token_value"]
                
                self.root.clipboard_clear()
                self.root.clipboard_append(full_token)
                self.log_manager.log_user("已复制完整令牌到剪贴板")
        except Exception as e:
            self.log_manager.log_error(f"复制完整令牌失败: {e}")
    
    def copy_display_token(self, item):
        """复制显示令牌到剪贴板"""
        try:
            if item:
                values = self.token_tree.item(item)['values']
                display_token = values[0]  # 第一列是显示的令牌
                
                self.root.clipboard_clear()
                self.root.clipboard_append(display_token)
                self.log_manager.log_user("已复制显示令牌到剪贴板")
        except Exception as e:
            self.log_manager.log_error(f"复制显示令牌失败: {e}")
    
    def copy_token_status(self, item):
        """复制令牌状态信息到剪贴板"""
        try:
            if item and item in self.full_token_data:
                token_data = self.full_token_data[item]
                token_value = token_data["token_value"]
                status = token_data["status"]
                total_balance = token_data.get("total_balance", "未知")
                charge_balance = token_data.get("charge_balance", "未知")
                
                info = f"令牌: {token_value}\n状态: {status}\n余额: {total_balance}\n充值余额: {charge_balance}"
                
                self.root.clipboard_clear()
                self.root.clipboard_append(info)
                self.log_manager.log_user("已复制令牌状态信息到剪贴板")
        except Exception as e:
            self.log_manager.log_error(f"复制令牌状态信息失败: {e}")

    def copy_selected_tokens(self):
        """复制所有选中的令牌到剪贴板"""
        try:
            selected_items = self.token_tree.selection()
            
            if not selected_items:
                self.log_manager.log_user("没有选中的令牌")
                return
            
            tokens_to_copy = []
            for item in selected_items:
                if item in self.full_token_data:
                    token_data = self.full_token_data[item]
                    tokens_to_copy.append(token_data["token_value"])
            
            if tokens_to_copy:
                # 用换行符连接所有令牌
                tokens_text = "\n".join(tokens_to_copy)
                
                self.root.clipboard_clear()
                self.root.clipboard_append(tokens_text)
                
                self.log_manager.log_user(f"已复制 {len(tokens_to_copy)} 个选中令牌到剪贴板")
            else:
                self.log_manager.log_user("没有有效的令牌可复制")
        except Exception as e:
            self.log_manager.log_error(f"复制选中令牌失败: {e}")
    
        
    def export_tokens(self):
        """导出令牌"""
        try:
            export_dialog = ExportDialog(self.root, self.db_manager, self.config_manager)
            if export_dialog.show():
                self.log_manager.log_user("令牌导出完成")
                self.refresh_data()
        except Exception as e:
            self.log_manager.log_error(f"打开导出对话框失败: {e}")
            messagebox.showerror("错误", f"打开导出对话框失败: {e}")
    
    def cleanup_tokens(self):
        """清理令牌"""
        try:
            # 创建清理对话框，先隐藏
            cleanup_window = tk.Toplevel(self.root)
            cleanup_window.withdraw()  # 隐藏窗口，直到完全准备好
            cleanup_window.title("清理令牌")
            cleanup_window.geometry("400x300")
            cleanup_window.minsize(350, 250)
            
            # 设置对话框图标
            try:
                if hasattr(self.root, 'iconbitmap'):
                    parent_icon = self.root.iconbitmap()
                    if parent_icon:
                        cleanup_window.iconbitmap(parent_icon)
                    elif os.path.exists("icon.ico"):
                        cleanup_window.iconbitmap("icon.ico")
            except:
                pass
            
            # 模态对话框
            cleanup_window.transient(self.root)
            cleanup_window.grab_set()
            
            # 创建清理界面
            main_frame = ttk.Frame(cleanup_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text="选择要清理的令牌状态:", font=("Arial", 12, "bold")).pack(pady=(0, 20))
            
            # 状态复选框
            status_vars = {}
            status_info = [
                ("invalid", "无效令牌"),
                ("low_balance", "余额不足令牌"),
                ("pending", "待处理令牌"),
                ("valid", "有效令牌"),
                ("charge_balance", "充值余额令牌")
            ]
            
            for status, label in status_info:
                var = tk.BooleanVar()
                status_vars[status] = var
                ttk.Checkbutton(main_frame, text=label, variable=var).pack(anchor=tk.W, pady=5)
            
            # 按钮
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            def cleanup_selected():
                selected_statuses = [status for status, var in status_vars.items() if var.get()]
                if not selected_statuses:
                    messagebox.showwarning("警告", "请选择要清理的令牌状态")
                    return
                
                if messagebox.askyesno("确认", f"确定要清理选中的令牌吗？\n此操作不可取消！"):
                    total_deleted = 0
                    for status in selected_statuses:
                        deleted = self.db_manager.delete_tokens_by_status(status)
                        total_deleted += deleted
                    
                    messagebox.showinfo("完成", f"已清理 {total_deleted} 个令牌")
                    self.log_manager.log_user(f"已清理 {total_deleted} 个令牌")
                    self.refresh_data()
                    cleanup_window.destroy()
            
            ttk.Button(button_frame, text="清理", command=cleanup_selected).pack(side=tk.RIGHT, padx=(0, 10))
            ttk.Button(button_frame, text="取消", command=cleanup_window.destroy).pack(side=tk.RIGHT)
            ttk.Button(button_frame, text="全选", command=lambda: [var.set(True) for var in status_vars.values()]).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="取消全选", command=lambda: [var.set(False) for var in status_vars.values()]).pack(side=tk.LEFT)
            
            # 居中显示
            cleanup_window.update_idletasks()
            width = cleanup_window.winfo_width()
            height = cleanup_window.winfo_height()
            x = (cleanup_window.winfo_screenwidth() // 2) - (width // 2)
            y = (cleanup_window.winfo_screenheight() // 2) - (height // 2)
            cleanup_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # 现在显示窗口
            cleanup_window.deiconify()
            
        except Exception as e:
            messagebox.showerror("错误", f"打开清理对话框失败: {e}")
    
    def open_settings(self):
        """打开设置对话框"""
        try:
            settings_dialog = SettingsDialog(self.root, self.config_manager, self.log_manager)
            if settings_dialog.show():
                self.log_manager.log_user("设置已保存")
                # 如果设置变了，可能需要更新界面
                self.auto_refresh_enabled = self.config_manager.is_auto_refresh_enabled()
                self.refresh_interval = self.config_manager.get_refresh_interval()
                # 更新调试模式
                debug_enabled = self.config_manager.is_debug_mode_enabled()
                self.log_manager.set_debug_mode(debug_enabled)
                if debug_enabled:
                    log_path = self.log_manager.get_log_file_path()
                    self.log_manager.log_user(f"调试模式已启用，日志文件: {log_path}")
                else:
                    self.log_manager.log_user("调试模式已禁用")
        except Exception as e:
            self.log_manager.log_error(f"打开设置对话框失败: {e}")
            messagebox.showerror("错误", f"打开设置对话框失败: {e}")
    
    # 调试模式已在初始化时从配置管理器加载
    
    def requery_all_tokens(self):
        """重新请求所有令牌数据"""
        def requery_async():
            self.process_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # 获取所有令牌（不仅仅是待处理的）
            all_tokens = []
            for status in ["pending", "valid", "low_balance", "charge_balance", "invalid"]:
                tokens = self.db_manager.get_tokens_by_status(status)
                all_tokens.extend(tokens)
            
            # 重新处理所有令牌
            result = self.query_service.process_tokens_multithreaded(all_tokens) if self.config_manager.is_threading_enabled() else self.query_service.process_tokens_single_threaded(all_tokens)
            
            self.root.after(0, lambda: self.update_requery_result(result))
        
        threading.Thread(target=requery_async, daemon=True).start()
    
    def log_message(self, message):
        """添加日志消息到GUI（仅用于用户级别消息）"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete("1.0", tk.END)
    
    def auto_refresh(self):
        """自动刷新"""
        if self.auto_refresh_enabled:
            self.refresh_data()
        
        # 安排下次刷新
        self.root.after(self.refresh_interval * 1000, self.auto_refresh)
    
    def _set_window_icon(self):
        """设置窗口图标（包括Windows任务栏图标）"""
        # 尝试多种路径的图标文件
        icon_paths = [
            "icon.ico",           # ICO格式图标
            "assets/icon.ico",    # 资源目录下的图标
            "images/icon.ico"
        ]
        
        icon_found = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    # 使用简化的Windows图标设置方法
                    self._set_windows_icon_simple(icon_path)
                    icon_found = True
                    break
                except Exception as e:
                    print(f"设置图标失败: {e}")
                    continue
        
        if not icon_found:
            # 如果没有找到图标文件，清空默认Python图标
            try:
                self.root.iconbitmap('')
            except:
                pass
        
        return icon_found
    
    def _set_windows_icon_simple(self, icon_path):
        """简化的Windows图标设置方法"""
        try:
            # 获取完整路径
            full_path = os.path.abspath(icon_path)
            
            # 基本图标设置
            self.root.iconbitmap(full_path)
            
            # 延迟设置以影响任务栏
            def set_taskbar_icon():
                try:
                    self.root.iconbitmap(full_path)
                    # 如果是Windows，尝试使用额外的图标设置
                    if self._is_windows():
                        import ctypes
                        from ctypes import wintypes
                        
                        # Windows API常量
                        IMAGE_ICON = 1
                        LR_LOADFROMFILE = 0x00000010
                        WM_SETICON = 0x0080
                        ICON_SMALL = 0
                        ICON_BIG = 1
                        
                        # 获取窗口句柄
                        hwnd = self.root.winfo_id()
                        if hwnd:
                            # 加载图标
                            hicon = ctypes.windll.user32.LoadImageW(
                                None,
                                full_path,
                                IMAGE_ICON,
                                0, 0,
                                LR_LOADFROMFILE
                            )
                            if hicon:
                                # 设置大小图标
                                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
                                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
                                ctypes.windll.user32.DestroyIcon(hicon)
                except Exception as e:
                    print(f"任务栏图标设置失败: {e}")
            
            # 延迟执行，确保窗口完全显示
            self.root.after(200, set_taskbar_icon)
            
        except Exception as e:
            print(f"图标设置失败: {e}")
    
    def _is_windows(self):
        """检测是否为Windows系统"""
        import sys
        return sys.platform.startswith('win')
    
    def on_window_close(self):
        """窗口关闭事件处理"""
        # 保存窗口大小和位置
        self.root.destroy()
    
    def run(self):
        """启动GUI"""
        self.refresh_data()
        self.root.mainloop()

def main():
    """主函数"""
    app = TokenManagerGUI()
    app.run()

if __name__ == "__main__":
    main()