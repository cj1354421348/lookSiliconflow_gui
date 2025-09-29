import requests
import json
import logging
import threading
import time
import os
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from database_manager import DatabaseManager
from config_manager import ConfigManager

class TokenQueryService:
    """令牌查询服务 - 处理所有令牌查询和分类逻辑"""
    
    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager, log_manager=None):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.logger = self._setup_logger()
        self.is_processing = False
        self.processing_lock = threading.Lock()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("TokenQueryService")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        return logger
    
    def check_single_token(self, token: str) -> Dict:
        """查询单个令牌余额"""
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.get(
                self.config_manager.get_api_endpoint(),
                headers=headers,
                timeout=self.config_manager.get_api_timeout()
            )
            response.raise_for_status()
            
            data = response.json()
            total_balance = data.get("data", {}).get("totalBalance")
            charge_balance = data.get("data", {}).get("chargeBalance")
            
            return {
                "success": True,
                "total_balance": total_balance,
                "charge_balance": charge_balance
            }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"请求失败: {e}"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON解析失败: {e}"}
        except Exception as e:
            return {"success": False, "error": f"未知错误: {e}"}
    
    def classify_token(self, token: str, query_result: Dict) -> str:
        """根据查询结果分类令牌"""
        if not query_result["success"]:
            if self.log_manager:
                self.log_manager.log_debug(f"Token: {token[:8]}...{token[-5:]} - {query_result['error']}")
            else:
                self.logger.error(f"Token: {token[:8]}...{token[-5:]} - {query_result['error']}")
            return "invalid"
        
        total_balance = query_result["total_balance"]
        charge_balance = query_result["charge_balance"]
        
        if total_balance is None:
            if self.log_manager:
                self.log_manager.log_debug(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 无效")
            else:
                self.logger.warning(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 无效")
            return "invalid"
        
        # 优先检查充值余额
        if charge_balance is not None and float(charge_balance) > 0:
            if self.log_manager:
                self.log_manager.log_debug(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 充值余额: {charge_balance} - 状态: 有充值余额")
            else:
                self.logger.info(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 充值余额: {charge_balance} - 状态: 有充值余额")
            return "charge_balance"
        
        # 检查普通余额
        if float(total_balance) >= self.config_manager.get_valid_threshold():
            if self.log_manager:
                self.log_manager.log_debug(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 有效")
            else:
                self.logger.info(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 有效")
            return "valid"
        elif float(total_balance) >= self.config_manager.get_low_balance_threshold():
            if self.log_manager:
                self.log_manager.log_debug(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 余额不足")
            else:
                self.logger.warning(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 余额不足")
            return "low_balance"
        else:
            if self.log_manager:
                self.log_manager.log_debug(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 无余额")
            else:
                self.logger.warning(f"Token: {token[:8]}...{token[-5:]} - 余额: {total_balance} - 状态: 无余额")
            return "low_balance"
    
    def process_single_token(self, token_id: int, token_value: str) -> Dict:
        """处理单个令牌（线程安全）"""
        try:
            # 查询令牌余额
            query_result = self.check_single_token(token_value)
            
            # 分类令牌
            status = self.classify_token(token_value, query_result)
            
            # 更新数据库
            self.db_manager.update_token_status(
                token_id=token_id,
                status=status,
                total_balance=query_result.get("total_balance"),
                charge_balance=query_result.get("charge_balance")
            )
            
            return {
                "token_id": token_id,
                "token_value": token_value,
                "status": status,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_debug(f"处理令牌异常: {token_value} - {e}")
            else:
                self.logger.error(f"处理令牌异常: {token_value} - {e}")
            
            # 更新为无效状态
            self.db_manager.update_token_status(token_id=token_id, status="invalid")
            
            return {
                "token_id": token_id,
                "token_value": token_value,
                "status": "invalid",
                "success": False,
                "error": str(e)
            }
    
    def _remove_duplicate_tokens(self):
        """清理数据库中的重复令牌记录"""
        try:
            # 获取所有令牌
            all_tokens = self.db_manager.get_all_tokens()
            
            # 使用字典来跟踪每个令牌值的ID
            token_dict = {}
            duplicates = []
            
            for token in all_tokens:
                token_value = token['token_value']
                token_id = token['id']
                
                if token_value in token_dict:
                    # 发现重复令牌，保留ID较小的记录
                    if token_id > token_dict[token_value]:
                        duplicates.append(token_id)
                    else:
                        duplicates.append(token_dict[token_value])
                        token_dict[token_value] = token_id
                else:
                    token_dict[token_value] = token_id
            
            # 删除重复记录
            for duplicate_id in duplicates:
                self.db_manager.delete_token_by_id(duplicate_id)
            
            if duplicates:
                self.logger.info(f"清理了 {len(duplicates)} 个重复的令牌记录")
        except Exception as e:
            self.logger.error(f"清理重复令牌时出错: {e}")
    
    def process_tokens_single_threaded(self, tokens: List[Dict]) -> List[Dict]:
        """单线程处理令牌"""
        results = []
        processed_token_ids = set()
        
        for token in tokens:
            token_id = token['id']
            # 避免重复处理同一令牌
            if token_id not in processed_token_ids:
                result = self.process_single_token(token_id, token['token_value'])
                results.append(result)
                processed_token_ids.add(token_id)
            
        return results
    
    def process_tokens_multithreaded(self, tokens: List[Dict]) -> List[Dict]:
        """多线程处理令牌"""
        max_workers = self.config_manager.get_max_workers()
        batch_size = self.config_manager.get_batch_size()
        
        # 去重处理
        unique_tokens = []
        processed_token_ids = set()
        
        for token in tokens:
            token_id = token['id']
            if token_id not in processed_token_ids:
                unique_tokens.append(token)
                processed_token_ids.add(token_id)
        
        results = []
        processed_count = 0
        total_count = len(unique_tokens)
        
        if self.log_manager:
            self.log_manager.log_process(f"开始多线程处理：共 {total_count} 个令牌，使用 {max_workers} 个线程")
        else:
            self.logger.info(f"开始多线程处理：共 {total_count} 个令牌，使用 {max_workers} 个线程")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_token = {
                executor.submit(self.process_single_token, token['id'], token['token_value']): token
                for token in unique_tokens
            }
            
            # 收集结果
            for future in as_completed(future_to_token):
                token = future_to_token[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # 更新进度
                    processed_count += 1
                    if processed_count % batch_size == 0 or processed_count == total_count:
                        progress = (processed_count / total_count) * 100
                    if self.log_manager:
                        self.log_manager.log_process(f"进度: {processed_count}/{total_count} ({progress:.1f}%)")
                    else:
                        self.logger.info(f"进度: {processed_count}/{total_count} ({progress:.1f}%)")
                        
                except Exception as e:
                    if self.log_manager:
                        self.log_manager.log_debug(f"令牌处理异常: {token['token_value']} - {e}")
                    else:
                        self.logger.error(f"令牌处理异常: {token['token_value']} - {e}")
                    results.append({
                        "token_id": token['id'],
                        "token_value": token['token_value'],
                        "status": "invalid",
                        "success": False,
                        "error": str(e)
                    })
        
        if self.log_manager:
            self.log_manager.log_process("多线程处理完成")
        else:
            self.logger.info("多线程处理完成")
        return results
    
    def process_pending_tokens(self, batch_id: int = None) -> Dict:
        """处理所有待处理的令牌"""
        with self.processing_lock:
            if self.is_processing:
                return {"success": False, "message": "已有处理任务在进行中"}
            
            self.is_processing = True
        
        try:
            if self.log_manager:
                self.log_manager.log_process("开始处理待处理的令牌")
            else:
                self.logger.info("开始处理待处理的令牌")
            
            # 清理数据库中的重复记录
            self._remove_duplicate_tokens()
            
            # 获取待处理的令牌 (无数量限制)
            pending_tokens = self.db_manager.get_pending_tokens(limit=1000000)
            
            if not pending_tokens:
                return {"success": True, "message": "没有待处理的令牌", "processed_count": 0}
            
            # 更新批次状态
            if batch_id:
                self.db_manager.update_batch_status(batch_id, "processing", len(pending_tokens))
            
            # 处理令牌
            if self.config_manager.is_threading_enabled():
                results = self.process_tokens_multithreaded(pending_tokens)
            else:
                results = self.process_tokens_single_threaded(pending_tokens)
            
            # 统计结果（去重处理）
            unique_token_ids = set()
            unique_results = []
            
            for result in results:
                token_id = result["token_id"]
                if token_id not in unique_token_ids:
                    unique_token_ids.add(token_id)
                    unique_results.append(result)
            
            processed_count = len(unique_results)
            successful_count = sum(1 for r in unique_results if r["success"])
            failed_count = processed_count - successful_count
            
            # 按状态统计
            status_counts = {}
            for result in unique_results:
                status = result["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # 更新批次状态
            if batch_id:
                self.db_manager.update_batch_status(batch_id, "completed", processed_count)
            
            if self.log_manager:
                self.log_manager.log_user(f"令牌处理完成: 总计 {processed_count}, 成功 {successful_count}, 失败 {failed_count}")
            else:
                self.logger.info(f"令牌处理完成: 总计 {processed_count}, 成功 {successful_count}, 失败 {failed_count}")
            
            return {
                "success": True,
                "message": "处理完成",
                "processed_count": processed_count,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "status_counts": status_counts
            }
            
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(f"处理令牌时发生错误: {e}")
            else:
                self.logger.error(f"处理令牌时发生错误: {e}")
            if batch_id:
                self.db_manager.update_batch_status(batch_id, "failed")
            return {"success": False, "message": f"处理失败: {e}"}
        finally:
            self.is_processing = False
    
    def add_tokens_from_file(self, file_path: str) -> Dict:
        """从文件添加令牌"""
        if not os.path.exists(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}"}
        
        tokens = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 支持逗号和换行符两种分割方式
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    # 在每行中用逗号分割
                    line_tokens = line.split(',')
                    for token in line_tokens:
                        cleaned_token = token.strip()
                        if cleaned_token:
                            tokens.append(cleaned_token)
            
        except Exception as e:
            return {"success": False, "message": f"读取文件失败: {e}"}
        
        if not tokens:
            return {"success": False, "message": "文件中没有找到有效的令牌"}
        
        # 检查新增令牌数量
        added_count = self.db_manager.add_tokens_batch(tokens)
        
        return {
            "success": True,
            "message": f"成功添加 {added_count} 个新令牌",
            "total_tokens": len(tokens),
            "added_tokens": added_count,
            "duplicates_skipped": len(tokens) - added_count
        }
    
    def add_tokens_from_text(self, text: str) -> Dict:
        """从文本添加令牌"""
        tokens = []
        
        # 支持逗号和换行符两种分割方式
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                # 在每行中用逗号分割
                line_tokens = line.split(',')
                for token in line_tokens:
                    cleaned_token = token.strip()
                    if cleaned_token:
                        tokens.append(cleaned_token)
        
        if not tokens:
            return {"success": False, "message": "文本中没有找到有效的令牌"}
        
        # 添加到数据库
        added_count = self.db_manager.add_tokens_batch(tokens)
        
        return {
            "success": True,
            "message": f"成功添加 {added_count} 个新令牌",
            "total_tokens": len(tokens),
            "added_tokens": added_count,
            "duplicates_skipped": len(tokens) - added_count
        }
    
    def get_processing_status(self) -> Dict:
        """获取处理状态"""
        return {
            "is_processing": self.is_processing,
            "pending_count": len(self.db_manager.get_pending_tokens(limit=1000000))
        }