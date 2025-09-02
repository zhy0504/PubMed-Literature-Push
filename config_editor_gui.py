import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import yaml
import os
import threading

# We need to be able to import from src
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from src.llm_service import LLMService
from src.email_sender import EmailSender

# 添加DPI感知支持
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)  # 设置DPI感知
except:
    pass  # 在非Windows系统上忽略

# Helper class for a scrollable frame
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

class ConfigEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PubMed Literature Push 配置编辑器")
        
        # 获取屏幕尺寸并设置响应式窗口大小
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # 计算窗口大小（屏幕的65%，适中的窗口大小）
        window_width = max(800, min(1200, int(screen_width * 0.65)))
        window_height = max(700, min(1000, int(screen_height * 0.8)))
        
        # 居中显示
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(900, 700)  # 增大最小尺寸确保内容显示完整
        
        # 使窗口可调整大小
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap(default="icon.ico")
        except:
            pass
        
        self.config_file = 'config.yaml'
        self.dirty = tk.BooleanVar(value=False)
        
        # 配置样式
        self.setup_styles()
        
        # 创建主容器框架 - 添加居中和间距
        main_container = ttk.Frame(root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Place the notebook inside the main container
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(pady=5, padx=5, expand=True, fill="both")

        self.load_config()

        # Create tabs
        self.create_general_tab()
        self.create_users_and_llm_tab()
        self.create_prompts_tab()

        # Place save button at the bottom of the main container
        save_frame = ttk.Frame(main_container)
        save_frame.pack(fill="x", pady=15, padx=15)
        
        self.save_button = ttk.Button(save_frame, text="💾 保存配置", command=self.save_config, style='Action.TButton')
        self.save_button.pack(side="right", padx=10)
        
        # 添加状态指示
        self.status_label = ttk.Label(save_frame, text="", style='Info.TLabel')
        self.status_label.pack(side="left", padx=10)

        # Set up traces for all input variables
        self.add_traces()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 绑定窗口大小改变事件
        self.root.bind('<Configure>', self.on_window_configure)

    def setup_styles(self):
        """设置界面样式 - 与主启动界面保持一致的风格"""
        style = ttk.Style()
        
        # 尝试使用现代主题
        try:
            style.theme_use('vista')  # Windows现代主题
        except:
            try:
                style.theme_use('clam')  # 跨平台现代主题
            except:
                style.theme_use('default')
        
        # 配置主题色彩 - 与主启动界面保持一致
        colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'light': '#ecf0f1',
            'dark': '#34495e'
        }
        
        # 配置自定义样式
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 14, 'bold'), foreground=colors['primary'])
        style.configure('Header.TLabel', font=('Microsoft YaHei UI', 10, 'bold'), foreground=colors['primary'])
        style.configure('Info.TLabel', font=('Microsoft YaHei UI', 9), foreground=colors['dark'])
        
        # 配置按钮样式 - 使用主启动界面的按钮风格，黑色文字配浅色背景
        style.configure('Action.TButton', font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('Action.TButton',
                  background=[('active', '#bdc3c7'), ('!disabled', '#ecf0f1')],
                  foreground=[('active', 'black'), ('!disabled', 'black')])
        
        # 配置默认按钮样式 - 深色文字在浅色背景上清晰可见
        style.configure('TButton', font=('Microsoft YaHei UI', 9))
        style.map('TButton',
                  background=[('active', '#e8e8e8'), ('!disabled', '#f5f5f5')],
                  foreground=[('active', colors['primary']), ('!disabled', colors['primary'])])
        
        # 配置输入框样式 - 与主启动界面保持一致
        style.configure('Modern.TEntry', fieldbackground='#ffffff', relief='flat', borderwidth=1)
        style.map('Modern.TEntry',
                  focuscolor=[('!focus', colors['light']), ('focus', colors['secondary'])])
        
        # 配置框架样式 - 使用主启动界面的背景色
        style.configure('TLabelFrame', relief='flat', borderwidth=1,
                       background='#f8f9fa', foreground=colors['primary'])
        style.configure('TFrame', background='#ffffff')
        
        # 配置Notebook样式 - 现代化风格
        style.configure('TNotebook', background='#f8f9fa', borderwidth=0)
        style.configure('TNotebook.Tab', padding=[15, 10], font=('Microsoft YaHei UI', 10, 'bold'),
                       background='#ecf0f1', foreground=colors['primary'])
        style.map('TNotebook.Tab',
                  background=[('selected', '#ffffff'), ('active', '#f8f9fa')])
        
        # 设置根窗口背景色 - 与主启动界面一致
        self.root.configure(bg='#f0f8ff')  # 浅蓝色背景
    
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

    def on_window_configure(self, event):
        """窗口大小改变事件处理"""
        if event.widget == self.root:
            # 更新所有Canvas的滚动区域
            self.update_all_scroll_regions()
    
    def update_all_scroll_regions(self):
        """更新所有滚动区域"""
        try:
            # 延迟更新以确保所有组件都已渲染完成
            self.root.after(100, self._delayed_scroll_update)
        except:
            pass
    
    def _delayed_scroll_update(self):
        """延迟更新滚动区域"""
        try:
            # 遍历所有标签页中的Canvas并更新滚动区域
            for tab_id in self.notebook.tabs():
                tab_widget = self.notebook.nametowidget(tab_id)
                if hasattr(tab_widget, 'configure'):
                    for child in tab_widget.winfo_children():
                        if isinstance(child, tk.Canvas):
                            child.configure(scrollregion=child.bbox("all"))
        except:
            pass

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                'scheduler': {}, 'pubmed': {}, 
                'llm_providers': [], 'task_model_mapping': {}, 
                'prompts': {}, 'smtp': {}, 'users': []
            }

    def create_general_tab(self):
        # 创建主容器
        main_container = ttk.Frame(self.notebook)
        main_container.configure(style='TFrame')
        self.notebook.add(main_container, text='⚙️ 通用和SMTP')
        
        # 创建滚动容器
        canvas = tk.Canvas(main_container, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        
        def configure_scroll_region(event=None):
            # 更新滚动区域
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 配置canvas内框架的宽度以适应canvas宽度
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:
                canvas.itemconfig(canvas_window, width=canvas_width)
        
        frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_scroll_region)
        
        canvas_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局管理
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 主标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        title_label = ttk.Label(title_frame, text="系统配置", style='Title.TLabel')
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="配置系统运行参数和邮件设置", style='Info.TLabel')
        subtitle_label.pack(anchor="w", pady=(0, 5))
        
        # 通用设置卡片
        general_frame = ttk.LabelFrame(frame, text="📅 调度设置", padding="15")
        general_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        # 使用网格布局，提高可读性
        settings_grid = ttk.Frame(general_frame)
        settings_grid.pack(fill="x", expand=True)
        
        # 每日运行时间
        ttk.Label(settings_grid, text="每日运行时间 (HH:MM):", style='Header.TLabel').grid(row=0, column=0, padx=(0, 15), pady=8, sticky="w")
        self.run_time_var = tk.StringVar(value=self.config.get('scheduler', {}).get('run_time', '08:00'))
        time_entry = ttk.Entry(settings_grid, textvariable=self.run_time_var, style='Modern.TEntry', width=15)
        time_entry.grid(row=0, column=1, padx=(0, 30), pady=8, sticky="w")
        
        # 最大文章数
        ttk.Label(settings_grid, text="最大文章数:", style='Header.TLabel').grid(row=0, column=2, padx=(0, 15), pady=8, sticky="w")
        self.max_articles_var = tk.IntVar(value=self.config.get('pubmed', {}).get('max_articles', 50))
        articles_entry = ttk.Entry(settings_grid, textvariable=self.max_articles_var, style='Modern.TEntry', width=10)
        articles_entry.grid(row=0, column=3, pady=8, sticky="w")
        
        # 关键词任务间隔
        ttk.Label(settings_grid, text="关键词任务间隔 (秒):", style='Header.TLabel').grid(row=1, column=0, padx=(0, 15), pady=8, sticky="w")
        self.delay_keywords_var = tk.IntVar(value=self.config.get('scheduler', {}).get('delay_between_keywords_sec', 60))
        delay_entry = ttk.Entry(settings_grid, textvariable=self.delay_keywords_var, style='Modern.TEntry', width=10)
        delay_entry.grid(row=1, column=1, pady=8, sticky="w")
        
        # 说明信息
        info_frame = ttk.Frame(general_frame)
        info_frame.pack(fill="x", pady=(10, 0))
        
        info_icon = ttk.Label(info_frame, text="ℹ️", font=('Arial', 12))
        info_icon.pack(side="left")
        
        info_label = ttk.Label(info_frame, text="邮件发送间隔由系统根据发件邮箱数量自动计算", style='Info.TLabel')
        info_label.pack(side="left", padx=(5, 0))

        # 翻译设置卡片
        trans_frame = ttk.LabelFrame(frame, text="🌐 翻译设置", padding="15")
        trans_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        trans_grid = ttk.Frame(trans_frame)
        trans_grid.pack(fill="x", expand=True)
        
        # 翻译批处理大小
        ttk.Label(trans_grid, text="翻译批处理大小:", style='Header.TLabel').grid(row=0, column=0, padx=(0, 15), pady=8, sticky="w")
        self.batch_size_var = tk.IntVar(value=self.config.get('translation_settings', {}).get('batch_size', 5))
        batch_entry = ttk.Entry(trans_grid, textvariable=self.batch_size_var, style='Modern.TEntry', width=10)
        batch_entry.grid(row=0, column=1, padx=(0, 30), pady=8, sticky="w")

        # 翻译批次间隔
        ttk.Label(trans_grid, text="翻译批次间隔 (秒):", style='Header.TLabel').grid(row=0, column=2, padx=(0, 15), pady=8, sticky="w")
        self.delay_batches_var = tk.IntVar(value=self.config.get('translation_settings', {}).get('delay_between_batches_sec', 5))
        delay_batch_entry = ttk.Entry(trans_grid, textvariable=self.delay_batches_var, style='Modern.TEntry', width=10)
        delay_batch_entry.grid(row=0, column=3, pady=8, sticky="w")

        # SMTP邮件设置卡片
        smtp_frame = ttk.LabelFrame(frame, text="📧 SMTP 邮件设置", padding="15")
        smtp_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        # 通用配置区域
        common_section = ttk.Frame(smtp_frame)
        common_section.pack(fill="x", pady=(0, 15))
        
        common_title = ttk.Label(common_section, text="通用配置", style='Header.TLabel')
        common_title.pack(anchor="w", pady=(0, 10))
        
        common_grid = ttk.Frame(common_section)
        common_grid.pack(fill="x")
        
        self.smtp_common_vars = {}
        common_fields = [
            ('max_retries', '最大重试次数', False),
            ('retry_delay_sec', '重试延迟(秒)', False),
            ('base_interval_minutes', '基础间隔(分钟)', False),
            ('admin_email', '管理员邮箱(接收报告)', False)
        ]
        
        # 前三个字段排成一行
        for i, (key, name, is_secret) in enumerate(common_fields[:3]):
            ttk.Label(common_grid, text=f"{name}:", style='Header.TLabel').grid(
                row=0, column=i*2, padx=(0, 10), pady=8, sticky="w"
            )
            
            defaults = {'max_retries': 3, 'retry_delay_sec': 300, 'base_interval_minutes': 10}
            default_val = str(self.config.get('smtp', {}).get(key, defaults.get(key, '')))
            
            var = tk.StringVar(value=default_val)
            entry = ttk.Entry(common_grid, textvariable=var, style='Modern.TEntry', width=10)
            entry.grid(row=0, column=i*2+1, padx=(0, 30), pady=8, sticky="w")
            self.smtp_common_vars[key] = var
        
        # 管理员邮箱单独一行
        ttk.Label(common_grid, text="管理员邮箱:", style='Header.TLabel').grid(
            row=1, column=0, padx=(0, 10), pady=8, sticky="w"
        )
        admin_email_val = str(self.config.get('smtp', {}).get('admin_email', ''))
        admin_var = tk.StringVar(value=admin_email_val)
        admin_entry = ttk.Entry(common_grid, textvariable=admin_var, style='Modern.TEntry', width=40)
        admin_entry.grid(row=1, column=1, columnspan=5, pady=8, sticky="ew")
        self.smtp_common_vars['admin_email'] = admin_var
        
        common_grid.columnconfigure(5, weight=1)
        
        # 发件邮箱管理区域
        accounts_section = ttk.Frame(smtp_frame)
        accounts_section.pack(fill="x", pady=(10, 15))
        
        accounts_header = ttk.Frame(accounts_section)
        accounts_header.pack(fill="x", pady=(0, 10))
        
        accounts_title = ttk.Label(accounts_header, text="发件邮箱管理", style='Header.TLabel')
        accounts_title.pack(side="left")
        
        # 账号状态信息
        accounts_info_frame = ttk.Frame(accounts_section)
        accounts_info_frame.pack(fill="x", pady=(0, 10))
        
        self.smtp_accounts_info = tk.StringVar(value=self.get_smtp_accounts_info())
        info_icon = ttk.Label(accounts_info_frame, text="📊", font=('Arial', 12))
        info_icon.pack(side="left")
        
        info_label = ttk.Label(accounts_info_frame, textvariable=self.smtp_accounts_info, style='Info.TLabel')
        info_label.pack(side="left", padx=(5, 0))
        
        # 管理按钮
        manage_accounts_button = ttk.Button(accounts_section, text="📝 管理发件邮箱",
                                          command=self.open_smtp_manager, style='Action.TButton')
        manage_accounts_button.pack(anchor="w", pady=(0, 15))
        
        # 测试邮件功能区域
        test_section = ttk.Frame(smtp_frame)
        test_section.pack(fill="x")
        
        test_title = ttk.Label(test_section, text="邮件测试", style='Header.TLabel')
        test_title.pack(anchor="w", pady=(0, 10))
        
        test_grid = ttk.Frame(test_section)
        test_grid.pack(fill="x")
        
        ttk.Label(test_grid, text="测试收件邮箱:", style='Header.TLabel').grid(
            row=0, column=0, padx=(0, 10), pady=8, sticky="w"
        )
        self.test_email_recipient_var = tk.StringVar()
        test_entry = ttk.Entry(test_grid, textvariable=self.test_email_recipient_var,
                              style='Modern.TEntry', width=30)
        test_entry.grid(row=0, column=1, padx=(0, 15), pady=8, sticky="ew")
        
        test_smtp_button = ttk.Button(test_grid, text="📨 发送测试邮件",
                                    command=self.test_smtp_connection, style='Action.TButton')
        test_smtp_button.grid(row=0, column=2, pady=8)
        
        test_grid.columnconfigure(1, weight=1)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def create_users_and_llm_tab(self):
        # 创建主容器
        main_container = ttk.Frame(self.notebook)
        main_container.configure(style='TFrame')
        self.notebook.add(main_container, text='🤖 智能配置')
        
        # 创建滚动容器
        canvas = tk.Canvas(main_container, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:
                canvas.itemconfig(canvas_window, width=canvas_width)
        
        frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_scroll_region)
        
        canvas_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局管理
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 主标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        title_label = ttk.Label(title_frame, text="AI智能配置", style='Title.TLabel')
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="配置用户组、关键词、LLM提供商和任务模型映射", style='Info.TLabel')
        subtitle_label.pack(anchor="w", pady=(0, 5))
        
        # 用户组配置卡片
        users_frame = ttk.LabelFrame(frame, text="👥 用户组和关键词", padding="15")
        users_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        # 自动转换传统格式到用户组格式
        if self.config.get('users') and not self.config.get('user_groups'):
            self.convert_users_to_user_groups()
        
        # 删除传统用户配置（如果存在）
        if 'users' in self.config:
            del self.config['users']
        
        # 确保有user_groups配置
        if 'user_groups' not in self.config:
            self.config['user_groups'] = []
        
        # 添加说明
        info_text = "用户组格式: 支持多个用户共享相同关键词，以邮箱作为用户标识"
        ttk.Label(users_frame, text=info_text, foreground="gray").pack(pady=(0, 10))
        
        # 显示当前用户组数量
        self.users_info = tk.StringVar(value=self.get_users_info())
        info_label = ttk.Label(users_frame, textvariable=self.users_info)
        info_label.pack(pady=5)
        
        # 管理按钮
        manage_users_button = ttk.Button(users_frame, text="管理用户组和关键词", command=self.open_users_manager)
        manage_users_button.pack(pady=10)
        
        # LLM提供商配置卡片
        providers_frame = ttk.LabelFrame(frame, text="🤖 LLM 提供商配置", padding="15")
        providers_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        # 显示当前提供商数量
        self.providers_info = tk.StringVar(value=self.get_providers_info())
        info_label = ttk.Label(providers_frame, textvariable=self.providers_info)
        info_label.pack(pady=5)
        
        # 管理按钮
        buttons_frame = ttk.Frame(providers_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        manage_providers_button = ttk.Button(buttons_frame, text="管理LLM提供商", command=self.open_llm_manager)
        manage_providers_button.pack(side="left", padx=(0, 10))
        
        test_llm_button = ttk.Button(buttons_frame, text="测试所有提供商", command=self.test_llm_connections)
        test_llm_button.pack(side="right")
        
        # 任务模型映射配置卡片
        task_mapping_frame = ttk.LabelFrame(frame, text="⚙️ 任务模型映射", padding="15")
        task_mapping_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        self.task_mapping_vars = {}
        
        tasks = {
            'query_generator': '检索词生成器',
            'summarizer': '综述生成器',
            'abstract_translator': '摘要翻译器'
        }
        for i, (task_key, task_name) in enumerate(tasks.items()):
            p_frame = ttk.LabelFrame(task_mapping_frame, text=task_name, padding="10")
            p_frame.pack(fill="x", expand=True, pady=5)

            task_map = self.config.get('task_model_mapping', {}).get(task_key, {})
            self.task_mapping_vars[task_key] = {}

            ttk.Label(p_frame, text="提供商:").grid(row=0, column=0, sticky="w", padx=5)
            provider_var = tk.StringVar(value=task_map.get('provider_name', ''))
            combo = ttk.Combobox(p_frame, textvariable=provider_var, state="readonly")
            combo.grid(row=0, column=1, sticky="ew", padx=5)
            self.task_mapping_vars[task_key]['provider_name'] = provider_var
            self.task_mapping_vars[task_key]['combo'] = combo

            ttk.Label(p_frame, text="模型名称:").grid(row=1, column=0, sticky="w", padx=5)
            model_var = tk.StringVar(value=task_map.get('model_name', ''))
            ttk.Entry(p_frame, textvariable=model_var).grid(row=1, column=1, sticky="ew", padx=5)
            self.task_mapping_vars[task_key]['model_name'] = model_var
            
            p_frame.columnconfigure(1, weight=1)
        
        # 更新任务映射选项
        self.update_task_mapping_options()

    # 移除旧的LLM提供商UI方法，因为现在使用弹出窗口管理

    # 移除create_task_mapping_tab方法，因为已经合并到create_llm_and_tasks_tab中

    def update_task_mapping_options(self):
        if not hasattr(self, 'task_mapping_vars'):
            return
        provider_names = [p.get('name', '') for p in self.config.get('llm_providers', [])]
        for task in self.task_mapping_vars.values():
            current_selection = task['provider_name'].get()
            task['combo']['values'] = provider_names
            if current_selection in provider_names:
                task['provider_name'].set(current_selection)
            elif provider_names:
                task['provider_name'].set(provider_names[0])
            else:
                task['provider_name'].set('')

    def create_prompts_tab(self):
        # 创建主容器
        main_container = ttk.Frame(self.notebook)
        main_container.configure(style='TFrame')
        self.notebook.add(main_container, text='📝 提示词')
        
        # 创建滚动容器
        canvas = tk.Canvas(main_container, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:
                canvas.itemconfig(canvas_window, width=canvas_width)
        
        frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_scroll_region)
        
        canvas_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局管理
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 主标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        title_label = ttk.Label(title_frame, text="AI提示词配置", style='Title.TLabel')
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="自定义AI模型的提示词模板", style='Info.TLabel')
        subtitle_label.pack(anchor="w", pady=(0, 5))
        self.prompt_vars = {}
        prompts = {
            'generate_query': ('🔍 生成检索词', '配置用于生成PubMed检索词的AI提示模板'),
            'generate_review': ('📄 生成综述', '配置用于生成文献综述的AI提示模板'),
            'translate_abstract': ('🌐 翻译摘要', '配置用于翻译英文摘要的AI提示模板')
        }
        
        for i, (key, (name, description)) in enumerate(prompts.items()):
            p_frame = ttk.LabelFrame(frame, text=name, padding="15")
            p_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))
            
            # 添加描述
            desc_label = ttk.Label(p_frame, text=description, style='Info.TLabel')
            desc_label.pack(anchor="w", pady=(0, 10))
            
            text_widget = scrolledtext.ScrolledText(p_frame, wrap=tk.WORD, height=8,
                                                  font=('Consolas', 10), relief='solid', borderwidth=1)
            text_widget.pack(fill="both", expand=True)
            text_widget.insert(tk.END, self.config.get('prompts', {}).get(key, ''))
            self.prompt_vars[key] = text_widget
            text_widget.bind("<<Modified>>", self.set_dirty_from_text)
            
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)


    # 移除format_change方法，因为不再支持格式切换

    def convert_users_to_user_groups(self):
        """将传统用户配置转换为用户组配置"""
        users = self.config.get('users', [])
        user_groups = []
        
        for i, user in enumerate(users):
            if user.get('email') and user.get('keywords'):
                user_groups.append({
                    'group_name': user.get('name', f'用户组{i+1}'),
                    'emails': [user['email']],
                    'keywords': user.get('keywords', [])
                })
        
        self.config['user_groups'] = user_groups
        if 'users' in self.config:
            del self.config['users']

    # 移除convert_user_groups_to_users方法，因为不再支持传统格式

    def rebuild_users_ui(self):
        for widget in self.user_widgets: widget.destroy()
        self.user_widgets = []
        self.user_data_vars = []
        
        format_type = self.config_format_var.get()
        if format_type == "user_groups":
            for i, group in enumerate(self.config.get('user_groups', [])):
                self.create_user_group_entry(i, group)
        else:
            for i, user in enumerate(self.config.get('users', [])):
                self.create_user_entry(i, user)

    def create_user_group_entry(self, index, group_data):
        frame = ttk.LabelFrame(self.users_frame, text=f"用户组 {index + 1}", padding="10")
        frame.pack(fill="x", expand=True, padx=5, pady=5)
        self.user_widgets.append(frame)
        data_vars = {}
        
        # 组名
        ttk.Label(frame, text="组名:").grid(row=0, column=0, sticky="w")
        group_name_var = tk.StringVar(value=group_data.get('group_name', ''))
        ttk.Entry(frame, textvariable=group_name_var).grid(row=0, column=1, sticky="ew", padx=5)
        data_vars['group_name'] = group_name_var
        
        # 邮箱列表
        ttk.Label(frame, text="邮箱 (空格分隔):").grid(row=1, column=0, sticky="w")
        emails_var = tk.StringVar(value=" ".join(group_data.get('emails', [])))
        ttk.Entry(frame, textvariable=emails_var).grid(row=1, column=1, sticky="ew", padx=5)
        data_vars['emails'] = emails_var
        
        # 关键词列表
        ttk.Label(frame, text="关键词 (空格分隔):").grid(row=2, column=0, sticky="w")
        keywords_var = tk.StringVar(value=" ".join(group_data.get('keywords', [])))
        ttk.Entry(frame, textvariable=keywords_var).grid(row=2, column=1, sticky="ew", padx=5)
        data_vars['keywords'] = keywords_var
        
        # 删除按钮
        remove_button = ttk.Button(frame, text="删除", command=lambda i=index: self.remove_user_or_group(i))
        remove_button.grid(row=0, column=2, padx=10)
        
        frame.columnconfigure(1, weight=1)
        self.user_data_vars.append(data_vars)
        
        # 绑定修改事件
        emails_var.trace_add("write", self.set_dirty)
        keywords_var.trace_add("write", self.set_dirty)

    def create_user_entry(self, index, user_data):
        frame = ttk.LabelFrame(self.users_frame, text=f"用户 {index + 1}", padding="10")
        frame.pack(fill="x", expand=True, padx=5, pady=5)
        self.user_widgets.append(frame)
        data_vars = {}
        ttk.Label(frame, text="用户名:").grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar(value=user_data.get('name', ''))
        ttk.Entry(frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", padx=5)
        data_vars['name'] = name_var
        ttk.Label(frame, text="邮箱:").grid(row=1, column=0, sticky="w")
        email_var = tk.StringVar(value=user_data.get('email', ''))
        ttk.Entry(frame, textvariable=email_var).grid(row=1, column=1, sticky="ew", padx=5)
        data_vars['email'] = email_var
        ttk.Label(frame, text="关键词 (空格分隔):").grid(row=2, column=0, sticky="w")
        keywords_var = tk.StringVar(value=" ".join(user_data.get('keywords', [])))
        ttk.Entry(frame, textvariable=keywords_var).grid(row=2, column=1, sticky="ew", padx=5)
        data_vars['keywords'] = keywords_var
        remove_button = ttk.Button(frame, text="删除", command=lambda i=index: self.remove_user_or_group(i))
        remove_button.grid(row=1, column=2, padx=10)
        frame.columnconfigure(1, weight=1)
        self.user_data_vars.append(data_vars)

    def add_user_or_group(self):
        format_type = self.config_format_var.get()
        if format_type == "user_groups":
            if 'user_groups' not in self.config:
                self.config['user_groups'] = []
            self.config['user_groups'].append({'group_name': '', 'emails': [], 'keywords': []})
        else:
            if 'users' not in self.config:
                self.config['users'] = []
            self.config['users'].append({'name': '', 'email': '', 'keywords': []})
        self.rebuild_users_ui()

    def remove_user_or_group(self, index):
        format_type = self.config_format_var.get()
        if format_type == "user_groups":
            if 0 <= index < len(self.config.get('user_groups', [])):
                del self.config['user_groups'][index]
        else:
            if 0 <= index < len(self.config.get('users', [])):
                del self.config['users'][index]
        self.rebuild_users_ui()

    def rebuild_smtp_accounts_ui(self):
        """重建SMTP账号配置UI"""
        for widget in self.smtp_account_widgets:
            widget.destroy()
        self.smtp_account_widgets = []
        self.smtp_account_data_vars = []
        
        accounts = self.config.get('smtp', {}).get('accounts', [])
        if not accounts:
            # 如果没有accounts配置，尝试从旧格式转换
            smtp_config = self.config.get('smtp', {})
            if smtp_config.get('server') and smtp_config.get('username'):
                accounts = [{
                    'server': smtp_config.get('server', ''),
                    'port': smtp_config.get('port', 587),
                    'username': smtp_config.get('username', ''),
                    'password': smtp_config.get('password', ''),
                    'sender_name': smtp_config.get('sender_name', 'PubMed Literature Push')
                }]
        
        # 确保至少有一个账号
        if not accounts:
            accounts = [{'server': '', 'port': 587, 'username': '', 'password': '', 'sender_name': 'PubMed Literature Push'}]
        
        for i, account in enumerate(accounts):
            self.create_smtp_account_entry(i, account)
    
    def create_smtp_account_entry(self, index, account_data):
        """创建单个SMTP账号配置条目"""
        # 找到accounts_frame
        accounts_frame = None
        for widget in self.scrollable_container.scrollable_frame.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for tab in widget.tabs():
                    tab_widget = widget.nametowidget(tab)
                    for child in tab_widget.winfo_children():
                        if isinstance(child, ttk.LabelFrame) and child.cget("text") == "SMTP 邮件设置":
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.LabelFrame) and grandchild.cget("text") == "发件邮箱账号":
                                    accounts_frame = grandchild
                                    break
        
        if not accounts_frame:
            return
        
        frame = ttk.LabelFrame(accounts_frame, text=f"发件邮箱 {index + 1}", padding="5")
        frame.pack(fill="x", padx=5, pady=3)
        self.smtp_account_widgets.append(frame)
        
        data_vars = {}
        fields = [
            ('server', '服务器地址', False),
            ('port', '端口', False),
            ('username', '邮箱用户名', False),
            ('password', '邮箱密码/授权码', True),
            ('sender_name', '发件人名称', False)
        ]
        
        for i, (key, name, is_secret) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(frame, text=f"{name}:").grid(row=row, column=col, padx=5, pady=2, sticky="w")
            
            default_val = str(account_data.get(key, ''))
            if key == 'port' and not default_val:
                default_val = '587'
            elif key == 'sender_name' and not default_val:
                default_val = 'PubMed Literature Push'
            
            var = tk.StringVar(value=default_val)
            entry_widget = ttk.Entry(frame, textvariable=var, show="*" if is_secret else None, width=25)
            entry_widget.grid(row=row, column=col+1, padx=5, pady=2, sticky="ew")
            data_vars[key] = var
            
            # 为StringVar添加trace
            var.trace_add("write", self.set_dirty)
        
        # 删除按钮
        remove_button = ttk.Button(frame, text="删除",
                                 command=lambda i=index: self.remove_smtp_account(i))
        remove_button.grid(row=0, column=4, rowspan=3, padx=10, pady=2)
        
        # 配置列权重
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        
        self.smtp_account_data_vars.append(data_vars)
    
    def add_smtp_account(self):
        """添加新的SMTP账号"""
        if 'smtp' not in self.config:
            self.config['smtp'] = {}
        if 'accounts' not in self.config['smtp']:
            self.config['smtp']['accounts'] = []
        
        self.config['smtp']['accounts'].append({
            'server': '',
            'port': 587,
            'username': '',
            'password': '',
            'sender_name': 'PubMed Literature Push'
        })
        
        self.rebuild_smtp_accounts_ui()
        self.set_dirty()
    
    def remove_smtp_account(self, index):
        """删除指定的SMTP账号"""
        accounts = self.config.get('smtp', {}).get('accounts', [])
        if 0 <= index < len(accounts):
            del accounts[index]
            if not accounts:
                # 至少保留一个空账号
                accounts.append({
                    'server': '', 'port': 587, 'username': '',
                    'password': '', 'sender_name': 'PubMed Literature Push'
                })
            self.config['smtp']['accounts'] = accounts
            self.rebuild_smtp_accounts_ui()
            self.set_dirty()

    def get_smtp_accounts_info(self):
        """获取SMTP账号信息字符串"""
        accounts = self.config.get('smtp', {}).get('accounts', [])
        if not accounts:
            # 检查旧格式
            smtp_config = self.config.get('smtp', {})
            if smtp_config.get('server') and smtp_config.get('username'):
                return "当前配置: 1个发件邮箱 (兼容格式)"
            return "当前配置: 未配置发件邮箱"
        return f"当前配置: {len(accounts)}个发件邮箱"
    
    def get_users_info(self):
        """获取用户组信息字符串"""
        groups = self.config.get('user_groups', [])
        total_emails = sum(len(group.get('emails', [])) for group in groups)
        return f"当前配置: {len(groups)}个用户组，共{total_emails}个邮箱用户"
    
    def open_smtp_manager(self):
        """打开SMTP账号管理窗口"""
        SMTPManagerDialog(self.root, self.config, self.on_smtp_updated)
    
    def open_users_manager(self):
        """打开用户组管理窗口"""
        UsersManagerDialog(self.root, self.config, "user_groups", self.on_users_updated)
    
    def get_providers_info(self):
        """获取LLM提供商信息字符串"""
        providers = self.config.get('llm_providers', [])
        return f"当前配置: {len(providers)}个LLM提供商"
    
    def open_llm_manager(self):
        """打开LLM提供商管理窗口"""
        LLMManagerDialog(self.root, self.config, self.on_llm_updated)
    
    def on_llm_updated(self):
        """LLM配置更新回调"""
        self.providers_info.set(self.get_providers_info())
        self.update_task_mapping_options()
        self.set_dirty()
    
    def on_smtp_updated(self):
        """SMTP配置更新回调"""
        self.smtp_accounts_info.set(self.get_smtp_accounts_info())
        self.set_dirty()
    
    def on_users_updated(self):
        """用户配置更新回调"""
        self.users_info.set(self.get_users_info())
        self.set_dirty()

    def _get_current_config_from_gui(self):
        current_config = {'smtp': {}}
        
        # SMTP通用配置
        if hasattr(self, 'smtp_common_vars'):
            for key, var in self.smtp_common_vars.items():
                val = var.get().strip()
                if key in ['max_retries', 'retry_delay_sec', 'base_interval_minutes']:
                    try:
                        current_config['smtp'][key] = int(val) if val else {'max_retries': 3, 'retry_delay_sec': 300, 'base_interval_minutes': 10}[key]
                    except ValueError:
                        current_config['smtp'][key] = {'max_retries': 3, 'retry_delay_sec': 300, 'base_interval_minutes': 10}[key]
                else:
                    current_config['smtp'][key] = val
        
        # SMTP账号配置
        if hasattr(self, 'smtp_account_data_vars'):
            accounts = []
            for account_vars in self.smtp_account_data_vars:
                account = {}
                for key, var in account_vars.items():
                    val = var.get().strip()
                    if key == 'port':
                        try:
                            account[key] = int(val) if val else 587
                        except ValueError:
                            account[key] = 587
                    else:
                        account[key] = val
                
                # 只保存非空的账号配置
                if account.get('server') and account.get('username'):
                    accounts.append(account)
            
            if accounts:
                current_config['smtp']['accounts'] = accounts
        
        return current_config

    def test_llm_connections(self):
        threading.Thread(target=self._test_llm_thread, daemon=True).start()

    def _test_llm_thread(self):
        messagebox.showinfo("正在测试...", "正在测试所有已定义的LLM提供商...", parent=self.root)
        
        # 使用完整的配置（来自self.config而不是GUI）
        providers = self.config.get('llm_providers', [])
        
        if not providers:
            messagebox.showwarning("警告", "没有配置任何LLM提供商！", parent=self.root)
            return
        
        results = []
        for p_config in providers:
            try:
                # 尝试获取任务模型映射中的模型名称，如果没有则使用通用测试模型
                task_mapping = self.config.get('task_model_mapping', {})
                test_model = None
                
                # 优先使用任务映射中与该提供商匹配的模型
                for task_key, task_config in task_mapping.items():
                    if task_config.get('provider_name') == p_config['name']:
                        test_model = task_config.get('model_name')
                        break
                
                # 如果没有找到匹配的模型，使用常见的测试模型名称
                if not test_model:
                    provider_type = p_config.get('provider', 'custom')
                    if provider_type == 'openai':
                        test_model = 'gpt-3.5-turbo'
                    elif provider_type == 'gemini':
                        test_model = 'gemini-pro'
                    else:
                        test_model = 'test-model'  # 自定义提供商的回退选项
                
                service = LLMService(p_config, test_model)
                service.generate("Hello")  # 简单测试请求
                results.append(f"✅ 提供商 '{p_config['name']}': 连接成功! (测试模型: {test_model})")
            except Exception as e:
                error_msg = str(e)[:100]
                results.append(f"❌ 提供商 '{p_config['name']}': 连接失败!\n   错误: {error_msg}")
        messagebox.showinfo("LLM 测试结果", "\n\n".join(results), parent=self.root)

    def test_smtp_connection(self):
        recipient = self.test_email_recipient_var.get()
        if not recipient:
            messagebox.showwarning("警告", "请输入一个用于接收测试邮件的邮箱地址。", parent=self.root)
            return
        threading.Thread(target=self._test_smtp_thread, args=(recipient,), daemon=True).start()

    def _test_smtp_thread(self, recipient):
        messagebox.showinfo("正在测试...", f"正在测试所有发件邮箱，向 {recipient} 发送测试邮件...", parent=self.root)
        
        # 使用完整的配置（包括弹出窗口保存的账号信息）
        smtp_config = self.config.get('smtp', {})
        
        # 合并GUI界面的通用配置
        gui_smtp_config = self._get_current_config_from_gui()['smtp']
        smtp_config.update(gui_smtp_config)
        
        # 确保有基础配置
        if not smtp_config.get('accounts'):
            messagebox.showerror("错误", "请先配置至少一个发件邮箱账号！", parent=self.root)
            return
        
        results = []
        accounts = smtp_config.get('accounts', [])
        
        for i, account in enumerate(accounts):
            try:
                # 为每个账号创建单独的配置
                single_account_config = smtp_config.copy()
                single_account_config['accounts'] = [account]
                
                sender = EmailSender(single_account_config)
                subject = f"PubMed Literature Push 测试邮件 - 发件账号 {i+1}"
                body = f"<h1>测试成功!</h1><p>这是来自发件邮箱 <strong>{account.get('username', 'Unknown')}</strong> 的测试邮件。</p><p>如果您收到了这封邮件，说明该发件邮箱配置正确。</p>"
                sender.send_email(recipient, subject, body)
                results.append(f"✅ 发件邮箱 {i+1} ({account.get('username', 'Unknown')}): 测试成功!")
            except Exception as e:
                results.append(f"❌ 发件邮箱 {i+1} ({account.get('username', 'Unknown')}): 测试失败!\n   错误: {str(e)[:100]}")
        
        messagebox.showinfo("SMTP测试结果", f"测试完成，共测试 {len(accounts)} 个发件邮箱：\n\n" + "\n\n".join(results), parent=self.root)

    def save_config(self):
        try:
            # General配置
            if 'scheduler' not in self.config:
                self.config['scheduler'] = {}
            if 'pubmed' not in self.config:
                self.config['pubmed'] = {}
                
            self.config['scheduler']['run_time'] = self.run_time_var.get()
            self.config['scheduler']['delay_between_keywords_sec'] = self.delay_keywords_var.get()
            # 移除手动设置的邮件发送间隔，现在由系统根据发件邮箱数量自动计算
            if 'delay_between_emails_sec' in self.config['scheduler']:
                del self.config['scheduler']['delay_between_emails_sec']
            self.config['pubmed']['max_articles'] = self.max_articles_var.get()
            
            # 翻译设置
            if 'translation_settings' not in self.config:
                self.config['translation_settings'] = {}
            self.config['translation_settings']['batch_size'] = self.batch_size_var.get()
            self.config['translation_settings']['delay_between_batches_sec'] = self.delay_batches_var.get()

            # 更新SMTP和LLM提供商配置
            gui_config = self._get_current_config_from_gui()
            
            # 只更新SMTP的通用配置，不覆盖accounts（已通过弹出窗口管理）
            if 'smtp' not in self.config:
                self.config['smtp'] = {}
            
            # 保留弹出窗口管理的accounts配置
            existing_accounts = self.config['smtp'].get('accounts', [])
            
            # 更新通用SMTP配置
            self.config['smtp'].update(gui_config['smtp'])
            
            # 恢复accounts配置（如果存在）
            if existing_accounts:
                self.config['smtp']['accounts'] = existing_accounts
            
            # LLM提供商配置已经通过弹出窗口直接修改self.config，这里不需要额外处理

            # Task Mapping
            self.config['task_model_mapping'] = {}
            for task_key, task_vars in self.task_mapping_vars.items():
                self.config['task_model_mapping'][task_key] = {
                    'provider_name': task_vars['provider_name'].get(),
                    'model_name': task_vars['model_name'].get()
                }

            # Prompts
            for key, widget in self.prompt_vars.items():
                self.config['prompts'][key] = widget.get("1.0", tk.END).strip()
            
            # Users/User Groups配置已经通过弹出窗口直接修改self.config，这里不需要额外处理
            # 弹出窗口的save_changes方法会正确更新user_groups或users配置

            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, sort_keys=False)
            
            self.dirty.set(False) # Reset dirty flag on successful save
            messagebox.showinfo("成功", "配置文件已成功保存！", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            
    def set_dirty(self, *args):
        self.dirty.set(True)

    def set_dirty_from_text(self, event):
        # The ScrolledText widget's <<Modified>> event needs to be handled carefully
        # It fires on every change, so we'll set dirty and then immediately un-flag it
        # to avoid event loops if we were to do more complex logic.
        widget = event.widget
        widget.edit_modified(False) # Reset the modified flag
        self.dirty.set(True)

    def add_traces(self):
        # General and Translation vars
        self.run_time_var.trace_add("write", self.set_dirty)
        self.max_articles_var.trace_add("write", self.set_dirty)
        self.delay_keywords_var.trace_add("write", self.set_dirty)
        self.batch_size_var.trace_add("write", self.set_dirty)
        self.delay_batches_var.trace_add("write", self.set_dirty)
        
        # SMTP通用配置vars
        if hasattr(self, 'smtp_common_vars'):
            for var in self.smtp_common_vars.values():
                var.trace_add("write", self.set_dirty)
        
        # SMTP账号配置vars
        if hasattr(self, 'smtp_account_data_vars'):
            for account_vars in self.smtp_account_data_vars:
                for var in account_vars.values():
                    var.trace_add("write", self.set_dirty)
        
        # LLM Providers - 现在通过弹出窗口管理，主界面不再需要traces
        pass

        # Task Mapping
        for task_vars in self.task_mapping_vars.values():
            task_vars['provider_name'].trace_add("write", self.set_dirty)
            task_vars['model_name'].trace_add("write", self.set_dirty)

        # Users/User Groups - 现在通过弹出窗口管理，主界面不再需要traces
        pass
                
        # For prompts, the text widget's modification is handled by a direct bind.

    def on_closing(self):
        if self.dirty.get():
            response = messagebox.askyesnocancel("退出", "您有未保存的更改。是否要保存？", parent=self.root)
            if response is True: # Yes
                self.save_config()
                # Check if save was successful (not captured here, but assume it is for now)
                self.root.destroy()
            elif response is False: # No
                self.root.destroy()
            else: # Cancel
                return
        else:
            self.root.destroy()


class SMTPManagerDialog:
    def __init__(self, parent, config, callback):
        self.parent = parent
        self.config = config
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("📧 发件邮箱管理")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 响应式窗口大小设置
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # 计算窗口大小（屏幕的50%，但不小于700x600，不大于1000x800）
        window_width = max(700, min(1000, int(screen_width * 0.5)))
        window_height = max(600, min(800, int(screen_height * 0.6)))
        
        # 居中显示
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.dialog.minsize(800, 600)  # 设置最小尺寸
        
        # 设置样式
        self.setup_styles()
        self.setup_ui()
        
    def setup_styles(self):
        """设置弹出窗口样式"""
        style = ttk.Style()
        
        # 配置对话框特定样式
        style.configure('Dialog.TLabelFrame', relief='solid', borderwidth=1,
                       background='#f8f9fa', foreground='#2c3e50')
        style.configure('DialogButton.TButton', font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('DialogButton.TButton',
                  background=[('active', '#27ae60'), ('!disabled', '#2ecc71')],
                  foreground=[('active', 'white'), ('!disabled', 'white')])
        
        self.dialog.configure(bg='#f0f8ff')
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="发件邮箱账号配置", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 滚动框架
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 账号列表
        self.account_widgets = []
        self.rebuild_accounts_ui()
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        add_button = ttk.Button(button_frame, text="添加账号", command=self.add_account)
        add_button.pack(side="left", padx=(0, 10))
        
        save_button = ttk.Button(button_frame, text="保存", command=self.save_changes)
        save_button.pack(side="right", padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="取消", command=self.dialog.destroy)
        cancel_button.pack(side="right")
    
    def rebuild_accounts_ui(self):
        for widget in self.account_widgets:
            widget.destroy()
        self.account_widgets = []
        self.account_data_vars = []
        
        accounts = self.config.get('smtp', {}).get('accounts', [])
        if not accounts:
            # 从旧格式转换
            smtp_config = self.config.get('smtp', {})
            if smtp_config.get('server') and smtp_config.get('username'):
                accounts = [{
                    'server': smtp_config.get('server', ''),
                    'port': smtp_config.get('port', 587),
                    'username': smtp_config.get('username', ''),
                    'password': smtp_config.get('password', ''),
                    'sender_name': smtp_config.get('sender_name', 'PubMed Literature Push')
                }]
        
        if not accounts:
            accounts = [{'server': '', 'port': 587, 'username': '', 'password': '', 'sender_name': 'PubMed Literature Push'}]
        
        for i, account in enumerate(accounts):
            self.create_account_entry(i, account)
    
    def create_account_entry(self, index, account_data):
        frame = ttk.LabelFrame(self.scrollable_frame, text=f"发件邮箱 {index + 1}", padding="10")
        frame.pack(fill="x", pady=5)
        self.account_widgets.append(frame)
        
        data_vars = {}
        fields = [
            ('server', '服务器地址', False),
            ('port', '端口', False),
            ('username', '邮箱用户名', False),
            ('password', '邮箱密码/授权码', True),
            ('sender_name', '发件人名称', False)
        ]
        
        for i, (key, name, is_secret) in enumerate(fields):
            ttk.Label(frame, text=f"{name}:").grid(row=i, column=0, padx=5, pady=3, sticky="w")
            
            default_val = str(account_data.get(key, ''))
            if key == 'port' and not default_val:
                default_val = '587'
            elif key == 'sender_name' and not default_val:
                default_val = 'PubMed Literature Push'
            
            var = tk.StringVar(value=default_val)
            entry_widget = ttk.Entry(frame, textvariable=var, show="*" if is_secret else None, width=50)
            entry_widget.grid(row=i, column=1, padx=5, pady=3, sticky="ew")
            data_vars[key] = var
        
        # 删除按钮 - 放在右侧，更加显眼
        remove_button = ttk.Button(frame, text="删除账号",
                                 command=lambda i=index: self.remove_account(i))
        remove_button.grid(row=0, column=2, rowspan=2, padx=15, pady=5, sticky="n")
        
        frame.columnconfigure(1, weight=1)
        self.account_data_vars.append(data_vars)
    
    def add_account(self):
        if 'smtp' not in self.config:
            self.config['smtp'] = {}
        if 'accounts' not in self.config['smtp']:
            self.config['smtp']['accounts'] = []
        
        self.config['smtp']['accounts'].append({
            'server': '',
            'port': 587,
            'username': '',
            'password': '',
            'sender_name': 'PubMed Literature Push'
        })
        
        self.rebuild_accounts_ui()
    
    def remove_account(self, index):
        accounts = self.config.get('smtp', {}).get('accounts', [])
        if 0 <= index < len(accounts):
            del accounts[index]
            if not accounts:
                accounts.append({
                    'server': '', 'port': 587, 'username': '',
                    'password': '', 'sender_name': 'PubMed Literature Push'
                })
            self.config['smtp']['accounts'] = accounts
            self.rebuild_accounts_ui()
    
    def save_changes(self):
        # 收集所有数据
        accounts = []
        for account_vars in self.account_data_vars:
            account = {}
            for key, var in account_vars.items():
                val = var.get().strip()
                if key == 'port':
                    try:
                        account[key] = int(val) if val else 587
                    except ValueError:
                        account[key] = 587
                else:
                    account[key] = val
            
            # 只保存非空的账号配置
            if account.get('server') and account.get('username'):
                accounts.append(account)
        
        if accounts:
            if 'smtp' not in self.config:
                self.config['smtp'] = {}
            self.config['smtp']['accounts'] = accounts
            
        self.callback()
        self.dialog.destroy()


class LLMManagerDialog:
    def __init__(self, parent, config, callback):
        self.parent = parent
        self.config = config
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🤖 LLM提供商管理")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 响应式窗口大小设置
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # 计算窗口大小（屏幕的50%，但不小于700x600，不大于1000x800）
        window_width = max(700, min(1000, int(screen_width * 0.5)))
        window_height = max(600, min(800, int(screen_height * 0.6)))
        
        # 居中显示
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.dialog.minsize(800, 600)  # 设置最小尺寸
        
        # 设置样式
        self.setup_styles()
        self.setup_ui()
        
    def setup_styles(self):
        """设置弹出窗口样式"""
        style = ttk.Style()
        
        # 配置对话框特定样式
        style.configure('Dialog.TLabelFrame', relief='solid', borderwidth=1,
                       background='#f8f9fa', foreground='#2c3e50')
        style.configure('DialogButton.TButton', font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('DialogButton.TButton',
                  background=[('active', '#e67e22'), ('!disabled', '#f39c12')],
                  foreground=[('active', 'white'), ('!disabled', 'white')])
        
        self.dialog.configure(bg='#f0f8ff')
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 标题
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="LLM提供商配置", font=("Arial", 12, "bold"))
        title_label.pack(side="left")
        
        # 滚动框架
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 提供商列表
        self.provider_widgets = []
        self.rebuild_providers_ui()
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        add_button = ttk.Button(button_frame, text="添加提供商", command=self.add_provider)
        add_button.pack(side="left", padx=(0, 10))
        
        save_button = ttk.Button(button_frame, text="保存", command=self.save_changes)
        save_button.pack(side="right", padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="取消", command=self.dialog.destroy)
        cancel_button.pack(side="right")
    
    def rebuild_providers_ui(self):
        for widget in self.provider_widgets:
            widget.destroy()
        self.provider_widgets = []
        self.provider_data_vars = []
        
        providers = self.config.get('llm_providers', [])
        if not providers:
            providers = [{'name': 'new_provider', 'provider': 'custom', 'api_key': '', 'api_endpoint': ''}]
        
        for i, provider in enumerate(providers):
            self.create_provider_entry(i, provider)
    
    def create_provider_entry(self, index, provider_data):
        frame = ttk.LabelFrame(self.scrollable_frame, text=f"提供商配置 {index + 1}", padding="10")
        frame.pack(fill="x", pady=5)
        self.provider_widgets.append(frame)

        data_vars = {}
        ttk.Label(frame, text="配置名称:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        name_var = tk.StringVar(value=provider_data.get('name', f'provider-{index}'))
        ttk.Entry(frame, textvariable=name_var, width=30).grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        data_vars['name'] = name_var
        
        ttk.Label(frame, text="提供商类型:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        provider_var = tk.StringVar(value=provider_data.get('provider', 'gemini'))
        ttk.Combobox(frame, textvariable=provider_var, values=['openai', 'gemini', 'custom'], width=27).grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        data_vars['provider'] = provider_var

        ttk.Label(frame, text="API Key:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        key_var = tk.StringVar(value=provider_data.get('api_key', ''))
        ttk.Entry(frame, textvariable=key_var, show="*", width=30).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        data_vars['api_key'] = key_var

        ttk.Label(frame, text="自定义接入点:").grid(row=3, column=0, sticky="w", padx=5, pady=3)
        endpoint_var = tk.StringVar(value=provider_data.get('api_endpoint', ''))
        ttk.Entry(frame, textvariable=endpoint_var, width=30).grid(row=3, column=1, sticky="ew", padx=5, pady=3)
        data_vars['api_endpoint'] = endpoint_var

        # 删除按钮
        remove_button = ttk.Button(frame, text="删除提供商", command=lambda i=index: self.remove_provider(i))
        remove_button.grid(row=0, column=2, rowspan=2, padx=15, pady=5, sticky="n")
        
        frame.columnconfigure(1, weight=1)
        self.provider_data_vars.append(data_vars)
    
    def add_provider(self):
        if 'llm_providers' not in self.config:
            self.config['llm_providers'] = []
        self.config['llm_providers'].append({'name': 'new_provider', 'provider': 'custom', 'api_key': '', 'api_endpoint': ''})
        self.rebuild_providers_ui()
    
    def remove_provider(self, index):
        providers = self.config.get('llm_providers', [])
        if 0 <= index < len(providers):
            del providers[index]
            if not providers:
                providers.append({'name': 'new_provider', 'provider': 'custom', 'api_key': '', 'api_endpoint': ''})
            self.config['llm_providers'] = providers
            self.rebuild_providers_ui()
    
    def save_changes(self):
        # 收集所有数据
        providers = []
        for provider_vars in self.provider_data_vars:
            provider = {}
            for key, var in provider_vars.items():
                provider[key] = var.get().strip()
            
            # 只保存有名称的提供商配置
            if provider.get('name'):
                providers.append(provider)
        
        self.config['llm_providers'] = providers
        self.callback()
        self.dialog.destroy()


class UsersManagerDialog:
    def __init__(self, parent, config, format_type, callback):
        self.parent = parent
        self.config = config
        self.format_type = "user_groups"  # 固定为用户组格式
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("👥 用户组和关键词管理")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 响应式窗口大小设置
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # 计算窗口大小（屏幕的55%，但不小于750x650，不大于1100x900）
        window_width = max(750, min(1100, int(screen_width * 0.55)))
        window_height = max(650, min(900, int(screen_height * 0.7)))
        
        # 居中显示
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.dialog.minsize(900, 650)  # 设置最小尺寸
        
        # 设置样式
        self.setup_styles()
        self.setup_ui()
        
    def setup_styles(self):
        """设置弹出窗口样式"""
        style = ttk.Style()
        
        # 配置对话框特定样式
        style.configure('Dialog.TLabelFrame', relief='solid', borderwidth=1,
                       background='#f8f9fa', foreground='#2c3e50')
        style.configure('DialogButton.TButton', font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('DialogButton.TButton',
                  background=[('active', '#8e44ad'), ('!disabled', '#9b59b6')],
                  foreground=[('active', 'white'), ('!disabled', 'white')])
        
        self.dialog.configure(bg='#f0f8ff')
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 标题
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="用户组和关键词配置", font=("Arial", 12, "bold"))
        title_label.pack(side="left")
        
        # 滚动框架
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 用户/用户组列表
        self.user_widgets = []
        self.rebuild_users_ui()
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        add_button = ttk.Button(button_frame, text="添加用户组", command=self.add_user_group)
        add_button.pack(side="left", padx=(0, 10))
        
        save_button = ttk.Button(button_frame, text="保存", command=self.save_changes)
        save_button.pack(side="right", padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="取消", command=self.dialog.destroy)
        cancel_button.pack(side="right")
    
    # 移除format_change方法，因为只支持用户组格式
    
    def rebuild_users_ui(self):
        for widget in self.user_widgets:
            widget.destroy()
        self.user_widgets = []
        self.user_data_vars = []
        
        for i, group in enumerate(self.config.get('user_groups', [])):
            self.create_user_group_entry(i, group)
    
    def create_user_group_entry(self, index, group_data):
        frame = ttk.LabelFrame(self.scrollable_frame, text=f"用户组 {index + 1}", padding="10")
        frame.pack(fill="x", pady=5)
        self.user_widgets.append(frame)
        
        data_vars = {}
        
        # 组名
        ttk.Label(frame, text="组名:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        group_name_var = tk.StringVar(value=group_data.get('group_name', ''))
        ttk.Entry(frame, textvariable=group_name_var, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        data_vars['group_name'] = group_name_var
        
        # 邮箱列表
        ttk.Label(frame, text="邮箱 (空格分隔):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        emails_var = tk.StringVar(value=" ".join(group_data.get('emails', [])))
        ttk.Entry(frame, textvariable=emails_var, width=50).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        data_vars['emails'] = emails_var
        
        # 关键词列表
        ttk.Label(frame, text="关键词 (空格分隔):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        keywords_var = tk.StringVar(value=" ".join(group_data.get('keywords', [])))
        ttk.Entry(frame, textvariable=keywords_var, width=50).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        data_vars['keywords'] = keywords_var
        
        # 删除按钮 - 放在右侧，更加显眼
        remove_button = ttk.Button(frame, text="删除组", command=lambda i=index: self.remove_user_group(i))
        remove_button.grid(row=0, column=2, rowspan=3, padx=15, pady=5, sticky="n")
        
        frame.columnconfigure(1, weight=1)
        self.user_data_vars.append(data_vars)
    
    # 移除create_user_entry方法，因为只支持用户组格式
    
    def add_user_group(self):
        if 'user_groups' not in self.config:
            self.config['user_groups'] = []
        self.config['user_groups'].append({'group_name': '', 'emails': [], 'keywords': []})
        self.rebuild_users_ui()
    
    def remove_user_group(self, index):
        if 0 <= index < len(self.config.get('user_groups', [])):
            del self.config['user_groups'][index]
        self.rebuild_users_ui()
    
    def save_changes(self):
        updated_user_groups = []
        for group_vars in self.user_data_vars:
            emails_text = group_vars['emails'].get().strip()
            emails = [e.strip() for e in emails_text.split() if e.strip()]
            
            keywords_text = group_vars['keywords'].get().strip()
            keywords = [k.strip() for k in keywords_text.split() if k.strip()]
            
            updated_user_groups.append({
                'group_name': group_vars['group_name'].get(),
                'emails': emails,
                'keywords': keywords
            })
        self.config['user_groups'] = updated_user_groups
        
        # 确保删除旧的users配置（如果存在）
        if 'users' in self.config:
            del self.config['users']
        
        self.callback()
        self.dialog.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigEditor(root)
    root.mainloop()