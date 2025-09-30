#!/usr/bin/env python3
"""
类型定义调试测试脚本

用于验证 src/logs/core/types.py 中的潜在问题
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from logs.core.types import LogLevel, ExceptionInfo, LogEntry

def test_type_safety_issues():
    """测试类型安全问题"""
    print("=== 测试类型安全问题 ===")
    
    # 测试1: Dict[str, Any] 的类型安全问题
    print("\n1. 测试 Dict[str, Any] 类型安全问题:")
    try:
        # 创建包含各种类型的数据
        malicious_context = {
            "function": lambda x: x**2,  # 函数对象
            "large_data": "x" * 1000000,  # 大字符串
            "circular_ref": None,  # 循环引用
            "nested": {"deep": {"very_deep": {"data": [1, 2, 3]}}}
        }
        
        # 创建循环引用
        malicious_context["circular_ref"] = malicious_context
        
        # 这应该能工作，但类型系统无法捕获问题
        exception_info = ExceptionInfo(
            exception_type="TestError",
            exception_message="Test message",
            context=malicious_context
        )
        
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message="Test message",
            logger_name="test_logger",
            thread_id=123,
            context=malicious_context
        )
        
        print("✅ 恶意上下文被接受（类型安全问题）")
        
        # 尝试序列化 - 这可能会失败
        try:
            dict_result = log_entry.to_dict()
            print("✅ 序列化成功（但可能包含不可序列化对象）")
        except Exception as e:
            print(f"❌ 序列化失败: {e}")
            
    except Exception as e:
        print(f"❌ 创建失败: {e}")

def test_boundary_conditions():
    """测试边界条件处理"""
    print("\n=== 测试边界条件处理 ===")
    
    # 测试1: LogLevel.from_name 边界条件
    print("\n1. 测试 LogLevel.from_name 边界条件:")
    test_cases = [None, "", " ", "INVALID", "debug", "DEBUG", 123]
    
    for case in test_cases:
        try:
            result = LogLevel.from_name(case)
            print(f"✅ 输入 {case!r} -> {result}")
        except Exception as e:
            print(f"❌ 输入 {case!r} -> 错误: {e}")
    
    # 测试2: ExceptionInfo.from_exception 边界条件
    print("\n2. 测试 ExceptionInfo.from_exception 边界条件:")
    try:
        # 传入 None 异常
        result = ExceptionInfo.from_exception(None)
        print(f"❌ None 异常被接受: {result}")
    except Exception as e:
        print(f"✅ None 异常正确拒绝: {e}")
    
    # 测试3: LogEntry 时区处理边界条件
    print("\n3. 测试 LogEntry 时区处理边界条件:")
    try:
        # 创建无时区的时间戳
        naive_timestamp = datetime.now()
        log_entry = LogEntry(
            timestamp=naive_timestamp,
            level=LogLevel.INFO,
            message="Test",
            logger_name="test",
            thread_id=123
        )
        print(f"✅ 无时区时间戳处理成功: {log_entry.timestamp.tzinfo}")
    except Exception as e:
        print(f"❌ 时区处理失败: {e}")
    
    # 测试4: to_dict 方法边界条件
    print("\n4. 测试 to_dict 方法边界条件:")
    try:
        # 创建 ExceptionInfo 但 timestamp 为 None
        exception_info = ExceptionInfo(
            exception_type="TestError",
            exception_message="Test message",
            timestamp=None
        )
        result = exception_info.to_dict()
        print(f"✅ None timestamp 处理成功: {result['timestamp']}")
    except Exception as e:
        print(f"❌ None timestamp 处理失败: {e}")

def test_copy_with_type_safety():
    """测试 copy_with 方法的类型安全问题"""
    print("\n=== 测试 copy_with 类型安全问题 ===")
    
    try:
        original = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message="Original message",
            logger_name="test_logger",
            thread_id=123
        )
        
        # 传入无效参数
        invalid_changes = {
            "level": "INVALID_LEVEL",  # 错误的类型
            "timestamp": "not a datetime",  # 错误的类型
            "new_field": "should not exist"  # 不存在的字段
        }
        
        # 这应该会失败，但让我们看看会发生什么
        result = original.copy_with(**invalid_changes)
        print(f"❌ 无效参数被接受: {result}")
        
    except Exception as e:
        print(f"✅ 无效参数正确拒绝: {e}")

def test_memory_leak_risks():
    """测试内存泄漏风险"""
    print("\n=== 测试内存泄漏风险 ===")
    
    try:
        # 创建大型堆栈跟踪
        import traceback
        try:
            # 故意创建一个深度调用栈
            def recursive_function(n):
                if n > 0:
                    return recursive_function(n - 1)
                else:
                    raise ValueError("Deep stack test")
            
            recursive_function(1000)
        except Exception as e:
            # 创建包含大型堆栈跟踪的 ExceptionInfo
            exception_info = ExceptionInfo.from_exception(e, include_traceback=True)
            traceback_size = len(exception_info.traceback_text) if exception_info.traceback_text else 0
            print(f"✅ 大型堆栈跟踪创建成功，大小: {traceback_size} 字符")
            
            # 创建包含大型上下文的 LogEntry
            large_context = {
                f"key_{i}": f"value_{i}" * 1000 for i in range(1000)
            }
            
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.ERROR,
                message="Memory test",
                logger_name="test",
                thread_id=123,
                context=large_context,
                exception_info=exception_info
            )
            
            context_size = sum(len(str(v)) for v in log_entry.context.values())
            print(f"✅ 大型上下文创建成功，大小: {context_size} 字符")
            
    except Exception as e:
        print(f"❌ 内存测试失败: {e}")

if __name__ == "__main__":
    print("开始类型定义调试测试...")
    
    test_type_safety_issues()
    test_boundary_conditions()
    test_copy_with_type_safety()
    test_memory_leak_risks()
    
    print("\n测试完成！")