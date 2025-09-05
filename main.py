import time
import re
import logging
from datetime import datetime, date
from logging.handlers import TimedRotatingFileHandler
import schedule
import os
import sys
import signal
import argparse
from typing import Tuple
from collections import defaultdict
import json

# 确保工作目录为脚本所在目录
if getattr(sys, 'frozen', False):
    # 如果是打包的可执行文件
    application_path = os.path.dirname(sys.executable)
else:
    # 如果是脚本运行
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)
sys.path.insert(0, application_path)

# 平台特定的进程终止处理
if sys.platform == 'win32':
    try:
        import win32api
        import win32con
        import win32gui
        WINDOWS_API_AVAILABLE = True
    except ImportError:
        WINDOWS_API_AVAILABLE = False
        print("Warning: pywin32 not available, some Windows features may not work")
    
    import threading
    import atexit
elif sys.platform == 'darwin':  # macOS
    try:
        import Foundation
        import objc
        MACOS_API_AVAILABLE = True
    except ImportError:
        MACOS_API_AVAILABLE = False
        print("Warning: macOS Foundation APIs not available, some macOS features may not work")
elif sys.platform.startswith('linux'):  # Linux
    try:
        import dbus
        LINUX_DBUS_AVAILABLE = True
    except ImportError:
        LINUX_DBUS_AVAILABLE = False
        print("Warning: dbus not available, some Linux features may not work")

from src.config import load_config
from src.pubmed_processor import PubMedProcessor
from src.email_sender import EmailSender
from src.data_processor import DataProcessor

# 跨平台进程终止处理基类
class CrossPlatformProcessHandler:
    def __init__(self):
        self.should_exit = False
        self.setup_handlers()
    
    def setup_handlers(self):
        """设置平台特定的进程终止处理器"""
        # 设置通用信号处理器
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # 注册退出处理器
        atexit.register(self.cleanup)
        
        # 设置平台特定的处理器
        if sys.platform == 'win32':
            self.setup_windows_handlers()
        elif sys.platform == 'darwin':
            self.setup_macos_handlers()
        elif sys.platform.startswith('linux'):
            self.setup_linux_handlers()
    
    def setup_windows_handlers(self):
        """设置Windows特定的进程终止处理器"""
        if sys.stdout is None or sys.stdout.isatty():  # 只在有控制台时设置
            try:
                if WINDOWS_API_AVAILABLE:
                    win32api.SetConsoleCtrlHandler(self.console_handler, True)
            except:
                pass  # 如果win32console不可用，忽略错误
    
    def setup_macos_handlers(self):
        """设置macOS特定的进程终止处理器"""
        try:
            if MACOS_API_AVAILABLE:
                # macOS可以通过NSWorkspace接收应用程序终止通知
                # 这里我们主要依赖信号处理
                pass
        except:
            pass
    
    def setup_linux_handlers(self):
        """设置Linux特定的进程终止处理器"""
        try:
            if LINUX_DBUS_AVAILABLE:
                # Linux可以通过DBus接收系统关闭通知
                # 这里我们主要依赖信号处理
                pass
        except:
            pass
    
    def console_handler(self, ctrl_type):
        """Windows控制台处理器"""
        if ctrl_type == win32con.CTRL_C_EVENT or ctrl_type == win32con.CTRL_BREAK_EVENT:
            logging.info("接收到终止信号，正在退出...")
            self.should_exit = True
            return 1  # 表示已处理
        return 0
    
    def signal_handler(self, signum, frame):
        """通用信号处理器"""
        logging.info(f"接收到信号 {signum}，正在退出...")
        self.should_exit = True
    
    def cleanup(self):
        """清理资源"""
        logging.info("执行清理操作...")
        self.should_exit = True
    
    def should_exit_now(self):
        """检查是否应该退出"""
        return self.should_exit

# 保持向后兼容的别名
WindowsProcessHandler = CrossPlatformProcessHandler

# 全局进程处理器
process_handler = None

def setup_logging():
    """配置全局日志记录器，带日志轮替功能。"""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # 设置文件处理器，每天轮替，保留30天
    file_handler = TimedRotatingFileHandler(
        "pubmed_push.log",
        when="D",
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    
    # 设置控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    
    # 获取根日志记录器并添加处理器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

def get_daily_run_marker_path():
    """获取每日运行标记文件路径"""
    return os.path.join(application_path, '.daily_run_marker.json')

def has_run_today():
    """检查今天是否已经运行过任务"""
    marker_path = get_daily_run_marker_path()
    if not os.path.exists(marker_path):
        return False
    
    try:
        with open(marker_path, 'r', encoding='utf-8') as f:
            marker_data = json.load(f)
        
        last_run_date = datetime.strptime(marker_data['last_run_date'], '%Y-%m-%d').date()
        today = date.today()
        
        return last_run_date == today
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        # 如果标记文件损坏，返回False并将在下次运行时重新创建
        return False

def mark_today_as_run():
    """标记今天已经运行过任务"""
    marker_path = get_daily_run_marker_path()
    marker_data = {
        'last_run_date': date.today().isoformat(),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(marker_path, 'w', encoding='utf-8') as f:
            json.dump(marker_data, f, ensure_ascii=False, indent=2)
        logging.info(f"已标记今日任务已执行: {marker_data['last_run_date']}")
    except OSError as e:
        logging.error(f"无法创建每日运行标记文件: {e}")

def clear_daily_run_marker():
    """清除每日运行标记，允许重新运行今日任务"""
    marker_path = get_daily_run_marker_path()
    
    if os.path.exists(marker_path):
        try:
            os.remove(marker_path)
            logging.info("已清除每日运行标记，今日任务可以重新执行。")
        except OSError as e:
            logging.error(f"无法清除每日运行标记文件: {e}")
    else:
        logging.info("没有找到每日运行标记文件。")

def run_job():
    """
    执行一次完整的任务：搜索、增强、翻译、生成报告并发送邮件。
    """
    # 检查今天是否已经运行过
    if has_run_today():
        logging.info("今日任务已经执行过，跳过本次执行。")
        return
    
    logging.info("开始执行每日任务...")
    start_time = datetime.now()
    job_stats = []
    error_occurred = False
    config = None

    try:
        config = load_config()
        pubmed_processor = PubMedProcessor(config)
        data_processor = DataProcessor()
        sender = EmailSender(config['smtp'])

        scheduler_config = config.get('scheduler', {})
        delay_keywords = scheduler_config.get('delay_between_keywords_sec', 60)
        delay_emails = scheduler_config.get('delay_between_emails_sec', 10)
        
        # 记录发件账号信息
        smtp_accounts = config['smtp'].get('accounts', [])
        if len(smtp_accounts) > 1:
            logging.info(f"启用多发件邮箱模式，共 {len(smtp_accounts)} 个账号，邮件发送间隔：{delay_emails} 秒")
        else:
            logging.info(f"使用单发件邮箱模式，邮件发送间隔：{delay_emails} 秒")

        # 使用新的配置处理逻辑
        keyword_to_emails = config.get('keyword_to_emails', {})
        
        if not keyword_to_emails:
            logging.warning("没有找到任何关键词配置，跳过任务执行。")
            return

        for i, (keyword, emails) in enumerate(keyword_to_emails.items()):
            logging.info(f"--- 正在处理关键词: '{keyword}' ---")
            
            articles = pubmed_processor.search_articles(keyword)
            if not articles:
                logging.info(f"关键词 '{keyword}' 没有新文章，跳过。")
                job_stats.append(f"- 关键词 '{keyword}': 未找到新文章。")
                continue

            job_stats.append(f"- 关键词 '{keyword}': 找到 {len(articles)} 篇文章，发送给 {len(emails)} 位用户。")

            for article in articles:
                article['zky_data'] = data_processor.get_zky_data(article['issn'], article['eissn'])
                article['jcr_data'] = data_processor.get_jcr_data(article['issn'], article['eissn'])
            
            logging.info(f"为 '{keyword}' 的 {len(articles)} 篇文章生成综述...")
            logging.info(f"文章列表: {[article.get('pmid', 'N/A') for article in articles]}")
            raw_review_content, cited_indices = pubmed_processor.generate_review(articles, keyword)
            
            # 只翻译被纳入综述的文章摘要（先去重）
            if cited_indices:
                # 获取去重后的引用索引
                unique_cited_indices = []
                seen_indices = set()
                for idx in cited_indices:
                    if idx not in seen_indices and idx <= len(articles):
                        unique_cited_indices.append(idx)
                        seen_indices.add(idx)
                
                # 获取去重后的文章列表
                cited_articles = [articles[i-1] for i in unique_cited_indices]
                logging.info(f"开始翻译被纳入综述的 {len(cited_articles)} 篇文章摘要（去重前：{len(cited_indices)} 篇）...")
                pubmed_processor.translate_abstracts_in_batch(cited_articles)
                
                # 将翻译结果更新回原文章列表
                cited_article_map = {article['pmid']: article for article in cited_articles}
                for original_article in articles:
                    if original_article['pmid'] in cited_article_map:
                        original_article['translated_abstract'] = cited_article_map[original_article['pmid']]['translated_abstract']
            else:
                logging.warning("综述中没有引用任何文章，跳过翻译步骤。")
            
            # 调试：保存原始综述文本到文件
            debug_dir = os.path.join(application_path, 'debug_output')
            os.makedirs(debug_dir, exist_ok=True)
            
            # 保存原始综述文本
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_review_file = os.path.join(debug_dir, f'{timestamp}_{keyword}_raw_review.txt')
            try:
                with open(raw_review_file, 'w', encoding='utf-8') as f:
                    f.write(f"关键词: {keyword}\n")
                    f.write(f"文章数量: {len(articles)}\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                    f.write("原始文章列表:\n")
                    for i, article in enumerate(articles):
                        f.write(f"[{i+1}] PMID: {article.get('pmid', 'N/A')} - {article.get('title', 'N/A')[:100]}...\n")
                    f.write("\n" + "="*50 + "\n\n")
                    f.write("LLM生成的综述:\n")
                    f.write(raw_review_content)
                logging.info(f"原始综述已保存到: {raw_review_file}")
            except Exception as e:
                logging.error(f"保存原始综述文件失败: {e}")
            
            logging.info("校准引用顺序并移除参考文献列表...")
            logging.debug(f"原始综述内容: {raw_review_content}")
            review_body, sorted_articles = process_review_and_sort_articles(raw_review_content, articles, keyword, timestamp)
            logging.info(f"排序后的文章数量: {len(sorted_articles)}")
            logging.info(f"排序后的文章列表: {[article.get('pmid', 'N/A') for article in sorted_articles]}")

            logging.info(f"准备将 '{keyword}' 的报告发送给: {', '.join(emails)}")
            for j, email in enumerate(emails):
                sender.send_report_email(email, keyword, review_body, sorted_articles)
                if j < len(emails) - 1:
                    logging.info(f"等待 {delay_emails} 秒后发送下一封邮件...")
                    time.sleep(delay_emails)

            if i < len(keyword_to_emails) - 1:
                logging.info(f"关键词 '{keyword}' 处理完毕。等待 {delay_keywords} 秒后处理下一个关键词...")
                time.sleep(delay_keywords)

    except Exception:
        error_occurred = True
        logging.critical("任务执行期间发生严重错误:", exc_info=True)
    
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        
        # 如果任务成功完成，标记今天已运行
        if not error_occurred:
            mark_today_as_run()
        
        if config:
            admin_email = config.get('smtp', {}).get('admin_email')
            if admin_email:
                logging.info(f"向管理员 {admin_email} 发送任务报告...")
                
                status = "失败" if error_occurred else "成功"
                subject = f"PubMed Literature Push 每日任务报告: {status}"
                
                body = (
                    f"任务执行报告\n"
                    f"--------------------------\n"
                    f"状态: {status}\n"
                    f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"总耗时: {duration}\n"
                    f"--------------------------\n\n"
                    f"摘要:\n"
                )
                body += "\n".join(job_stats) if job_stats else "没有处理任何关键词。"
                
                if error_occurred:
                    body += "\n\n错误: 任务因严重错误而中断。请查看 pubmed_push.log 获取详细信息。"
                
                try:
                    # 使用一个新的 sender 实例或确保旧的实例仍然可用
                    sender = EmailSender(config['smtp'])
                    sender.send_email(admin_email, subject, body.replace('\n', '<br>'))
                    logging.info("管理员报告邮件发送成功。")
                except Exception:
                    logging.error("发送管理员报告邮件失败:", exc_info=True)

        logging.info("每日任务执行完毕。")

def process_review_and_sort_articles(review_text: str, original_articles: list, keyword: str = "", timestamp: str = "") -> Tuple[str, list]:
    """
    根据综述正文中的引用顺序，对原始文章列表进行排序，更新正文中的引用编号，并移除参考文献列表。
    """
    try:
        # 调试：创建调试目录
        debug_dir = os.path.join(application_path, 'debug_output')
        os.makedirs(debug_dir, exist_ok=True)
        
        # 1. 分割正文，并丢弃参考文献部分
        body = re.split(r'\n#*\s*参考文献\s*#*', review_text, flags=re.IGNORECASE)[0].strip()

        # 2. 提取正文中引用的原始顺序（支持[1]和[1,2,3]格式）
        # 先找到所有引用标记，然后解析其中的数字
        citation_matches = re.findall(r'\[(\d+(?:\s*,\s*\d+)*)\]', body)
        citations_in_order = []
        for match in citation_matches:
            # 分割每个引用标记中的数字
            numbers = [int(n.strip()) for n in match.split(',')]
            citations_in_order.extend(numbers)
        logging.info(f"从综述中提取到的引用顺序: {citations_in_order}")
        
        # 调试：保存引用分析结果
        if keyword and timestamp:
            analysis_file = os.path.join(debug_dir, f'{timestamp}_{keyword}_citation_analysis.txt')
            try:
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(f"关键词: {keyword}\n")
                    f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"原始文章总数: {len(original_articles)}\n")
                    f.write("="*50 + "\n\n")
                    
                    f.write("【步骤1】分割正文后的内容:\n")
                    f.write(body[:1000] + "...\n\n")
                    
                    f.write("【步骤2】提取到的所有引用（按出现顺序）:\n")
                    f.write(str(citations_in_order) + "\n")
                    f.write(f"引用总数: {len(citations_in_order)}\n\n")
            except Exception as e:
                logging.error(f"保存引用分析文件失败: {e}")
        
        if not citations_in_order:
            # 如果没有引用，按原样返回正文，并为文章添加默认序号
            logging.warning("综述中没有找到任何引用，返回所有文章")
            for i, article in enumerate(original_articles):
                article['citation_index'] = i + 1
            return body, original_articles

        # 3. 确定唯一的、按出现顺序的旧引用号
        unique_ordered_old_refs = []
        for c in citations_in_order:
            if c not in unique_ordered_old_refs:
                unique_ordered_old_refs.append(c)
        logging.info(f"去重后的引用列表: {unique_ordered_old_refs}")
        
        # 调试：保存去重分析
        if keyword and timestamp:
            try:
                with open(analysis_file, 'a', encoding='utf-8') as f:
                    f.write("【步骤3】去重后的引用列表:\n")
                    f.write(str(unique_ordered_old_refs) + "\n")
                    f.write(f"去重后引用数: {len(unique_ordered_old_refs)}\n\n")
            except Exception as e:
                logging.error(f"追加引用分析文件失败: {e}")
        
        # 4. 创建旧引用号到新引用号的映射
        old_to_new_map = {old_idx: new_idx + 1 for new_idx, old_idx in enumerate(unique_ordered_old_refs)}
        logging.info(f"引用映射关系: {old_to_new_map}")

        # 5. 根据正文引用顺序，对我们自己的 `original_articles` 列表进行排序
        sorted_articles = []
        skipped_articles = []
        for old_idx in unique_ordered_old_refs:
            # 原始文章列表是0-indexed，而引用是1-indexed
            if 0 < old_idx <= len(original_articles):
                article = original_articles[old_idx - 1]
                article['citation_index'] = old_to_new_map[old_idx]
                sorted_articles.append(article)
                logging.info(f"包含文章: PMID {article.get('pmid', 'N/A')} (原始引用 [{old_idx}] -> 新引用 [{old_to_new_map[old_idx]}])")
            else:
                logging.warning(f"跳过无效引用: [{old_idx}]，超出文章范围 (1-{len(original_articles)})")
                skipped_articles.append(old_idx)
        
        if skipped_articles:
            logging.warning(f"综述中引用了 {len(skipped_articles)} 个不存在的文章编号: {skipped_articles}")
        
        # 检查是否有文章未被引用
        total_articles = len(original_articles)
        referenced_count = len(sorted_articles)
        unreferenced_count = total_articles - referenced_count
        
        if unreferenced_count > 0:
            unreferenced_articles = []
            referenced_indices = set(unique_ordered_old_refs)
            
            for i, article in enumerate(original_articles):
                article_index = i + 1
                if article_index not in referenced_indices:
                    unreferenced_articles.append({
                        'pmid': article.get('pmid', 'N/A'),
                        'index': article_index
                    })
            
            # 计算引用比例
            reference_rate = (referenced_count / total_articles) * 100
            
            # 根据引用比例调整日志级别
            if reference_rate >= 80:
                level = "INFO"
                message = "综述引用了大部分文章"
            elif reference_rate >= 50:
                level = "INFO"  
                message = "综述选择性引用了相关文章"
            elif reference_rate >= 20:
                level = "WARNING"
                message = "综述引用的文章比例较低"
            else:
                level = "WARNING"
                message = "综述仅引用了少量文章"
            
            logging.info(f"文章引用统计: 总计{total_articles}篇, 被引用{referenced_count}篇({reference_rate:.1f}%), 未引用{unreferenced_count}篇")
            logging.log(
                logging.INFO if level == "INFO" else logging.WARNING,
                f"{message} - 这是LLM综述生成的正常行为，系统会智能选择最相关的文章进行引用"
            )
            
            # 调试：保存详细分析
            if keyword and timestamp:
                try:
                    with open(analysis_file, 'a', encoding='utf-8') as f:
                        f.write("【步骤4】文章引用统计:\n")
                        f.write(f"总文章数: {total_articles}\n")
                        f.write(f"被引用文章数: {referenced_count}\n")
                        f.write(f"未引用文章数: {unreferenced_count}\n")
                        f.write(f"引用率: {reference_rate:.1f}%\n\n")
                        
                        f.write("【步骤5】引用映射关系:\n")
                        for old_idx, new_idx in old_to_new_map.items():
                            article = original_articles[old_idx - 1] if 0 < old_idx <= len(original_articles) else None
                            if article:
                                f.write(f"[{old_idx}] -> [{new_idx}] (PMID: {article.get('pmid', 'N/A')})\n")
                            else:
                                f.write(f"[{old_idx}] -> [{new_idx}] (无效引用)\n")
                        f.write("\n")
                        
                        if skipped_articles:
                            f.write("【步骤6】跳过的无效引用:\n")
                            f.write(f"{skipped_articles}\n\n")
                        
                        if unreferenced_count <= 50:  # 只在未引用文章较少时显示详细信息
                            f.write("【步骤7】未被引用的文章:\n")
                            for item in unreferenced_articles:
                                f.write(f"[{item['index']}] PMID: {item['pmid']}\n")
                        else:
                            f.write(f"【步骤7】未被引用的文章过多({unreferenced_count}篇)，仅显示前20篇:\n")
                            for item in unreferenced_articles[:20]:
                                f.write(f"[{item['index']}] PMID: {item['pmid']}\n")
                            f.write(f"...还有{unreferenced_count - 20}篇未被引用\n")
                except Exception as e:
                    logging.error(f"保存详细分析文件失败: {e}")
            
            # 仅在引用率极低时显示详细信息
            if reference_rate < 20:
                unreferenced_pmids = [item['pmid'] for item in unreferenced_articles[:10]]  # 只显示前10个
                logging.warning(f"未被引用的文章PMID（前10个）: {unreferenced_pmids}")
                if unreferenced_count > 10:
                    logging.warning(f"还有{unreferenced_count - 10}篇文章未被引用...")
        else:
            logging.info(f"所有{total_articles}篇文章都被综述引用")
        
        # 6. 更新正文中的引用标记（支持[1]和[1,2,3]格式）
        def replace_citation(match):
            citation_content = match.group(1)  # 获取引用标记内的内容，如 "1" 或 "1,2,3"
            # 分割引用数字
            old_indices = [int(idx.strip()) for idx in citation_content.split(',')]
            # 为每个引用数字查找新的编号
            new_indices = [str(old_to_new_map.get(old_idx, old_idx)) for old_idx in old_indices]
            # 重新组合引用标记
            return f"[{','.join(new_indices)}]"

        new_body = re.sub(r'\[(\d+(?:\s*,\s*\d+)*)\]', replace_citation, body)

        # 调试：保存最终结果
        if keyword and timestamp:
            processed_file = os.path.join(debug_dir, f'{timestamp}_{keyword}_processed_review.txt')
            try:
                with open(processed_file, 'w', encoding='utf-8') as f:
                    f.write(f"关键词: {keyword}\n")
                    f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                    f.write("处理后的综述正文（引用已重新编号）:\n")
                    f.write(new_body)
                    f.write("\n\n" + "="*50 + "\n\n")
                    f.write("最终排序的文章列表:\n")
                    for i, article in enumerate(sorted_articles):
                        f.write(f"[{i+1}] PMID: {article.get('pmid', 'N/A')} - {article.get('title', 'N/A')[:100]}...\n")
                logging.info(f"处理后的综述已保存到: {processed_file}")
            except Exception as e:
                logging.error(f"保存处理后综述文件失败: {e}")

        return new_body, sorted_articles

    except Exception:
        logging.error("综述后处理时出错:", exc_info=True)
        # 出错时，也尝试只返回正文部分，并添加默认序号
        body = re.split(r'\n#*\s*参考文献\s*#*', review_text, flags=re.IGNORECASE)[0].strip()
        for i, article in enumerate(original_articles):
            article['citation_index'] = i + 1
        return body, original_articles

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='PubMed Literature Push - 每日文献推送系统')
    parser.add_argument('--clear-marker', action='store_true', 
                       help='清除每日运行标记，允许重新运行今日任务')
    parser.add_argument('--force-run', action='store_true',
                       help='强制立即运行任务，忽略标记和时间检查')
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    setup_logging()
    
    # 初始化跨平台进程处理器
    process_handler = CrossPlatformProcessHandler()
    
    # 处理命令行参数
    if args.clear_marker:
        logging.info("收到清除每日运行标记的指令...")
        clear_daily_run_marker()
        sys.exit(0)
    
    logging.info("程序已启动。正在检查执行时间...")
    
    try:
        config = load_config()
        run_time = config.get('scheduler', {}).get('run_time', '08:00')
        logging.info(f"配置的任务执行时间：{run_time}")
        
        # 获取当前时间
        current_time = datetime.now()
        current_time_str = current_time.strftime('%H:%M')
        
        # 解析设定时间
        scheduled_hour, scheduled_minute = map(int, run_time.split(':'))
        scheduled_time = current_time.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0)
        
        logging.info(f"当前时间：{current_time_str}")
        logging.info(f"设定执行时间：{run_time}")
        
        # 处理强制运行选项
        if args.force_run:
            logging.info("收到强制运行指令，立即执行任务...")
            run_job()
            logging.info("强制运行完成。")
        else:
            # 判断是否需要立即执行
            if current_time > scheduled_time:
                # 检查今天是否已经运行过任务
                if has_run_today():
                    logging.info("当前时间已超过今日设定执行时间，但今日任务已执行过，跳过立即执行。")
                else:
                    logging.info("当前时间已超过今日设定执行时间，立即执行一次任务...")
                    run_job()
                    logging.info("立即执行完成。")
            else:
                logging.info("当前时间早于设定执行时间，等待定时执行。")
        
        # 设置定时任务
        logging.info(f"任务计划在每天 {run_time} 执行。")
        schedule.every().day.at(run_time).do(run_job)
        
    except Exception:
        logging.critical("无法设置计划任务，程序将不会自动运行:", exc_info=True)

    # 改进的主循环，支持多种终止方式
    logging.info("进入主循环...")
    
    # 为pythonw.exe环境添加文件监控终止机制
    stop_file_path = os.path.join(os.path.dirname(__file__), '.stop_signal')
    
    try:
        while not process_handler.should_exit_now():
            # 检查终止信号文件
            if os.path.exists(stop_file_path):
                logging.info("检测到终止信号文件，正在退出...")
                try:
                    os.remove(stop_file_path)
                except:
                    pass
                break
            
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logging.info("程序被手动中断。正在退出...")
                break
            except Exception:
                logging.error("主循环发生未知错误:", exc_info=True)
                time.sleep(5)
    finally:
        # 清理终止信号文件
        if os.path.exists(stop_file_path):
            try:
                os.remove(stop_file_path)
            except:
                pass
    
    logging.info("程序正常退出。")