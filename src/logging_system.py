#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志模块
提供统一的日志记录、格式化和分析功能
"""

import os
import sys
import json
import logging
import logging.handlers
import traceback
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
from enum import Enum
import structlog
from contextlib import contextmanager
import threading
from functools import wraps

from .exceptions import FileSystemError

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogFormatter:
    """日志格式化器"""
    
    def __init__(self, include_timestamp: bool = True, include_level: bool = True,
                 include_logger: bool = True, include_thread: bool = False,
                 include_function: bool = True, include_line_number: bool = True):
        """
        初始化日志格式化器
        
        Args:
            include_timestamp: 是否包含时间戳
            include_level: 是否包含日志级别
            include_logger: 是否包含日志器名称
            include_thread: 是否包含线程信息
            include_function: 是否包含函数名
            include_line_number: 是否包含行号
        """
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_thread = include_thread
        self.include_function = include_function
        self.include_line_number = include_line_number
    
    def format_structlog(self, logger, method_name, event_dict) -> Dict[str, Any]:
        """格式化structlog事件"""
        result = {}
        
        # 添加时间戳
        if self.include_timestamp:
            result['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # 添加日志级别
        if self.include_level:
            result['level'] = method_name.upper()
        
        # 添加日志器名称
        if self.include_logger:
            result['logger'] = logger.name
        
        # 添加线程信息
        if self.include_thread:
            result['thread_id'] = threading.get_ident()
            result['thread_name'] = threading.current_thread().name
        
        # 添加位置信息
        if self.include_function or self.include_line_number:
            frame = sys._getframe(2)
            if self.include_function:
                result['function'] = frame.f_code.co_name
            if self.include_line_number:
                result['line_number'] = frame.f_lineno
        
        # 添加事件信息
        if 'event' in event_dict:
            result['message'] = event_dict.pop('event')
        
        # 添加其他字段
        result.update(event_dict)
        
        return result
    
    def format_python_logging(self, record: logging.LogRecord) -> Dict[str, Any]:
        """格式化Python标准日志记录"""
        result = {}
        
        # 添加时间戳
        if self.include_timestamp:
            result['timestamp'] = datetime.utcfromtimestamp(record.created).isoformat() + 'Z'
        
        # 添加日志级别
        if self.include_level:
            result['level'] = record.levelname
        
        # 添加日志器名称
        if self.include_logger:
            result['logger'] = record.name
        
        # 添加线程信息
        if self.include_thread:
            result['thread_id'] = record.thread
            result['thread_name'] = record.threadName
        
        # 添加位置信息
        if self.include_function:
            result['function'] = record.funcName
        if self.include_line_number:
            result['line_number'] = record.lineno
        
        # 添加消息
        result['message'] = record.getMessage()
        
        # 添加异常信息
        if record.exc_info:
            result['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return result

class JSONFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def __init__(self, formatter: LogFormatter):
        super().__init__()
        self.formatter = formatter
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON"""
        log_dict = self.formatter.format_python_logging(record)
        return json.dumps(log_dict, ensure_ascii=False, default=str)

class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def __init__(self, formatter: LogFormatter):
        super().__init__()
        self.formatter = formatter
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为彩色文本"""
        log_dict = self.formatter.format_python_logging(record)
        
        # 构建彩色消息
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        message_parts = []
        
        if 'timestamp' in log_dict:
            message_parts.append(f"{log_dict['timestamp']}")
        
        if 'level' in log_dict:
            message_parts.append(f"{level_color}[{log_dict['level']}]{reset_color}")
        
        if 'logger' in log_dict:
            message_parts.append(f"[{log_dict['logger']}]")
        
        if 'function' in log_dict and 'line_number' in log_dict:
            message_parts.append(f"{log_dict['function']}:{log_dict['line_number']}")
        
        if 'message' in log_dict:
            message_parts.append(log_dict['message'])
        
        # 添加额外字段
        extra_fields = {k: v for k, v in log_dict.items() 
                       if k not in ['timestamp', 'level', 'logger', 'function', 'line_number', 'message']}
        if extra_fields:
            message_parts.append(f"({json.dumps(extra_fields, ensure_ascii=False)})")
        
        return ' '.join(message_parts)

class LogManager:
    """日志管理器"""
    
    def __init__(self, log_dir: str = "logs", max_file_size: int = 10 * 1024 * 1024,
                 backup_count: int = 5, log_level: LogLevel = LogLevel.INFO,
                 enable_structlog: bool = True):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录
            max_file_size: 最大文件大小（字节）
            backup_count: 备份文件数量
            log_level: 日志级别
            enable_structlog: 是否启用structlog
        """
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.log_level = log_level
        self.enable_structlog = enable_structlog
        
        # 日志器字典
        self.loggers: Dict[str, logging.Logger] = {}
        
        # 统计信息
        self.stats = {
            'total_logs': 0,
            'debug_logs': 0,
            'info_logs': 0,
            'warning_logs': 0,
            'error_logs': 0,
            'critical_logs': 0
        }
        
        # 初始化
        self._initialize_logging()
    
    def _initialize_logging(self) -> None:
        """初始化日志系统"""
        try:
            # 创建日志目录
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化格式化器
            self.formatter = LogFormatter()
            
            # 配置structlog
            if self.enable_structlog:
                structlog.configure(
                    processors=[
                        structlog.stdlib.filter_by_level,
                        structlog.stdlib.add_logger_name,
                        structlog.stdlib.add_log_level,
                        structlog.stdlib.PositionalArgumentsFormatter(),
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.processors.StackInfoRenderer(),
                        structlog.processors.format_exc_info,
                        self.formatter.format_structlog
                    ],
                    context_class=dict,
                    logger_factory=structlog.stdlib.LoggerFactory(),
                    wrapper_class=structlog.stdlib.BoundLogger,
                    cache_logger_on_first_use=True,
                )
            
            # 配置根日志器
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, self.log_level.value))
            
            # 清除现有处理器
            root_logger.handlers.clear()
            
            # 添加控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.log_level.value))
            console_handler.setFormatter(ColoredFormatter(self.formatter))
            root_logger.addHandler(console_handler)
            
            # 添加文件处理器
            self._add_file_handlers(root_logger)
            
            logging.info("日志系统初始化完成")
            
        except Exception as e:
            raise FileSystemError(f"日志系统初始化失败: {e}")
    
    def _add_file_handlers(self, logger: logging.Logger) -> None:
        """添加文件处理器"""
        # 主日志文件
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "app.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(getattr(logging, self.log_level.value))
        main_handler.setFormatter(JSONFormatter(self.formatter))
        logger.addHandler(main_handler)
        
        # 错误日志文件
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter(self.formatter))
        logger.addHandler(error_handler)
        
        # 性能日志文件
        perf_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "performance.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(JSONFormatter(self.formatter))
        
        # 性能日志过滤器
        class PerformanceFilter(logging.Filter):
            def filter(self, record):
                return hasattr(record, 'performance') or 'performance' in record.__dict__.lower()
        
        perf_handler.addFilter(PerformanceFilter())
        logger.addHandler(perf_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            日志器实例
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]
    
    def get_structlog_logger(self, name: str):
        """
        获取structlog日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            structlog日志器实例
        """
        if not self.enable_structlog:
            return self.get_logger(name)
        return structlog.get_logger(name)
    
    def log_with_context(self, logger_name: str, level: LogLevel, message: str, 
                        **context) -> None:
        """
        带上下文的日志记录
        
        Args:
            logger_name: 日志器名称
            level: 日志级别
            message: 日志消息
            **context: 上下文信息
        """
        logger = self.get_logger(logger_name)
        log_method = getattr(logger, level.value.lower())
        
        # 添加上下文到extra字段
        extra = {'context': context}
        
        log_method(message, extra=extra)
        
        # 更新统计信息
        self.stats['total_logs'] += 1
        self.stats[f'{level.value.lower()}_logs'] += 1
    
    def log_performance(self, operation: str, duration: float, **metadata) -> None:
        """
        记录性能日志
        
        Args:
            operation: 操作名称
            duration: 持续时间（秒）
            **metadata: 元数据
        """
        logger = self.get_logger('performance')
        logger.info(
            f"性能: {operation} 耗时 {duration:.3f}秒",
            extra={
                'performance': True,
                'operation': operation,
                'duration': duration,
                'metadata': metadata
            }
        )
    
    def log_error_with_traceback(self, logger_name: str, error: Exception, 
                               context: Optional[Dict[str, Any]] = None) -> None:
        """
        记录错误和堆栈跟踪
        
        Args:
            logger_name: 日志器名称
            error: 异常对象
            context: 上下文信息
        """
        logger = self.get_logger(logger_name)
        
        extra = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if context:
            extra['context'] = context
        
        logger.error(f"异常: {type(error).__name__}: {str(error)}", extra=extra)
        
        # 更新统计信息
        self.stats['total_logs'] += 1
        self.stats['error_logs'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        return self.stats.copy()
    
    def set_log_level(self, level: LogLevel) -> None:
        """
        设置日志级别
        
        Args:
            level: 日志级别
        """
        self.log_level = level
        logging.getLogger().setLevel(getattr(logging, level.value))
        
        # 更新所有处理器的级别
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                if 'error.log' in str(handler.baseFilename):
                    handler.setLevel(logging.ERROR)
                else:
                    handler.setLevel(getattr(logging, level.value))
            else:
                handler.setLevel(getattr(logging, level.value))
    
    @contextmanager
    def log_operation(self, operation_name: str, logger_name: str = 'app', 
                     log_level: LogLevel = LogLevel.INFO):
        """
        操作日志上下文管理器
        
        Args:
            operation_name: 操作名称
            logger_name: 日志器名称
            log_level: 日志级别
        """
        logger = self.get_logger(logger_name)
        start_time = time.time()
        
        log_method = getattr(logger, log_level.value.lower())
        log_method(f"开始操作: {operation_name}")
        
        try:
            yield logger
            duration = time.time() - start_time
            log_method(f"完成操作: {operation_name}，耗时 {duration:.3f}秒")
            self.log_performance(operation_name, duration)
        except Exception as e:
            duration = time.time() - start_time
            log_method(f"操作失败: {operation_name}，耗时 {duration:.3f}秒")
            self.log_error_with_traceback(logger_name, e, {'operation': operation_name})
            raise

def performance_logger(operation_name: str):
    """
    性能日志装饰器
    
    Args:
        operation_name: 操作名称
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger('performance')
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"性能: {operation_name} 耗时 {duration:.3f}秒",
                    extra={
                        'performance': True,
                        'operation': operation_name,
                        'duration': duration,
                        'success': True,
                        'function': func.__name__
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"性能: {operation_name} 耗时 {duration:.3f}秒",
                    extra={
                        'performance': True,
                        'operation': operation_name,
                        'duration': duration,
                        'success': False,
                        'function': func.__name__,
                        'error': str(e)
                    }
                )
                raise
        return wrapper
    return decorator

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        初始化日志分析器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
    
    def analyze_logs(self, start_date: Optional[datetime] = None, 
                    end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        分析日志文件
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            分析结果
        """
        analysis = {
            'total_logs': 0,
            'level_distribution': {},
            'hourly_distribution': {},
            'error_summary': [],
            'performance_summary': {},
            'top_errors': []
        }
        
        # 分析主日志文件
        main_log = self.log_dir / "app.log"
        if main_log.exists():
            self._analyze_log_file(main_log, analysis, start_date, end_date)
        
        # 分析错误日志文件
        error_log = self.log_dir / "error.log"
        if error_log.exists():
            self._analyze_log_file(error_log, analysis, start_date, end_date)
        
        return analysis
    
    def _analyze_log_file(self, log_file: Path, analysis: Dict[str, Any], 
                         start_date: Optional[datetime], end_date: Optional[datetime]) -> None:
        """分析单个日志文件"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # 检查时间范围
                        if 'timestamp' in log_entry:
                            log_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                            if start_date and log_time < start_date:
                                continue
                            if end_date and log_time > end_date:
                                continue
                        
                        # 统计总数
                        analysis['total_logs'] += 1
                        
                        # 级别分布
                        level = log_entry.get('level', 'UNKNOWN')
                        analysis['level_distribution'][level] = analysis['level_distribution'].get(level, 0) + 1
                        
                        # 小时分布
                        if 'timestamp' in log_entry:
                            hour = log_time.hour
                            analysis['hourly_distribution'][hour] = analysis['hourly_distribution'].get(hour, 0) + 1
                        
                        # 错误分析
                        if level in ['ERROR', 'CRITICAL']:
                            error_info = {
                                'timestamp': log_entry.get('timestamp'),
                                'message': log_entry.get('message'),
                                'error_type': log_entry.get('error_type'),
                                'logger': log_entry.get('logger')
                            }
                            analysis['error_summary'].append(error_info)
                        
                        # 性能分析
                        if log_entry.get('performance'):
                            perf_data = {
                                'operation': log_entry.get('operation'),
                                'duration': log_entry.get('duration'),
                                'success': log_entry.get('success', True)
                            }
                            analysis['performance_summary'].append(perf_data)
                        
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            # 统计最常见错误
            error_counts = {}
            for error in analysis['error_summary']:
                error_key = f"{error.get('error_type', 'Unknown')}: {error.get('message', 'No message')[:50]}"
                error_counts[error_key] = error_counts.get(error_key, 0) + 1
            
            analysis['top_errors'] = sorted(
                error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
        except Exception as e:
            logging.error(f"分析日志文件失败: {e}")

# 全局实例
_default_log_manager = None

def get_default_log_manager() -> LogManager:
    """获取默认的日志管理器"""
    global _default_log_manager
    if _default_log_manager is None:
        _default_log_manager = LogManager()
    return _default_log_manager

def get_logger(name: str) -> logging.Logger:
    """获取日志器的便捷函数"""
    return get_default_log_manager().get_logger(name)

def get_structlog_logger(name: str):
    """获取structlog日志器的便捷函数"""
    return get_default_log_manager().get_structlog_logger(name)

# 为了兼容性，添加常用的日志函数
def log_info(message: str, **context) -> None:
    """信息日志"""
    get_default_log_manager().log_with_context('app', LogLevel.INFO, message, **context)

def log_error(message: str, **context) -> None:
    """错误日志"""
    get_default_log_manager().log_with_context('app', LogLevel.ERROR, message, **context)

def log_warning(message: str, **context) -> None:
    """警告日志"""
    get_default_log_manager().log_with_context('app', LogLevel.WARNING, message, **context)

def log_debug(message: str, **context) -> None:
    """调试日志"""
    get_default_log_manager().log_with_context('app', LogLevel.DEBUG, message, **context)

if __name__ == '__main__':
    # 测试代码
    import time
    
    # 初始化日志系统
    log_manager = get_default_log_manager()
    
    # 测试基本日志
    logger = get_logger('test')
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    
    # 测试结构化日志
    struct_logger = get_structlog_logger('test_struct')
    struct_logger.info("结构化日志", key1="value1", key2="value2")
    
    # 测试性能日志装饰器
    @performance_logger("测试函数")
    def test_function():
        time.sleep(0.1)
        return "测试结果"
    
    result = test_function()
    print(f"函数结果: {result}")
    
    # 测试操作日志上下文
    with log_manager.log_operation("测试操作"):
        time.sleep(0.2)
    
    # 查看统计信息
    print("日志统计:", log_manager.get_stats())