"""
代理请求日志查看对话框
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
from datetime import datetime
import threading


class ProxyLogsDialog:
    """代理请求日志查看对话框"""

    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        self.dialog = None
        self.logs_tree = None

        # 排序状态
        self._sort_column = "request_timestamp"
        self._sort_direction = True  # True为降序

        # 分页状态
        self.current_page = 0
        self.page_size = 50
        self.total_count = 0

        # 过滤状态
        self.status_filter = "全部"

        self.create_dialog()

    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent.root)
        self.dialog.title("代理请求日志")
        self.dialog.geometry("1200x700")
        self.dialog.resizable(True, True)

        # 设置模态
        self.dialog.transient(self.parent.root)
        self.dialog.grab_set()

        # 创建主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # 创建控制面板
        self.create_control_panel(main_frame)

        # 创建统计信息面板
        self.create_stats_panel(main_frame)

        # 创建日志列表
        self.create_logs_table(main_frame)

        # 创建分页控制
        self.create_pagination_controls(main_frame)

        # 居中对话框
        self.center_dialog()

        # 初始化排序状态
        self.sort_column = None
        self.sort_reverse = False

        # 加载初始数据
        self.refresh_data()

    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="筛选和控制", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 第一行：筛选功能
        ttk.Label(control_frame, text="状态筛选:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.status_filter_var = tk.StringVar(value="全部")
        status_combo = ttk.Combobox(
            control_frame,
            textvariable=self.status_filter_var,
            values=["全部", "成功", "失败", "请求中"],
            width=10,
            state="readonly"
        )
        status_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        status_combo.bind("<<ComboboxSelected>>", self.on_filter_changed)

        # 保留最新日志功能
        ttk.Label(control_frame, text="保留最新:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.max_logs_var = tk.StringVar(value="1000")
        max_logs_entry = ttk.Entry(control_frame, textvariable=self.max_logs_var, width=10)
        max_logs_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        ttk.Label(control_frame, text="条").grid(row=0, column=4, sticky=tk.W, padx=(0, 10))

        ttk.Button(control_frame, text="应用保留", command=self.apply_max_logs).grid(row=0, column=5, padx=(0, 10))
        ttk.Button(control_frame, text="刷新", command=self.refresh_data).grid(row=0, column=6, padx=(0, 10))

        # 第二行：清理和控制
        ttk.Button(control_frame, text="清理30天前日志", command=self.clear_old_logs).grid(row=1, column=0, padx=(0, 10), pady=(5, 0))
        ttk.Button(control_frame, text="清空所有日志", command=self.clear_all_logs).grid(row=1, column=1, padx=(0, 10), pady=(5, 0))
        ttk.Button(control_frame, text="导出日志", command=self.export_logs).grid(row=1, column=2, padx=(0, 10), pady=(5, 0))
        ttk.Button(control_frame, text="关闭", command=self.close_dialog).grid(row=1, column=3, padx=(0, 10), pady=(5, 0))

    def create_stats_panel(self, parent):
        """创建统计信息面板"""
        stats_frame = ttk.LabelFrame(parent, text="统计信息", padding="10")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 统计标签
        self.stats_labels = {}
        stats_info = [
            ("总请求数:", "total_requests"),
            ("成功数:", "successful_requests"),
            ("失败数:", "failed_requests"),
            ("平均耗时:", "avg_duration"),
            ("今日请求:", "today_requests"),
            ("流式响应:", "streaming_requests")
        ]

        for i, (label_text, key) in enumerate(stats_info):
            row = i // 3
            col = (i % 3) * 2
            ttk.Label(stats_frame, text=label_text).grid(row=row, column=col, sticky=tk.W, padx=(0, 5))
            value_label = ttk.Label(stats_frame, text="0", font=("Arial", 9, "bold"))
            value_label.grid(row=row, column=col+1, sticky=tk.W, padx=(0, 20))
            self.stats_labels[key] = value_label

    def create_logs_table(self, parent):
        """创建日志表格"""
        table_frame = ttk.LabelFrame(parent, text="日志记录", padding="10")
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # 定义列
        columns = ("时间", "状态", "响应类型", "状态码", "耗时(ms)", "模型", "Key", "方法", "端点")
        self.logs_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, selectmode="extended")

        # 设置列标题和属性
        column_widths = {
            "时间": 150,
            "状态": 60,
            "响应类型": 80,
            "状态码": 60,
            "耗时(ms)": 80,
            "模型": 150,
            "Key": 200,
            "方法": 60,
            "端点": 200
        }

        for col in columns:
            self.logs_tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.logs_tree.column(col, width=column_widths.get(col, 100), minwidth=50)

        # 滚动条
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.logs_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.logs_tree.xview)
        self.logs_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # 布局
        self.logs_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.E, tk.W))

        # 设置行颜色
        self.logs_tree.tag_configure('success', background='#E8F5E8')
        self.logs_tree.tag_configure('failed', background='#FFE8E8')
        self.logs_tree.tag_configure('pending', background='#E8E8FF')

        # 绑定事件
        self.logs_tree.bind("<Button-3>", self.show_context_menu)  # 右键菜单
        self.logs_tree.bind("<Button-1>", self.on_left_click)  # 左键选中

    def create_pagination_controls(self, parent):
        """创建分页控制"""
        page_frame = ttk.Frame(parent)
        page_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 分页信息
        self.page_info_label = ttk.Label(page_frame, text="第 1 页，共 0 条记录")
        self.page_info_label.grid(row=0, column=0, sticky=tk.W)

        # 分页按钮
        button_frame = ttk.Frame(page_frame)
        button_frame.grid(row=0, column=1, sticky=tk.E)

        self.prev_button = ttk.Button(button_frame, text="上一页", command=self.prev_page, state=tk.DISABLED)
        self.prev_button.grid(row=0, column=0, padx=(0, 5))

        self.next_button = ttk.Button(button_frame, text="下一页", command=self.next_page, state=tk.DISABLED)
        self.next_button.grid(row=0, column=1)

        # 配置页面框架的权重
        page_frame.columnconfigure(1, weight=1)

    def on_filter_changed(self, event=None):
        """筛选条件改变"""
        self.status_filter = self.status_filter_var.get()
        self.current_page = 0
        self.refresh_data()

    def sort_by_column(self, col):
        """按列排序"""
        # 列名映射到数据库字段
        column_map = {
            "时间": "request_timestamp",
            "状态": "status",
            "响应类型": "response_type",
            "状态码": "status_code",
            "耗时(ms)": "duration_ms",
            "模型": "model",
            "Key": "token_value",
            "方法": "method",
            "端点": "endpoint"
        }

        db_column = column_map.get(col, "request_timestamp")

        if self._sort_column == db_column:
            self._sort_direction = not self._sort_direction
        else:
            self._sort_column = db_column
            self._sort_direction = True

        self.refresh_data()

    def refresh_data(self):
        """刷新数据"""
        def load_data():
            try:
                # 获取统计信息
                stats = self.db_manager.get_proxy_logs_statistics()

                # 获取日志数据，支持排序，包含ID用于操作
                status_filter = None if self.status_filter == "全部" else self.status_filter
                logs = self.db_manager.get_proxy_request_logs(
                    limit=self.page_size,
                    offset=self.current_page * self.page_size,
                    status_filter=status_filter,
                    sort_column=self.sort_column,
                    sort_reverse=self.sort_reverse,
                    include_id=True
                )

                # 更新UI
                self.dialog.after(0, lambda: self.update_ui(stats, logs))

            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror("错误", f"加载数据失败: {e}"))

        # 在后台线程加载数据
        threading.Thread(target=load_data, daemon=True).start()

    def update_ui(self, stats, logs):
        """更新UI显示"""
        # 更新统计信息
        overall = stats.get('overall', {})
        today = stats.get('today', {})

        self.stats_labels['total_requests'].config(text=str(overall.get('total_requests', 0)))
        self.stats_labels['successful_requests'].config(text=str(overall.get('successful_requests', 0)))
        self.stats_labels['failed_requests'].config(text=str(overall.get('failed_requests', 0)))

        avg_duration = overall.get('avg_duration_ms', 0)
        if avg_duration:
            self.stats_labels['avg_duration'].config(text=f"{avg_duration:.1f}ms")
        else:
            self.stats_labels['avg_duration'].config(text="0ms")

        self.stats_labels['today_requests'].config(text=str(today.get('today_requests', 0)))
        self.stats_labels['streaming_requests'].config(text=str(overall.get('streaming_requests', 0)))

        # 清空现有数据
        for item in self.logs_tree.get_children():
            self.logs_tree.delete(item)

        # 添加新数据
        for log in logs:
            # 格式化时间 - 使用系统本地时间
            timestamp = log.get('request_timestamp', '')
            if timestamp:
                try:
                    # 直接解析为本地时间，不带时区转换
                    if timestamp.endswith('Z'):
                        # 如果是UTC时间，转换为本地时间显示
                        dt = datetime.fromisoformat(timestamp[:-1]).astimezone()
                    else:
                        # 已经是有时区信息的时间，直接使用
                        dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%m-%d %H:%M:%S")
                except:
                    time_str = timestamp[:16] if len(timestamp) >= 16 else timestamp
            else:
                time_str = "-"

            # 格式化Key显示
            token_value = log.get('token_value', '')
            key_display = token_value[:12] + "..." if len(token_value) > 12 else token_value

            # 确定行标签（用于着色）
            status = log.get('status', '')
            if status == '成功':
                tag = 'success'
            elif status == '失败':
                tag = 'failed'
            elif status == '请求中':
                tag = 'pending'
            else:
                tag = ''

            values = (
                time_str,
                status,
                log.get('response_type', ''),
                log.get('status_code', ''),
                log.get('duration_ms', ''),
                log.get('model', ''),
                key_display,
                log.get('method', ''),
                log.get('endpoint', '')
            )

            # 将log_id存储为Treeview项的数据（添加到values中但不显示）
            log_id = log.get('id')
            extended_values = values + (log_id,)  # 将ID添加到末尾

            item = self.logs_tree.insert("", tk.END, values=extended_values, tags=(tag,))

        # 更新分页信息
        self.total_count = overall.get('total_requests', 0)
        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        current_page_display = self.current_page + 1

        self.page_info_label.config(
            text=f"第 {current_page_display} 页，共 {self.total_count} 条记录"
        )

        # 更新分页按钮状态
        self.prev_button.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if current_page_display < total_pages else tk.DISABLED)

    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_data()

    def next_page(self):
        """下一页"""
        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        if self.current_page + 1 < total_pages:
            self.current_page += 1
            self.refresh_data()

    def clear_old_logs(self):
        """清理旧日志"""
        if messagebox.askyesno("确认清理", "确定要清理30天前的代理请求日志吗？\n此操作不可恢复！"):
            try:
                deleted_count = self.db_manager.clear_proxy_request_logs(days_to_keep=30)
                messagebox.showinfo("清理完成", f"已清理 {deleted_count} 条旧日志记录")
                self.refresh_data()
            except Exception as e:
                messagebox.showerror("清理失败", f"清理日志时发生错误: {e}")

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

    def close_dialog(self):
        """关闭对话框"""
        self.dialog.destroy()

    def show(self):
        """显示对话框"""
        # 等待对话框关闭
        self.parent.root.wait_window(self.dialog)

    # ===== 新增功能方法 =====

    def sort_by_column(self, col):
        """按列排序"""
        # 获取列索引
        column_map = {
            "时间": "request_timestamp",
            "状态": "status",
            "响应类型": "response_type",
            "状态码": "status_code",
            "耗时(ms)": "duration_ms",
            "模型": "model",
            "Key": "token_value",
            "方法": "method",
            "端点": "endpoint"
        }

        db_column = column_map.get(col)
        if not db_column:
            return

        # 切换排序方向
        if self.sort_column == db_column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = db_column
            self.sort_reverse = False

        self.refresh_data()

    def apply_max_logs(self):
        """应用保留最新日志行数设置"""
        try:
            max_logs = int(self.max_logs_var.get())
            if max_logs < 1:
                messagebox.showwarning("参数错误", "保留日志数量必须大于0")
                return

            if messagebox.askyesno("确认保留", f"确定要只保留最新的 {max_logs} 条日志吗？\n其他日志将被删除！"):
                try:
                    # 获取总日志数
                    total_logs = self.db_manager.get_proxy_logs_count()
                    if total_logs <= max_logs:
                        messagebox.showinfo("无需清理", f"当前日志总数为 {total_logs} 条，无需删除")
                        return

                    # 计算需要删除的数量
                    logs_to_delete = total_logs - max_logs
                    deleted_count = self.db_manager.delete_oldest_proxy_logs(count=logs_to_delete)

                    messagebox.showinfo("保留完成", f"已保留最新 {max_logs} 条日志，删除 {deleted_count} 条旧日志")
                    self.refresh_data()

                except Exception as e:
                    messagebox.showerror("操作失败", f"保留日志时发生错误: {e}")

        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的数字")

    def clear_all_logs(self):
        """清空所有日志"""
        if messagebox.askyesno("确认清空", "确定要清空所有代理请求日志吗？\n此操作不可恢复！"):
            try:
                deleted_count = self.db_manager.clear_all_proxy_request_logs()
                messagebox.showinfo("清空完成", f"已清空所有日志记录，共 {deleted_count} 条")
                self.refresh_data()
            except Exception as e:
                messagebox.showerror("清空失败", f"清空日志时发生错误: {e}")

    def export_logs(self):
        """导出日志"""
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime

            # 选择保存文件
            file_path = filedialog.asksaveasfilename(
                title="导出日志",
                defaultextension=".csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )

            if not file_path:
                return

            # 获取所有日志数据
            logs_data = self.db_manager.get_proxy_request_logs_for_export(
                status_filter=self.status_filter_var.get() if self.status_filter_var.get() != "全部" else None
            )

            if not logs_data:
                messagebox.showinfo("无数据", "没有可导出的日志数据")
                return

            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['时间', '状态', '响应类型', '状态码', '耗时(ms)', '模型', 'Key', '方法', '端点', '重试次数', '错误信息']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for log in logs_data:
                    # 格式化时间显示
                    timestamp = log['request_timestamp']
                    formatted_time = timestamp
                    if timestamp:
                        try:
                            # 直接解析为本地时间，不带时区转换
                            if timestamp.endswith('Z'):
                                # 如果是UTC时间，转换为本地时间显示
                                dt = datetime.fromisoformat(timestamp[:-1]).astimezone()
                            else:
                                # 已经是有时区信息的时间，直接使用
                                dt = datetime.fromisoformat(timestamp)
                            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            formatted_time = timestamp[:19] if len(timestamp) >= 19 else timestamp

                    writer.writerow({
                        '时间': formatted_time,
                        '状态': log['status'],
                        '响应类型': log['response_type'],
                        '状态码': log['status_code'],
                        '耗时(ms)': log['duration_ms'],
                        '模型': log['model'],
                        'Key': log['token_value'],
                        '方法': log['method'],
                        '端点': log['endpoint'],
                        '重试次数': log['retry_count'],
                        '错误信息': log['error_message'] or ''
                    })

            messagebox.showinfo("导出完成", f"日志已导出到:\n{file_path}\n共 {len(logs_data)} 条记录")

        except Exception as e:
            messagebox.showerror("导出失败", f"导出日志时发生错误: {e}")

    def on_left_click(self, event):
        """左键点击选中处理"""
        # 获取点击位置的项
        item = self.logs_tree.identify_row(event.y)
        if item:
            # 检查是否按住了Ctrl键（多选）
            if event.state & 0x0004:  # Ctrl键被按下
                # 切换选中状态
                if item in self.logs_tree.selection():
                    self.logs_tree.selection_remove(item)
                else:
                    self.logs_tree.selection_set(item)
            elif event.state & 0x0001:  # Shift键被按下
                # Shift多选逻辑
                current_selection = self.logs_tree.selection()
                if current_selection:
                    # 获取当前选中项的索引
                    last_item = current_selection[-1]
                    try:
                        last_index = self.logs_tree.index(last_item)
                        current_index = self.logs_tree.index(item)

                        # 选择范围内的所有项
                        start_idx = min(last_index, current_index)
                        end_idx = max(last_index, current_index)

                        # 清除现有选中
                        self.logs_tree.selection_remove(self.logs_tree.selection())

                        # 选中范围内的所有项
                        for i in range(start_idx, end_idx + 1):
                            tree_item = self.logs_tree.get_children()[i]
                            self.logs_tree.selection_set(tree_item)
                    except (ValueError, IndexError):
                        # 如果索引获取失败，只选中当前项
                        self.logs_tree.selection_remove(self.logs_tree.selection())
                        self.logs_tree.selection_set(item)
                else:
                    # 没有当前选中，直接选中当前项
                    self.logs_tree.selection_set(item)
            else:
                # 普通点击，只选中当前项
                self.logs_tree.selection_remove(self.logs_tree.selection())
                self.logs_tree.selection_set(item)

    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击位置的项
        clicked_item = self.logs_tree.identify_row(event.y)
        selected_items = self.logs_tree.selection()

        if not clicked_item:
            # 如果点击在空白区域，检查是否有选中项
            if not selected_items:
                return
        else:
            # 如果点击了项目，且该项目未被选中，则只选中点击的项目
            if clicked_item not in selected_items:
                self.logs_tree.selection_remove(self.logs_tree.selection())
                self.logs_tree.selection_set(clicked_item)
                selected_items = [clicked_item]

        # 创建右键菜单
        context_menu = tk.Menu(self.dialog, tearoff=0)

        # 复制功能
        copy_menu = tk.Menu(context_menu, tearoff=0)
        context_menu.add_cascade(label="复制", menu=copy_menu)
        copy_menu.add_command(label="复制选中行", command=lambda: self.copy_selected_rows())
        copy_menu.add_command(label="复制选中Key", command=lambda: self.copy_selected_field("Key"))
        copy_menu.add_command(label="复制选中端点", command=lambda: self.copy_selected_field("端点"))
        copy_menu.add_command(label="复制选中模型", command=lambda: self.copy_selected_field("模型"))

        # 导出选中项
        context_menu.add_separator()
        context_menu.add_command(label="导出选中记录", command=lambda: self.export_selected_logs())

        # 删除功能
        context_menu.add_separator()
        if len(selected_items) == 1:
            context_menu.add_command(label="删除此记录", command=lambda: self.delete_log_records(selected_items))
        else:
            context_menu.add_command(label=f"删除选中记录 ({len(selected_items)}条)", command=lambda: self.delete_log_records(selected_items))

        # 显示菜单
        context_menu.post(event.x_root, event.y_root)

    def copy_selected_rows(self):
        """复制选中行的数据"""
        try:
            selected_items = self.logs_tree.selection()
            if not selected_items:
                messagebox.showwarning("无选中项", "请先选择要复制的日志记录")
                return

            all_data = []
            headers = ["时间", "状态", "响应类型", "状态码", "耗时(ms)", "模型", "Key", "方法", "端点"]

            for item in selected_items:
                values = self.logs_tree.item(item, 'values')
                if values and len(values) >= 9:  # 忽略最后面的ID字段
                    display_values = values[:9]  # 只取前9个显示字段
                    # 将每行数据格式化为制表符分隔的文本
                    row_text = "\t".join(f"{header}: {value}" for header, value in zip(headers, display_values))
                    all_data.append(row_text)

            if all_data:
                # 合并所有行数据，每行用换行符分隔
                combined_data = "\n\n".join(all_data)
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(combined_data)
                messagebox.showinfo("复制成功", f"已复制 {len(selected_items)} 条记录到剪贴板")

        except Exception as e:
            messagebox.showerror("复制失败", f"复制数据时发生错误: {e}")

    def copy_selected_field(self, field_name):
        """复制选中项的指定字段"""
        try:
            selected_items = self.logs_tree.selection()
            if not selected_items:
                messagebox.showwarning("无选中项", "请先选择要复制的日志记录")
                return

            # 字段索引映射（注意：现在values包含10个字段，第10个是ID）
            field_index = {
                "Key": 6,
                "端点": 8,
                "模型": 5
            }.get(field_name)

            if field_index is None:
                messagebox.showerror("字段错误", f"不支持的复制字段: {field_name}")
                return

            all_values = []
            for item in selected_items:
                values = self.logs_tree.item(item, 'values')
                if values and len(values) >= 9 and field_index < 9:  # 确保索引在显示字段范围内
                    field_value = values[field_index]
                    all_values.append(str(field_value))

            if all_values:
                # 合并所有值，每行一个
                combined_values = "\n".join(all_values)
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(combined_values)
                messagebox.showinfo("复制成功", f"已复制 {len(all_values)} 个{field_name}到剪贴板")

        except Exception as e:
            messagebox.showerror("复制失败", f"复制{field_name}时发生错误: {e}")

    def export_selected_logs(self):
        """导出选中的日志记录"""
        try:
            selected_items = self.logs_tree.selection()
            if not selected_items:
                messagebox.showwarning("无选中项", "请先选择要导出的日志记录")
                return

            from tkinter import filedialog
            import csv

            # 选择保存文件
            file_path = filedialog.asksaveasfilename(
                title="导出选中日志",
                defaultextension=".csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )

            if not file_path:
                return

            # 获取选中项的数据
            export_data = []
            headers = ["时间", "状态", "响应类型", "状态码", "耗时(ms)", "模型", "Key", "方法", "端点"]

            for item in selected_items:
                values = self.logs_tree.item(item, 'values')
                if values and len(values) >= 9:  # 忽略ID字段
                    display_values = values[:9]  # 只取前9个显示字段
                    export_data.append(dict(zip(headers, display_values)))

            if not export_data:
                messagebox.showinfo("无数据", "选中的记录没有有效数据")
                return

            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = headers
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row_data in export_data:
                    writer.writerow(row_data)

            messagebox.showinfo("导出完成", f"选中记录已导出到:\n{file_path}\n共 {len(export_data)} 条记录")

        except Exception as e:
            messagebox.showerror("导出失败", f"导出选中记录时发生错误: {e}")

    def delete_log_records(self, items):
        """删除选中的日志记录"""
        try:
            if not items:
                return

            # 提取选中项的数据库ID
            log_ids = []
            display_info = []

            for item in items:
                values = self.logs_tree.item(item, 'values')
                if values and len(values) > 9:  # 前面9个是显示字段，第10个是ID
                    log_id = values[9]  # ID是第10个字段
                    if log_id:
                        log_ids.append(int(log_id))
                        # 收集显示信息用于确认
                        display_info.append(f"时间: {values[0]}, Key: {values[6]}, 端点: {values[8]}")

            if not log_ids:
                messagebox.showwarning("无法删除", "选中的记录没有有效的ID信息")
                return

            # 构建确认消息
            if len(log_ids) == 1:
                confirm_msg = f"确定要删除以下日志记录吗？\n\n{display_info[0]}\n\n此操作不可恢复！"
            else:
                confirm_msg = f"确定要删除选中的 {len(log_ids)} 条日志记录吗？\n\n此操作不可恢复！"

            if messagebox.askyesno("确认删除", confirm_msg):
                # 直接通过ID删除，100%可靠
                try:
                    deleted_count = self.db_manager.delete_proxy_request_logs_by_ids(log_ids)

                    if deleted_count > 0:
                        messagebox.showinfo("删除成功", f"已成功删除 {deleted_count} 条记录")
                        self.refresh_data()
                    else:
                        messagebox.showwarning("删除失败", "未找到匹配的记录或删除失败")

                except Exception as e:
                    messagebox.showerror("删除失败", f"删除记录时发生错误: {e}")

        except Exception as e:
            messagebox.showerror("删除失败", f"删除记录时发生错误: {e}")