"""
线程安全诊断脚本
用于验证日志系统的线程安全问题
"""

import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from logs.core.abstracts import AbstractLogger
from logs.singleton.log_manager import LogManager
from logs.error_handling.error_handler import ErrorHandlingManager, ErrorContext, ErrorSeverity, ErrorCategory
from logs.loggers.async_logger import AsyncLogger
from logs.performance.performance_optimization import BatchProcessor, AsyncBatchProcessor


class ThreadSafetyDiagnostics:
    """线程安全诊断器"""
    
    def __init__(self):
        self.diagnostic_results = []
        self.lock = threading.Lock()
        
    def add_diagnostic(self, test_name: str, result: str, details: Dict[str, Any] = None):
        """添加诊断结果"""
        with self.lock:
            self.diagnostic_results.append({
                'test_name': test_name,
                'result': result,
                'details': details or {},
                'timestamp': time.time()
            })
    
    def test_lock_initialization_race(self):
        """测试锁初始化的竞态条件"""
        print("🔍 测试锁初始化竞态条件...")
        
        race_detected = False
        lock_objects = []
        
        def create_logger_instance():
            nonlocal race_detected
            logger = AbstractLogger("test_logger")
            
            # 记录锁对象
            if logger._observers_lock is not None:
                lock_objects.append(id(logger._observers_lock))
            
            # 模拟并发访问
            for _ in range(100):
                logger.add_observer(lambda x: None)
                logger.remove_observer(lambda x: None)
        
        # 创建多个线程同时初始化
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_logger_instance) for _ in range(10)]
            for future in futures:
                future.result()
        
        # 检查是否创建了多个锁对象
        unique_locks = set(lock_objects)
        if len(unique_locks) > 1:
            race_detected = True
            print(f"❌ 检测到竞态条件：创建了 {len(unique_locks)} 个不同的锁对象")
        else:
            print("✅ 锁初始化竞态条件测试通过")
        
        self.add_diagnostic(
            "锁初始化竞态条件",
            "失败" if race_detected else "通过",
            {"unique_lock_count": len(unique_locks), "total_lock_creations": len(lock_objects)}
        )
    
    def test_deadlock_scenario(self):
        """测试死锁场景"""
        print("🔍 测试死锁场景...")
        
        deadlock_detected = False
        start_time = time.time()
        
        def simulate_config_update():
            nonlocal deadlock_detected
            try:
                manager = LogManager()
                if not manager.is_initialized():
                    manager.initialize()
                
                # 模拟配置更新
                for _ in range(50):
                    manager.update_config(manager.get_config())
                    
            except Exception as e:
                deadlock_detected = True
                print(f"❌ 检测到可能的死锁: {e}")
        
        def simulate_logger_access():
            nonlocal deadlock_detected
            try:
                manager = LogManager()
                if not manager.is_initialized():
                    manager.initialize()
                
                # 模拟日志器访问
                for _ in range(50):
                    logger = manager.get_logger(f"test_{random.randint(1, 100)}")
                    
            except Exception as e:
                deadlock_detected = True
                print(f"❌ 检测到可能的死锁: {e}")
        
        # 创建并发访问
        with ThreadPoolExecutor(max_workers=20) as executor:
            config_futures = [executor.submit(simulate_config_update) for _ in range(10)]
            logger_futures = [executor.submit(simulate_logger_access) for _ in range(10)]
            
            all_futures = config_futures + logger_futures
            
            # 设置超时
            try:
                for future in all_futures:
                    future.result(timeout=5.0)  # 5秒超时
            except Exception as e:
                deadlock_detected = True
                print(f"❌ 检测到超时，可能存在死锁: {e}")
        
        elapsed_time = time.time() - start_time
        if not deadlock_detected and elapsed_time > 10.0:
            deadlock_detected = True
            print(f"❌ 执行时间过长 ({elapsed_time:.2f}s)，可能存在死锁")
        elif not deadlock_detected:
            print("✅ 死锁测试通过")
        
        self.add_diagnostic(
            "死锁场景",
            "失败" if deadlock_detected else "通过",
            {"execution_time": elapsed_time, "timeout_detected": deadlock_detected}
        )
    
    def test_error_recursion(self):
        """测试错误处理递归"""
        print("🔍 测试错误处理递归...")
        
        recursion_detected = False
        error_manager = ErrorHandlingManager()
        
        def create_recursive_error():
            nonlocal recursion_detected
            
            def error_handler_that_fails(context):
                # 这个错误处理器本身会失败
                raise Exception("错误处理器失败")
            
            # 添加会失败的错误处理器
            from logs.error_handling.error_handler import ErrorHandler
            class FailingErrorHandler(ErrorHandler):
                def handle_error(self, context):
                    raise Exception("错误处理器失败")
            
            error_manager.add_handler(FailingErrorHandler())
            
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
        
        create_recursive_error()
        
        if not recursion_detected:
            print("✅ 错误处理递归测试通过")
        
        self.add_diagnostic(
            "错误处理递归",
            "失败" if recursion_detected else "通过",
            {"recursion_detected": recursion_detected}
        )
    
    def test_async_queue_overflow(self):
        """测试异步队列溢出"""
        print("🔍 测试异步队列溢出...")
        
        overflow_detected = False
        dropped_messages = 0
        
        # 创建小队列的异步处理器
        from logs.core.interfaces import LogConfig
        from logs.core.types import LogLevel
        
        class MockConfig(LogConfig):
            def get_min_level(self):
                return LogLevel.DEBUG
            
            def get_format_string(self):
                return "%(message)s"
            
            def is_async_enabled(self):
                return True
            
            def get_queue_size(self):
                return 10  # 很小的队列
            
            def get_flush_interval(self):
                return 1.0
            
            def get_output_strategies(self):
                return []
        
        async_logger = AsyncLogger("test", MockConfig())
        
        def flood_queue():
            nonlocal dropped_messages
            for i in range(100):
                success = async_logger.log(LogLevel.INFO, f"测试消息 {i}")
                if not success:
                    dropped_messages += 1
        
        # 快速 flooding 队列
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(flood_queue) for _ in range(5)]
            for future in futures:
                future.result()
        
        if dropped_messages > 0:
            overflow_detected = True
            print(f"❌ 检测到队列溢出，丢弃了 {dropped_messages} 条消息")
        else:
            print("✅ 队列溢出测试通过")
        
        self.add_diagnostic(
            "异步队列溢出",
            "失败" if overflow_detected else "通过",
            {"dropped_messages": dropped_messages}
        )
    
    def test_performance_bottlenecks(self):
        """测试性能瓶颈"""
        print("🔍 测试性能瓶颈...")
        
        performance_issues = []
        
        # 测试批量处理器性能
        def test_batch_processor():
            start_time = time.time()
            
            def mock_processor(batch):
                time.sleep(0.01)  # 模拟处理时间
            
            processor = BatchProcessor(
                batch_size=10,
                max_wait_time=1.0,
                processor=mock_processor
            )
            
            # 添加大量消息
            for i in range(100):
                from logs.core.types import LogEntry
                from datetime import datetime
                entry = LogEntry(
                    timestamp=datetime.now(),
                    level=None,
                    message=f"消息 {i}",
                    logger_name="test",
                    thread_id=0,
                    exception_info=None,
                    context={}
                )
                processor.add_entry(entry)
            
            # 等待处理完成
            processor.flush()
            processor.stop()
            
            elapsed_time = time.time() - start_time
            if elapsed_time > 5.0:  # 超过5秒认为性能有问题
                performance_issues.append(f"批量处理器处理时间过长: {elapsed_time:.2f}s")
        
        test_batch_processor()
        
        if performance_issues:
            print(f"❌ 检测到性能问题: {performance_issues}")
        else:
            print("✅ 性能测试通过")
        
        self.add_diagnostic(
            "性能瓶颈",
            "失败" if performance_issues else "通过",
            {"issues": performance_issues}
        )
    
    def run_all_diagnostics(self):
        """运行所有诊断"""
        print("🚀 开始线程安全诊断...")
        print("=" * 50)
        
        self.test_lock_initialization_race()
        print()
        
        self.test_deadlock_scenario()
        print()
        
        self.test_error_recursion()
        print()
        
        self.test_async_queue_overflow()
        print()
        
        self.test_performance_bottlenecks()
        print()
        
        print("=" * 50)
        print("📊 诊断结果汇总:")
        
        failed_tests = [r for r in self.diagnostic_results if r['result'] == '失败']
        passed_tests = [r for r in self.diagnostic_results if r['result'] == '通过']
        
        print(f"✅ 通过测试: {len(passed_tests)}")
        print(f"❌ 失败测试: {len(failed_tests)}")
        
        if failed_tests:
            print("\n🔴 失败的测试详情:")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['details']}")
        
        return len(failed_tests) == 0


if __name__ == "__main__":
    diagnostics = ThreadSafetyDiagnostics()
    success = diagnostics.run_all_diagnostics()
    
    if success:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  发现问题，需要修复！")
        sys.exit(1)