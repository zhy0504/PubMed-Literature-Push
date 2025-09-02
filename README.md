# 📚 PubMed Literature Push - 智能文献推送系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

**一个基于AI的智能PubMed文献推送系统，支持多关键词搜索、自动摘要生成和邮件推送**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [安装指南](#-安装指南) • [使用方法](#-使用方法) • [配置说明](#-配置说明) • [故障排除](#-故障排除)

</div>

---

## 🌟 功能特性

### 🔍 智能文献检索
- **高级PubMed搜索**：基于AI生成优化的检索式，提高检索精确度
- **多关键词支持**：支持多个关键词的批量检索和分类
- **智能过滤**：自动过滤低质量或无关文献

### 🤖 AI增强功能
- **自动摘要生成**：使用LLM生成专业的文献综述
- **智能翻译**：将英文摘要翻译为中文，保持学术专业性
- **查询优化**：AI自动优化PubMed检索策略

### 📧 邮件推送系统
- **定时推送**：支持自定义推送时间和频率
- **多账户支持**：配置多个SMTP账户提高发送成功率
- **模板定制**：支持HTML邮件模板的个性化定制

### 🎮 跨平台图形界面
- **现代化GUI**：基于tkinter的直观图形界面
- **一键操作**：启动、停止、重启后台服务
- **实时监控**：系统状态实时显示和日志查看

### 🔧 系统管理
- **开机自启动**：支持Windows、macOS、Linux系统
- **后台服务**：稳定的服务进程管理
- **日志系统**：完整的操作日志和错误追踪

---

## 🚀 快速开始

### 系统要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **内存**: 最少 512MB RAM
- **网络**: 稳定的互联网连接

### 一键启动

#### Windows系统
```powershell
# 启动图形界面
.\cross_platform_launcher_gui.py

# 或使用PowerShell启动器
.\launcher.ps1
```

#### macOS系统
```bash
# 启动图形界面
python3 cross_platform_launcher_gui.py

# 或使用Shell启动器
./launcher_macos.sh
```

#### Linux系统
```bash
# 启动图形界面
python3 cross_platform_launcher_gui.py

# 或使用Shell启动器
./launcher_linux.sh
```

---

## 📦 安装指南

### Windows系统

#### 1. 环境准备
```powershell
# 检查Python版本
python --version

# 如果未安装Python，请从 https://python.org 下载安装
```

#### 2. 下载项目
```powershell
# 克隆项目
git clone https://github.com/yourusername/PubMed-Literature-Push.git
cd PubMed-Literature-Push
```

#### 3. 启动GUI
```powershell
# 启动图形界面安装器
python cross_platform_launcher_gui.py
```

### macOS系统

#### 1. 环境准备
```bash
# 使用Homebrew安装Python
brew install python3

# 验证安装
python3 --version
```

#### 2. 下载项目
```bash
# 克隆项目
git clone https://github.com/yourusername/PubMed-Literature-Push.git
cd PubMed-Literature-Push
```

#### 3. 启动GUI
```bash
# 启动图形界面安装器
python3 cross_platform_launcher_gui.py
```

### Linux系统

#### 1. 环境准备

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk git
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install python3 python3-pip python3-tkinter git
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip tk git
```

#### 2. 下载项目
```bash
# 克隆项目
git clone https://github.com/yourusername/PubMed-Literature-Push.git
cd PubMed-Literature-Push
```

#### 3. 启动GUI
```bash
# 启动图形界面安装器
python3 cross_platform_launcher_gui.py
```

---

## 🎯 使用方法

### 图形界面操作

#### 1. 启动配置工具
点击"⚙️ 启动配置工具"按钮，打开配置编辑器进行系统设置。

#### 2. 检查环境状态
点击"🔍 检查环境状态"按钮，验证系统依赖和配置。

#### 3. 运行程序
- **前台运行**: 点击"🚀 运行主程序(前台)"，适合调试和实时监控
- **后台服务**: 点击"▶️ 启动后台服务"，推荐日常使用

#### 4. 服务管理
- **停止服务**: 点击"⏹️ 停止主程序"
- **重启服务**: 点击"🔄 重启后台服务"

#### 5. 自启动设置
- **启用自启动**: 点击"✅ 启用开机自启"
- **禁用自启动**: 点击"❌ 禁用开机自启"

### 命令行操作

#### Windows PowerShell
```powershell
# 启动配置编辑器
.\launcher.ps1 -Action config

# 检查环境状态
.\launcher.ps1 -Action check

# 启动后台服务
.\launcher.ps1 -Action start

# 停止后台服务
.\launcher.ps1 -Action stop

# 重启后台服务
.\launcher.ps1 -Action restart

# 前台运行（调试）
.\launcher.ps1 -Action run

# 启用开机自启动
.\launcher.ps1 -Action enable-autostart

# 禁用开机自启动
.\launcher.ps1 -Action disable-autostart
```

#### macOS/Linux Bash
```bash
# 启动配置编辑器
./launcher_macos.sh config  # macOS
./launcher_linux.sh config  # Linux

# 检查环境状态
./launcher_macos.sh check   # macOS
./launcher_linux.sh check   # Linux

# 启动后台服务
./launcher_macos.sh start   # macOS
./launcher_linux.sh start   # Linux

# 停止后台服务
./launcher_macos.sh stop    # macOS
./launcher_linux.sh stop    # Linux

# 重启后台服务
./launcher_macos.sh restart # macOS
./launcher_linux.sh restart # Linux

# 前台运行（调试）
./launcher_macos.sh run     # macOS
./launcher_linux.sh run     # Linux

# 启用开机自启动
./launcher_macos.sh enable-autostart  # macOS
./launcher_linux.sh enable-autostart  # Linux

# 禁用开机自启动
./launcher_macos.sh disable-autostart # macOS
./launcher_linux.sh disable-autostart # Linux
```

---

## ⚙️ 配置说明

### 主要配置文件

#### config.yaml - 主配置文件
```yaml
# 调度器设置
scheduler:
  run_time: '12:00'                    # 每日运行时间
  delay_between_keywords_sec: 60       # 关键词间延迟

# PubMed设置
pubmed:
  max_articles: 500                     # 最大文章数量

# LLM提供商配置
llm_providers:
- name: zhy
  provider: custom
  api_key: your_api_key               # API密钥
  api_endpoint: https://api.example.com/v1  # API端点

# 任务模型映射
task_model_mapping:
  query_generator:
    provider_name: zhy
    model_name: gemini-2.5-flash
  summarizer:
    provider_name: zhy
    model_name: gemini-2.5-flash
  abstract_translator:
    provider_name: zhy
    model_name: gemini-2.5-flash

# 翻译设置
translation_settings:
  batch_size: 20                      # 批处理大小
  delay_between_batches_sec: 5        # 批次间延迟

# SMTP设置
smtp:
  max_retries: 3                      # 最大重试次数
  retry_delay_sec: 300                # 重试延迟
  base_interval_minutes: 10           # 基础间隔
  admin_email: admin@example.com     # 管理员邮箱
  accounts:
  - server: smtp.qq.com
    port: 465
    username: your_email@qq.com
    password: your_password
    sender_name: PubMed Literature Push

# 用户组配置
user_groups:
- group_name: 结核病
  emails:
  - user1@example.com
  keywords:
  - 结核病
  - 肺结核
```

### 邮件配置

#### 支持的邮箱服务商
- **QQ邮箱**: smtp.qq.com:465
- **163邮箱**: smtp.163.com:465
- **Gmail**: smtp.gmail.com:587
- **Outlook**: smtp.office365.com:587

#### 配置示例
```yaml
smtp:
  accounts:
  - server: smtp.gmail.com
    port: 587
    username: your_email@gmail.com
    password: your_app_password
    sender_name: PubMed Literature Push
```

### LLM配置

#### 支持的模型提供商
- **OpenAI**: GPT-3.5, GPT-4
- **Google**: Gemini系列
- **自定义API**: 支持OpenAI兼容的API端点

#### 配置示例
```yaml
llm_providers:
- name: openai
  provider: openai
  api_key: sk-your-openai-key
  api_endpoint: https://api.openai.com/v1

- name: gemini
  provider: google
  api_key: your-gemini-key
  api_endpoint: https://generativelanguage.googleapis.com/v1beta
```

### 用户组配置

#### 多用户组支持
```yaml
user_groups:
- group_name: 研究组A
  emails:
  - researcher1@example.com
  - researcher2@example.com
  keywords:
  - cancer immunotherapy
  - CAR-T cells
  - tumor microenvironment

- group_name: 研究组B
  emails:
  - clinician1@example.com
  keywords:
  - diabetes mellitus
  - insulin resistance
  - metabolic syndrome
```

---

## 🔧 故障排除

### 常见问题

#### 1. GUI无法启动
**症状**: 运行GUI脚本时出现错误

**解决方案**:
```bash
# Windows - 安装tkinter
python -m pip install tkinter

# macOS - 安装Xcode命令行工具
xcode-select --install

# Linux - 安装tkinter
# Ubuntu/Debian
sudo apt install python3-tk

# CentOS/RHEL/Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

#### 2. 邮件发送失败
**症状**: 邮件无法正常发送

**解决方案**:
- 检查SMTP服务器设置是否正确
- 确认邮箱密码或应用专用密码是否正确
- 检查网络连接是否正常
- 对于Gmail，需要启用"不够安全的应用的访问权限"或使用应用专用密码

#### 3. API调用失败
**症状**: LLM API调用失败

**解决方案**:
- 检查API密钥是否正确
- 确认API端点是否可用
- 检查网络连接是否正常
- 验证API配额是否充足

#### 4. 后台服务无法启动
**症状**: 后台服务启动失败

**解决方案**:
```bash
# 检查Python环境
python --version

# 检查依赖包
pip list

# 查看详细错误日志
tail -f pubmed_push.log
```

#### 5. 自启动功能不工作
**症状**: 开机自启动功能失效

**解决方案**:
```bash
# macOS - 检查LaunchAgent
launchctl list | grep pubmed

# Linux - 检查systemd服务
systemctl --user status pubmed-literature-push.service

# Windows - 检查启动项
Get-CimInstance -ClassName Win32_StartupCommand | Where-Object {$_.Name -like "*pubmed*"}
```

### 日志查看

#### 程序日志
```bash
# 查看实时日志
tail -f pubmed_push.log

# 查看错误日志
grep ERROR pubmed_push.log

# 查看特定时间的日志
grep "2024-01-01" pubmed_push.log
```

#### 系统日志
```bash
# Windows - 事件查看器
eventvwr.msc

# macOS - 系统日志
log show --predicate 'process == "PubMed"' --info --debug

# Linux - 系统日志
journalctl -u pubmed-literature-push -f
```

### 性能优化

#### 内存使用优化
```yaml
# 减少批处理大小
translation_settings:
  batch_size: 10  # 从20减少到10

# 增加延迟时间
translation_settings:
  delay_between_batches_sec: 10  # 从5增加到10
```

#### 网络优化
```yaml
# 增加重试次数
smtp:
  max_retries: 5  # 从3增加到5

# 调整重试延迟
smtp:
  retry_delay_sec: 600  # 从300增加到600
```

---

## 📚 高级功能

### 自定义邮件模板

#### HTML模板定制
编辑 `templates/email_template.html` 文件：

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PubMed Literature Push</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .header { background-color: #f8f9fa; padding: 20px; }
        .content { padding: 20px; }
        .article { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; }
        .title { font-weight: bold; color: #2c3e50; }
        .authors { color: #7f8c8d; font-size: 0.9em; }
        .abstract { margin-top: 10px; }
        .footer { background-color: #f8f9fa; padding: 10px; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 PubMed Literature Push</h1>
        <p>最新文献推送 - {{ date }}</p>
    </div>
    
    <div class="content">
        {% for group in user_groups %}
        <h2>{{ group.group_name }}</h2>
        {% for article in group.articles %}
        <div class="article">
            <div class="title">{{ article.title }}</div>
            <div class="authors">{{ article.authors }}</div>
            <div class="abstract">{{ article.abstract }}</div>
            <div class="link">
                <a href="{{ article.url }}">查看原文</a>
            </div>
        </div>
        {% endfor %}
        {% endfor %}
    </div>
    
    <div class="footer">
        <p>本邮件由 PubMed Literature Push 自动发送</p>
        <p>如有问题，请联系：{{ admin_email }}</p>
    </div>
</body>
</html>
```

### 高级检索策略

#### 复杂检索式配置
```yaml
prompts:
  generate_query: "# 高级PubMed检索策略
  ## 分析关键词：{keyword}
  ## 日期范围：{date_query}
  
  ## 步骤：
  1. 识别核心概念
  2. 查找MeSH术语
  3. 构建同义词组
  4. 组合检索式
  
  ## 输出：
  仅返回PubMed检索式，无其他内容"
```

### 多语言支持

#### 翻译设置优化
```yaml
translation_settings:
  batch_size: 15
  delay_between_batches_sec: 3
  target_language: zh-CN  # 中文简体
  preserve_formatting: true
  academic_style: true
```

---

## 🔄 更新和维护

### 依赖包更新
```bash
# 更新所有依赖包
pip install -r requirements.txt --upgrade

# 更新特定包
pip install package-name --upgrade
```

### 配置文件备份
```bash
# 备份配置文件
cp config.yaml config.yaml.backup.$(date +%Y%m%d)

# 备份整个项目
tar -czf pubmed-push-backup-$(date +%Y%m%d).tar.gz .
```

### 数据库维护
```bash
# 清理旧日志
find . -name "*.log" -mtime +30 -delete

# 清理缓存
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

---

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. **Fork项目**
2. **创建功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送分支** (`git push origin feature/AmazingFeature`)
5. **创建Pull Request**

### 开发环境设置
```bash
# 克隆项目
git clone https://github.com/yourusername/PubMed-Literature-Push.git
cd PubMed-Literature-Push

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# 运行测试
pytest tests/

# 代码格式化
black .
flake8 .
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---




<div align="center">

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**

![Star History](https://img.shields.io/github/stars/yourusername/PubMed-Literature-Push?style=social)

</div>