"""
准确的线程安全诊断
修正之前诊断脚本的问题
"""

import threading
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_lock_initialization_properly():
    """正确测试锁初始化"""
    print("🔍 测试锁初始化机制...")
    
    from logs.core.abstracts import AbstractLogger
    
    lock_creation_issues = []
    successful_creations = 0
    
    def test_single_thread():
        nonlocal successful_creations
        try:
            logger = AbstractLogger(f"logger_{threading.get_ident()}")
            
            # 触发锁初始化
            logger.add_observer(lambda x: None)
            
            # 检查锁是否正确初始化
            if logger._observers_lock is None:
                lock_creation_issues.append("锁未被初始化")
            elif not isinstance(logger._observers_lock, threading.Lock):
                lock_creation_issues.append(f"锁类型错误: {type(logger._observers_lock)}")
            else:
                successful_creations += 1
                
        except Exception as e:
            lock_creation_issues.append(f"异常: {e}")
    
    # 单线程测试
    test_single_thread()
    
    if successful_creations == 0:
        print("❌ 锁初始化完全失败")
        return False
    elif lock_creation_issues:
        print(f"❌ 锁初始化存在问题: {lock_creation_issues}")
        return False
    else:
        print("✅ 锁初始化测试通过")
        return True

def test_concurrent_lock_creation():
    """测试并发锁创建"""
    print("🔍 测试并发锁创建...")
    
    from logs.core.abstracts import AbstractLogger
    
    lock_objects = []
    errors = []
    
    def create_logger_concurrently():
        try:
            logger = AbstractLogger(f"concurrent_logger_{threading.get_ident()}")
            
            # 触发锁初始化
            logger.add_observer(lambda x: None)
            
            if logger._observers_lock is not None:
                lock_objects.append(id(logger._observers_lock))
                
        except Exception as e:
            errors.append(str(e))
    
    # 创建多个线程同时测试
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_logger_concurrently) for _ in range(20)]
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
    elif len(unique_locks) > len(lock_objects) * 0.8:  # 允许一些差异
        print("❌ 检测到竞态条件：创建了过多不同的锁对象")
        return False
    else:
        print("✅ 并发锁创建测试通过")
        return True

def test_deadlock_with_proper_timeout():
    """使用适当超时测试死锁"""
    print("🔍 测试死锁场景（改进版）...")
    
    from logs.singleton.log_manager import LogManager
    
    deadlock_detected = False
    timeout_occurred = False
    exceptions_occurred = []
    
    def config_updater():
        nonlocal deadlock_detected, exceptions_occurred
        try:
            manager = LogManager()
            if not manager.is_initialized():
                # 简化初始化，避免依赖
                pass
            
            # 简化的配置更新测试
            for i in range(10):
                try:
                    if hasattr(manager, '_config_lock') and hasattr(manager, '_loggers_lock'):
                        # 模拟锁获取
                        with manager._config_lock:
                            time.sleep(0.001)  # 很短的延迟
                            with manager._loggers_lock:
                                pass
                except Exception as e:
                    exceptions_occurred.append(f"配置更新异常: {e}")
                    
        except Exception as e:
            exceptions_occurred.append(f"配置更新器异常: {e}")
    
    def logger_accessor():
        nonlocal deadlock_detected, exceptions_occurred
        try:
            manager = LogManager()
            if not manager.is_initialized():
                pass
            
            # 简化的日志器访问测试
            for i in range(10):
                try:
                    if hasattr(manager, '_loggers_lock') and hasattr(manager, '_config_lock'):
                        # 模拟相反的锁获取顺序
                        with manager._loggers_lock:
                            time.sleep(0.001)  # 很短的延迟
                            with manager._config_lock:
                                pass
                except Exception as e:
                    exceptions_occurred.append(f"日志器访问异常: {e}")
                    
        except Exception as e:
            exceptions_occurred.append(f"日志器访问器异常: {e}")
    
    start_time = time.time()
    
    # 创建并发线程
    threads = []
    for i in range(3):  # 减少线程数以避免过多干扰
        t1 = threading.Thread(target=config_updater)
        t2 = threading.Thread(target=logger_accessor)
        threads.extend([t1, t2])
        t1.start()
        t2.start()
    
    # 等待完成，设置合理的超时
    for thread in threads:
        thread.join(timeout=5.0)
        if thread.is_alive():
            timeout_occurred = True
            print("❌ 检测到线程超时，可能存在死锁")
            # 强制停止线程
            break
    
    elapsed_time = time.time() - start_time
    
    if timeout_occurred:
        deadlock_detected = True
    elif elapsed_time > 10.0:
        deadlock_detected = True
        print(f"❌ 执行时间过长 ({elapsed_time:.2f}s)，可能存在死锁")
    elif exceptions_occurred:
        print(f"❌ 检测到异常: {exceptions_occurred}")
        deadlock_detected = True
    
    if not deadlock_detected:
        print("✅ 死锁测试通过")
        return True
    else:
        return False

def test_error_handler_interface():
    """测试错误处理器接口"""
    print("🔍 测试错误处理器接口...")
    
    from logs.error_handling.error_handler import ErrorHandlingManager, ErrorSeverity, ErrorCategory, ErrorHandler
    
    interface_issues = []
    
    # 测试1：标准错误处理器
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
        
        print("✅ 标准错误处理器测试通过")
        
    except Exception as e:
        interface_issues.append(f"标准错误处理器失败: {e}")
    
    # 测试2：不完整的错误处理器（应该失败）
    try:
        class IncompleteErrorHandler:
            def handle_error(self, context):
                raise Exception("处理器失败")
            # 缺少 can_handle 方法
        
        manager = ErrorHandlingManager()
        manager.add_handler(IncompleteErrorHandler())  # 这应该会失败
        
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
    print("🚀 开始准确的线程安全诊断...")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(test_lock_initialization_properly())
    print()
    
    results.append(test_concurrent_lock_creation())
    print()
    
    results.append(test_deadlock_with_proper_timeout())
    print()
    
    results.append(test_error_handler_interface())
    print()
    
    print("=" * 60)
    print("📊 准确的诊断结果汇总:")
    
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