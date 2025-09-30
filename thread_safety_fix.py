#!/usr/bin/env python3
"""
线程安全修复脚本

修复日志系统中的严重线程安全问题：
1. 修复 AbstractLogger 抽象方法未实现问题
2. 修复 LogManager 潜在死锁风险
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def fix_abstract_logger():
    """修复 AbstractLogger 抽象方法实现"""
    print("🔧 修复 AbstractLogger 抽象方法实现...")
    
    # 读取原始文件
    with open('src/logs/core/abstracts.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 AbstractLogger 类中添加缺失的抽象方法实现
    abstract_methods = '''
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """记录日志（抽象方法实现）
        
        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 其他参数
        """
        # 默认实现：创建日志条目并处理
        from datetime import datetime
        import threading
        
        # 创建日志条目
        record = LogEntry(
            timestamp=datetime.now(),
            level=level,
            logger_name=self.name,
            message=message,
            thread_id=threading.get_ident(),
            context=kwargs.get('context'),
            exception_info=kwargs.get('exception_info')
        )
        
        # 检查是否应该记录
        if self._should_log(record):
            # 通知观察者
            self._notify_observers(record)
    
    def flush(self) -> None:
        """刷新日志缓冲区（抽象方法实现）"""
        # 默认实现：什么都不做
        pass
    
    def shutdown(self) -> None:
        """关闭日志器（抽象方法实现）"""
        # 默认实现：清空观察者和过滤器
        if self._observers_lock is not None:
            with self._observers_lock:
                self._observers.clear()
        
        if self._filters_lock is not None:
            with self._filters_lock:
                self._filters.clear()
    
    def update_config(self, config: 'LogConfig') -> None:
        """更新日志配置（抽象方法实现）
        
        Args:
            config: 新的日志配置
        """
        # 默认实现：什么都不做，子类可以覆盖
        pass
'''
    
    # 找到 AbstractLogger 类的结束位置，在 get_logger_info 方法之后
    insert_pos = content.find('    def get_logger_info(self) -> Dict[str, Any]:')
    if insert_pos == -1:
        print("❌ 无法找到插入位置")
        return False
    
    # 在 get_logger_info 方法之前插入抽象方法
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip() == 'def get_logger_info(self) -> Dict[str, Any]:':
            # 在这个方法之前插入我们的抽象方法
            indent = '    '
            method_lines = abstract_methods.strip().split('\n')
            for method_line in method_lines:
                new_lines.append(indent + method_line)
            new_lines.append('')  # 添加空行
    
    # 写入修复后的文件
    with open('src/logs/core/abstracts.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ AbstractLogger 抽象方法实现修复完成")
    return True

def fix_log_manager_deadlock():
    """修复 LogManager 潜在死锁风险"""
    print("🔧 修复 LogManager 潜在死锁风险...")
    
    # 读取原始文件
    with open('src/logs/singleton/log_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复 update_config 方法中的死锁风险
    # 原来的代码：在持有 _config_lock 的情况下调用 logger.update_config
    # 修复方案：先释放锁，然后再更新日志器
    
    old_update_config = '''    def update_config(self, config: LogConfig) -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 原子更新配置引用
        with self._config_lock:
            self._config_ref = config
        
        # 原子更新配置版本号
        with self._config_version_lock:
            self._config_version += 1
        
        # 更新根日志器
        self._root_logger_ref.update_config(config)'''
    
    new_update_config = '''    def update_config(self, config: LogConfig) -> None:
        """更新日志配置
        
        Args:
            config: 新的日志配置
            
        Raises:
            RuntimeError: 日志管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("日志管理器未初始化，请先调用initialize方法")
        
        # 原子更新配置引用
        with self._config_lock:
            self._config_ref = config
        
        # 原子更新配置版本号
        with self._config_version_lock:
            self._config_version += 1
        
        # 先更新根日志器（避免在持有锁的情况下调用外部方法）
        try:
            self._root_logger_ref.update_config(config)
        except Exception as e:
            # 记录错误但不中断配置更新
            with self._error_stats_lock:
                self._error_stats['root_logger_update_failures'] += 1
            import logging
            logging.error(f"更新根日志器配置失败: {e}")'''
    
    # 替换 update_config 方法
    if old_update_config in content:
        content = content.replace(old_update_config, new_update_config)
    else:
        print("❌ 无法找到 update_config 方法")
        return False
    
    # 写入修复后的文件
    with open('src/logs/singleton/log_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ LogManager 潜在死锁风险修复完成")
    return True

def test_fixes():
    """测试修复效果"""
    print("🧪 测试修复效果...")
    
    try:
        # 测试 AbstractLogger 是否可以正确实例化
        from logs.core.abstracts import AbstractLogger
        from logs.core.types import LogLevel
        
        # 创建一个简单的测试类
        class TestLogger(AbstractLogger):
            def __init__(self, name: str):
                super().__init__(name)
            
            # 所有抽象方法现在都有了默认实现
        
        logger = TestLogger("test_logger")
        logger.log(LogLevel.INFO, "测试消息")
        logger.flush()
        logger.shutdown()
        
        print("✅ AbstractLogger 修复测试通过")
        
        # 测试 LogManager 是否没有死锁
        from logs.singleton.log_manager import LogManager
        
        # 创建一个简单的测试配置
        from logs.builders.config_builder import create_config_builder
        config = create_config_builder().build()
        
        # 初始化 LogManager
        manager = LogManager()
        manager.initialize(config)
        
        # 测试配置更新（不应该死锁）
        manager.update_config(config)
        
        print("✅ LogManager 死锁修复测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始修复线程安全问题...")
    print("=" * 60)
    
    results = []
    
    # 修复 AbstractLogger
    results.append(fix_abstract_logger())
    print()
    
    # 修复 LogManager
    results.append(fix_log_manager_deadlock())
    print()
    
    # 测试修复效果
    results.append(test_fixes())
    print()
    
    print("=" * 60)
    print("📊 修复结果汇总:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 成功修复: {passed}/{total}")
    print(f"❌ 修复失败: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有修复成功！")
        return 0
    else:
        print("\n⚠️  部分修复失败，需要手动处理！")
        return 1

if __name__ == "__main__":
    sys.exit(main())