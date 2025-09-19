"""
轻量级API代理服务器
实现轮询使用多个API key的功能
"""

import threading
import time
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib
import queue
import uuid

from database_manager import DatabaseManager
from config_manager import ConfigManager


class KeyPool:
    """智能API密钥池管理器 - 按状态和余额类型分类管理密钥"""

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.logger = logging.getLogger("KeyPool")

        # 按状态分类的密钥池
        self.key_pools = {
            "non_blacklist": [],      # 非黑名单（有效的和充值余额的）
            "available_balance": [],   # 可用余额
            "gift_balance": [],        # 赠金
            "unavailable_balance": []  # 不可用余额
        }

        # 密钥状态管理
        self.key_status = {}  # key_id -> status_info
        self.key_usage = {}    # key_id -> usage_info

        # 重试计数
        self.small_retry_counts = {}    # key_id -> small_retry_count
        self.max_small_retries = self.config_manager.get_proxy_max_small_retries()

        # 防抖机制
        self.last_used_key = None
        self.last_used_time = 0
        self.key_debounce_interval = self.config_manager.get_proxy_key_debounce_interval()

        # 当前选择的池子类型（用户配置）
        self.current_pool_type = self.config_manager.get_proxy_pool_type()

        # 大重试次数配置
        self.max_big_retries = self.config_manager.get_proxy_max_big_retries()

        # 线程安全
        self.lock = threading.Lock()

        # 初始化密钥池
        self._load_keys_from_db()

    def _load_keys_from_db(self):
        """从数据库加载所有有效的密钥并分类"""
        try:
            with self.lock:
                # 清空现有池子
                for pool_name in self.key_pools:
                    self.key_pools[pool_name] = []

                self.key_status.clear()
                self.key_usage.clear()
                self.small_retry_counts.clear()

                # 获取所有有效的密钥
                valid_statuses = ["pending", "valid", "low_balance", "charge_balance"]
                all_keys = []

                for status in valid_statuses:
                    keys = self.db_manager.get_tokens_by_status(status)
                    all_keys.extend(keys)

                # 按规则分类
                for key in all_keys:
                    self._classify_and_add_key(key)

                # 按ID排序确保一致性
                for pool_name in self.key_pools:
                    self.key_pools[pool_name].sort(key=lambda x: x['id'])

                self.logger.info(f"密钥池重新加载完成:")
                for pool_name, keys in self.key_pools.items():
                    self.logger.info(f"  {pool_name}: {len(keys)} 个密钥")

        except Exception as e:
            self.logger.error(f"从数据库加载密钥失败: {e}")

    def _classify_and_add_key(self, key: Dict):
        """根据状态和余额类型分类密钥"""
        key_id = key['id']
        status = key['status']
        total_balance = key.get('total_balance', 0) or 0
        charge_balance = key.get('charge_balance', 0) or 0
        gift_balance = total_balance - charge_balance

        # 初始化密钥状态
        self.key_status[key_id] = {
            'status': status,
            'total_balance': total_balance,
            'charge_balance': charge_balance,
            'gift_balance': gift_balance
        }

        # 初始化使用信息
        self.key_usage[key_id] = {
            'last_used': 0,
            'success_count': 0,
            'failure_count': 0
        }

        # 初始化小重试计数
        self.small_retry_counts[key_id] = 0

        # 分类规则
        # 1. 非黑名单池子：有效的和充值余额的
        if status in ["valid", "charge_balance"] or (status == "low_balance" and charge_balance > 0):
            self.key_pools["non_blacklist"].append(key)

        # 2. 可用余额池子：有可用余额的
        if total_balance > 0:
            self.key_pools["available_balance"].append(key)

        # 3. 赠金池子：有赠金的
        if gift_balance > 0:
            self.key_pools["gift_balance"].append(key)

        # 4. 不可用余额池子：无余额或余额不足
        if total_balance <= 0:
            self.key_pools["unavailable_balance"].append(key)

    def get_current_pool(self) -> List[Dict]:
        """获取当前选择的池子"""
        return self.key_pools.get(self.current_pool_type, [])

    def set_pool_type(self, pool_type: str):
        """设置当前使用的池子类型"""
        if pool_type in self.key_pools:
            self.current_pool_type = pool_type
            self.config_manager.set("proxy.pool_type", pool_type)
            self.logger.info(f"切换到池子类型: {pool_type}")
        else:
            self.logger.error(f"不支持的池子类型: {pool_type}")

    def get_next_key(self, force_change: bool = False) -> Optional[Dict]:
        """智能获取下一个可用的密钥（防抖机制）"""
        current_time = time.time()
        is_debounce_switch = False

        with self.lock:
            # 检查是否在防抖时间内，且不强制更换
            if not force_change and self.last_used_key:
                time_diff = current_time - self.last_used_time
                if time_diff < self.key_debounce_interval:
                    # 在防抖时间内，继续使用上次的密钥
                    key_id = self.last_used_key['id']
                    current_pool = self.get_current_pool()
                    last_key = next((k for k in current_pool if k['id'] == key_id), None)

                    if last_key:
                        self.logger.info(f"防抖机制：继续使用上次密钥 ID: {key_id} (间隔: {time_diff:.1f}s)")
                        # 标记这不是防抖切换
                        result_key = last_key.copy()
                        result_key['_is_debounce_switch'] = False
                        return result_key
                    else:
                        self.logger.warning(f"上次使用的密钥 {key_id} 已不在当前池子中")

            # 获取当前池子的密钥列表
            current_pool = self.get_current_pool()

            if not current_pool:
                self.logger.error(f"当前池子类型 '{self.current_pool_type}' 为空")
                return None

            # 防抖时间已过或强制更换，选择新密钥
            if not force_change and self.last_used_key:
                # 防抖时间已过，这是正常的防抖切换
                time_diff = current_time - self.last_used_time
                if time_diff >= self.key_debounce_interval:
                    is_debounce_switch = True
                    self.logger.info(f"防抖时间已过 ({time_diff:.1f}s >= {self.key_debounce_interval}s)，将切换密钥")

            # 选择新密钥
            selected_key = self._select_key_randomly(current_pool)

            if selected_key:
                self.last_used_key = selected_key
                self.last_used_time = current_time
                key_id = selected_key['id']

                # 标记是否是防抖切换
                result_key = selected_key.copy()
                result_key['_is_debounce_switch'] = is_debounce_switch

                switch_info = "防抖切换" if is_debounce_switch else "首次选择"
                self.logger.info(f"选择密钥 ID: {key_id}, 池子类型: {self.current_pool_type}, {switch_info}, 防抖时间: {self.key_debounce_interval}s")
                return result_key
            else:
                self.logger.error("无法选择密钥")
                return None

    def _select_key_randomly(self, keys: List[Dict]) -> Optional[Dict]:
        """从密钥列表中随机选择一个密钥"""
        if not keys:
            return None

        import random
        return random.choice(keys)

    def retry_with_same_key(self) -> Optional[Dict]:
        """小重试：使用同一个密钥重试"""
        if not self.last_used_key:
            self.logger.warning("没有上次使用的密钥，无法进行小重试")
            return None

        key_id = self.last_used_key['id']

        with self.lock:
            self.small_retry_counts[key_id] += 1
            retry_count = self.small_retry_counts[key_id]

            if retry_count <= self.max_small_retries:
                self.logger.info(f"小重试 #{retry_count}: 使用密钥 ID: {key_id}")
                return self.last_used_key
            else:
                # 小重试次数用完，重置计数器
                self.small_retry_counts[key_id] = 0
                self.logger.warning(f"小重试次数已用完 ({self.max_small_retries}次)，将进行大重试")
                return None

    def retry_with_new_key(self, is_debounce_switch: bool = False) -> Optional[Dict]:
        """大重试：更换密钥重试"""
        if is_debounce_switch:
            self.logger.info("大重试：防抖时间切换密钥")
        else:
            self.logger.info("大重试：失败后更换密钥")

        # 清除最后一次使用的密钥记录，强制选择新密钥
        with self.lock:
            self.last_used_key = None
            self.last_used_time = 0

        result = self.get_next_key(force_change=True)
        if result:
            # 标记这次是否是防抖切换
            result['_is_debounce_switch'] = is_debounce_switch
        return result

    def mark_key_success(self, key_id: int):
        """标记密钥使用成功"""
        with self.lock:
            # 重置小重试计数
            self.small_retry_counts[key_id] = 0

            # 更新使用统计
            if key_id in self.key_usage:
                self.key_usage[key_id]['success_count'] += 1
                self.key_usage[key_id]['last_used'] = time.time()

        self.logger.info(f"密钥 {key_id} 使用成功，重置重试计数")

    def mark_key_failure(self, key_id: int, error_message: str = ""):
        """标记密钥使用失败（仅记录日志）"""
        with self.lock:
            # 更新使用统计
            if key_id in self.key_usage:
                self.key_usage[key_id]['failure_count'] += 1

        self.logger.info(f"密钥 {key_id} 使用失败，错误: {error_message}")





    def refresh_keys(self):
        """刷新密钥池（重新从数据库加载）"""
        self._load_keys_from_db()
        self.logger.info("密钥池已刷新")

    def get_pool_status(self) -> Dict:
        """获取密钥池状态"""
        with self.lock:
            status = {
                "current_pool_type": self.current_pool_type,
                "pool_sizes": {name: len(keys) for name, keys in self.key_pools.items()},
                "last_used_key": self.last_used_key['id'] if self.last_used_key else None,
                "last_used_time": self.last_used_time,
                "key_debounce_interval": self.key_debounce_interval,
                "max_small_retries": self.max_small_retries,
                "small_retry_counts": dict(self.small_retry_counts)
            }

            # 添加池子详情
            for pool_name, keys in self.key_pools.items():
                if keys:
                    status[f"{pool_name}_details"] = [{
                        "id": key["id"],
                        "status": key.get("status", "unknown"),
                        "total_balance": key.get("total_balance", 0),
                        "charge_balance": key.get("charge_balance", 0)
                    } for key in keys[:5]]  # 只显示前5个

            return status

    def get_key_usage_stats(self, key_id: int) -> Optional[Dict]:
        """获取特定密钥的使用统计"""
        with self.lock:
            if key_id in self.key_usage:
                usage_info = self.key_usage[key_id].copy()
                status_info = self.key_status.get(key_id, {})
                retry_count = self.small_retry_counts.get(key_id, 0)

                return {
                    "key_id": key_id,
                    "status": status_info,
                    "usage": usage_info,
                    "small_retry_count": retry_count
                }
            return None

    def refresh_keys(self):
        """刷新密钥池（重新从数据库加载）"""
        self._load_keys_from_db()
        self.logger.info("密钥池已刷新")

    def get_pool_status(self) -> Dict:
        """获取密钥池状态"""
        return {
            "total_keys": len(self.active_keys),
            "current_index": self.current_key_index,
            "failure_counts": dict(self.key_failure_counts)
        }


class RequestLog:
    """增强请求日志记录 - 包含详细key信息和使用状态"""

    def __init__(self, db_manager: DatabaseManager, key_pool: KeyPool):
        self.db_manager = db_manager
        self.key_pool = key_pool
        self.logger = logging.getLogger("RequestLog")

    def log_request(self, key_id: int, endpoint: str, method: str,
                   status_code: int, duration: float, success: bool,
                   error_message: str = "", retry_count: int = 0,
                   retry_type: str = "initial", model: str = None,
                   response_type: str = "普通响应", request_data: str = None,
                   response_size: int = None, token_value: str = None):
        """记录增强的请求日志（控制台 + 数据库）"""
        try:
            # 获取key的详细状态信息
            key_usage_stats = self.key_pool.get_key_usage_stats(key_id)
            key_status_info = "unknown"
            balance_info = "unknown"

            if key_usage_stats:
                status_data = key_usage_stats.get('status', {})
                usage_data = key_usage_stats.get('usage', {})
                retry_count_total = key_usage_stats.get('small_retry_count', 0)

                key_status_info = status_data.get('status', 'unknown')
                total_balance = status_data.get('total_balance', 0)
                charge_balance = status_data.get('charge_balance', 0)
                gift_balance = status_data.get('gift_balance', 0)
                success_count = usage_data.get('success_count', 0)
                failure_count = usage_data.get('failure_count', 0)

                balance_info = f"总:{total_balance},充:{charge_balance},赠:{gift_balance}"
                usage_summary = f"成:{success_count},败:{failure_count},小重:{retry_count_total}"
            else:
                usage_summary = "未知"

            # 构建详细的日志数据（控制台输出）
            log_data = {
                "key_id": key_id,
                "key_status": key_status_info,
                "balance_info": balance_info,
                "usage_summary": usage_summary,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": int(duration * 1000),
                "success": success,
                "retry_count": retry_count,
                "retry_type": retry_type,
                "error_message": error_message,
                "timestamp": datetime.now().astimezone().isoformat()
            }

            # 构建易于阅读的日志消息
            status_indicator = "✅" if success else "❌"
            retry_indicator = f"[{retry_type}#{retry_count}]" if retry_count > 0 else "[初始]"

            log_message = (
                f"{status_indicator} Key[{key_id}] {key_status_info} | "
                f"{method} {endpoint} | "
                f"状态:{status_code} | "
                f"耗时:{duration*1000:.1f}ms | "
                f"{retry_indicator} | "
                f"余额:{balance_info} | "
                f"统计:{usage_summary}"
            )

            if error_message:
                log_message += f" | 错误:{error_message[:100]}..." if len(error_message) > 100 else f" | 错误:{error_message}"

            # 记录到控制台日志
            self.logger.info(log_message)

            # 记录到数据库
            try:
                # 确定状态文本
                if success:
                    status_text = "成功"
                elif retry_count > 0 and retry_type == "initial":
                    status_text = "请求中"  # 如果是第一次失败但会重试，算作请求中
                else:
                    status_text = "失败"

                # 记录到数据库
                self.db_manager.add_proxy_request_log(
                    key_id=key_id,
                    token_value=token_value or f"Key[{key_id}]",
                    endpoint=endpoint,
                    method=method,
                    status=status_text,
                    response_type=response_type,
                    status_code=status_code,
                    duration_ms=int(duration * 1000),
                    model=model,
                    error_message=error_message,
                    retry_count=retry_count,
                    retry_type=retry_type,
                    request_data=request_data,
                    response_size=response_size
                )
            except Exception as db_error:
                self.logger.error(f"记录数据库日志失败: {db_error}")

            # 如果失败率较高，发出警告
            if key_usage_stats and not success:
                usage_data = key_usage_stats.get('usage', {})
                success_count = usage_data.get('success_count', 0)
                failure_count = usage_data.get('failure_count', 0)
                total = success_count + failure_count

                if total >= 3 and failure_count / total > 0.5:
                    self.logger.warning(f"🔥 Key[{key_id}] 失败率偏高的提示: {failure_count}/{total} ({failure_count/total:.1%})")

        except Exception as e:
            self.logger.error(f"记录请求日志失败: {e}")

    def log_key_pool_status(self, title: str = "密钥池状态"):
        """记录密钥池状态概览"""
        try:
            pool_status = self.key_pool.get_pool_status()

            current_pool_type = pool_status.get("current_pool_type", "unknown")
            pool_sizes = pool_status.get("pool_sizes", {})
            last_used_key = pool_status.get("last_used_key")
            last_used_time = pool_status.get("last_used_time", 0)
            debounce_interval = self.key_debounce_interval

            # 计算最后使用时间间隔
            time_diff = time.time() - last_used_time if last_used_time > 0 else 0
            time_info = f"{time_diff:.1f}s前" if last_used_time > 0 else "从未使用"

            status_message = f"📊 {title}\n"
            status_message += f"   当前池子: {current_pool_type}\n"
            status_message += f"   池子大小: {pool_sizes}\n"
            status_message += f"   最后使用的Key: {last_used_key or '无'} ({time_info})\n"
            status_message += f"   防抖间隔: {debounce_interval}s"

            self.logger.info(status_message)

        except Exception as e:
            self.logger.error(f"记录密钥池状态失败: {e}")

    def log_retry_event(self, key_id: int, retry_type: str, retry_count: int,
                       max_allowed: int, success: bool = False):
        """记录重试事件"""
        try:
            if success:
                icon = "✅"
                message = f"{icon} Key[{key_id}] {retry_type} 第{retry_count}次尝试成功"
            else:
                icon = "🔄"
                message = f"{icon} Key[{key_id}] {retry_type} 第{retry_count}次尝试 (最多{max_allowed}次)"

            self.logger.info(message)

        except Exception as e:
            self.logger.error(f"记录重试事件失败: {e}")


class ProxyServer:
    """轻量级API代理服务器"""

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.logger = self._setup_logger()

        # 初始化组件
        self.key_pool = KeyPool(db_manager, config_manager)
        self.request_log = RequestLog(db_manager, self.key_pool)

        # 服务器状态
        self.is_running = False
        self.server_thread = None
        self.port = self.config_manager.get_proxy_port()

        # 请求队列（用于异步处理）
        self.request_queue = queue.Queue()

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "start_time": datetime.now()
        }

    def _parse_api_error(self, status_code: int, response_text: str) -> str:
        """解析上游API错误信息，根据xy.md格式规范"""
        try:
            # 根据参考文件xy.md的格式规范解析错误
            if status_code in [400, 429, 503]:
                # 这些状态码返回JSON格式: {"message": "<string>"}
                try:
                    error_data = json.loads(response_text)
                    if isinstance(error_data, dict) and 'message' in error_data:
                        # 返回格式: {错误码}: {message内容}
                        return f"{{{status_code}: {error_data['message']}}}"
                    else:
                        # 格式不符合预期，显示原始内容
                        return f"{{{status_code}: {response_text[:500]}}}"
                except json.JSONDecodeError:
                    # JSON解析失败，显示原始内容
                    return f"{{{status_code}: {response_text[:500]}}}"

            elif status_code in [401, 404, 504]:
                # 这些状态码返回字符串格式: "string"
                if len(response_text.strip()) > 0:
                    # 如果有内容，显示前500个字符
                    error_content = response_text.strip()
                    if len(error_content) > 500:
                        error_content = error_content[:500] + "..."
                    return f"{{{status_code}: {error_content}}}"
                else:
                    return f"{{{status_code}: 空错误响应}}"

            else:
                # 其他状态码，显示原始响应内容前500个字符
                error_content = response_text.strip()
                if len(error_content) > 500:
                    error_content = error_content[:500] + "..."
                return f"{{{status_code}: {error_content}}}"

        except Exception as e:
            # 解析异常，记录并返回原始错误
            self.logger.error(f"解析API错误信息时发生异常: {e}")
            return f"{{{status_code}: 解析失败 - {response_text[:200] if response_text else '空响应'}}}"

    def _extract_model_info(self, request_data: bytes) -> str:
        """从请求数据中提取模型信息"""
        try:
            if request_data:
                # 尝试解析JSON数据
                data_str = request_data.decode('utf-8')
                try:
                    data_json = json.loads(data_str)
                    return data_json.get('model', '未知模型')
                except json.JSONDecodeError:
                    return '非JSON请求'
            return None
        except Exception:
            return None

    def _detect_response_type(self, request_data: bytes) -> str:
        """检测响应类型（流式或普通）"""
        try:
            if request_data:
                data_str = request_data.decode('utf-8')
                data_json = json.loads(data_str)
                # 检查是否有stream参数
                if data_json.get('stream', False):
                    return '流式响应'
            return '普通响应'
        except Exception:
            return '普通响应'

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("ProxyServer")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def start(self, port: int = None) -> bool:
        """启动代理服务器"""
        if self.is_running:
            self.logger.warning("代理服务器已在运行中")
            return False

        if port:
            self.port = port

        try:
            # 导入Flask（延迟导入，避免依赖问题）
            from flask import Flask, request, jsonify, Response
            import requests

            self.app = Flask(__name__)

            # 注册路由
            self._register_routes()

            # 确保路由已注册
            self.logger.info(f"已注册路由: {[rule.rule for rule in self.app.url_map.iter_rules()]}")

            # 在后台线程启动服务器
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.is_running = True
            self.server_thread.start()

            self.logger.info(f"代理服务器已启动，监听端口 {self.port}")
            return True

        except ImportError as e:
            self.logger.error(f"缺少依赖包: {e}")
            self.logger.error("请安装Flask: pip install flask")
            return False
        except Exception as e:
            self.logger.error(f"启动代理服务器失败: {e}")
            self.is_running = False
            return False

    def _run_server(self):
        """运行Flask服务器"""
        try:
            self.app.run(
                host='0.0.0.0',
                port=self.port,
                debug=False,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"服务器运行错误: {e}")
            self.is_running = False

    def _register_routes(self):
        """注册路由"""
        # 代理所有请求
        @self.app.route('/proxy/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
        def proxy_request(path):
            return self._handle_proxy_request(path)

        # 健康检查
        @self.app.route('/health')
        def health_check():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().astimezone().isoformat(),
                "stats": self.get_stats()
            })

        # 状态信息
        @self.app.route('/status')
        def status():
            # 记录密钥池状态到日志
            self.request_log.log_key_pool_status("代理服务器状态查询")
            return jsonify({
                "running": self.is_running,
                "port": self.port,
                "key_pool": self.key_pool.get_pool_status(),
                "stats": self.get_stats()
            })

        # 设置池子类型
        @self.app.route('/set_pool_type/<pool_type>', methods=['POST'])
        def set_pool_type(pool_type):
            result = self.key_pool.set_pool_type(pool_type)
            return jsonify({
                "success": result,
                "current_pool_type": pool_type,
                "message": f"池子类型已设置为: {pool_type}" if result else f"无效的池子类型: {pool_type}"
            })

        # 获取池子类型信息
        @self.app.route('/pool_info')
        def pool_info():
            return jsonify({
                "available_pool_types": list(self.key_pool.key_pools.keys()),
                "current_pool_type": self.key_pool.current_pool_type,
                "pool_sizes": {name: len(keys) for name, keys in self.key_pool.key_pools.items()},
                "config": {
                    "key_debounce_interval": self.key_pool.key_debounce_interval,
                    "max_small_retries": self.key_pool.max_small_retries
                }
            })

    def _handle_proxy_request(self, path: str):
        """处理代理请求（支持双重重试逻辑）"""
        from flask import request, Response, jsonify
        import requests
        import time

        self.logger.info(f"收到代理请求，路径: {path}")

        start_time = time.time()
        retry_count = 0
        # 计算最大总尝试次数
        # 初始尝试 + (每次大重试包含小重试次数 + 1次换密钥后尝试) * 大重试次数
        max_small_retries = self.key_pool.max_small_retries
        max_big_retries = self.key_pool.max_big_retries
        # 最大总尝试次数 = 1(初始) + 大重试次数 * (小重试次数 + 1)
        max_total_attempts = 1 + max_big_retries * (max_small_retries + 1)

        self.logger.info(f"重试配置: 小重试{max_small_retries}次, 大重试{max_big_retries}次, 最大总尝试次数{max_total_attempts}次")

        # 初始化变量用于日志记录
        current_key_id = None
        current_key_value = None
        current_model = None
        current_response_type = None
        current_request_data = None

        # 智能重试循环
        while retry_count <= max_total_attempts:
            retry_count += 1
            self.logger.info(f"第 {retry_count} 次尝试")

            # 获取当前使用的密钥
            if retry_count == 1:
                # 第一次请求，正常获取密钥
                api_key = self.key_pool.get_next_key()
            else:
                # 检查是否需要小重试
                small_retry_key = self.key_pool.retry_with_same_key()
                if small_retry_key:
                    api_key = small_retry_key
                    self.logger.info(f"执行小重试，使用同一密钥 ID: {api_key['id']}")
                else:
                    # 小重试失败或用完，执行大重试
                    api_key = self.key_pool.retry_with_new_key()
                    if not api_key:
                        self.logger.error("大重试失败，没有可用的备用密钥")
                        break
                    self.logger.info(f"执行大重试，切换到新密钥 ID: {api_key['id']}")

            if not api_key:
                self.logger.error("没有可用的API密钥")
                return jsonify({"error": "No available API keys"}), 503

            current_key_id = api_key['id']
            current_key_value = api_key['token_value']
            key_id = current_key_id
            key_value = current_key_value

            # 构建目标URL（使用SiliconFlow API）
            target_url = f"https://api.siliconflow.cn/v1/{path}"

            # 复制请求头
            headers = dict(request.headers)
            # 替换Authorization头
            headers['Authorization'] = f"Bearer {key_value}"
            # 移除可能冲突的头部
            headers.pop('Host', None)
            headers.pop('Content-Length', None)

            # 获取请求数据
            method = request.method
            data = request.get_data()

            # 提取额外信息用于日志记录
            current_model = self._extract_model_info(data)
            current_response_type = self._detect_response_type(data)
            current_request_data = data.decode('utf-8', errors='ignore')[:500] if data else None
            model = current_model
            response_type = current_response_type
            request_data_str = current_request_data

            # 只显示API密钥的前12位，保护密钥安全
            key_display = key_value[:12] if len(key_value) > 12 else key_value
            self.logger.info(f"代理请求: {method} {target_url} 使用密钥: {key_display} (尝试 #{retry_count})")

            try:
                # 发送请求到上游API
                response = requests.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    data=data,
                    # 使用新的超时配置（分钟转换为秒）
                    timeout=self.config_manager.get_proxy_request_timeout_minutes() * 60,
                    stream=True  # 支持流式响应
                )

                # 检查HTTP响应状态码
                if response.status_code >= 400:
                    # HTTP错误，解析详细错误信息
                    error_msg = self._parse_api_error(response.status_code, response.text)
                    self.logger.warning(f"HTTP错误，状态码: {response.status_code}，详细错误: {error_msg}")

                    # 检查这次尝试是否是防抖切换，防抖切换不算作失败
                    is_debounce_switch = api_key.get('_is_debounce_switch', False)
                    if not is_debounce_switch:
                        self.key_pool.mark_key_failure(key_id, error_msg)
                    else:
                        self.logger.info(f"这是防抖切换，不记录为密钥失败")
                    continue  # 继续重试

                # 成功响应
                self.key_pool.mark_key_success(key_id)
                self.stats["successful_requests"] += 1
                self.stats["total_requests"] += 1

                # 计算耗时
                duration = time.time() - start_time

                # 记录请求日志
                self.request_log.log_request(
                    key_id=key_id,
                    endpoint=target_url,
                    method=method,
                    status_code=response.status_code,
                    duration=duration,
                    success=True,
                    model=model,
                    response_type=response_type,
                    request_data=request_data_str,
                    response_size=len(response.content) if response.content else None,
                    token_value=key_value
                )

                # 只显示API密钥的前12位，保护密钥安全
                key_display = key_value[:12] if len(key_value) > 12 else key_value
                self.logger.info(f"请求成功，使用密钥: {key_display}，状态码: {response.status_code}，耗时: {duration:.2f}s")

                # 返回响应
                return Response(
                    response.iter_content(chunk_size=1024),
                    status=response.status_code,
                    headers=dict(response.headers)
                )

            except requests.exceptions.RequestException as e:
                # 网络或请求异常
                error_msg = f"请求异常: {str(e)}"
                self.logger.warning(f"请求异常: {error_msg}")

                # 检查这次尝试是否是防抖切换，防抖切换不算作失败
                is_debounce_switch = api_key.get('_is_debounce_switch', False)
                if not is_debounce_switch:
                    self.key_pool.mark_key_failure(key_id, error_msg)
                else:
                    self.logger.info(f"这是防抖切换，不记录为密钥失败")
                continue  # 继续重试

            except Exception as e:
                # 其他异常
                error_msg = f"未知异常: {str(e)}"
                self.logger.error(f"未知异常: {error_msg}", exc_info=True)

                # 检查这次尝试是否是防抖切换，防抖切换不算作失败
                is_debounce_switch = api_key.get('_is_debounce_switch', False)
                if not is_debounce_switch:
                    self.key_pool.mark_key_failure(key_id, error_msg)
                else:
                    self.logger.info(f"这是防抖切换，不记录为密钥失败")
                continue  # 继续重试

        # 所有重试都失败了
        self.stats["failed_requests"] += 1
        self.stats["total_requests"] += 1

        duration = time.time() - start_time

        error_msg = f"所有重试都失败了 (共 {retry_count-1} 次)"
        self.logger.error(error_msg)

        # 记录最终失败
        if current_key_id:
            last_api_key = getattr(self.key_pool, 'last_used_key', None)
            retry_type = "initial" if retry_count == 1 else ("small_retry" if last_api_key and 'id' in last_api_key and last_api_key['id'] == current_key_id else "big_retry")

            self.request_log.log_request(
                key_id=current_key_id,
                endpoint=target_url if 'target_url' in locals() else "unknown",
                method=method if 'method' in locals() else "unknown",
                status_code=500,
                duration=duration,
                success=False,
                error_message=error_msg,
                retry_count=retry_count - 1,
                retry_type=retry_type,
                model=current_model,
                response_type=current_response_type,
                request_data=current_request_data,
                token_value=current_key_value
            )

        return jsonify({
            "error": error_msg,
            "retry_attempts": retry_count - 1,
            "max_small_retries": max_small_retries,
            "max_big_retries": max_big_retries,
            "max_total_attempts": max_total_attempts
        }), 500

    def stop(self):
        """停止代理服务器"""
        if self.is_running:
            self.is_running = False
            self.logger.info("代理服务器已停止")

    def refresh_keys(self):
        """刷新密钥池"""
        self.key_pool.refresh_keys()

    def get_stats(self) -> Dict:
        """获取服务器统计信息"""
        uptime = datetime.now() - self.stats["start_time"]
        total_requests = self.stats["total_requests"]
        successful_requests = self.stats["successful_requests"]
        failed_requests = self.stats["failed_requests"]

        success_rate = 0
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100

        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round(success_rate, 2)
        }

    def get_key_pool_status(self) -> Dict:
        """获取密钥池状态"""
        return self.key_pool.get_pool_status()


# 用于测试的简单启动函数
def run_proxy_server(port: int = 8080):
    """运行代理服务器的便捷函数"""
    db_manager = DatabaseManager()
    config_manager = ConfigManager(db_manager)

    proxy = ProxyServer(db_manager, config_manager)
    if proxy.start(port):
        print(f"代理服务器已在端口 {port} 上启动")
        print(f"使用方式: curl -X POST http://localhost:{port}/proxy/v1/chat/completions \\")
        print(f"          -H \"Content-Type: application/json\" \\")
        print(f"          -d '{{\"model\": \"Qwen/Qwen2.5-7B-Instruct\", \"messages\": [{{\"role\": \"user\", \"content\": \"Hello\"}}]}}'")

        # 保持服务器运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止服务器...")
            proxy.stop()
    else:
        print("启动代理服务器失败")


if __name__ == "__main__":
    run_proxy_server()