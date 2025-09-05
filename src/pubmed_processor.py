from Bio import Entrez
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.llm_service import LLMService

class PubMedProcessor:
    """
    处理与 PubMed 相关的所有操作，包括生成查询、搜索文章和总结摘要。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 PubMedProcessor。

        Args:
            config (Dict[str, Any]): 从 config.yaml 加载的完整配置字典。
        """
        self.config = config
        
        # 获取邮箱地址用于PubMed API（兼容新旧配置格式）
        smtp_config = config.get('smtp', {})
        email_for_entrez = None
        
        # 优先从新格式（accounts数组）获取第一个邮箱
        accounts = smtp_config.get('accounts', [])
        if accounts and len(accounts) > 0:
            email_for_entrez = accounts[0].get('username')
        
        # 如果新格式没有，尝试从旧格式获取
        if not email_for_entrez:
            email_for_entrez = smtp_config.get('username')
        
        # 如果还是没有，使用管理员邮箱作为fallback
        if not email_for_entrez:
            email_for_entrez = smtp_config.get('admin_email')
        
        # 确保有邮箱地址
        if not email_for_entrez:
            raise ValueError("配置中未找到有效的邮箱地址。PubMed API需要邮箱地址。")
        
        Entrez.email = email_for_entrez  # PubMed 要求提供邮箱

        providers_map = {p['name']: p for p in config.get('llm_providers', [])}
        task_mapping = config.get('task_model_mapping', {})

        def get_service(task_name):
            task_map = task_mapping.get(task_name, {})
            provider_name = task_map.get('provider_name')
            model_name = task_map.get('model_name')
            if not provider_name or not model_name:
                raise ValueError(f"任务 '{task_name}' 的模型映射不完整。")
            provider_config = providers_map.get(provider_name)
            if not provider_config:
                raise ValueError(f"在 'llm_providers' 中找不到名为 '{provider_name}' 的配置。")
            return LLMService(provider_config, model_name)

        self.query_generator = get_service('query_generator')
        self.summarizer = get_service('summarizer')
        self.abstract_translator = get_service('abstract_translator')

    def _generate_search_term(self, keyword: str, date_query: str) -> str:
        """使用 LLM 将用户友好的关键词转换为高级 PubMed 搜索词。"""
        prompt_template = self.config['prompts']['generate_query']
        prompt = prompt_template.format(keyword=keyword, date_query=date_query)
        logging.info("正在生成搜索词 (流式)...")
        search_term = self.query_generator.generate(prompt, stream=True)
        logging.info(f"LLM 生成的原始搜索词: '{search_term}'")
        return search_term.strip()


    def search_articles(self, keyword: str, days: int = 3) -> List[Dict[str, Any]]:
        """
        为一个关键词搜索过去指定天数内的文章。
        """
        # 精确搜索 UTC 时间的前三天的当天
        target_date_utc = datetime.utcnow() - timedelta(days=days)
        target_date_str = target_date_utc.strftime("%Y/%m/%d")
        
        date_query = f'("{target_date_str}"[Date - Publication])'
        
        logging.info(f"正在为关键词 '{keyword}' 生成搜索词...")
        search_term = self._generate_search_term(keyword, date_query)
        
        logging.info(f"使用最终搜索词进行搜索: {search_term}")

        try:
            max_articles = self.config.get('pubmed', {}).get('max_articles', 20)
            handle = Entrez.esearch(db="pubmed", term=search_term, retmax=str(max_articles))
            record = Entrez.read(handle)
            handle.close()
            id_list = record["IdList"]

            if not id_list:
                logging.info(f"关键词 '{keyword}' 没有找到新文章。")
                return []

            logging.info(f"找到 {len(id_list)} 篇文章。正在获取摘要...")
            handle = Entrez.efetch(db="pubmed", id=id_list, rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            articles = []
            for paper in records['PubmedArticle']:
                article_details = paper['MedlineCitation']['Article']
                pmid = paper['MedlineCitation']['PMID']
                title = article_details.get('ArticleTitle', '无标题')
                
                abstract_parts = article_details.get('Abstract', {}).get('AbstractText', [])
                abstract = ' '.join(abstract_parts) if abstract_parts else "无摘要"
                
                author_list = article_details.get('AuthorList', [])
                authors = ", ".join([author.get('LastName', '') + " " + author.get('Initials', '') for author in author_list])
                journal_info = article_details.get('Journal', {})
                journal_title = journal_info.get('ISOAbbreviation', journal_info.get('Title', '未知期刊'))
                pub_date = article_details.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
                year = pub_date.get('Year', datetime.now().year)
                
                # 尝试从多个位置解析 ISSN 和 EISSN
                issn = ''
                eissn = ''

                # 1. 优先从 MedlineJournalInfo 获取 EISSN (通常最准)
                medline_journal_info = paper['MedlineCitation'].get('MedlineJournalInfo', {})
                if medline_journal_info.get('ISSNLinking'):
                    eissn = medline_journal_info['ISSNLinking']

                # 2. 处理 Journal -> ISSN 标签，可能是单个或列表
                issn_tags = journal_info.get('ISSN', [])
                if not isinstance(issn_tags, list):
                    issn_tags = [issn_tags] # 统一为列表处理

                for tag in issn_tags:
                    if not tag: continue
                    tag_type = tag.attributes.get('IssnType') if hasattr(tag, 'attributes') else None
                    tag_value = str(tag)

                    if tag_type == 'Electronic':
                        if not eissn: eissn = tag_value # 如果之前没找到，则使用这个
                    elif tag_type == 'Print':
                        issn = tag_value
                
                # 3. 如果 'Print' 类型未明确指定，将找到的第一个非 Electronic 的 ISSN 作为 print ISSN
                if not issn:
                    for tag in issn_tags:
                        if not tag: continue
                        tag_type = tag.attributes.get('IssnType') if hasattr(tag, 'attributes') else None
                        if tag_type != 'Electronic':
                             issn = str(tag)
                             break # 找到第一个就停止
                
                # 清理，以防万一
                issn = issn.strip()
                eissn = eissn.strip()
                
                logging.info(f"PMID {pmid}: 解析得到 ISSN='{issn}', EISSN='{eissn}'")

                article_data = {
                    "title": title, "abstract": abstract, "pmid": pmid,
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "authors": authors, "journal": journal_title, "year": year,
                    "issn": issn, "eissn": eissn,
                }
                
                # 如果没有摘要，直接标记，避免进入翻译流程
                if abstract == "无摘要":
                    article_data['translated_abstract'] = '未检索到英文摘要'
                
                articles.append(article_data)
            return articles
        except Exception:
            logging.error("PubMed 搜索出错:", exc_info=True)
            return []

    def generate_review(self, articles: List[Dict[str, Any]], keyword: str) -> tuple[str, List[int]]:
        if not articles:
            return "没有可供综述的文章。", []

        logging.info(f"准备为 {len(articles)} 篇文章生成综述")
        articles_text = ""
        for i, article in enumerate(articles):
            articles_text += f"文献 [{i+1}]:\n"
            articles_text += f"标题: {article['title']}\n"
            articles_text += f"作者: {article['authors']}\n"
            articles_text += f"期刊: {article['journal']}\n"
            articles_text += f"年份: {article['year']}\n"
            articles_text += f"PMID: [{article['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/)\n"
            articles_text += f"摘要: {article['abstract']}\n\n"
            logging.debug(f"文献 [{i+1}]: PMID {article['pmid']} - {article['title']}")

        prompt_template = self.config['prompts']['generate_review']
        prompt = prompt_template.format(keyword=keyword, articles_text=articles_text)
        
        logging.info("正在生成综述 (流式)...")
        review = self.summarizer.generate(prompt, stream=True)
        
        # 分析综述中的引用情况（支持[1]和[1,2,3]格式）
        import re
        # 先找到所有引用标记，然后解析其中的数字
        citation_matches = re.findall(r'\[(\d+(?:\s*,\s*\d+)*)\]', review)
        citations_in_review = []
        for match in citation_matches:
            # 分割每个引用标记中的数字
            numbers = [int(n.strip()) for n in match.split(',')]
            citations_in_review.extend(numbers)
        logging.info(f"LLM生成的综述中包含的引用: {citations_in_review}")
        
        # 检查是否有文章未被引用
        unreferenced = []
        for i in range(1, len(articles) + 1):
            if i not in citations_in_review:
                unreferenced.append(i)
        
        if unreferenced:
            logging.warning(f"LLM综述中未引用以下文章编号: {unreferenced}")
            for idx in unreferenced:
                if idx <= len(articles):
                    logging.warning(f"未引用文章 [{idx}]: PMID {articles[idx-1].get('pmid', 'N/A')} - {articles[idx-1].get('title', 'N/A')[:50]}...")
        
        return review, citations_in_review

    def translate_abstracts_in_batch(self, articles: List[Dict[str, Any]]):
        translation_config = self.config.get('translation_settings', {})
        batch_size = translation_config.get('batch_size', 5)
        delay = translation_config.get('delay_between_batches_sec', 5)
        
        articles_to_translate = [a for a in articles if not a.get('translated_abstract')] # 只翻译尚未处理的
        
        # 为所有待翻译文章设置默认失败提示，以防翻译过程意外中断
        for article in articles_to_translate:
            article['translated_abstract'] = '翻译服务调用失败'

        for i in range(0, len(articles_to_translate), batch_size):
            batch = articles_to_translate[i:i + batch_size]
            logging.info(f"正在翻译第 {i+1} 到 {i+len(batch)} 篇摘要 (流式)...")
            
            separator = "\n|||---|||\n"
            abstracts_batch_str = separator.join([article['abstract'] for article in batch])
            prompt_template = self.config['prompts']['translate_abstract']
            prompt = prompt_template.format(abstracts_batch=abstracts_batch_str)
            
            try:
                translated_results_str = self.abstract_translator.generate(prompt, stream=True)
                # logging.info(f"LLM 返回的原始翻译结果: '{translated_results_str}'") # Removed for cleaner logs
                translated_batch = translated_results_str.split(separator.strip())
                
                if len(translated_batch) == len(batch):
                    for j, article in enumerate(batch):
                        article['translated_abstract'] = translated_batch[j].strip()
                else:
                    logging.warning(f"翻译批次返回结果数量 ({len(translated_batch)}) 与预期 ({len(batch)}) 不符。")
                    for article in batch:
                        article['translated_abstract'] = "翻译失败或格式错误"
            except Exception:
                logging.error("批量翻译时出错:", exc_info=True)
                for article in batch:
                    article['translated_abstract'] = "翻译时发生错误"

            if i + batch_size < len(articles_to_translate):
                logging.info(f"等待 {delay} 秒后进行下一批翻译...")
                time.sleep(delay)

if __name__ == '__main__':
    pass