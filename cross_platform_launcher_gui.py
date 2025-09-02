#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PubMed Literature Push Launcher GUI - Cross Platform Version
跨平台启动器图形界面 - 支持Windows、macOS和Linux
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
import json
from pathlib import Path
import psutil
import time
import platform
import math

class CrossPlatformLauncherGUI:
    def __init__(self, root):
        self.root = root
        self.system = platform.system().lower()
        
        # 初始化按钮状态字典
        self.buttons = {}
        
        self.setup_ui()
        
        # 调试信息：记录路径信息
        print(f"DEBUG: __file__ = {__file__}")
        print(f"DEBUG: Path(__file__).parent = {Path(__file__).parent}")
        print(f"DEBUG: 当前工作目录 = {os.getcwd()}")
        print(f"DEBUG: 操作系统 = {self.system}")
        
        # 使用更健壮的路径检测方法
        self.project_root = self._get_project_root()
        
        # 根据操作系统设置脚本路径
        if self.system == "windows":
            self.launcher_script = self.project_root / "launcher.ps1"
            self.command_executor = self._execute_powershell
        elif self.system == "darwin":  # macOS
            self.launcher_script = self.project_root / "launcher_macos.sh"
            self.command_executor = self._execute_shell
        else:  # Linux
            self.launcher_script = self.project_root / "launcher_linux.sh"
            self.command_executor = self._execute_shell
        
        # 调试信息：验证关键文件和路径
        print(f"DEBUG: project_root = {self.project_root}")
        print(f"DEBUG: launcher_script = {self.launcher_script}")
        print(f"DEBUG: launcher_script exists = {self.launcher_script.exists()}")
        print(f"DEBUG: main.py exists = {(self.project_root / 'main.py').exists()}")
        print(f"DEBUG: .venv exists = {(self.project_root / '.venv').exists()}")
        
        # 状态变量
        self.is_checking_status = False
        self.status_check_thread = None
        self.auto_refresh_interval = 30000  # 30秒自动刷新间隔（毫秒）
        self.auto_refresh_job = None
        
        # 加载状态变量
        self.loading_states = {
            'config': False,
            'run': False,
            'start': False,
            'stop': False,
            'restart': False,
            'enable_autostart': False,
            'disable_autostart': False,
            'check': False,
            'status': False
        }
        
        # 按钮引用字典
        self.buttons = {}
        
        # 加载动画相关
        self.loading_animation_angle = 0
        self.loading_animation_job = None
        
        # 启动时检查状态
        self.refresh_status()
        
        # 启动自动状态检测
        self.start_auto_refresh()
    
    def create_loading_indicator(self, parent, size=20):
        """创建加载指示器"""
        canvas = tk.Canvas(parent, width=size, height=size, bg='white', highlightthickness=0)
        canvas.loading_items = []
        
        # 创建旋转的圆点
        for i in range(8):
            angle = i * math.pi / 4
            x1 = size/2 + (size/3 - 2) * math.cos(angle)
            y1 = size/2 + (size/3 - 2) * math.sin(angle)
            x2 = size/2 + (size/3) * math.cos(angle)
            y2 = size/2 + (size/3) * math.sin(angle)
            
            dot = canvas.create_line(x1, y1, x2, y2, width=2, fill='#3498db', capstyle='round')
            canvas.loading_items.append(dot)
        
        return canvas
    
    def animate_loading_indicator(self, canvas):
        """动画加载指示器"""
        if not hasattr(canvas, 'loading_items') or not canvas.loading_items:
            return
        
        # 更新角度
        self.loading_animation_angle += 0.2
        
        # 更新每个圆点的透明度和位置
        for i, item in enumerate(canvas.loading_items):
            angle = i * math.pi / 4 + self.loading_animation_angle
            # 计算透明度（基于角度）
            opacity = (math.sin(angle) + 1) / 2
            # 将透明度转换为颜色强度
            intensity = int(52 + opacity * 179)  # 52-231 范围
            color = f'#{intensity:02x}{intensity+20:02x}{intensity+40:02x}'
            canvas.itemconfig(item, fill=color)
        
        # 继续动画
        self.loading_animation_job = self.root.after(50, lambda: self.animate_loading_indicator(canvas))
    
    def start_loading_animation(self, canvas):
        """启动加载动画"""
        if canvas and hasattr(canvas, 'loading_items'):
            self.animate_loading_indicator(canvas)
    
    def stop_loading_animation(self, canvas):
        """停止加载动画"""
        if self.loading_animation_job:
            self.root.after_cancel(self.loading_animation_job)
            self.loading_animation_job = None
        
        if canvas and hasattr(canvas, 'loading_items'):
            # 重置所有圆点为默认颜色
            for item in canvas.loading_items:
                canvas.itemconfig(item, fill='#3498db')
    
    def set_button_loading(self, button_key, loading=True):
        """设置按钮加载状态"""
        if button_key not in self.buttons:
            return
        
        button, loading_canvas = self.buttons[button_key]
        
        if loading:
            # 禁用按钮
            button.configure(state='disabled')
            # 显示加载指示器
            if loading_canvas:
                loading_canvas.place(x=button.winfo_width()-25, y=button.winfo_height()//2-10)
                self.start_loading_animation(loading_canvas)
        else:
            # 启用按钮
            button.configure(state='normal')
            # 隐藏加载指示器
            if loading_canvas:
                self.stop_loading_animation(loading_canvas)
                loading_canvas.place_forget()
    
    def set_operation_loading(self, operation_key, loading=True):
        """设置操作加载状态"""
        if operation_key in self.loading_states:
            self.loading_states[operation_key] = loading
        
        # 更新对应的按钮状态
        button_key_map = {
            'config': 'config',
            'run': 'run_main',
            'start': 'start_bg', 
            'stop': 'stop_bg',
            'restart': 'restart_bg',
            'enable_autostart': 'enable_autostart',
            'disable_autostart': 'disable_autostart',
            'check': 'check_env',
            'status': 'refresh_status'
        }
        
        if operation_key in button_key_map:
            self.set_button_loading(button_key_map[operation_key], loading)
    
    def create_enhanced_button(self, parent, text, command, color, button_key, width=14, height=1):
        """创建增强按钮（带加载指示器）"""
        # 固定按钮尺寸以确保显示
        button_font_size = 9
        button_padx = 10
        button_pady = 6
        
        # 创建按钮框架
        button_frame = tk.Frame(parent, bg='white')
        button_frame.grid(row=0, column=0, sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        
        # 创建按钮
        btn = tk.Button(button_frame, text=text, command=command,
                       font=(self.system_font, button_font_size, 'bold'),
                       bg=color, fg='white',
                       relief='flat', bd=0,
                       padx=button_padx, pady=button_pady,
                       cursor='hand2',
                       width=width, height=height)
        btn.grid(row=0, column=0, sticky='ew')
        
        # 创建加载指示器
        loading_canvas = self.create_loading_indicator(button_frame, size=20)
        
        # 添加悬停效果
        self.add_button_hover_effect(btn, color)
        
        # 存储按钮引用
        self.buttons[button_key] = (btn, loading_canvas)
        
        return btn
    
    def _get_project_root(self):
        """获取项目根目录的健壮方法"""
        # 方法1：基于__file__的路径
        file_based_path = Path(__file__).parent
        print(f"DEBUG: file_based_path = {file_based_path}")
        
        # 方法2：基于工作目录的路径
        cwd_based_path = Path(os.getcwd())
        print(f"DEBUG: cwd_based_path = {cwd_based_path}")
        
        # 检查哪个路径包含必要的项目文件
        if self.system == "windows":
            required_files = ['main.py', 'launcher.ps1', 'config.yaml']
        elif self.system == "darwin":
            required_files = ['main.py', 'launcher_macos.sh', 'config.yaml']
        else:  # Linux
            required_files = ['main.py', 'launcher_linux.sh', 'config.yaml']
        
        for path in [file_based_path, cwd_based_path]:
            if all((path / f).exists() for f in required_files):
                print(f"DEBUG: 选择路径 {path}，因为它包含所有必需文件")
                return path
        
        # 如果没有完美匹配，选择包含最多文件的路径
        file_scores = {}
        for path in [file_based_path, cwd_based_path]:
            score = sum(1 for f in required_files if (path / f).exists())
            file_scores[path] = score
            print(f"DEBUG: 路径 {path} 的文件匹配分数 = {score}")
        
        best_path = max(file_scores, key=file_scores.get)
        print(f"DEBUG: 选择最佳路径 {best_path}")
        
        return best_path
    
    def get_system_font(self):
        """获取系统默认的中文字体"""
        if self.system == "windows":
            return "Microsoft YaHei UI"
        elif self.system == "darwin":
            return "PingFang SC"
        else:  # Linux
            # 尝试多种常见的Linux中文字体
            linux_fonts = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Microsoft YaHei", "Arial Unicode MS"]
            for font in linux_fonts:
                try:
                    # 测试字体是否可用
                    test_font = tk.font.Font(family=font, size=12)
                    return font
                except:
                    continue
            return "Arial"  # 默认字体
    
    def setup_ui(self):
        """设置用户界面"""
        self.root.title("📚 PubMed Literature Push 启动器")
        
        # 获取系统字体
        self.system_font = self.get_system_font()
        
        # 获取屏幕分辨率
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 设置窗口最小大小
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        
        # 设置合适的窗口大小，不自动最大化
        window_width = min(1200, screen_width - 100)
        window_height = min(900, screen_height - 100)
        
        # 窗口居中显示
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 存储窗口尺寸以供其他方法使用
        self.window_width = window_width
        self.window_height = window_height
        
        # 设置主题色彩
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db', 
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'light': '#ecf0f1',
            'dark': '#34495e'
        }
        
        # 设置背景渐变色
        self.root.configure(bg='#f8f9fa')
        
        # 主框架 - 使用Canvas实现渐变背景
        self.create_gradient_background()
        
        # 主内容框架
        main_frame = tk.Frame(self.root, bg='#ffffff', relief='flat', bd=0)
        main_frame.place(x=20, y=20, relwidth=0.955, relheight=0.94)
        
        # 添加阴影效果
        shadow_frame = tk.Frame(self.root, bg='#e0e0e0', relief='flat', bd=0)
        shadow_frame.place(x=25, y=25, relwidth=0.955, relheight=0.94)
        main_frame.lift()
        
        # 配置网格权重
        main_frame.grid_rowconfigure(0, weight=0)  # header - 固定高度
        main_frame.grid_rowconfigure(1, weight=0)  # status - 固定高度
        main_frame.grid_rowconfigure(2, weight=0)  # control - 固定高度
        main_frame.grid_rowconfigure(3, weight=1)  # log - 可扩展
        main_frame.grid_columnconfigure(0, weight=1)
        
        # 创建标题区域
        self.create_header(main_frame)
        
        # 状态面板
        self.create_status_panel(main_frame)
        
        # 控制按钮面板
        self.create_control_panel(main_frame)
        
        # 日志面板
        self.create_log_panel(main_frame)
    
    def create_gradient_background(self):
        """创建渐变背景"""
        # 简化背景处理，直接设置窗口背景色
        self.root.configure(bg='#f0f8ff')  # 浅蓝色背景
    
    def create_header(self, parent):
        """创建标题区域"""
        header_frame = tk.Frame(parent, bg='#ffffff', height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(10, 5))
        header_frame.grid_propagate(False)
        
        # 主标题
        title_label = tk.Label(header_frame, text="📚 PubMed Literature Push", 
                              font=(self.system_font, 18, 'bold'),
                              fg='#2c3e50', bg='#ffffff')
        title_label.grid(row=0, column=0, sticky='w', pady=(10, 0))
        
        # 副标题
        subtitle_label = tk.Label(header_frame, text="智能文献推送系统 - 启动控制台", 
                                 font=(self.system_font, 10),
                                 fg='#7f8c8d', bg='#ffffff')
        subtitle_label.grid(row=1, column=0, sticky='w', pady=(5, 0))
        
        # 配置grid列权重
        header_frame.grid_columnconfigure(0, weight=1)
    
    def create_status_panel(self, parent):
        """创建状态面板"""
        # 状态面板容器
        status_container = tk.Frame(parent, bg='#ffffff')
        status_container.grid(row=1, column=0, sticky="ew", padx=30, pady=(5, 10))
        
        # 状态面板标题
        status_title = tk.Label(status_container, text="📊 系统状态 (每30秒自动刷新)",
                               font=(self.system_font, 12, 'bold'),
                               fg='#2c3e50', bg='#ffffff')
        status_title.grid(row=0, column=0, sticky='w', pady=(0, 10))
        
        # 状态卡片容器
        cards_frame = tk.Frame(status_container, bg='#ffffff')
        cards_frame.grid(row=1, column=0, sticky='ew')
        
        # 配置grid列权重
        status_container.grid_columnconfigure(0, weight=1)
        
        # 后台服务状态卡片
        self.service_card = self.create_status_card(cards_frame, "🔧 后台服务", "检查中...", 0)
        
        # 自启动状态卡片
        self.autostart_card = self.create_status_card(cards_frame, "🚀 开机自启", "检查中...", 1)
        
        # 配置状态卡片列权重
        cards_frame.grid_columnconfigure(0, weight=1)  # 后台服务卡片
        cards_frame.grid_columnconfigure(1, weight=1)  # 自启动卡片
        
        # 刷新按钮容器 - 单独一行
        refresh_frame = tk.Frame(status_container, bg='#ffffff')
        refresh_frame.grid(row=2, column=0, sticky='e', pady=(5, 0))
        
        # 刷新按钮
        refresh_font_size = max(8, min(9, int(self.window_width / 120)))
        refresh_btn = self.create_enhanced_button(refresh_frame, "🔄 刷新状态",
                                                  self.refresh_status, '#3498db', 'refresh_status',
                                                  width=8, height=1)
        refresh_btn.grid(row=0, column=0, sticky='e')
    
    def create_status_card(self, parent, title, status, col):
        """创建状态卡片"""
        card_frame = tk.Frame(parent, bg='#f8f9fa', relief='solid', bd=1, height=55)
        card_frame.grid(row=0, column=col, padx=(0, 15) if col == 0 else (15, 0),
                       pady=8, sticky='ew', ipady=8)
        card_frame.grid_propagate(False)  # 保持固定高度
        
        # 内容框架
        content_frame = tk.Frame(card_frame, bg='#f8f9fa')
        content_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=5)
        card_frame.grid_columnconfigure(0, weight=1)
        card_frame.grid_rowconfigure(0, weight=1)
        
        # 标题和状态框架
        info_frame = tk.Frame(content_frame, bg='#f8f9fa')
        info_frame.grid(row=0, column=0, sticky='ew')
        content_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        title_label = tk.Label(info_frame, text=title,
                              font=(self.system_font, 10, 'bold'),
                              fg='#2c3e50', bg='#f8f9fa')
        title_label.grid(row=0, column=0, sticky='w', pady=(0, 2))
        
        # 状态
        status_var = tk.StringVar(value=status)
        status_label = tk.Label(info_frame, textvariable=status_var,
                               font=(self.system_font, 9),
                               fg='#7f8c8d', bg='#f8f9fa')
        status_label.grid(row=1, column=0, sticky='w')
        
        # 加载指示器框架
        loading_frame = tk.Frame(content_frame, bg='#f8f9fa', width=20)
        loading_frame.grid(row=0, column=1, sticky='nse', padx=(5, 0))
        loading_frame.grid_propagate(False)
        content_frame.grid_columnconfigure(1, weight=0)
        
        # 创建加载指示器
        loading_canvas = self.create_loading_indicator(loading_frame, size=16)
        loading_canvas.place(x=2, y=2)
        
        # 返回状态变量和标签以便后续更新
        return {
            'var': status_var, 
            'label': status_label,
            'loading_canvas': loading_canvas,
            'card_frame': card_frame
        }
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        # 控制面板容器
        control_container = tk.Frame(parent, bg='#ffffff')
        control_container.grid(row=2, column=0, sticky="ew", padx=30, pady=(5, 10))
        
        # 控制面板标题
        panel_title_size = max(10, min(14, int(self.window_width / 70)))
        control_title = tk.Label(control_container, text="🎮 程序控制",
                                font=(self.system_font, panel_title_size, 'bold'),
                                fg='#2c3e50', bg='#ffffff')
        control_title.grid(row=0, column=0, sticky='w', pady=(0, 15))
        
        # 按钮网格容器
        buttons_frame = tk.Frame(control_container, bg='#ffffff', height=120)
        buttons_frame.grid(row=1, column=0, sticky='ew')
        buttons_frame.grid_propagate(False)
        
        # 配置grid列权重
        control_container.grid_columnconfigure(0, weight=1)
        control_container.grid_rowconfigure(1, weight=1)
        
        # 按钮配置 - 重新组织为更直观的布局
        button_configs = [
            # 第一行 - 基础操作
            [
                ("⚙️ 启动配置工具", self.start_config_editor, "#3498db", "config"),
                ("🔍 检查环境状态", self.check_environment, "#9b59b6", "check_env"),
            ],
            # 第二行 - 运行控制
            [
                ("🚀 运行主程序(前台)", self.run_main_program, "#27ae60", "run_main"),
                ("▶️ 启动后台服务", self.start_background, "#2980b9", "start_bg"),
            ],
            # 第三行 - 服务管理
            [
                ("⏹️ 停止主程序", self.stop_background, "#e74c3c", "stop_bg"),
                ("🔄 重启后台服务", self.restart_background, "#f39c12", "restart_bg"),
            ]
        ]
        
        # 创建按钮网格 - 使用固定高度
        for row_idx, button_row in enumerate(button_configs):
            row_frame = tk.Frame(buttons_frame, bg='#ffffff')
            row_frame.grid(row=row_idx, column=0, sticky='ew', pady=(0, 8))
            # 设置两列等权重，确保按钮均匀分布
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            
            for col_idx, (text, command, color, button_key) in enumerate(button_row):
                # 直接在row_frame中创建按钮
                btn = tk.Button(row_frame, text=text, command=command,
                               font=(self.system_font, 9, 'bold'),
                               bg=color, fg='white',
                               relief='flat', bd=0,
                               padx=185, pady=6,
                               width=20,  # 设置固定宽度，确保所有按钮长度一致
                               cursor='hand2')
                # 使用统一的间距，确保按钮长度一致
                btn.grid(row=0, column=col_idx, sticky='ew', padx=6)
                
                # 添加悬停效果
                self.add_button_hover_effect(btn, color)
                
                # 存储按钮引用
                self.buttons[button_key] = (btn, None)
        
        # 自启动控制区域
        autostart_frame = tk.Frame(control_container, bg='#ffffff')
        autostart_frame.grid(row=2, column=0, sticky='ew', pady=(15, 0))
        
        autostart_title = tk.Label(autostart_frame, text="🚀 开机自启动设置", 
                                  font=(self.system_font, 11, 'bold'),
                                  fg='#2c3e50', bg='#ffffff')
        autostart_title.grid(row=0, column=0, sticky='w', pady=(0, 10))
        
        autostart_buttons = tk.Frame(autostart_frame, bg='#ffffff')
        autostart_buttons.grid(row=1, column=0, sticky='ew')
        
        # 配置grid列权重
        autostart_frame.grid_columnconfigure(0, weight=1)
        
        # 自启动按钮 - 使用与主按钮相同的创建方法
        enable_btn = tk.Button(autostart_buttons, text="✅ 启用开机自启", 
                              command=self.enable_autostart,
                              font=(self.system_font, 9, 'bold'),
                              bg='#27ae60', fg='white',
                              relief='flat', bd=0,
                              padx=30, pady=6,
                              width=20, height=1,
                              cursor='hand2')
        enable_btn.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        
        disable_btn = tk.Button(autostart_buttons, text="❌ 禁用开机自启", 
                               command=self.disable_autostart,
                               font=(self.system_font, 9, 'bold'),
                               bg='#e74c3c', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=6,
                               width=20, height=1,
                               cursor='hand2')
        disable_btn.grid(row=0, column=1, sticky='ew', padx=(6, 0))
        
        # 添加悬停效果
        self.add_button_hover_effect(enable_btn, '#27ae60')
        self.add_button_hover_effect(disable_btn, '#e74c3c')
        
        # 存储按钮引用
        self.buttons['enable_autostart'] = (enable_btn, None)
        self.buttons['disable_autostart'] = (disable_btn, None)
        
        # 配置grid列权重
        autostart_buttons.grid_columnconfigure(0, weight=1)
        autostart_buttons.grid_columnconfigure(1, weight=1)
    
    def add_button_hover_effect(self, button, original_color):
        """添加按钮悬停效果"""
        def on_enter(e):
            # 计算更深的颜色
            darker_color = self.darken_color(original_color, 0.1)
            button.configure(bg=darker_color)
        
        def on_leave(e):
            button.configure(bg=original_color)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def darken_color(self, color, factor):
        """使颜色变深"""
        if color.startswith('#'):
            color = color[1:]
        
        r = int(color[0:2], 16)
        g = int(color[2:4], 16) 
        b = int(color[4:6], 16)
        
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def create_log_panel(self, parent):
        """创建日志面板"""
        # 日志面板容器
        log_container = tk.Frame(parent, bg='#ffffff')
        log_container.grid(row=3, column=0, sticky="ewns", padx=30, pady=(5, 10))
        
        # 配置网格权重
        log_container.grid_rowconfigure(1, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        
        # 日志面板标题
        log_title = tk.Label(log_container, text="📋 操作日志", 
                            font=(self.system_font, 12, 'bold'),
                            fg='#2c3e50', bg='#ffffff')
        log_title.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(log_container, 
                                                 height=25, width=70,
                                                 font=('Consolas', 9),
                                                 bg='#f8f9fa',
                                                 fg='#2c3e50',
                                                 relief='flat',
                                                 bd=1)
        self.log_text.grid(row=1, column=0, sticky="ewns", pady=(0, 10))
        
        # 按钮区域
        button_frame = tk.Frame(log_container, bg='#ffffff')
        button_frame.grid(row=2, column=0, sticky="ew")
        
        # 清空日志按钮
        clear_btn = tk.Button(button_frame, text="🗑️ 清空日志", 
                             command=self.clear_log,
                             font=(self.system_font, 9),
                             bg='#e74c3c', fg='white',
                             relief='flat', bd=0,
                             padx=15, pady=6,
                             cursor='hand2')
        clear_btn.grid(row=0, column=0, sticky='e')
        button_frame.grid_columnconfigure(0, weight=1)
        
        # 添加悬停效果
        self.add_button_hover_effect(clear_btn, '#e74c3c')
    
    def log_message(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("日志已清空")
    
    def _execute_powershell(self, action, show_output=True, stream_output=False):
        """执行PowerShell命令 (Windows)"""
        def run():
            try:
                # 设置加载状态
                self.root.after(0, lambda: self.set_operation_loading(action, True))
                self.log_message(f"执行操作: {action}")
                
                cmd = [
                    "powershell.exe",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(self.launcher_script),
                    "-Action", action
                ]
                
                if stream_output:
                    # 流式输出模式（用于前台运行）
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='gbk',  # 使用GBK编码处理中文输出
                        errors='ignore',  # 忽略编码错误
                        bufsize=1,
                        universal_newlines=True,
                        cwd=self.project_root,
                        creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏PowerShell窗口
                    )
                    
                    # 实时读取输出
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            self.root.after(0, lambda msg=output.strip(): self.log_message(msg))
                    
                    process.wait()
                    return_code = process.returncode
                else:
                    # 批量输出模式（用于其他操作）
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='gbk',  # 使用GBK编码处理中文输出
                        errors='ignore',  # 忽略编码错误
                        cwd=self.project_root,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    stdout, stderr = process.communicate()
                    return_code = process.returncode
                    
                    if show_output:
                        if stdout.strip():
                            self.log_message(f"输出:\n{stdout.strip()}")
                        if stderr.strip():
                            self.log_message(f"错误:\n{stderr.strip()}", "ERROR")
                
                if return_code == 0:
                    self.log_message(f"操作 '{action}' 完成", "SUCCESS")
                else:
                    self.log_message(f"操作 '{action}' 失败 (退出码: {return_code})", "ERROR")
                    
                # 操作完成后刷新状态
                self.root.after(1000, self.refresh_status)
                
            except Exception as e:
                self.log_message(f"执行操作时发生错误: {str(e)}", "ERROR")
            finally:
                # 清除加载状态
                self.root.after(0, lambda: self.set_operation_loading(action, False))
        
        # 在后台线程中运行
        threading.Thread(target=run, daemon=True).start()
    
    def _execute_shell(self, action, show_output=True, stream_output=False):
        """执行Shell命令 (macOS/Linux)"""
        def run():
            try:
                # 设置加载状态
                self.root.after(0, lambda: self.set_operation_loading(action, True))
                self.log_message(f"执行操作: {action}")
                
                # 确保脚本有执行权限
                if not os.access(self.launcher_script, os.X_OK):
                    os.chmod(self.launcher_script, 0o755)
                
                cmd = [str(self.launcher_script), "--action", action]
                
                if stream_output:
                    # 流式输出模式（用于前台运行）
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        bufsize=1,
                        universal_newlines=True,
                        cwd=self.project_root
                    )
                    
                    # 实时读取输出
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            self.root.after(0, lambda msg=output.strip(): self.log_message(msg))
                    
                    process.wait()
                    return_code = process.returncode
                else:
                    # 批量输出模式（用于其他操作）
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        cwd=self.project_root
                    )
                    
                    stdout, stderr = process.communicate()
                    return_code = process.returncode
                    
                    if show_output:
                        if stdout.strip():
                            self.log_message(f"输出:\n{stdout.strip()}")
                        if stderr.strip():
                            self.log_message(f"错误:\n{stderr.strip()}", "ERROR")
                
                if return_code == 0:
                    self.log_message(f"操作 '{action}' 完成", "SUCCESS")
                else:
                    self.log_message(f"操作 '{action}' 失败 (退出码: {return_code})", "ERROR")
                    
                # 操作完成后刷新状态
                self.root.after(1000, self.refresh_status)
                
            except Exception as e:
                self.log_message(f"执行操作时发生错误: {str(e)}", "ERROR")
            finally:
                # 清除加载状态
                self.root.after(0, lambda: self.set_operation_loading(action, False))
        
        # 在后台线程中运行
        threading.Thread(target=run, daemon=True).start()
    
    def start_config_editor(self):
        """启动配置编辑器"""
        self.command_executor("config")
    
    def run_main_program(self):
        """运行主程序"""
        # 检查是否已有后台服务在运行
        if self.is_background_service_running():
            response = messagebox.askyesno(
                "后台服务检测",
                "检测到后台服务正在运行！\n\n"
                "同时运行前台和后台程序可能导致冲突。\n"
                "建议先停止后台服务再运行前台程序。\n\n"
                "是否继续运行前台程序？",
                icon='warning'
            )
            if not response:
                self.log_message("用户取消前台程序启动", "INFO")
                return
            else:
                self.log_message("用户选择继续启动前台程序（后台服务仍在运行）", "WARNING")
        
        self.log_message("启动前台主程序，将显示实时日志输出...", "INFO")
        self.command_executor("run", show_output=True, stream_output=True)
    
    def start_background(self):
        """启动后台服务"""
        # 检查是否已有前台程序在运行
        if self.is_foreground_program_running():
            response = messagebox.askyesno(
                "前台程序检测",
                "检测到前台程序正在运行！\n\n"
                "同时运行前台和后台程序可能导致冲突。\n"
                "建议先停止前台程序再启动后台服务。\n\n"
                "是否继续启动后台服务？",
                icon='warning'
            )
            if not response:
                self.log_message("用户取消后台服务启动", "INFO")
                return
            else:
                self.log_message("用户选择继续启动后台服务（前台程序仍在运行）", "WARNING")
        
        # 检查后台服务是否已经在运行
        if self.is_background_service_running():
            self.log_message("后台服务已经在运行中", "WARNING")
            messagebox.showwarning("服务状态", "后台服务已经在运行中，无需重复启动。")
            return
            
        self.command_executor("start")
    
    def stop_background(self):
        """停止后台服务"""
        self.command_executor("stop")
    
    def restart_background(self):
        """重启后台服务"""
        self.command_executor("restart")
    
    def enable_autostart(self):
        """启用开机自启动"""
        self.command_executor("enable-autostart")
    
    def disable_autostart(self):
        """禁用开机自启动"""
        self.command_executor("disable-autostart")
    
    def check_environment(self):
        """检查环境状态"""
        self.command_executor("check")
    
    def refresh_status(self):
        """刷新状态"""
        if self.is_checking_status:
            return
            
        def check_status():
            self.is_checking_status = True
            try:
                # 显示加载状态
                self.root.after(0, lambda: self.show_status_loading(True))
                
                # 检查后台进程
                service_running = self.is_background_service_running()
                
                # 检查自启动状态
                autostart_enabled = self.is_autostart_enabled()
                
                # 更新UI
                self.root.after(0, lambda: self.update_status_display(service_running, autostart_enabled))
                
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"状态检查失败: {str(e)}", "ERROR"))
            finally:
                self.is_checking_status = False
                # 清除加载状态
                self.root.after(0, lambda: self.show_status_loading(False))
        
        if self.status_check_thread and self.status_check_thread.is_alive():
            return
            
        self.status_check_thread = threading.Thread(target=check_status, daemon=True)
        self.status_check_thread.start()
    
    def update_status_display(self, service_running, autostart_enabled):
        """更新状态显示"""
        # 停止加载动画
        if hasattr(self.service_card, 'loading_canvas'):
            self.stop_loading_animation(self.service_card['loading_canvas'])
            self.service_card['loading_canvas'].place_forget()
        
        if hasattr(self.autostart_card, 'loading_canvas'):
            self.stop_loading_animation(self.autostart_card['loading_canvas'])
            self.autostart_card['loading_canvas'].place_forget()
        
        if service_running:
            self.service_card['var'].set("🟢 运行中")
            self.service_card['label'].configure(fg="#27ae60")
        else:
            self.service_card['var'].set("🔴 已停止")
            self.service_card['label'].configure(fg="#e74c3c")
            
        if autostart_enabled:
            self.autostart_card['var'].set("🟢 已启用")
            self.autostart_card['label'].configure(fg="#27ae60")
        else:
            self.autostart_card['var'].set("🔴 已禁用")
            self.autostart_card['label'].configure(fg="#e74c3c")
    
    def show_status_loading(self, loading=True):
        """显示状态加载状态"""
        if loading:
            # 显示加载动画
            if hasattr(self.service_card, 'loading_canvas'):
                self.service_card['loading_canvas'].place(x=2, y=2)
                self.start_loading_animation(self.service_card['loading_canvas'])
            
            if hasattr(self.autostart_card, 'loading_canvas'):
                self.autostart_card['loading_canvas'].place(x=2, y=2)
                self.start_loading_animation(self.autostart_card['loading_canvas'])
            
            # 更新状态文本
            self.service_card['var'].set("⏳ 检查中...")
            self.service_card['label'].configure(fg="#7f8c8d")
            self.autostart_card['var'].set("⏳ 检查中...")
            self.autostart_card['label'].configure(fg="#7f8c8d")
        else:
            # 停止加载动画
            if hasattr(self.service_card, 'loading_canvas'):
                self.stop_loading_animation(self.service_card['loading_canvas'])
                self.service_card['loading_canvas'].place_forget()
            
            if hasattr(self.autostart_card, 'loading_canvas'):
                self.stop_loading_animation(self.autostart_card['loading_canvas'])
                self.autostart_card['loading_canvas'].place_forget()
    
    def start_auto_refresh(self):
        """启动自动状态刷新"""
        self.schedule_auto_refresh()
    
    def schedule_auto_refresh(self):
        """安排下一次自动刷新"""
        if self.auto_refresh_job:
            self.root.after_cancel(self.auto_refresh_job)
        
        self.auto_refresh_job = self.root.after(self.auto_refresh_interval, self.auto_refresh_callback)
    
    def auto_refresh_callback(self):
        """自动刷新回调函数"""
        self.refresh_status()
        # 安排下一次刷新
        self.schedule_auto_refresh()
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        if self.auto_refresh_job:
            self.root.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None
    
    def is_background_service_running(self):
        """检查后台服务是否运行（跨平台）"""
        try:
            print(f"DEBUG: 开始检测后台服务，project_root = {self.project_root}")
            found_processes = []  # 用于调试
            
            # 根据操作系统确定进程名称
            if self.system == "windows":
                process_names = ['python.exe', 'pythonw.exe']
            else:
                process_names = ['python', 'python3']
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name']
                    if proc_name in process_names and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        
                        # 调试信息：记录所有Python进程
                        if 'main.py' in cmdline:
                            found_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc_name,
                                'cmdline': cmdline
                            })
                        
                        # 检查是否为运行main.py的进程
                        if 'main.py' in cmdline:
                            # 使用跨平台路径匹配
                            project_root_str = str(self.project_root)
                            
                            # 统一使用正斜杠进行路径匹配
                            cmdline_normalized = cmdline.replace('\\', '/')
                            project_root_normalized = project_root_str.replace('\\', '/')
                            
                            print(f"DEBUG: 检查进程 PID={proc.info['pid']}")
                            print(f"DEBUG:   cmdline = {cmdline}")
                            print(f"DEBUG:   project_root_str = {project_root_str}")
                            print(f"DEBUG:   cmdline_normalized = {cmdline_normalized}")
                            print(f"DEBUG:   project_root_normalized = {project_root_normalized}")
                            print(f"DEBUG:   路径匹配结果 = {project_root_normalized.lower() in cmdline_normalized.lower()}")
                            
                            if (project_root_normalized.lower() in cmdline_normalized.lower() or
                                'main.py' in cmdline_normalized):
                                # 排除启动器GUI本身
                                if 'launcher_gui.py' not in cmdline and 'cross_platform_launcher_gui.py' not in cmdline:
                                    print(f"DEBUG: 找到匹配的进程！")
                                    # 输出调试信息到日志
                                    self.root.after(0, lambda: self.log_message(
                                        f"检测到运行中的程序: PID={proc.info['pid']}, CMD={cmdline}", "DEBUG"))
                                    return True
                                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 如果没找到，输出调试信息
            print(f"DEBUG: 未找到匹配的进程，found_processes = {len(found_processes)}")
            if found_processes:
                debug_msg = f"找到{len(found_processes)}个main.py进程，但都不匹配项目路径"
                for p in found_processes:
                    debug_msg += f"\n  PID={p['pid']}: {p['cmdline']}"
                debug_msg += f"\n  项目路径: {self.project_root}"
                self.root.after(0, lambda msg=debug_msg: self.log_message(msg, "DEBUG"))
            
            return False
        except Exception as e:
            print(f"DEBUG: 进程检测异常: {str(e)}")
            self.root.after(0, lambda: self.log_message(f"进程检测异常: {str(e)}", "ERROR"))
            return False
    
    def is_foreground_program_running(self):
        """检查前台程序是否运行（与后台检测共用逻辑）"""
        # 现在统一检测，不区分前台后台
        return self.is_background_service_running()
    
    def is_autostart_enabled(self):
        """检查自启动是否启用（跨平台）"""
        try:
            if self.system == "windows":
                startup_path = Path(os.path.expanduser("~")) / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
                vbs_file = startup_path / "PubMedLiteraturePush.vbs"
                batch_file = startup_path / "PubMedLiteraturePush.bat"
                return vbs_file.exists() or batch_file.exists()
            
            elif self.system == "darwin":
                # macOS LaunchAgent
                plist_file = Path.home() / "Library/LaunchAgents/com.pubmed-literature-push.plist"
                return plist_file.exists()
            
            else:  # Linux
                # Linux systemd user service
                service_file = Path.home() / ".config/systemd/user/pubmed-literature-push.service"
                return service_file.exists()
                
        except Exception as e:
            print(f"DEBUG: 自启动检测异常: {str(e)}")
            return False

def main():
    """主函数"""
    root = tk.Tk()
    app = CrossPlatformLauncherGUI(root)
    
    # 窗口关闭事件
    def on_closing():
        app.stop_auto_refresh()  # 停止自动刷新
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()