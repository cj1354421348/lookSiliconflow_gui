#!/usr/bin/env python3
"""
简单的线程安全测试

验证我们修复的线程安全问题是否真的解决了
"""

import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_abstract_logger_fix():
    """测试 AbstractLogger 修复"""
    print("🔍 测试 AbstractLogger 修复...")
    
    try:
        from logs.core.abstracts import AbstractLogger
        from logs.core.types import LogLevel
        
        # 创建测试类
        class TestLogger(AbstractLogger):
            pass
        
        # 测试基本功能
        logger = TestLogger("test")
        logger.log(LogLevel.INFO, "测试消息")
        logger.flush()
        logger.shutdown()
        
        print("✅ AbstractLogger 修复测试通过")
        return True
        
    except Exception as e:
        print(f"❌ AbstractLogger 修复测试失败: {e}")
        return False

def test_log_manager_deadlock_fix():
    """测试 LogManager 死锁修复"""
    print("🔍 测试 LogManager 死锁修复...")
    
    try:
        from logs.singleton.log_manager import LogManager
        from logs.builders.config_builder import create_config_builder
        
        # 创建配置
        config = create_config_builder().build()
        
        # 初始化 LogManager
        manager = LogManager()
        manager.initialize(config)
        
        # 测试并发配置更新
        def update_config():
            try:
                manager.update_config(config)
                return True
            except Exception as e:
                print(f"配置更新失败: {e}")
                return False
        
        # 使用线程池并发测试
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_config) for _ in range(10)]
            results = [future.result(timeout=5.0) for future in futures]
        
        if all(results):
            print("✅ LogManager 死锁修复测试通过")
            return True
        else:
            print("❌ LogManager 死锁修复测试失败")
            return False
            
    except Exception as e:
        print(f"❌ LogManager 死锁修复测试异常: {e}")
        return False

def test_concurrent_logger_creation():
    """测试并发日志器创建"""
    print("🔍 测试并发日志器创建...")
    
    try:
        from logs.singleton.log_manager import LogManager
        from logs.builders.config_builder import create_config_builder
        
        # 创建配置
        config = create_config_builder().build()
        
        # 初始化 LogManager
        manager = LogManager()
        manager.initialize(config)
        
        # 并发创建日志器
        def create_logger(i):
            try:
                from logs.core.types import LogLevel
                logger = manager.get_logger(f"test_logger_{i}")
                logger.log(LogLevel.INFO, f"Logger {i} created")
                return True
            except Exception as e:
                print(f"创建日志器 {i} 失败: {e}")
                return False
        
        # 使用线程池并发测试
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_logger, i) for i in range(20)]
            results = [future.result(timeout=5.0) for future in futures]
        
        if all(results):
            print("✅ 并发日志器创建测试通过")
            return True
        else:
            print("❌ 并发日志器创建测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 并发日志器创建测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始简单的线程安全测试...")
    print("=" * 60)
    
    results = []
    
    # 测试 AbstractLogger 修复
    results.append(test_abstract_logger_fix())
    print()
    
    # 测试 LogManager 死锁修复
    results.append(test_log_manager_deadlock_fix())
    print()
    
    # 测试并发日志器创建
    results.append(test_concurrent_logger_creation())
    print()
    
    print("=" * 60)
    print("📊 简单测试结果汇总:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 通过测试: {passed}/{total}")
    print(f"❌ 失败测试: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有简单测试通过！线程安全问题已修复！")
        return 0
    else:
        print("\n⚠️  部分测试失败，需要进一步调查！")
        return 1

if __name__ == "__main__":
    sys.exit(main())