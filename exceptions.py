#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PubMed Literature Push 自定义异常类
定义项目中使用的各种异常类型
"""

from typing import Optional, Dict, Any


class PubMedPushError(Exception):
    """PubMed Push 系统异常基类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, **kwargs):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = kwargs
        
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(PubMedPushError):
    """配置相关错误"""
    
    def __init__(self, message: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_path = config_path


class ConfigurationValidationError(ConfigurationError):
    """配置验证错误"""
    
    def __init__(self, message: str, validation_errors: Optional[list] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_VALIDATION_ERROR", **kwargs)
        self.validation_errors = validation_errors or []


class ConfigurationFileNotFoundError(ConfigurationError):
    """配置文件未找到错误"""
    
    def __init__(self, config_path: str, **kwargs):
        message = f"配置文件未找到: {config_path}"
        super().__init__(message, error_code="CONFIG_FILE_NOT_FOUND", **kwargs)


class PubMedAPIError(PubMedPushError):
    """PubMed API 相关错误"""
    
    def __init__(self, message: str, api_endpoint: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="PUBMED_API_ERROR", **kwargs)
        self.api_endpoint = api_endpoint


class PubMedRateLimitError(PubMedAPIError):
    """PubMed API 速率限制错误"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="PUBMED_RATE_LIMIT", **kwargs)
        self.retry_after = retry_after


class PubMedSearchError(PubMedAPIError):
    """PubMed 搜索错误"""
    
    def __init__(self, message: str, search_term: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="PUBMED_SEARCH_ERROR", **kwargs)
        self.search_term = search_term


class EmailSendError(PubMedPushError):
    """邮件发送相关错误"""
    
    def __init__(self, message: str, recipient: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="EMAIL_SEND_ERROR", **kwargs)
        self.recipient = recipient


class SMTPAuthenticationError(EmailSendError):
    """SMTP 认证错误"""
    
    def __init__(self, message: str, smtp_server: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="SMTP_AUTH_ERROR", **kwargs)
        self.smtp_server = smtp_server


class SMTPConnectionError(EmailSendError):
    """SMTP 连接错误"""
    
    def __init__(self, message: str, smtp_server: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="SMTP_CONNECTION_ERROR", **kwargs)
        self.smtp_server = smtp_server


class LLMServiceError(PubMedPushError):
    """LLM 服务相关错误"""
    
    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="LLM_SERVICE_ERROR", **kwargs)
        self.provider = provider
        self.model = model


class LLMRateLimitError(LLMServiceError):
    """LLM 服务速率限制错误"""
    
    def __init__(self, message: str, provider: Optional[str] = None, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="LLM_RATE_LIMIT", **kwargs)
        self.retry_after = retry_after


class LLMAuthenticationError(LLMServiceError):
    """LLM 服务认证错误"""
    
    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="LLM_AUTH_ERROR", **kwargs)


class DataProcessingError(PubMedPushError):
    """数据处理相关错误"""
    
    def __init__(self, message: str, data_file: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_PROCESSING_ERROR", **kwargs)
        self.data_file = data_file


class DataFileNotFoundError(DataProcessingError):
    """数据文件未找到错误"""
    
    def __init__(self, data_file: str, **kwargs):
        message = f"数据文件未找到: {data_file}"
        super().__init__(message, error_code="DATA_FILE_NOT_FOUND", **kwargs)


class DataFormatError(DataProcessingError):
    """数据格式错误"""
    
    def __init__(self, message: str, expected_format: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_FORMAT_ERROR", **kwargs)
        self.expected_format = expected_format


class FileSystemError(PubMedPushError):
    """文件系统相关错误"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="FILE_SYSTEM_ERROR", **kwargs)
        self.file_path = file_path


class PermissionError(FileSystemError):
    """权限错误"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="PERMISSION_ERROR", **kwargs)


class NetworkError(PubMedPushError):
    """网络相关错误"""
    
    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="NETWORK_ERROR", **kwargs)
        self.url = url


class TimeoutError(NetworkError):
    """超时错误"""
    
    def __init__(self, message: str, timeout_seconds: Optional[float] = None, **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        self.timeout_seconds = timeout_seconds


class SchedulerError(PubMedPushError):
    """任务调度器相关错误"""
    
    def __init__(self, message: str, task_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="SCHEDULER_ERROR", **kwargs)
        self.task_name = task_name


class EncryptionError(PubMedPushError):
    """加密相关错误"""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="ENCRYPTION_ERROR", **kwargs)
        self.operation = operation


class GUIError(PubMedPushError):
    """GUI 相关错误"""
    
    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="GUI_ERROR", **kwargs)
        self.component = component


def handle_exception(func):
    """异常处理装饰器"""
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PubMedPushError as e:
            # 已知的业务异常，直接抛出
            raise
        except FileNotFoundError as e:
            raise FileSystemError(f"文件未找到: {str(e)}")
        except PermissionError as e:
            raise PermissionError(f"权限不足: {str(e)}")
        except ConnectionError as e:
            raise NetworkError(f"网络连接错误: {str(e)}")
        except TimeoutError as e:
            raise TimeoutError(f"操作超时: {str(e)}")
        except ValueError as e:
            raise ConfigurationError(f"配置错误: {str(e)}")
        except Exception as e:
            # 未预期的异常，包装为通用异常
            raise PubMedPushError(f"未预期的错误: {str(e)}", error_code="UNEXPECTED_ERROR")
    
    return wrapper


def log_and_raise(logger, exception: PubMedPushError, level: str = "error"):
    """记录日志并抛出异常"""
    
    log_method = getattr(logger, level.lower(), logger.error)
    
    # 构建日志消息
    log_message = {
        "error_code": exception.error_code,
        "message": exception.message,
        "details": exception.details
    }
    
    # 添加特定异常类型的额外信息
    if hasattr(exception, 'config_path'):
        log_message["config_path"] = exception.config_path
    if hasattr(exception, 'recipient'):
        log_message["recipient"] = exception.recipient
    if hasattr(exception, 'provider'):
        log_message["provider"] = exception.provider
    
    log_method("Exception occurred", **log_message)
    raise exception


if __name__ == "__main__":
    # 测试异常类
    try:
        raise ConfigurationError("测试配置错误", config_path="config.yaml")
    except ConfigurationError as e:
        print(f"捕获到配置错误: {e}")
        print(f"错误代码: {e.error_code}")
        print(f"配置路径: {e.config_path}")
    
    try:
        raise EmailSendError("邮件发送失败", recipient="test@example.com")
    except EmailSendError as e:
        print(f"捕获到邮件错误: {e}")
        print(f"收件人: {e.recipient}")