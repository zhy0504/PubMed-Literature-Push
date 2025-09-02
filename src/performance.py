#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化模块
提供缓存机制和邮件队列功能，提升系统性能
"""

import os
import json
import time
import threading
import pickle
import hashlib
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
import queue
import sqlite3
from contextlib import contextmanager

from .exceptions import DataProcessingError, FileSystemError

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hit_count: int = 0
    last_accessed: float = 0

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_size: int = 1000, 
                 default_ttl: int = 3600, enable_persistence: bool = True):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
            enable_persistence: 是否启用持久化
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_persistence = enable_persistence
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        
        # 初始化缓存
        self._initialize_cache()
        
        # 启动清理线程
        self._start_cleanup_thread()
    
    def _initialize_cache(self) -> None:
        """初始化缓存"""
        try:
            if self.enable_persistence:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                
                # 初始化SQLite数据库
                self.db_path = self.cache_dir / "cache.db"
                self._init_database()
                
                # 加载持久化缓存
                self._load_persistent_cache()
            
            logging.info(f"缓存管理器初始化完成，目录: {self.cache_dir}")
        except Exception as e:
            logging.warning(f"缓存初始化失败: {e}")
            self.enable_persistence = False
    
    def _init_database(self) -> None:
        """初始化SQLite数据库"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value BLOB,
                        created_at REAL,
                        expires_at REAL,
                        hit_count INTEGER,
                        last_accessed REAL
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)')
                conn.commit()
        except Exception as e:
            raise FileSystemError(f"初始化缓存数据库失败: {e}")
    
    def _load_persistent_cache(self) -> None:
        """加载持久化缓存"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key, value, created_at, expires_at, hit_count, last_accessed
                    FROM cache_entries
                    WHERE expires_at > ?
                ''', (time.time(),))
                
                for row in cursor.fetchall():
                    key, value_blob, created_at, expires_at, hit_count, last_accessed = row
                    try:
                        value = pickle.loads(value_blob)
                        entry = CacheEntry(
                            key=key,
                            value=value,
                            created_at=created_at,
                            expires_at=expires_at,
                            hit_count=hit_count,
                            last_accessed=last_accessed
                        )
                        self.memory_cache[key] = entry
                    except Exception as e:
                        logging.warning(f"加载缓存条目失败 {key}: {e}")
                
                self.stats['size'] = len(self.memory_cache)
                logging.info(f"加载了 {len(self.memory_cache)} 个持久化缓存条目")
        except Exception as e:
            logging.warning(f"加载持久化缓存失败: {e}")
    
    def _start_cleanup_thread(self) -> None:
        """启动清理线程"""
        def cleanup_worker():
            while True:
                time.sleep(60)  # 每分钟清理一次
                try:
                    self.cleanup_expired()
                except Exception as e:
                    logging.error(f"缓存清理失败: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 创建参数的哈希值
        args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
        kwargs_str = json.dumps(kwargs, sort_keys=True)
        combined = f"{func_name}:{args_str}:{kwargs_str}"
        
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _evict_if_needed(self) -> None:
        """如果需要，淘汰缓存条目"""
        with self.lock:
            if len(self.memory_cache) >= self.max_size:
                # LRU淘汰策略
                sorted_entries = sorted(
                    self.memory_cache.values(),
                    key=lambda x: x.last_accessed or x.created_at
                )
                
                # 淘汰20%的条目
                evict_count = int(self.max_size * 0.2)
                for entry in sorted_entries[:evict_count]:
                    del self.memory_cache[entry.key]
                    if self.enable_persistence:
                        self._remove_from_database(entry.key)
                
                self.stats['evictions'] += evict_count
                self.stats['size'] = len(self.memory_cache)
                logging.info(f"淘汰了 {evict_count} 个缓存条目")
    
    def _remove_from_database(self, key: str) -> None:
        """从数据库中删除条目"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                conn.commit()
        except Exception as e:
            logging.warning(f"从数据库删除缓存条目失败 {key}: {e}")
    
    def _save_to_database(self, entry: CacheEntry) -> None:
        """保存条目到数据库"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                value_blob = pickle.dumps(entry.value)
                conn.execute('''
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, created_at, expires_at, hit_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entry.key,
                    value_blob,
                    entry.created_at,
                    entry.expires_at,
                    entry.hit_count,
                    entry.last_accessed
                ))
                conn.commit()
        except Exception as e:
            logging.warning(f"保存缓存条目到数据库失败 {entry.key}: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期返回None
        """
        with self.lock:
            entry = self.memory_cache.get(key)
            
            if entry is None:
                self.stats['misses'] += 1
                return None
            
            # 检查是否过期
            if time.time() > entry.expires_at:
                del self.memory_cache[key]
                if self.enable_persistence:
                    self._remove_from_database(key)
                self.stats['misses'] += 1
                self.stats['size'] = len(self.memory_cache)
                return None
            
            # 更新访问信息
            entry.hit_count += 1
            entry.last_accessed = time.time()
            self.stats['hits'] += 1
            
            # 异步更新数据库
            if self.enable_persistence:
                threading.Thread(
                    target=self._save_to_database,
                    args=(entry,),
                    daemon=True
                ).start()
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为None使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl
        
        current_time = time.time()
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=current_time,
            expires_at=current_time + ttl
        )
        
        with self.lock:
            self.memory_cache[key] = entry
            self.stats['size'] = len(self.memory_cache)
            
            # 淘汰旧条目
            self._evict_if_needed()
            
            # 异步保存到数据库
            if self.enable_persistence:
                threading.Thread(
                    target=self._save_to_database,
                    args=(entry,),
                    daemon=True
                ).start()
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self.memory_cache:
                del self.memory_cache[key]
                if self.enable_persistence:
                    self._remove_from_database(key)
                self.stats['size'] = len(self.memory_cache)
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.memory_cache.clear()
            if self.enable_persistence:
                try:
                    with sqlite3.connect(str(self.db_path)) as conn:
                        conn.execute('DELETE FROM cache_entries')
                        conn.commit()
                except Exception as e:
                    logging.warning(f"清空缓存数据库失败: {e}")
            
            self.stats['size'] = 0
            logging.info("缓存已清空")
    
    def cleanup_expired(self) -> int:
        """
        清理过期条目
        
        Returns:
            清理的条目数量
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if current_time > entry.expires_at
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                if self.enable_persistence:
                    self._remove_from_database(key)
            
            if expired_keys:
                self.stats['size'] = len(self.memory_cache)
                logging.info(f"清理了 {len(expired_keys)} 个过期缓存条目")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            return {
                **self.stats,
                'hit_rate': hit_rate,
                'memory_usage': len(self.memory_cache),
                'max_size': self.max_size
            }
    
    def cache_result(self, ttl: Optional[int] = None):
        """
        缓存函数结果的装饰器
        
        Args:
            ttl: 过期时间（秒）
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                key = self._generate_key(func.__name__, *args, **kwargs)
                
                # 尝试从缓存获取
                result = self.get(key)
                if result is not None:
                    return result
                
                # 执行函数并缓存结果
                try:
                    result = func(*args, **kwargs)
                    self.set(key, result, ttl)
                    return result
                except Exception as e:
                    logging.warning(f"函数执行失败，不缓存结果: {e}")
                    raise
            
            return wrapper
        return decorator

@dataclass
class EmailTask:
    """邮件任务"""
    id: str
    recipient: str
    subject: str
    content: str
    html_content: Optional[str] = None
    priority: int = 0  # 0=普通, 1=高, 2=紧急
    created_at: float = 0
    attempts: int = 0
    max_attempts: int = 3
    delay_until: float = 0
    smtp_account_index: int = 0  # 使用的SMTP账号索引
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()

class EmailQueue:
    """邮件队列"""
    
    def __init__(self, queue_dir: str = "email_queue", max_queue_size: int = 10000,
                 batch_size: int = 10, retry_delay: int = 300):
        """
        初始化邮件队列
        
        Args:
            queue_dir: 队列目录
            max_queue_size: 最大队列大小
            batch_size: 批量处理大小
            retry_delay: 重试延迟（秒）
        """
        self.queue_dir = Path(queue_dir)
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.retry_delay = retry_delay
        
        # 内存队列
        self.pending_queue = deque()
        self.processing_queue = {}
        self.failed_queue = deque()
        
        # 线程锁
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'enqueued': 0,
            'processed': 0,
            'failed': 0,
            'retried': 0,
            'queue_size': 0
        }
        
        # 初始化队列
        self._initialize_queue()
        
        # 启动工作线程
        self._start_worker_threads()
    
    def _initialize_queue(self) -> None:
        """初始化队列"""
        try:
            self.queue_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化SQLite数据库
            self.db_path = self.queue_dir / "queue.db"
            self._init_database()
            
            # 加载持久化队列
            self._load_persistent_queue()
            
            logging.info(f"邮件队列初始化完成，目录: {self.queue_dir}")
        except Exception as e:
            logging.error(f"邮件队列初始化失败: {e}")
            raise
    
    def _init_database(self) -> None:
        """初始化队列数据库"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS email_queue (
                        id TEXT PRIMARY KEY,
                        recipient TEXT,
                        subject TEXT,
                        content TEXT,
                        html_content TEXT,
                        priority INTEGER,
                        created_at REAL,
                        attempts INTEGER,
                        max_attempts INTEGER,
                        delay_until REAL,
                        smtp_account_index INTEGER,
                        status TEXT,
                        error_message TEXT
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON email_queue(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_priority ON email_queue(priority)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_delay_until ON email_queue(delay_until)')
                conn.commit()
        except Exception as e:
            raise FileSystemError(f"初始化队列数据库失败: {e}")
    
    def _load_persistent_queue(self) -> None:
        """加载持久化队列"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, recipient, subject, content, html_content, priority,
                           created_at, attempts, max_attempts, delay_until, smtp_account_index
                    FROM email_queue
                    WHERE status = 'pending' AND delay_until <= ?
                    ORDER BY priority DESC, created_at ASC
                ''', (time.time(),))
                
                for row in cursor.fetchall():
                    task = EmailTask(
                        id=row[0],
                        recipient=row[1],
                        subject=row[2],
                        content=row[3],
                        html_content=row[4],
                        priority=row[5],
                        created_at=row[6],
                        attempts=row[7],
                        max_attempts=row[8],
                        delay_until=row[9],
                        smtp_account_index=row[10]
                    )
                    self.pending_queue.append(task)
                
                self.stats['queue_size'] = len(self.pending_queue)
                logging.info(f"加载了 {len(self.pending_queue)} 个待处理邮件任务")
        except Exception as e:
            logging.warning(f"加载持久化队列失败: {e}")
    
    def _start_worker_threads(self) -> None:
        """启动工作线程"""
        def worker():
            while True:
                try:
                    self.process_batch()
                    time.sleep(5)  # 每5秒处理一次
                except Exception as e:
                    logging.error(f"邮件队列工作线程错误: {e}")
                    time.sleep(10)
        
        # 启动多个工作线程
        for i in range(3):
            worker_thread = threading.Thread(target=worker, daemon=True)
            worker_thread.name = f"EmailWorker-{i}"
            worker_thread.start()
        
        logging.info("邮件队列工作线程已启动")
    
    def enqueue(self, recipient: str, subject: str, content: str, 
                html_content: Optional[str] = None, priority: int = 0,
                smtp_account_index: int = 0) -> str:
        """
        添加邮件到队列
        
        Args:
            recipient: 收件人
            subject: 主题
            content: 内容
            html_content: HTML内容
            priority: 优先级
            smtp_account_index: SMTP账号索引
            
        Returns:
            任务ID
        """
        with self.lock:
            if len(self.pending_queue) >= self.max_queue_size:
                raise DataProcessingError("邮件队列已满")
            
            task_id = hashlib.md5(f"{recipient}:{subject}:{time.time()}".encode()).hexdigest()
            task = EmailTask(
                id=task_id,
                recipient=recipient,
                subject=subject,
                content=content,
                html_content=html_content,
                priority=priority,
                smtp_account_index=smtp_account_index
            )
            
            self.pending_queue.append(task)
            self.stats['enqueued'] += 1
            self.stats['queue_size'] = len(self.pending_queue)
            
            # 按优先级排序
            self.pending_queue = deque(sorted(self.pending_queue, key=lambda x: (-x.priority, x.created_at)))
            
            # 持久化到数据库
            self._save_task_to_database(task, 'pending')
            
            logging.info(f"邮件任务已加入队列: {task_id} -> {recipient}")
            return task_id
    
    def _save_task_to_database(self, task: EmailTask, status: str, error_message: str = "") -> None:
        """保存任务到数据库"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO email_queue 
                    (id, recipient, subject, content, html_content, priority,
                     created_at, attempts, max_attempts, delay_until, smtp_account_index, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id, task.recipient, task.subject, task.content, task.html_content,
                    task.priority, task.created_at, task.attempts, task.max_attempts,
                    task.delay_until, task.smtp_account_index, status, error_message
                ))
                conn.commit()
        except Exception as e:
            logging.warning(f"保存邮件任务到数据库失败 {task.id}: {e}")
    
    def process_batch(self) -> int:
        """
        处理一批邮件任务
        
        Returns:
            处理的任务数量
        """
        if not self.pending_queue:
            return 0
        
        processed_count = 0
        current_time = time.time()
        
        with self.lock:
            # 获取可处理的一批任务
            batch = []
            while len(batch) < self.batch_size and self.pending_queue:
                task = self.pending_queue[0]
                if task.delay_until > current_time:
                    break
                
                batch.append(task)
                self.pending_queue.popleft()
                self.processing_queue[task.id] = task
            
            if not batch:
                return 0
        
        # 处理任务（无锁状态）
        for task in batch:
            try:
                # 这里应该调用实际的邮件发送函数
                success = self._send_email(task)
                
                with self.lock:
                    if success:
                        # 处理成功
                        del self.processing_queue[task.id]
                        self.stats['processed'] += 1
                        self._save_task_to_database(task, 'processed')
                        logging.info(f"邮件发送成功: {task.id} -> {task.recipient}")
                    else:
                        # 处理失败，重试
                        task.attempts += 1
                        if task.attempts >= task.max_attempts:
                            # 超过最大重试次数
                            del self.processing_queue[task.id]
                            self.failed_queue.append(task)
                            self.stats['failed'] += 1
                            self._save_task_to_database(task, 'failed', '超过最大重试次数')
                            logging.error(f"邮件发送失败，超过最大重试次数: {task.id}")
                        else:
                            # 延迟重试
                            task.delay_until = current_time + self.retry_delay
                            self.pending_queue.append(task)
                            del self.processing_queue[task.id]
                            self.stats['retried'] += 1
                            self._save_task_to_database(task, 'pending')
                            logging.warning(f"邮件发送失败，将在{self.retry_delay}秒后重试: {task.id}")
                
                processed_count += 1
                
            except Exception as e:
                with self.lock:
                    del self.processing_queue[task.id]
                    task.attempts += 1
                    if task.attempts >= task.max_attempts:
                        self.failed_queue.append(task)
                        self.stats['failed'] += 1
                        self._save_task_to_database(task, 'failed', str(e))
                    else:
                        task.delay_until = current_time + self.retry_delay
                        self.pending_queue.append(task)
                        self.stats['retried'] += 1
                        self._save_task_to_database(task, 'pending')
                
                logging.error(f"邮件任务处理异常: {task.id} - {e}")
                processed_count += 1
        
        with self.lock:
            self.stats['queue_size'] = len(self.pending_queue)
        
        return processed_count
    
    def _send_email(self, task: EmailTask) -> bool:
        """
        发送邮件（占位符，需要实际的邮件发送逻辑）
        
        Args:
            task: 邮件任务
            
        Returns:
            是否发送成功
        """
        # 这里应该调用实际的邮件发送功能
        # 现在只是模拟发送
        try:
            # 模拟发送延迟
            time.sleep(0.1)
            
            # 模拟随机失败（10%失败率）
            import random
            if random.random() < 0.1:
                return False
            
            return True
        except Exception as e:
            logging.error(f"邮件发送失败: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        with self.lock:
            return {
                **self.stats,
                'pending_size': len(self.pending_queue),
                'processing_size': len(self.processing_queue),
                'failed_size': len(self.failed_queue)
            }
    
    def retry_failed_tasks(self) -> int:
        """重试失败的任务"""
        with self.lock:
            retry_count = len(self.failed_queue)
            
            while self.failed_queue:
                task = self.failed_queue.popleft()
                task.attempts = 0
                task.delay_until = time.time()
                self.pending_queue.append(task)
                self._save_task_to_database(task, 'pending')
            
            if retry_count > 0:
                self.stats['queue_size'] = len(self.pending_queue)
                logging.info(f"重试了 {retry_count} 个失败的任务")
            
            return retry_count
    
    def clear_failed_tasks(self) -> int:
        """清空失败的任务"""
        with self.lock:
            clear_count = len(self.failed_queue)
            self.failed_queue.clear()
            
            # 从数据库删除
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute("DELETE FROM email_queue WHERE status = 'failed'")
                    conn.commit()
            except Exception as e:
                logging.warning(f"清空失败任务数据库记录失败: {e}")
            
            logging.info(f"清空了 {clear_count} 个失败的任务")
            return clear_count

# 全局实例
_default_cache_manager = None
_default_email_queue = None

def get_default_cache_manager() -> CacheManager:
    """获取默认的缓存管理器"""
    global _default_cache_manager
    if _default_cache_manager is None:
        _default_cache_manager = CacheManager()
    return _default_cache_manager

def get_default_email_queue() -> EmailQueue:
    """获取默认的邮件队列"""
    global _default_email_queue
    if _default_email_queue is None:
        _default_email_queue = EmailQueue()
    return _default_email_queue

if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试缓存
    cache = get_default_cache_manager()
    
    # 测试基本操作
    cache.set("test_key", "test_value", ttl=60)
    print(f"缓存获取: {cache.get('test_key')}")
    
    # 测试缓存装饰器
    @cache.cache_result(ttl=30)
    def slow_function(x):
        time.sleep(1)
        return x * 2
    
    print("第一次调用（应该慢）:", slow_function(5))
    print("第二次调用（应该快）:", slow_function(5))
    
    # 测试邮件队列
    email_queue = get_default_email_queue()
    
    # 添加邮件任务
    task_id = email_queue.enqueue(
        recipient="test@example.com",
        subject="测试邮件",
        content="这是一封测试邮件",
        priority=1
    )
    print(f"邮件任务ID: {task_id}")
    
    # 等待处理
    time.sleep(10)
    
    # 查看统计信息
    print("缓存统计:", cache.get_stats())
    print("邮件队列统计:", email_queue.get_queue_stats())