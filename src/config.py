import yaml
import os
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
from src.exceptions import (
    ConfigurationError, ConfigurationValidationError, ConfigurationFileNotFoundError,
    EmailSendError, LLMServiceError, SchedulerError
)

def validate_email(email: str) -> bool:
    """
    验证邮箱格式。
    
    Args:
        email (str): 邮箱地址
        
    Returns:
        bool: 邮箱格式是否正确
    """
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_smtp_config(smtp_config: Dict[str, Any]) -> List[str]:
    """
    验证SMTP配置。
    
    Args:
        smtp_config (Dict[str, Any]): SMTP配置字典
        
    Returns:
        List[str]: 验证错误信息列表，空列表表示无错误
    """
    errors = []
    
    if not isinstance(smtp_config, dict):
        errors.append("SMTP配置必须是字典格式")
        return errors
    
    # 验证多账号配置
    if 'accounts' in smtp_config:
        accounts = smtp_config.get('accounts', [])
        if not accounts:
            errors.append("SMTP accounts列表不能为空")
        elif not isinstance(accounts, list):
            errors.append("SMTP accounts必须是列表格式")
        else:
            for i, account in enumerate(accounts):
                if not isinstance(account, dict):
                    errors.append(f"SMTP账号 {i+1}: 必须是字典格式")
                    continue
                    
                # 验证必要字段
                required_fields = ['server', 'port', 'username', 'password']
                for field in required_fields:
                    if field not in account:
                        errors.append(f"SMTP账号 {i+1}: 缺少 '{field}' 字段")
                    elif not account[field]:
                        errors.append(f"SMTP账号 {i+1}: '{field}' 不能为空")
                
                # 验证端口范围
                if 'port' in account:
                    try:
                        port = int(account['port'])
                        if not (1 <= port <= 65535):
                            errors.append(f"SMTP账号 {i+1}: 端口号必须在1-65535范围内")
                    except (ValueError, TypeError):
                        errors.append(f"SMTP账号 {i+1}: 端口号必须是整数")
                
                # 验证邮箱格式
                if 'username' in account and not validate_email(account['username']):
                    errors.append(f"SMTP账号 {i+1}: 用户名必须是有效的邮箱地址")
    
    # 验证基础间隔配置
    if 'base_interval_minutes' in smtp_config:
        try:
            interval = int(smtp_config['base_interval_minutes'])
            if interval < 1:
                errors.append("base_interval_minutes必须大于0")
        except (ValueError, TypeError):
            errors.append("base_interval_minutes必须是整数")
    
    return errors

def validate_llm_config(llm_config: Dict[str, Any]) -> List[str]:
    """
    验证LLM配置。
    
    Args:
        llm_config (Dict[str, Any]): LLM配置字典
        
    Returns:
        List[str]: 验证错误信息列表，空列表表示无错误
    """
    errors = []
    
    if not isinstance(llm_config, dict):
        errors.append("LLM配置必须是字典格式")
        return errors
    
    # 验证提供商配置
    providers = ['openai', 'google']
    has_valid_provider = False
    
    for provider in providers:
        if provider in llm_config:
            provider_config = llm_config[provider]
            if not isinstance(provider_config, dict):
                errors.append(f"LLM {provider}: 配置必须是字典格式")
                continue
            
            # 验证API密钥
            if 'api_key' not in provider_config:
                errors.append(f"LLM {provider}: 缺少 'api_key' 字段")
            elif not provider_config['api_key'] or not isinstance(provider_config['api_key'], str):
                errors.append(f"LLM {provider}: 'api_key' 必须是非空字符串")
            
            # 验证模型配置
            if 'model' in provider_config:
                if not provider_config['model'] or not isinstance(provider_config['model'], str):
                    errors.append(f"LLM {provider}: 'model' 必须是非空字符串")
            
            # 验证温度参数
            if 'temperature' in provider_config:
                try:
                    temp = float(provider_config['temperature'])
                    if not (0.0 <= temp <= 2.0):
                        errors.append(f"LLM {provider}: temperature必须在0.0-2.0范围内")
                except (ValueError, TypeError):
                    errors.append(f"LLM {provider}: temperature必须是数字")
            
            has_valid_provider = True
    
    if not has_valid_provider:
        errors.append("必须至少配置一个LLM提供商（openai或google）")
    
    return errors

def validate_scheduler_config(scheduler_config: Dict[str, Any]) -> List[str]:
    """
    验证调度器配置。
    
    Args:
        scheduler_config (Dict[str, Any]): 调度器配置字典
        
    Returns:
        List[str]: 验证错误信息列表，空列表表示无错误
    """
    errors = []
    
    if not isinstance(scheduler_config, dict):
        errors.append("调度器配置必须是字典格式")
        return errors
    
    # 验证运行时间
    if 'run_time' in scheduler_config:
        run_time = scheduler_config['run_time']
        if not isinstance(run_time, str):
            errors.append("run_time必须是字符串格式（HH:MM）")
        else:
            # 验证时间格式
            time_pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'
            if not re.match(time_pattern, run_time):
                errors.append("run_time格式错误，应为HH:MM（24小时制）")
    
    # 验证间隔配置
    interval_fields = ['delay_between_emails_sec', 'delay_between_groups_sec']
    for field in interval_fields:
        if field in scheduler_config:
            try:
                interval = int(scheduler_config[field])
                if interval < 1:
                    errors.append(f"{field}必须大于0")
            except (ValueError, TypeError):
                errors.append(f"{field}必须是整数")
    
    # 验证重试配置
    if 'max_retries' in scheduler_config:
        try:
            retries = int(scheduler_config['max_retries'])
            if retries < 0:
                errors.append("max_retries不能为负数")
        except (ValueError, TypeError):
            errors.append("max_retries必须是整数")
    
    return errors

def validate_data_files_config(data_files_config: Dict[str, Any]) -> List[str]:
    """
    验证数据文件配置。
    
    Args:
        data_files_config (Dict[str, Any]): 数据文件配置字典
        
    Returns:
        List[str]: 验证错误信息列表，空列表表示无错误
    """
    errors = []
    
    if not isinstance(data_files_config, dict):
        errors.append("数据文件配置必须是字典格式")
        return errors
    
    # 验证文件路径
    file_fields = ['zky_path', 'jcr_path']
    for field in file_fields:
        if field in data_files_config:
            file_path = data_files_config[field]
            if not isinstance(file_path, str) or not file_path.strip():
                errors.append(f"{field}必须是非空字符串")
            elif not os.path.exists(file_path):
                # 只警告，不报错，因为文件可能稍后创建
                logging.warning(f"数据文件 '{file_path}' 不存在")
    
    return errors

def validate_user_groups(user_groups: List[Dict]) -> List[str]:
    """
    验证用户组配置。
    
    Args:
        user_groups (List[Dict]): 用户组配置列表
        
    Returns:
        List[str]: 验证错误信息列表，空列表表示无错误
    """
    errors = []
    group_names = set()
    
    for i, group in enumerate(user_groups):
        if not isinstance(group, dict):
            errors.append(f"用户组 {i+1}: 配置必须是字典格式")
            continue
            
        # 验证组名
        group_name = group.get('group_name', '')
        if not group_name:
            errors.append(f"用户组 {i+1}: 缺少 'group_name' 字段")
        elif group_name in group_names:
            errors.append(f"用户组 {i+1}: 组名 '{group_name}' 重复")
        else:
            group_names.add(group_name)
            
        # 验证邮箱列表
        emails = group.get('emails', [])
        if not emails:
            errors.append(f"用户组 '{group_name}': 'emails' 列表不能为空")
        elif not isinstance(emails, list):
            errors.append(f"用户组 '{group_name}': 'emails' 必须是列表格式")
        else:
            for j, email in enumerate(emails):
                if not validate_email(email):
                    errors.append(f"用户组 '{group_name}': 邮箱 '{email}' 格式无效")
        
        # 验证关键词列表
        keywords = group.get('keywords', [])
        if not keywords:
            errors.append(f"用户组 '{group_name}': 'keywords' 列表不能为空")
        elif not isinstance(keywords, list):
            errors.append(f"用户组 '{group_name}': 'keywords' 必须是列表格式")
        else:
            for keyword in keywords:
                if not isinstance(keyword, str) or not keyword.strip():
                    errors.append(f"用户组 '{group_name}': 关键词不能为空字符串")
    
    return errors

def convert_user_groups_to_keyword_mapping(user_groups: List[Dict]) -> Dict[str, List[str]]:
    """
    将用户组配置转换为关键词到邮箱的映射。
    
    Args:
        user_groups (List[Dict]): 用户组配置列表
        
    Returns:
        Dict[str, List[str]]: 关键词到邮箱列表的映射
    """
    keyword_to_emails = defaultdict(list)
    
    for group in user_groups:
        emails = group.get('emails', [])
        keywords = group.get('keywords', [])
        
        for keyword in keywords:
            for email in emails:
                if email not in keyword_to_emails[keyword]:
                    keyword_to_emails[keyword].append(email)
    
    return dict(keyword_to_emails)

def convert_legacy_users_to_keyword_mapping(users: List[Dict]) -> Dict[str, List[str]]:
    """
    将旧版用户配置转换为关键词到邮箱的映射（向后兼容）。
    
    Args:
        users (List[Dict]): 旧版用户配置列表
        
    Returns:
        Dict[str, List[str]]: 关键词到邮箱列表的映射
    """
    keyword_to_emails = defaultdict(list)
    
    for user in users:
        email = user.get('email')
        keywords = user.get('keywords', [])
        
        if email:
            for keyword in keywords:
                if email not in keyword_to_emails[keyword]:
                    keyword_to_emails[keyword].append(email)
    
    return dict(keyword_to_emails)

def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    验证整个配置文件的所有部分。
    
    Args:
        config (Dict[str, Any]): 配置字典
        
    Returns:
        List[str]: 验证错误信息列表，空列表表示无错误
    """
    errors = []
    
    if not isinstance(config, dict):
        errors.append("配置文件必须是字典格式")
        return errors
    
    # 验证SMTP配置
    if 'smtp' in config:
        smtp_errors = validate_smtp_config(config['smtp'])
        errors.extend([f"SMTP: {error}" for error in smtp_errors])
    
    # 验证LLM配置
    if 'llm' in config:
        llm_errors = validate_llm_config(config['llm'])
        errors.extend([f"LLM: {error}" for error in llm_errors])
    
    # 验证调度器配置
    if 'scheduler' in config:
        scheduler_errors = validate_scheduler_config(config['scheduler'])
        errors.extend([f"调度器: {error}" for error in scheduler_errors])
    
    # 验证数据文件配置
    if 'data_files' in config:
        data_files_errors = validate_data_files_config(config['data_files'])
        errors.extend([f"数据文件: {error}" for error in data_files_errors])
    
    # 验证用户组配置
    user_groups = config.get('user_groups', [])
    if user_groups:
        user_group_errors = validate_user_groups(user_groups)
        errors.extend([f"用户组: {error}" for error in user_group_errors])
    
    return errors

def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    加载并解析 YAML 配置文件，支持新的用户组配置和旧版用户配置。

    Args:
        config_path (str): 配置文件的路径。

    Returns:
        Dict[str, Any]: 包含配置信息的字典。
    
    Raises:
        ConfigurationFileNotFoundError: 如果配置文件未找到。
        ConfigurationValidationError: 如果配置验证失败。
        ConfigurationError: 如果配置文件格式错误。
    """
    if not os.path.exists(config_path):
        raise ConfigurationFileNotFoundError(config_path)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 处理SMTP配置，支持多个发件邮箱
        smtp_config = config.get('smtp', {})
        if 'accounts' in smtp_config:
            # 新的多账号配置
            accounts = smtp_config['accounts']
            if 'scheduler' not in config:
                config['scheduler'] = {}
                
            # 计算邮件发送间隔：基础间隔（默认10分钟）/ 发件邮箱数量，最小1分钟
            base_minutes = smtp_config.get('base_interval_minutes', 10)
            calculated_interval = max(60, int((base_minutes * 60) / len(accounts)))  # 最小1分钟
            config['scheduler']['delay_between_emails_sec'] = calculated_interval
            logging.info(f"检测到 {len(accounts)} 个发件邮箱，自动调整邮件发送间隔为 {calculated_interval} 秒（最小1分钟）")
        else:
            # 兼容旧的单账号配置
            if all(key in smtp_config for key in ['server', 'username', 'password']):
                smtp_config['accounts'] = [{
                    'server': smtp_config['server'],
                    'port': smtp_config.get('port', 587),
                    'username': smtp_config['username'],
                    'password': smtp_config['password'],
                    'sender_name': smtp_config.get('sender_name', 'PubMed Literature Push')
                }]
                logging.info("转换旧版SMTP配置为新的多账号格式")
        
        # 处理用户组配置
        user_groups = config.get('user_groups', [])
        legacy_users = config.get('users', [])
        
        if user_groups and legacy_users:
            logging.warning("配置文件同时包含 'user_groups' 和 'users' 配置，将优先使用 'user_groups'")
        
        if user_groups:
            # 验证用户组配置
            validation_errors = validate_user_groups(user_groups)
            if validation_errors:
                error_msg = "用户组配置验证失败:\n" + "\n".join(validation_errors)
                raise ConfigurationValidationError(error_msg, validation_errors)
            
            # 转换为关键词映射并添加到配置中
            config['keyword_to_emails'] = convert_user_groups_to_keyword_mapping(user_groups)
            logging.info(f"加载了 {len(user_groups)} 个用户组")
            
        elif legacy_users:
            # 处理旧版用户配置（向后兼容）
            config['keyword_to_emails'] = convert_legacy_users_to_keyword_mapping(legacy_users)
            logging.info(f"加载了 {len(legacy_users)} 个用户（兼容模式）")
        else:
            # 没有用户配置
            config['keyword_to_emails'] = {}
            logging.warning("配置文件中未找到 'user_groups' 或 'users' 配置")
        
        # 验证整个配置
        validation_errors = validate_config(config)
        if validation_errors:
            error_msg = "配置验证失败:\n" + "\n".join(validation_errors)
            raise ConfigurationValidationError(error_msg, validation_errors)
        
        return config
    except yaml.YAMLError as e:
        raise ConfigurationError(f"解析配置文件 '{config_path}' 时出错: {e}")

def save_config(config: Dict[str, Any], config_path: str = 'config.yaml') -> None:
    """
    保存配置到YAML文件。
    
    Args:
        config (Dict[str, Any]): 配置字典
        config_path (str): 配置文件路径
        
    Raises:
        ConfigurationError: 如果保存失败
    """
    try:
        # 创建备份
        backup_path = config_path + '.backup'
        if os.path.exists(config_path):
            import shutil
            shutil.copy2(config_path, backup_path)
            logging.info(f"已创建配置文件备份: {backup_path}")
        
        # 保存新配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        logging.info(f"配置已保存到: {config_path}")
        
    except Exception as e:
        raise ConfigurationError(f"保存配置文件失败: {e}")

def get_config_section(section: str, config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    获取配置文件的特定部分。
    
    Args:
        section (str): 配置部分名称
        config_path (str): 配置文件路径
        
    Returns:
        Dict[str, Any]: 配置部分字典
        
    Raises:
        ConfigurationError: 如果部分不存在
    """
    try:
        config = load_config(config_path)
        if section not in config:
            raise ConfigurationError(f"配置部分 '{section}' 不存在")
        return config[section]
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"获取配置部分失败: {e}")

def update_config_section(section: str, section_config: Dict[str, Any], config_path: str = 'config.yaml') -> None:
    """
    更新配置文件的特定部分。
    
    Args:
        section (str): 配置部分名称
        section_config (Dict[str, Any]): 新的配置
        config_path (str): 配置文件路径
        
    Raises:
        ConfigurationError: 如果更新失败
    """
    try:
        config = load_config(config_path)
        
        # 验证新配置
        temp_config = config.copy()
        temp_config[section] = section_config
        validation_errors = validate_config(temp_config)
        if validation_errors:
            error_msg = f"配置部分 '{section}' 验证失败:\n" + "\n".join(validation_errors)
            raise ConfigurationValidationError(error_msg, validation_errors)
        
        # 更新配置
        config[section] = section_config
        save_config(config, config_path)
        
        logging.info(f"配置部分 '{section}' 已更新")
        
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"更新配置部分失败: {e}")

# 可以在这里添加更多的配置验证或处理逻辑
if __name__ == '__main__':
    # 用于测试 load_config 函数
    try:
        # 假设脚本是从项目根目录运行的
        config = load_config()
        import json
        print("配置加载成功:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        # 测试验证功能
        print("\n测试配置验证:")
        errors = validate_config(config)
        if errors:
            print("验证错误:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("配置验证通过")
            
    except (ConfigurationFileNotFoundError, ConfigurationValidationError, ConfigurationError) as e:
        print(f"配置错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")