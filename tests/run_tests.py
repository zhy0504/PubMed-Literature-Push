#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行器
提供便捷的测试运行功能
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_basic_tests():
    """运行基础测试"""
    print("=" * 60)
    print("运行基础单元测试")
    print("=" * 60)
    
    try:
        from tests.test_basic import run_tests
        success = run_tests()
        return success
    except ImportError as e:
        print(f"导入测试模块失败: {e}")
        return False
    except Exception as e:
        print(f"运行测试时发生错误: {e}")
        return False

def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("运行性能测试")
    print("=" * 60)
    
    try:
        import time
        import tempfile
        import shutil
        
        # 导入被测试的模块
        from src.performance import CacheManager, EmailQueue
        from src.security import SensitiveDataProtector
        
        # 缓存性能测试
        print("测试缓存性能...")
        temp_dir = tempfile.mkdtemp()
        
        try:
            cache = CacheManager(cache_dir=temp_dir, max_size=1000)
            
            # 测试写入性能
            start_time = time.time()
            for i in range(1000):
                cache.set(f"key_{i}", f"value_{i}")
            write_time = time.time() - start_time
            
            # 测试读取性能
            start_time = time.time()
            for i in range(1000):
                cache.get(f"key_{i}")
            read_time = time.time() - start_time
            
            print(f"缓存写入性能: {1000/write_time:.2f} ops/sec")
            print(f"缓存读取性能: {1000/read_time:.2f} ops/sec")
            
            # 缓存命中率测试
            hits = 0
            for i in range(1000):
                if cache.get(f"key_{i % 100}") is not None:  # 重复访问前100个键
                    hits += 1
            
            hit_rate = hits / 1000
            print(f"缓存命中率: {hit_rate:.2%}")
            
        finally:
            shutil.rmtree(temp_dir)
        
        # 加密性能测试
        print("\n测试加密性能...")
        protector = SensitiveDataProtector()
        test_key = b'test-key-32-bytes-long-for-encryption-'
        protector._setup_fernet(test_key)
        
        # 测试加密性能
        test_data = "sensitive_data_" * 100  # 较大的测试数据
        
        start_time = time.time()
        for i in range(100):
            encrypted = protector.encrypt_value(test_data)
        encrypt_time = time.time() - start_time
        
        # 测试解密性能
        encrypted = protector.encrypt_value(test_data)
        start_time = time.time()
        for i in range(100):
            decrypted = protector.decrypt_value(encrypted)
        decrypt_time = time.time() - start_time
        
        print(f"加密性能: {100/encrypt_time:.2f} ops/sec")
        print(f"解密性能: {100/decrypt_time:.2f} ops/sec")
        
        # 邮件队列性能测试
        print("\n测试邮件队列性能...")
        temp_dir = tempfile.mkdtemp()
        
        try:
            email_queue = EmailQueue(queue_dir=temp_dir, max_queue_size=1000)
            
            # 测试入队性能
            start_time = time.time()
            for i in range(100):
                email_queue.enqueue(
                    recipient=f"test{i}@example.com",
                    subject=f"测试邮件 {i}",
                    content=f"邮件内容 {i}"
                )
            enqueue_time = time.time() - start_time
            
            print(f"邮件入队性能: {100/enqueue_time:.2f} ops/sec")
            
            # 获取队列统计
            stats = email_queue.get_queue_stats()
            print(f"队列状态: {stats['enqueued']} 封邮件待发送")
            
        finally:
            shutil.rmtree(temp_dir)
        
        print("\n✅ 性能测试完成")
        return True
        
    except Exception as e:
        print(f"性能测试失败: {e}")
        return False

def run_integration_tests():
    """运行集成测试"""
    print("=" * 60)
    print("运行集成测试")
    print("=" * 60)
    
    try:
        import tempfile
        import yaml
        import shutil
        from pathlib import Path
        
        # 创建临时测试环境
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # 测试配置文件加载和处理
            print("测试配置文件处理...")
            
            # 创建测试配置
            test_config = {
                'smtp': {
                    'accounts': [
                        {
                            'server': 'smtp.gmail.com',
                            'port': 587,
                            'username': 'test@gmail.com',
                            'password': 'secret_password'
                        }
                    ]
                },
                'llm': {
                    'openai': {
                        'api_key': 'sk-test-api-key',
                        'model': 'gpt-4',
                        'temperature': 0.7
                    }
                },
                'user_groups': [
                    {
                        'group_name': 'test_group',
                        'emails': ['user1@example.com', 'user2@example.com'],
                        'keywords': ['人工智能', '机器学习', '深度学习']
                    }
                ]
            }
            
            config_file = temp_dir / "config.yaml"
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
            
            # 测试配置加载
            from src.config import load_config
            config = load_config(str(config_file))
            
            # 验证配置加载正确
            assert 'smtp' in config
            assert 'llm' in config
            assert 'keyword_to_emails' in config
            assert len(config['keyword_to_emails']['人工智能']) == 2
            
            print("✅ 配置文件加载测试通过")
            
            # 测试敏感数据保护
            print("测试敏感数据保护...")
            
            from src.security import SensitiveDataProtector
            protector = SensitiveDataProtector()
            test_key = b'test-key-32-bytes-long-for-encryption-'
            protector._setup_fernet(test_key)
            
            # 加密配置
            encrypted_config = protector.encrypt_sensitive_data(config)
            
            # 验证敏感数据被加密
            assert encrypted_config['smtp']['accounts'][0]['password'] != 'secret_password'
            assert encrypted_config['llm']['openai']['api_key'] != 'sk-test-api-key'
            
            # 解密配置
            decrypted_config = protector.decrypt_sensitive_data(encrypted_config)
            
            # 验证解密正确
            assert decrypted_config['smtp']['accounts'][0]['password'] == 'secret_password'
            assert decrypted_config['llm']['openai']['api_key'] == 'sk-test-api-key'
            
            print("✅ 敏感数据保护测试通过")
            
            # 测试缓存和日志系统集成
            print("测试缓存和日志系统集成...")
            
            from src.performance import CacheManager
            from src.logging_system import LogManager
            
            # 创建缓存和日志管理器
            cache_dir = temp_dir / "cache"
            log_dir = temp_dir / "logs"
            cache_dir.mkdir()
            log_dir.mkdir()
            
            cache = CacheManager(cache_dir=str(cache_dir), max_size=100)
            log_manager = LogManager(log_dir=str(log_dir))
            
            # 测试带缓存的函数
            @cache.cache_result(ttl=60)
            def cached_function(x):
                log_manager.log_with_context(
                    logger_name="test",
                    level="INFO",
                    message=f"执行缓存函数: {x}",
                    input_value=x
                )
                return x * 2
            
            # 第一次调用
            result1 = cached_function(5)
            assert result1 == 10
            
            # 第二次调用（应该从缓存获取）
            result2 = cached_function(5)
            assert result2 == 10
            
            print("✅ 缓存和日志系统集成测试通过")
            
            # 测试完整的配置保存和加载流程
            print("测试配置保存和加载流程...")
            
            from src.config import save_config
            
            # 保存加密后的配置
            encrypted_config_path = temp_dir / "encrypted_config.yaml"
            protector.save_encrypted_config(config, str(encrypted_config_path))
            
            # 加载加密配置
            loaded_config = protector.load_encrypted_config(str(encrypted_config_path))
            
            # 验证数据完整性
            assert loaded_config['smtp']['accounts'][0]['username'] == 'test@gmail.com'
            assert loaded_config['user_groups'][0]['group_name'] == 'test_group'
            
            print("✅ 配置保存和加载流程测试通过")
            
            print("\n🎉 所有集成测试通过!")
            return True
            
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_memory_tests():
    """运行内存使用测试"""
    print("=" * 60)
    print("运行内存使用测试")
    print("=" * 60)
    
    try:
        import psutil
        import gc
        import tempfile
        import shutil
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"初始内存使用: {initial_memory:.2f} MB")
        
        # 测试缓存内存使用
        print("测试缓存内存使用...")
        temp_dir = tempfile.mkdtemp()
        
        try:
            from src.performance import CacheManager
            
            # 创建大量缓存条目
            cache = CacheManager(cache_dir=temp_dir, max_size=10000)
            
            # 添加大量数据
            for i in range(5000):
                cache.set(f"key_{i}", f"value_" * 100)  # 较大的值
            
            # 测量内存使用
            cache_memory = process.memory_info().rss / 1024 / 1024
            print(f"缓存后内存使用: {cache_memory:.2f} MB")
            print(f"内存增加: {cache_memory - initial_memory:.2f} MB")
            
            # 清理缓存
            cache.clear()
            gc.collect()
            
            # 测量清理后的内存使用
            cleaned_memory = process.memory_info().rss / 1024 / 1024
            print(f"清理后内存使用: {cleaned_memory:.2f} MB")
            print(f"内存释放: {cache_memory - cleaned_memory:.2f} MB")
            
        finally:
            shutil.rmtree(temp_dir)
        
        print("✅ 内存使用测试完成")
        return True
        
    except ImportError:
        print("⚠️  psutil未安装，跳过内存测试")
        return True
    except Exception as e:
        print(f"内存测试失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PubMed Literature Push 测试运行器")
    parser.add_argument('--basic', action='store_true', help='运行基础单元测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--memory', action='store_true', help='运行内存测试')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 如果没有指定测试类型，运行所有测试
    if not any([args.basic, args.performance, args.integration, args.memory, args.all]):
        args.all = True
    
    results = {}
    
    # 运行基础测试
    if args.basic or args.all:
        results['basic'] = run_basic_tests()
        print()
    
    # 运行性能测试
    if args.performance or args.all:
        results['performance'] = run_performance_tests()
        print()
    
    # 运行集成测试
    if args.integration or args.all:
        results['integration'] = run_integration_tests()
        print()
    
    # 运行内存测试
    if args.memory or args.all:
        results['memory'] = run_memory_tests()
        print()
    
    # 输出总结
    print("=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    for test_type, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_type.capitalize():<12}: {status}")
    
    # 计算总体结果
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    print(f"\n总体结果: {passed_tests}/{total_tests} 测试套件通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1

if __name__ == '__main__':
    exit(main())