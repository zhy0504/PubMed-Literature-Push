#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试模块
提供基本的单元测试覆盖
"""

import unittest
import tempfile
import os
import json
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

# 导入被测试的模块
from src.exceptions import (
    PubMedPushError, ConfigurationError, ConfigurationValidationError,
    EmailSendError, LLMServiceError, EncryptionError
)
from src.config import (
    validate_email, validate_smtp_config, validate_llm_config,
    validate_scheduler_config, load_config, save_config
)
from src.security import SensitiveDataProtector
from src.performance import CacheManager, EmailQueue
from src.logging_system import LogManager, LogAnalyzer

class TestExceptions(unittest.TestCase):
    """测试异常类"""
    
    def test_pubmed_push_error(self):
        """测试基础异常类"""
        error = PubMedPushError("测试错误", error_code="TEST_ERROR", detail="测试详情")
        self.assertEqual(str(error), "[TEST_ERROR] 测试错误")
        self.assertEqual(error.error_code, "TEST_ERROR")
        self.assertEqual(error.details, {"detail": "测试详情"})
    
    def test_configuration_error(self):
        """测试配置错误"""
        error = ConfigurationError("配置错误", config_path="/path/to/config.yaml")
        self.assertEqual(error.config_path, "/path/to/config.yaml")
        self.assertEqual(error.error_code, "CONFIG_ERROR")
    
    def test_configuration_validation_error(self):
        """测试配置验证错误"""
        errors = ["错误1", "错误2"]
        error = ConfigurationValidationError("验证失败", validation_errors=errors)
        self.assertEqual(error.validation_errors, errors)
        self.assertEqual(error.error_code, "CONFIG_VALIDATION_ERROR")
    
    def test_email_send_error(self):
        """测试邮件发送错误"""
        error = EmailSendError("邮件发送失败", recipient="test@example.com")
        self.assertEqual(error.recipient, "test@example.com")
        self.assertEqual(error.error_code, "EMAIL_SEND_ERROR")
    
    def test_llm_service_error(self):
        """测试LLM服务错误"""
        error = LLMServiceError("LLM服务错误", provider="openai", model="gpt-4")
        self.assertEqual(error.provider, "openai")
        self.assertEqual(error.model, "gpt-4")
        self.assertEqual(error.error_code, "LLM_SERVICE_ERROR")

class TestConfigValidation(unittest.TestCase):
    """测试配置验证功能"""
    
    def test_validate_email(self):
        """测试邮箱验证"""
        self.assertTrue(validate_email("test@example.com"))
        self.assertTrue(validate_email("user.name+tag@domain.co.uk"))
        self.assertFalse(validate_email("invalid-email"))
        self.assertFalse(validate_email(""))
        self.assertFalse(validate_email(None))
    
    def test_validate_smtp_config(self):
        """测试SMTP配置验证"""
        # 有效配置
        valid_config = {
            'accounts': [
                {
                    'server': 'smtp.gmail.com',
                    'port': 587,
                    'username': 'test@gmail.com',
                    'password': 'password'
                }
            ]
        }
        errors = validate_smtp_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # 无效配置 - 缺少必要字段
        invalid_config = {
            'accounts': [
                {
                    'server': 'smtp.gmail.com',
                    'port': 587
                    # 缺少username和password
                }
            ]
        }
        errors = validate_smtp_config(invalid_config)
        self.assertGreater(len(errors), 0)
        
        # 无效配置 - 端口号超出范围
        invalid_config = {
            'accounts': [
                {
                    'server': 'smtp.gmail.com',
                    'port': 99999,
                    'username': 'test@gmail.com',
                    'password': 'password'
                }
            ]
        }
        errors = validate_smtp_config(invalid_config)
        self.assertGreater(len(errors), 0)
    
    def test_validate_llm_config(self):
        """测试LLM配置验证"""
        # 有效配置
        valid_config = {
            'openai': {
                'api_key': 'sk-test-key',
                'model': 'gpt-4',
                'temperature': 0.7
            }
        }
        errors = validate_llm_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # 无效配置 - 缺少API密钥
        invalid_config = {
            'openai': {
                'model': 'gpt-4',
                'temperature': 0.7
            }
        }
        errors = validate_llm_config(invalid_config)
        self.assertGreater(len(errors), 0)
        
        # 无效配置 - 温度超出范围
        invalid_config = {
            'openai': {
                'api_key': 'sk-test-key',
                'temperature': 3.0  # 超出范围
            }
        }
        errors = validate_llm_config(invalid_config)
        self.assertGreater(len(errors), 0)
    
    def test_validate_scheduler_config(self):
        """测试调度器配置验证"""
        # 有效配置
        valid_config = {
            'run_time': '09:00',
            'delay_between_emails_sec': 60,
            'max_retries': 3
        }
        errors = validate_scheduler_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # 无效配置 - 时间格式错误
        invalid_config = {
            'run_time': '25:00',  # 无效时间
            'delay_between_emails_sec': 60
        }
        errors = validate_scheduler_config(invalid_config)
        self.assertGreater(len(errors), 0)
        
        # 无效配置 - 间隔为负数
        invalid_config = {
            'delay_between_emails_sec': -1
        }
        errors = validate_scheduler_config(invalid_config)
        self.assertGreater(len(errors), 0)

class TestSensitiveDataProtection(unittest.TestCase):
    """测试敏感数据保护功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.protector = SensitiveDataProtector()
        self.test_key = b'test-key-32-bytes-long-for-encryption-'
        self.protector._setup_fernet(self.test_key)
    
    def test_encrypt_decrypt_value(self):
        """测试值加密和解密"""
        original_value = "sensitive_password_123"
        
        # 加密
        encrypted_value = self.protector.encrypt_value(original_value)
        self.assertNotEqual(encrypted_value, original_value)
        
        # 解密
        decrypted_value = self.protector.decrypt_value(encrypted_value)
        self.assertEqual(decrypted_value, original_value)
    
    def test_is_encrypted_value(self):
        """测试加密值检测"""
        original_value = "normal_value"
        encrypted_value = self.protector.encrypt_value(original_value)
        
        self.assertFalse(self.protector.is_encrypted_value(original_value))
        self.assertTrue(self.protector.is_encrypted_value(encrypted_value))
    
    def test_find_sensitive_fields(self):
        """测试敏感字段查找"""
        config = {
            'smtp': {
                'accounts': [
                    {
                        'username': 'test@gmail.com',
                        'password': 'secret_password',
                        'api_key': 'secret_api_key'
                    }
                ]
            },
            'llm': {
                'openai': {
                    'api_key': 'openai_secret_key'
                }
            },
            'normal_field': 'normal_value'
        }
        
        sensitive_paths = self.protector.find_sensitive_fields(config)
        
        # 应该找到敏感字段
        self.assertIn('smtp.accounts[0].password', sensitive_paths)
        self.assertIn('smtp.accounts[0].api_key', sensitive_paths)
        self.assertIn('llm.openai.api_key', sensitive_paths)
        self.assertNotIn('normal_field', sensitive_paths)
    
    def test_encrypt_sensitive_data(self):
        """测试敏感数据加密"""
        config = {
            'smtp': {
                'accounts': [
                    {
                        'username': 'test@gmail.com',
                        'password': 'secret_password'
                    }
                ]
            },
            'normal_field': 'normal_value'
        }
        
        encrypted_config = self.protector.encrypt_sensitive_data(config)
        
        # 敏感数据应该被加密
        self.assertNotEqual(encrypted_config['smtp']['accounts'][0]['password'], 'secret_password')
        # 正常数据应该保持不变
        self.assertEqual(encrypted_config['normal_field'], 'normal_value')
    
    def test_decrypt_sensitive_data(self):
        """测试敏感数据解密"""
        config = {
            'smtp': {
                'accounts': [
                    {
                        'username': 'test@gmail.com',
                        'password': 'secret_password'
                    }
                ]
            }
        }
        
        # 加密
        encrypted_config = self.protector.encrypt_sensitive_data(config)
        
        # 解密
        decrypted_config = self.protector.decrypt_sensitive_data(encrypted_config)
        
        # 应该恢复原始数据
        self.assertEqual(decrypted_config['smtp']['accounts'][0]['password'], 'secret_password')
    
    def test_create_masked_config(self):
        """测试脱敏配置创建"""
        config = {
            'smtp': {
                'password': 'secret_password',
                'username': 'test@gmail.com'
            }
        }
        
        masked_config = self.protector.create_masked_config(config)
        
        # 敏感数据应该被脱敏
        self.assertEqual(masked_config['smtp']['password'], '***MASKED***')
        # 正常数据应该保持不变
        self.assertEqual(masked_config['smtp']['username'], 'test@gmail.com')

class TestCacheManager(unittest.TestCase):
    """测试缓存管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(
            cache_dir=self.temp_dir,
            max_size=10,
            default_ttl=60,
            enable_persistence=True
        )
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_set_get_cache(self):
        """测试缓存设置和获取"""
        key = "test_key"
        value = {"data": "test_value"}
        
        # 设置缓存
        self.cache_manager.set(key, value)
        
        # 获取缓存
        cached_value = self.cache_manager.get(key)
        self.assertEqual(cached_value, value)
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        key = "test_key"
        value = "test_value"
        
        # 设置短期缓存
        self.cache_manager.set(key, value, ttl=1)
        
        # 立即获取应该成功
        self.assertEqual(self.cache_manager.get(key), value)
        
        # 等待过期
        time.sleep(1.1)
        
        # 过期后应该返回None
        self.assertIsNone(self.cache_manager.get(key))
    
    def test_cache_deletion(self):
        """测试缓存删除"""
        key = "test_key"
        value = "test_value"
        
        # 设置缓存
        self.cache_manager.set(key, value)
        self.assertIsNotNone(self.cache_manager.get(key))
        
        # 删除缓存
        result = self.cache_manager.delete(key)
        self.assertTrue(result)
        self.assertIsNone(self.cache_manager.get(key))
    
    def test_cache_stats(self):
        """测试缓存统计"""
        # 设置一些缓存
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        
        # 获取缓存
        self.cache_manager.get("key1")
        self.cache_manager.get("key1")  # 命中两次
        self.cache_manager.get("nonexistent")  # 未命中
        
        stats = self.cache_manager.get_stats()
        
        self.assertEqual(stats['hits'], 2)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['memory_usage'], 2)
    
    def test_cache_decorator(self):
        """测试缓存装饰器"""
        call_count = 0
        
        @self.cache_manager.cache_result(ttl=60)
        def slow_function(x):
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # 模拟耗时操作
            return x * 2
        
        # 第一次调用
        result1 = slow_function(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count, 1)
        
        # 第二次调用应该从缓存获取
        result2 = slow_function(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count, 1)  # 不应该增加

class TestEmailQueue(unittest.TestCase):
    """测试邮件队列"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.email_queue = EmailQueue(
            queue_dir=self.temp_dir,
            max_queue_size=100,
            batch_size=5,
            retry_delay=1
        )
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_enqueue_email(self):
        """测试邮件入队"""
        task_id = self.email_queue.enqueue(
            recipient="test@example.com",
            subject="测试邮件",
            content="这是一封测试邮件",
            priority=1
        )
        
        self.assertIsInstance(task_id, str)
        self.assertEqual(len(self.email_queue.pending_queue), 1)
    
    def test_queue_stats(self):
        """测试队列统计"""
        # 添加几封邮件
        self.email_queue.enqueue("test1@example.com", "主题1", "内容1")
        self.email_queue.enqueue("test2@example.com", "主题2", "内容2")
        
        stats = self.email_queue.get_queue_stats()
        
        self.assertEqual(stats['enqueued'], 2)
        self.assertEqual(stats['pending_size'], 2)
    
    def test_retry_failed_tasks(self):
        """测试重试失败任务"""
        # 添加一个失败的任务
        task_id = self.email_queue.enqueue("test@example.com", "主题", "内容")
        
        # 模拟任务失败
        task = self.email_queue.pending_queue[0]
        task.attempts = task.max_attempts
        self.email_queue.failed_queue.append(task)
        self.email_queue.pending_queue.clear()
        
        # 重试失败任务
        retry_count = self.email_queue.retry_failed_tasks()
        
        self.assertEqual(retry_count, 1)
        self.assertEqual(len(self.email_queue.pending_queue), 1)
        self.assertEqual(len(self.email_queue.failed_queue), 0)

class TestLoggingSystem(unittest.TestCase):
    """测试日志系统"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_manager = LogManager(
            log_dir=self.temp_dir,
            max_file_size=1024 * 1024,  # 1MB
            backup_count=2,
            enable_structlog=True
        )
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_logger(self):
        """测试获取日志器"""
        logger = self.log_manager.get_logger("test_logger")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_logger")
    
    def test_log_with_context(self):
        """测试带上下文的日志记录"""
        from src.logging_system import LogLevel
        
        self.log_manager.log_with_context(
            logger_name="test",
            level=LogLevel.INFO,
            message="测试消息",
            key1="value1",
            key2="value2"
        )
        
        stats = self.log_manager.get_stats()
        self.assertEqual(stats['info_logs'], 1)
    
    def test_log_performance(self):
        """测试性能日志"""
        self.log_manager.log_performance(
            operation="test_operation",
            duration=1.5,
            metadata={"size": 100}
        )
        
        stats = self.log_manager.get_stats()
        self.assertEqual(stats['total_logs'], 1)
    
    def test_set_log_level(self):
        """测试设置日志级别"""
        from src.logging_system import LogLevel
        
        self.log_manager.set_log_level(LogLevel.DEBUG)
        self.assertEqual(self.log_manager.log_level, LogLevel.DEBUG)
    
    @patch('src.logging_system.logging.getLogger')
    def test_log_operation_context_manager(self, mock_get_logger):
        """测试操作日志上下文管理器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with self.log_manager.log_operation("test_operation", "test_logger"):
            pass
        
        # 验证日志调用
        mock_logger.info.assert_called()

class TestLogAnalyzer(unittest.TestCase):
    """测试日志分析器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试日志文件
        self.log_file = Path(self.temp_dir) / "app.log"
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('{"timestamp": "2024-01-01T10:00:00Z", "level": "INFO", "message": "测试消息"}\n')
            f.write('{"timestamp": "2024-01-01T10:01:00Z", "level": "ERROR", "message": "错误消息"}\n')
        
        self.analyzer = LogAnalyzer(self.temp_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_analyze_logs(self):
        """测试日志分析"""
        from datetime import datetime
        
        analysis = self.analyzer.analyze_logs()
        
        self.assertEqual(analysis['total_logs'], 2)
        self.assertEqual(analysis['level_distribution']['INFO'], 1)
        self.assertEqual(analysis['level_distribution']['ERROR'], 1)
        self.assertEqual(len(analysis['error_summary']), 1)

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置文件
        self.config_file = Path(self.temp_dir) / "config.yaml"
        test_config = {
            'smtp': {
                'accounts': [
                    {
                        'server': 'smtp.gmail.com',
                        'port': 587,
                        'username': 'test@gmail.com',
                        'password': 'test_password'
                    }
                ]
            },
            'llm': {
                'openai': {
                    'api_key': 'test_api_key',
                    'model': 'gpt-4',
                    'temperature': 0.7
                }
            },
            'user_groups': [
                {
                    'group_name': 'test_group',
                    'emails': ['test@example.com'],
                    'keywords': ['test']
                }
            ]
        }
        
        import yaml
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading_and_validation(self):
        """测试配置加载和验证"""
        # 测试加载配置
        config = load_config(str(self.config_file))
        
        # 验证配置结构
        self.assertIn('smtp', config)
        self.assertIn('llm', config)
        self.assertIn('user_groups', config)
        self.assertIn('keyword_to_emails', config)
        
        # 验证用户组转换
        self.assertEqual(config['keyword_to_emails']['test'], ['test@example.com'])
    
    def test_config_with_sensitive_data_protection(self):
        """测试配置与敏感数据保护的集成"""
        # 加载配置
        config = load_config(str(self.config_file))
        
        # 创建敏感数据保护器
        protector = SensitiveDataProtector()
        test_key = b'test-key-32-bytes-long-for-encryption-'
        protector._setup_fernet(test_key)
        
        # 加密敏感数据
        encrypted_config = protector.encrypt_sensitive_data(config)
        
        # 验证敏感数据被加密
        self.assertNotEqual(
            encrypted_config['smtp']['accounts'][0]['password'],
            'test_password'
        )
        
        # 解密并验证
        decrypted_config = protector.decrypt_sensitive_data(encrypted_config)
        self.assertEqual(
            decrypted_config['smtp']['accounts'][0]['password'],
            'test_password'
        )

def run_tests():
    """运行所有测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestExceptions,
        TestConfigValidation,
        TestSensitiveDataProtection,
        TestCacheManager,
        TestEmailQueue,
        TestLoggingSystem,
        TestLogAnalyzer,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出结果
    print(f"\n测试结果:")
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)