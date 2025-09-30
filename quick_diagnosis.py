"""
快速线程安全诊断
验证最关键的线程安全问题
"""

import threading
import time
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_lock_race_condition():
    """测试锁初始化竞态条件"""
    print("🔍 测试锁初始化竞态条件...")
    
    from logs.core.abstracts import AbstractLogger
    
    lock_ids = []
    errors = []
    
    def create_logger():
        try:
            logger = AbstractLogger(f"test_logger_{threading.get_ident()}")
            
            # 触发锁初始化
            logger.add_observer(lambda x: None)
            
            # 记录锁对象ID
            if logger._observers_lock is not None:
                lock_ids.append(id(logger._observers_lock))
                
        except Exception as e:
            errors.append(str(e))
    
    # 创建多个线程同时测试
    threads = []
    for i in range(20):
        thread = threading.Thread(target=create_logger)
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 分析结果
    unique_locks = set(lock_ids)
    print(f"创建了 {len(lock_ids)} 个锁对象，其中 {len(unique_locks)} 个唯一锁")
    
    if len(unique_locks) > 1:
        print("❌ 检测到竞态条件：多个线程创建了不同的锁对象")
        return False
    else:
        print("✅ 锁初始化竞态条件测试通过")
        return True

def test_deadlock_scenario():
    """测试死锁场景"""
    print("🔍 测试死锁场景...")
    
    from logs.singleton.log_manager import LogManager
    
    deadlock_detected = False
    start_time = time.time()
    
    def config_updater():
        nonlocal deadlock_detected
        try:
            manager = LogManager()
            if not manager.is_initialized():
                from logs.builders.config_builder import create_config_builder
                manager.initialize(create_config_builder().build())
            
            # 频繁更新配置
            for i in range(50):
                config = manager.get_config()
                manager.update_config(config)
                
        except Exception as e:
            deadlock_detected = True
            print(f"配置更新线程异常: {e}")
    
    def logger_accessor():
        nonlocal deadlock_detected
        try:
            manager = LogManager()
            if not manager.is_initialized():
                from logs.builders.config_builder import create_config_builder
                manager.initialize(create_config_builder().build())
            
            # 频繁访问日志器
            for i in range(50):
                logger = manager.get_logger(f"test_logger_{i % 10}")
                
        except Exception as e:
            deadlock_detected = True
            print(f"日志器访问线程异常: {e}")
    
    # 创建并发线程
    threads = []
    for i in range(5):
        t1 = threading.Thread(target=config_updater)
        t2 = threading.Thread(target=logger_accessor)
        threads.extend([t1, t2])
        t1.start()
        t2.start()
    
    # 等待完成，设置超时
    for thread in threads:
        thread.join(timeout=3.0)
        if thread.is_alive():
            deadlock_detected = True
            print("❌ 检测到线程超时，可能存在死锁")
            break
    
    elapsed_time = time.time() - start_time
    if elapsed_time > 10.0:
        deadlock_detected = True
        print(f"❌ 执行时间过长 ({elapsed_time:.2f}s)，可能存在死锁")
    
    if not deadlock_detected:
        print("✅ 死锁测试通过")
        return True
    else:
        return False

def test_error_recursion():
    """测试错误处理递归"""
    print("🔍 测试错误处理递归...")
    
    from logs.error_handling.error_handler import ErrorHandlingManager, ErrorSeverity, ErrorCategory
    
    recursion_detected = False
    error_manager = ErrorHandlingManager()
    
    class FailingHandler:
        def handle_error(self, context):
            # 这个处理器会失败，触发递归
            raise Exception("处理器失败")
    
    # 添加会失败的处理器
    error_manager.add_handler(FailingHandler())
    
    try:
        # 触发错误处理
        error_manager.handle_error(
            Exception("测试错误"),
            ErrorSeverity.HIGH,
            ErrorCategory.UNKNOWN
        )
    except Exception as e:
        if "recursion" in str(e).lower() or "递归" in str(e):
            recursion_detected = True
            print(f"❌ 检测到递归问题: {e}")
    
    if not recursion_detected:
        print("✅ 错误处理递归测试通过")
        return True
    else:
        return False

def main():
    """主函数"""
    print("🚀 开始快速线程安全诊断...")
    print("=" * 50)
    
    results = []
    
    # 运行测试
    results.append(test_lock_race_condition())
    print()
    
    results.append(test_deadlock_scenario())
    print()
    
    results.append(test_error_recursion())
    print()
    
    print("=" * 50)
    print("📊 诊断结果汇总:")
    
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