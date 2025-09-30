"""
最终的线程安全诊断
使用正确的配置类进行测试
"""

import threading
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_async_logger_lock_initialization():
    """测试AsyncLogger的锁初始化"""
    print("🔍 测试AsyncLogger锁初始化...")
    
    from logs.loggers.async_logger import AsyncLogger
    from logs.config.log_config import LogConfigData
    from logs.core.types import LogLevel
    from logs.strategies.output_strategies import ConsoleOutputStrategy
    
    # 使用正确的配置类
    config = LogConfigData(
        min_level=LogLevel.DEBUG,
        format_string="%(message)s",
        output_strategies=[ConsoleOutputStrategy()],
        enable_async=True,
        queue_size=100,
        flush_interval=1.0
    )
    
    lock_objects = []
    errors = []
    
    def create_async_logger():
        try:
            logger = AsyncLogger(f"async_logger_{threading.get_ident()}", config)
            
            # 触发锁初始化
            logger.add_observer(lambda x: None)
            
            # 检查锁是否正确初始化
            if logger._observers_lock is not None:
                lock_objects.append(id(logger._observers_lock))
            else:
                errors.append("观察者锁未被初始化")
                
        except Exception as e:
            errors.append(f"异常: {e}")
    
    # 单线程测试
    create_async_logger()
    
    if not lock_objects:
        print("❌ 锁初始化失败")
        return False
    elif errors:
        print(f"❌ 锁初始化存在问题: {errors}")
        return False
    else:
        print("✅ AsyncLogger锁初始化测试通过")
        return True

def test_concurrent_async_logger_creation():
    """测试并发AsyncLogger创建"""
    print("🔍 测试并发AsyncLogger创建...")
    
    from logs.loggers.async_logger import AsyncLogger
    from logs.config.log_config import LogConfigData
    from logs.core.types import LogLevel
    from logs.strategies.output_strategies import ConsoleOutputStrategy
    
    # 使用正确的配置类
    config = LogConfigData(
        min_level=LogLevel.DEBUG,
        format_string="%(message)s",
        output_strategies=[ConsoleOutputStrategy()],
        enable_async=True,
        queue_size=100,
        flush_interval=1.0
    )
    
    lock_objects = []
    errors = []
    
    def create_logger_concurrently():
        try:
            logger = AsyncLogger(f"concurrent_async_logger_{threading.get_ident()}", config)
            
            # 触发锁初始化
            logger.add_observer(lambda x: None)
            
            if logger._observers_lock is not None:
                lock_objects.append(id(logger._observers_lock))
                
        except Exception as e:
            errors.append(str(e))
    
    # 创建多个线程同时测试
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_logger_concurrently) for _ in range(10)]
        for future in futures:
            try:
                future.result(timeout=2.0)
            except Exception as e:
                errors.append(f"线程超时或异常: {e}")
    
    # 分析结果
    unique_locks = set(lock_objects)
    print(f"创建了 {len(lock_objects)} 个锁对象，其中 {len(unique_locks)} 个唯一锁")
    
    if errors:
        print(f"❌ 并发创建时出现错误: {errors}")
        return False
    elif len(unique_locks) == len(lock_objects):
        print("✅ 每个logger都有独立的锁，这是正确的")
        return True
    else:
        print("❌ 检测到锁共享问题")
        return False

def test_log_manager_deadlock():
    """测试LogManager死锁"""
    print("🔍 测试LogManager死锁...")
    
    from logs.singleton.log_manager import LogManager
    
    deadlock_detected = False
    timeout_occurred = False
    exceptions_occurred = []
    
    def config_updater():
        nonlocal deadlock_detected, exceptions_occurred
        try:
            manager = LogManager()
            if not manager.is_initialized():
                from logs.builders.config_builder import create_config_builder
                manager.initialize(create_config_builder().build())
            
            # 频繁更新配置
            for i in range(20):
                try:
                    config = manager.get_config()
                    manager.update_config(config)
                    time.sleep(0.001)  # 短暂延迟
                except Exception as e:
                    exceptions_occurred.append(f"配置更新异常: {e}")
                    break
                    
        except Exception as e:
            exceptions_occurred.append(f"配置更新器异常: {e}")
    
    def logger_accessor():
        nonlocal deadlock_detected, exceptions_occurred
        try:
            manager = LogManager()
            if not manager.is_initialized():
                from logs.builders.config_builder import create_config_builder
                manager.initialize(create_config_builder().build())
            
            # 频繁访问日志器
            for i in range(20):
                try:
                    logger = manager.get_logger(f"test_logger_{i % 5}")
                    time.sleep(0.001)  # 短暂延迟
                except Exception as e:
                    exceptions_occurred.append(f"日志器访问异常: {e}")
                    break
                    
        except Exception as e:
            exceptions_occurred.append(f"日志器访问器异常: {e}")
    
    start_time = time.time()
    
    # 创建并发线程
    threads = []
    for i in range(3):  # 减少线程数
        t1 = threading.Thread(target=config_updater)
        t2 = threading.Thread(target=logger_accessor)
        threads.extend([t1, t2])
        t1.start()
        t2.start()
    
    # 等待完成，设置合理的超时
    for thread in threads:
        thread.join(timeout=3.0)
        if thread.is_alive():
            timeout_occurred = True
            print("❌ 检测到线程超时，可能存在死锁")
            break
    
    elapsed_time = time.time() - start_time
    
    if timeout_occurred:
        deadlock_detected = True
    elif elapsed_time > 8.0:
        deadlock_detected = True
        print(f"❌ 执行时间过长 ({elapsed_time:.2f}s)，可能存在死锁")
    elif exceptions_occurred:
        print(f"❌ 检测到异常: {exceptions_occurred}")
        deadlock_detected = True
    
    if not deadlock_detected:
        print("✅ LogManager死锁测试通过")
        return True
    else:
        return False

def test_error_handler_interface():
    """测试错误处理器接口"""
    print("🔍 测试错误处理器接口...")
    
    from logs.error_handling.error_handler import ErrorHandlingManager, ErrorSeverity, ErrorCategory, ErrorHandler
    
    interface_issues = []
    
    # 测试1：正确的错误处理器
    try:
        class ProperErrorHandler(ErrorHandler):
            def handle_error(self, context):
                pass
            
            def can_handle(self, context):
                return True
        
        manager = ErrorHandlingManager()
        manager.add_handler(ProperErrorHandler())
        
        # 触发错误处理
        manager.handle_error(
            Exception("测试错误"),
            ErrorSeverity.MEDIUM,
            ErrorCategory.UNKNOWN
        )
        
        print("✅ 正确的错误处理器测试通过")
        
    except Exception as e:
        interface_issues.append(f"正确的错误处理器失败: {e}")
    
    # 测试2：不完整的错误处理器（应该被拒绝）
    try:
        class IncompleteErrorHandler:
            def handle_error(self, context):
                pass
            # 缺少 can_handle 方法
        
        manager = ErrorHandlingManager()
        manager.add_handler(IncompleteErrorHandler())
        
        # 如果没有抛出异常，说明接口验证有问题
        interface_issues.append("不完整的错误处理器被错误地接受")
        
    except Exception as e:
        print(f"✅ 正确拒绝了不完整的错误处理器: {e}")
    
    if interface_issues:
        print(f"❌ 错误处理器接口存在问题: {interface_issues}")
        return False
    else:
        print("✅ 错误处理器接口测试通过")
        return True

def main():
    """主函数"""
    print("🚀 开始最终的线程安全诊断...")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(test_async_logger_lock_initialization())
    print()
    
    results.append(test_concurrent_async_logger_creation())
    print()
    
    results.append(test_log_manager_deadlock())
    print()
    
    results.append(test_error_handler_interface())
    print()
    
    print("=" * 60)
    print("📊 最终的诊断结果汇总:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 通过测试: {passed}/{total}")
    print(f"❌ 失败测试: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  发现问题，需要修复！")
        return 1

if __name__ == "__main__":
    sys.exit(main())