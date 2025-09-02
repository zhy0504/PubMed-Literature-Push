#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敏感信息保护模块
提供配置文件中敏感信息的加密、解密和安全存储功能
"""

import os
import base64
import logging
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import yaml

from .exceptions import EncryptionError, ConfigurationError

class SensitiveDataProtector:
    """敏感数据保护器"""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        初始化敏感数据保护器
        
        Args:
            encryption_key: 可选的加密密钥，如果未提供将生成新密钥
        """
        self.encryption_key = encryption_key
        self.fernet = None
        self.sensitive_fields = {
            'smtp': ['password', 'api_key'],
            'llm': ['api_key'],
            'database': ['password', 'api_key', 'connection_string'],
            'api': ['api_key', 'secret', 'token']
        }
        
        if encryption_key:
            self._setup_fernet(encryption_key)
    
    def _setup_fernet(self, key: bytes) -> None:
        """设置Fernet加密器"""
        try:
            self.fernet = Fernet(key)
        except Exception as e:
            raise EncryptionError(f"设置加密器失败: {e}")
    
    def generate_key(self) -> bytes:
        """生成新的加密密钥"""
        try:
            return Fernet.generate_key()
        except Exception as e:
            raise EncryptionError(f"生成加密密钥失败: {e}")
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        从密码派生加密密钥
        
        Args:
            password: 密码
            salt: 可选的盐值，如果未提供将生成新盐值
            
        Returns:
            bytes: 派生的加密密钥
        """
        try:
            if salt is None:
                salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key
        except Exception as e:
            raise EncryptionError(f"从密码派生密钥失败: {e}")
    
    def encrypt_value(self, value: str) -> str:
        """
        加密敏感值
        
        Args:
            value: 要加密的值
            
        Returns:
            str: 加密后的值（Base64编码）
        """
        if not self.fernet:
            raise EncryptionError("加密器未初始化")
        
        try:
            if not value:
                return value
            
            encrypted_data = self.fernet.encrypt(value.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            raise EncryptionError(f"加密失败: {e}")
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """
        解密敏感值
        
        Args:
            encrypted_value: 加密的值
            
        Returns:
            str: 解密后的值
        """
        if not self.fernet:
            raise EncryptionError("加密器未初始化")
        
        try:
            if not encrypted_value:
                return encrypted_value
            
            encrypted_data = base64.b64decode(encrypted_value.encode())
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            raise EncryptionError(f"解密失败: {e}")
    
    def is_encrypted_value(self, value: str) -> bool:
        """
        检查值是否已加密
        
        Args:
            value: 要检查的值
            
        Returns:
            bool: 是否已加密
        """
        if not value or not isinstance(value, str):
            return False
        
        try:
            # 尝试Base64解码
            decoded = base64.b64decode(value.encode())
            # 尝试解密
            if self.fernet:
                self.fernet.decrypt(decoded)
                return True
        except Exception:
            pass
        
        return False
    
    def find_sensitive_fields(self, config: Dict[str, Any], path: str = "") -> List[str]:
        """
        递归查找配置中的敏感字段路径
        
        Args:
            config: 配置字典
            path: 当前路径
            
        Returns:
            List[str]: 敏感字段路径列表
        """
        sensitive_paths = []
        
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            # 检查是否是敏感字段
            if key.lower() in ['password', 'api_key', 'secret', 'token', 'private_key']:
                sensitive_paths.append(current_path)
            
            # 检查是否在敏感字段列表中
            for section, fields in self.sensitive_fields.items():
                if key == section and isinstance(value, dict):
                    for field in fields:
                        if field in value:
                            sensitive_paths.append(f"{current_path}.{field}")
            
            # 递归检查嵌套字典
            if isinstance(value, dict):
                sensitive_paths.extend(self.find_sensitive_fields(value, current_path))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        sensitive_paths.extend(self.find_sensitive_fields(item, f"{current_path}[{i}]"))
        
        return sensitive_paths
    
    def encrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        加密配置中的敏感数据
        
        Args:
            config: 配置字典
            
        Returns:
            Dict[str, Any]: 加密后的配置
        """
        if not self.fernet:
            raise EncryptionError("加密器未初始化")
        
        try:
            config_copy = json.loads(json.dumps(config))  # 深拷贝
            sensitive_paths = self.find_sensitive_fields(config_copy)
            
            for path in sensitive_paths:
                # 解析路径并更新值
                keys = path.split('.')
                current = config_copy
                
                for key in keys[:-1]:
                    if '[' in key and ']' in key:
                        # 处理数组索引
                        array_key = key.split('[')[0]
                        index = int(key.split('[')[1].split(']')[0])
                        current = current[array_key][index]
                    else:
                        current = current[key]
                
                final_key = keys[-1]
                if '[' in final_key and ']' in final_key:
                    array_key = final_key.split('[')[0]
                    index = int(final_key.split('[')[1].split(']')[0])
                    original_value = current[array_key][index]
                    current[array_key][index] = self.encrypt_value(original_value)
                else:
                    original_value = current[final_key]
                    current[final_key] = self.encrypt_value(original_value)
            
            return config_copy
        except Exception as e:
            raise EncryptionError(f"加密敏感数据失败: {e}")
    
    def decrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密配置中的敏感数据
        
        Args:
            config: 配置字典
            
        Returns:
            Dict[str, Any]: 解密后的配置
        """
        if not self.fernet:
            raise EncryptionError("加密器未初始化")
        
        try:
            config_copy = json.loads(json.dumps(config))  # 深拷贝
            sensitive_paths = self.find_sensitive_fields(config_copy)
            
            for path in sensitive_paths:
                # 解析路径并更新值
                keys = path.split('.')
                current = config_copy
                
                for key in keys[:-1]:
                    if '[' in key and ']' in key:
                        # 处理数组索引
                        array_key = key.split('[')[0]
                        index = int(key.split('[')[1].split(']')[0])
                        current = current[array_key][index]
                    else:
                        current = current[key]
                
                final_key = keys[-1]
                if '[' in final_key and ']' in final_key:
                    array_key = final_key.split('[')[0]
                    index = int(final_key.split('[')[1].split(']')[0])
                    encrypted_value = current[array_key][index]
                    if self.is_encrypted_value(encrypted_value):
                        current[array_key][index] = self.decrypt_value(encrypted_value)
                else:
                    encrypted_value = current[final_key]
                    if self.is_encrypted_value(encrypted_value):
                        current[final_key] = self.decrypt_value(encrypted_value)
            
            return config_copy
        except Exception as e:
            raise EncryptionError(f"解密敏感数据失败: {e}")
    
    def save_encrypted_config(self, config: Dict[str, Any], config_path: str) -> None:
        """
        保存加密后的配置文件
        
        Args:
            config: 配置字典
            config_path: 配置文件路径
        """
        try:
            # 加密敏感数据
            encrypted_config = self.encrypt_sensitive_data(config)
            
            # 创建备份
            backup_path = config_path + '.backup'
            if os.path.exists(config_path):
                import shutil
                shutil.copy2(config_path, backup_path)
                logging.info(f"已创建配置文件备份: {backup_path}")
            
            # 保存加密配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(encrypted_config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logging.info(f"加密配置已保存到: {config_path}")
            
        except Exception as e:
            raise EncryptionError(f"保存加密配置失败: {e}")
    
    def load_encrypted_config(self, config_path: str) -> Dict[str, Any]:
        """
        加载并解密配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict[str, Any]: 解密后的配置
        """
        try:
            if not os.path.exists(config_path):
                raise ConfigurationError(f"配置文件 '{config_path}' 未找到")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                encrypted_config = yaml.safe_load(f)
            
            # 解密敏感数据
            decrypted_config = self.decrypt_sensitive_data(encrypted_config)
            
            return decrypted_config
        except Exception as e:
            if isinstance(e, (EncryptionError, ConfigurationError)):
                raise
            raise EncryptionError(f"加载加密配置失败: {e}")
    
    def create_masked_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建脱敏配置（用于日志和显示）
        
        Args:
            config: 配置字典
            
        Returns:
            Dict[str, Any]: 脱敏后的配置
        """
        try:
            config_copy = json.loads(json.dumps(config))  # 深拷贝
            sensitive_paths = self.find_sensitive_fields(config_copy)
            
            for path in sensitive_paths:
                # 解析路径并更新值
                keys = path.split('.')
                current = config_copy
                
                for key in keys[:-1]:
                    if '[' in key and ']' in key:
                        array_key = key.split('[')[0]
                        index = int(key.split('[')[1].split(']')[0])
                        current = current[array_key][index]
                    else:
                        current = current[key]
                
                final_key = keys[-1]
                if '[' in final_key and ']' in final_key:
                    array_key = final_key.split('[')[0]
                    index = int(final_key.split('[')[1].split(']')[0])
                    current[array_key][index] = "***MASKED***"
                else:
                    current[final_key] = "***MASKED***"
            
            return config_copy
        except Exception as e:
            raise EncryptionError(f"创建脱敏配置失败: {e}")

# 全局实例
_default_protector = None

def get_default_protector() -> SensitiveDataProtector:
    """获取默认的敏感数据保护器"""
    global _default_protector
    if _default_protector is None:
        # 尝试从环境变量获取密钥
        key_env = os.environ.get('PUBMED_ENCRYPTION_KEY')
        if key_env:
            try:
                key = base64.urlsafe_b64decode(key_env.encode())
                _default_protector = SensitiveDataProtector(key)
            except Exception:
                logging.warning("加密密钥格式错误，将创建新密钥")
                _default_protector = SensitiveDataProtector()
        else:
            _default_protector = SensitiveDataProtector()
    return _default_protector

def initialize_encryption(password: Optional[str] = None) -> bytes:
    """
    初始化加密系统
    
    Args:
        password: 可选的密码，如果未提供将生成随机密钥
        
    Returns:
        bytes: 加密密钥
    """
    try:
        protector = get_default_protector()
        
        if password:
            salt = os.urandom(16)
            key = protector.derive_key_from_password(password, salt)
        else:
            key = protector.generate_key()
        
        protector._setup_fernet(key)
        
        # 保存密钥到环境变量
        os.environ['PUBMED_ENCRYPTION_KEY'] = base64.urlsafe_b64encode(key).decode()
        
        logging.info("加密系统已初始化")
        return key
    except Exception as e:
        raise EncryptionError(f"初始化加密系统失败: {e}")

if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 初始化加密
        key = initialize_encryption("test_password")
        print(f"加密密钥: {base64.urlsafe_b64encode(key).decode()}")
        
        # 测试加密解密
        protector = get_default_protector()
        
        test_config = {
            'smtp': {
                'accounts': [{
                    'server': 'smtp.gmail.com',
                    'port': 587,
                    'username': 'test@gmail.com',
                    'password': 'secret_password'
                }]
            },
            'llm': {
                'openai': {
                    'api_key': 'sk-test-api-key',
                    'model': 'gpt-4'
                }
            }
        }
        
        print("原始配置:")
        print(json.dumps(test_config, indent=2, ensure_ascii=False))
        
        # 加密配置
        encrypted_config = protector.encrypt_sensitive_data(test_config)
        print("\n加密配置:")
        print(json.dumps(encrypted_config, indent=2, ensure_ascii=False))
        
        # 解密配置
        decrypted_config = protector.decrypt_sensitive_data(encrypted_config)
        print("\n解密配置:")
        print(json.dumps(decrypted_config, indent=2, ensure_ascii=False))
        
        # 脱敏配置
        masked_config = protector.create_masked_config(test_config)
        print("\n脱敏配置:")
        print(json.dumps(masked_config, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"测试失败: {e}")