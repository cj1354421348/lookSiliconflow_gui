import sqlite3
import json
import hashlib
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    """数据库管理器 - 统一管理所有数据库操作"""
    
    def __init__(self, db_path: str = "database/token_manager.db"):
        self.db_path = db_path
        self.logger = self._setup_logger()
        self._ensure_database_exists()
        
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("DatabaseManager")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        return logger
    
    def _ensure_database_exists(self):
        """确保数据库和表存在"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # 创建表结构
        self.create_tables()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典形式的行
        return conn
    
    def create_tables(self):
        """创建所有需要的表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 配置表 - 存储系统配置
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 令牌表 - 存储所有令牌信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_hash TEXT UNIQUE NOT NULL,
                    token_value TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'valid', 'low_balance', 'invalid', 'charge_balance')),
                    total_balance REAL,
                    charge_balance REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP
                )
            """)
            
            # 批次表 - 存储查询批次信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_name TEXT NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    processed_tokens INTEGER DEFAULT 0,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    description TEXT
                )
            """)
            
            # 结果导出表 - 存储导出记录
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_criteria TEXT,
                    token_count INTEGER NOT NULL,
                    export_path TEXT NOT NULL,
                    export_type TEXT NOT NULL CHECK(export_type IN ('file', 'clipboard')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 索引优化
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_status ON tokens(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_token_hash ON tokens(token_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_created_at ON tokens(created_at)")
            
            conn.commit()
            self.logger.info("数据库表结构创建/验证完成")
    
    # 配置管理方法
    def get_config(self, key: str, default_value=None):
        """获取配置值"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default_value
    
    def set_config(self, key: str, value):
        """设置配置值"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if isinstance(value, (dict, list)):
                value_json = json.dumps(value, ensure_ascii=False)
            else:
                value_json = str(value)
            
            # 获取本地时区时间
            local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_json, local_time))
            conn.commit()
    
    # 令牌管理方法
    def add_token(self, token_value: str, status: str = 'pending') -> int:
        """添加令牌到数据库"""
        import hashlib
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO tokens (token_hash, token_value, status)
                    VALUES (?, ?, ?)
                """, (token_hash, token_value, status))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # 令牌已存在，返回现有ID
                cursor.execute("SELECT id FROM tokens WHERE token_hash = ?", (token_hash,))
                return cursor.fetchone()['id']
    
    def add_tokens_batch(self, tokens: List[str], batch_id: int = None) -> int:
        """批量添加令牌"""
        added_count = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for token in tokens:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO tokens (token_hash, token_value, status)
                        VALUES (?, ?, 'pending')
                    """, (token_hash, token))
                    if cursor.rowcount > 0:
                        added_count += 1
                except Exception as e:
                    self.logger.error(f"添加令牌失败: {e}")
            
            conn.commit()
        
        return added_count
    
    def update_token_status(self, token_id: int, status: str, total_balance: float = None, charge_balance: float = None):
        """更新令牌状态和余额"""
        # 获取本地时区时间
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tokens 
                SET status = ?, total_balance = ?, charge_balance = ?, 
                    updated_at = ?, last_checked = ?
                WHERE id = ?
            """, (status, total_balance, charge_balance, local_time, local_time, token_id))
            conn.commit()
    
    def get_tokens_by_status(self, status: str) -> List[Dict]:
        """根据状态获取令牌"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, token_value, status, total_balance, charge_balance, 
                       created_at, updated_at, last_checked
                FROM tokens WHERE status = ?
                ORDER BY created_at DESC
            """, (status,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_tokens(self, limit: int = 100) -> List[Dict]:
        """获取待处理的令牌"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, token_value, status, created_at
                FROM tokens 
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_token_statistics(self) -> Dict:
        """获取令牌统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取各状态统计
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM tokens
                GROUP BY status
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['status']] = {
                    'count': row['count']
                }
            
            # 获取总数
            cursor.execute("SELECT COUNT(*) as total FROM tokens")
            total_count = cursor.fetchone()['total']
            
            return {
                'by_status': stats,
                'total_count': total_count
            }
    
    def delete_tokens_by_status(self, status: str) -> int:
        """根据状态删除令牌"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tokens WHERE status = ?", (status,))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def export_tokens_to_file(self, file_path: str, status_filter: List[str] = None) -> int:
        """导出令牌到文件"""
        export_dir = os.path.dirname(file_path)
        if export_dir and not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status_filter:
                placeholders = ','.join(['?' for _ in status_filter])
                cursor.execute(f"""
                    SELECT token_value FROM tokens 
                    WHERE status IN ({placeholders})
                    ORDER BY token_value
                """, status_filter)
            else:
                cursor.execute("""
                    SELECT token_value FROM tokens 
                    ORDER BY token_value
                """)
            
            tokens = [row['token_value'] for row in cursor.fetchall()]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for token in tokens:
                    f.write(f"{token}\n")
        
        # 记录导出
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO exports (filter_criteria, token_count, export_path, export_type)
                VALUES (?, ?, ?, 'file')
            """, (json.dumps(status_filter) if status_filter else None, len(tokens), file_path))
            conn.commit()
        
        return len(tokens)
    
    # 批次管理方法
    def create_batch(self, batch_name: str, description: str = None) -> int:
        """创建新的批次"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO batches (batch_name, total_tokens, processed_tokens, status, description)
                VALUES (?, 0, 0, 'pending', ?)
            """, (batch_name, description))
            conn.commit()
            return cursor.lastrowid
    
    def update_batch_status(self, batch_id: int, status: str, processed_tokens: int = None):
        """更新批次状态"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取本地时区时间
            local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if processed_tokens is not None:
                cursor.execute("""
                    UPDATE batches 
                    SET status = ?, processed_tokens = ?, 
                        completed_at = CASE WHEN ? = 'completed' THEN ? ELSE NULL END
                    WHERE id = ?
                """, (status, processed_tokens, status, local_time, batch_id))
            else:
                cursor.execute("""
                    UPDATE batches 
                    SET status = ?, 
                        completed_at = CASE WHEN ? = 'completed' THEN ? ELSE NULL END
                    WHERE id = ?
                """, (status, status, local_time, batch_id))
            
            conn.commit()
    
    def get_batches(self) -> List[Dict]:
        """获取所有批次信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, batch_name, total_tokens, processed_tokens, status,
                       created_at, completed_at, description
                FROM batches
                ORDER BY created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]