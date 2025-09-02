import smtplib
import ssl
import logging
import time
import markdown
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

class EmailSender:
    """
    负责渲染邮件模板并通过 SMTP 发送邮件，支持多个发件邮箱轮替发送。
    """

    def __init__(self, smtp_config: Dict[str, Any]):
        """
        初始化 EmailSender。
        """
        self.config = smtp_config
        self.env = Environment(loader=FileSystemLoader('templates'))
        
        # 处理多账号配置
        self.accounts = smtp_config.get('accounts', [])
        if not self.accounts:
            # 兼容旧配置格式
            if all(key in smtp_config for key in ['server', 'username', 'password']):
                self.accounts = [{
                    'server': smtp_config['server'],
                    'port': smtp_config.get('port', 587),
                    'username': smtp_config['username'],
                    'password': smtp_config['password'],
                    'sender_name': smtp_config.get('sender_name', 'PubMed Literature Push')
                }]
        
        self.current_account_index = 0  # 用于轮替的索引
        logging.info(f"邮件发送器初始化完成，共 {len(self.accounts)} 个发件账号")
    
    def get_next_account(self) -> Dict[str, Any]:
        """
        获取下一个要使用的发件账号（轮替）。
        """
        if not self.accounts:
            raise ValueError("没有可用的发件账号配置")
        
        account = self.accounts[self.current_account_index]
        self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
        return account

    def send_email(self, recipient_email: str, subject: str, html_content: str, account_index: int = None):
        """
        通过 SMTP 发送邮件，支持指定账号或自动轮替。
        """
        if account_index is not None and 0 <= account_index < len(self.accounts):
            account = self.accounts[account_index]
        else:
            account = self.get_next_account()
        
        message = MIMEMultipart()
        sender_name = account.get('sender_name', 'PubMed Literature Push')
        message['From'] = Header(f"{sender_name} <{account['username']}>")
        message['To'] = Header(recipient_email)
        message['Subject'] = Header(subject)
        message.attach(MIMEText(html_content, 'html', 'utf-8'))

        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay_sec', 300)
        
        logging.info(f"使用账号 {account['username']} 发送邮件至 {recipient_email}")
        
        for attempt in range(max_retries):
            server = None
            try:
                port = account.get('port', 587)
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                if port == 465:
                    server = smtplib.SMTP_SSL(account['server'], port, timeout=10, context=context)
                else:
                    server = smtplib.SMTP(account['server'], port, timeout=10)
                    server.starttls(context=context)
                
                server.login(account['username'], account['password'])
                server.sendmail(account['username'], [recipient_email], message.as_string())
                logging.info(f"邮件已成功发送至 {recipient_email}（发件人：{account['username']}）")
                return

            except smtplib.SMTPConnectError as e:
                if e.smtp_code == 451 and attempt < max_retries - 1:
                    logging.warning(f"SMTP服务器临时不可用 (451)，将在 {retry_delay} 秒后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"使用账号 {account['username']} 发送邮件至 {recipient_email} 时遇到连接错误:", exc_info=True)
                    return
            except Exception:
                logging.error(f"使用账号 {account['username']} 发送邮件至 {recipient_email} 时遇到未知错误:", exc_info=True)
                return
            finally:
                if server:
                    try:
                        server.quit()
                    except (smtplib.SMTPServerDisconnected, smtplib.SMTPResponseException):
                        pass
        
        logging.error(f"使用账号 {account['username']} 发送邮件至 {recipient_email} 失败，已达到最大重试次数。")

    def send_report_email(self, recipient_email: str, keyword: str, review_body: str, sorted_articles: list):
        """
        发送包含综述和文献详情表格的邮件。
        """
        template = self.env.get_template('email_template.html')
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        subject = f"PubMed每日文献报告与综述 - {keyword}专题 - {today_str}"
        
        review_html = markdown.markdown(review_body, extensions=['fenced_code', 'tables'])

        html_content = template.render(
            keyword=keyword,
            date=today_str,
            review_html=review_html,
            articles=sorted_articles
        )
        
        self.send_email(recipient_email, subject, html_content)

if __name__ == '__main__':
    pass