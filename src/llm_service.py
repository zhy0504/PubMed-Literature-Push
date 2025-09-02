import os
from typing import Dict, Any, Literal
import openai
import google.generativeai as genai
import httpx
import json
import logging

# 设置详细的日志记录
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LLMService:
    """
    一个统一的服务类，用于与不同的大语言模型（LLM）提供商进行交互。
    支持 OpenAI, Gemini, 以及自定义的兼容 OpenAI API 的端点。
    
    重要说明:
    - OpenAI: 支持官方API和自定义端点（通过base_url参数）
    - Gemini: 仅支持官方Google API，不支持自定义端点（Google官方库限制）
    - 自定义端点: 必须兼容OpenAI API格式，包括Gemini兼容的代理服务
    
    根据 Google 官方文档，google-generativeai 库不支持自定义端点。
    如果需要连接自定义的Gemini端点，必须使用支持OpenAI兼容格式的代理服务。
    """

    def __init__(self, provider_config: Dict[str, Any], model_name: str):
        """
        初始化 LLMService。

        Args:
            provider_config (Dict[str, Any]): 来自 config['llm_providers'] 列表的单个提供商配置。
            model_name (str): 要使用的具体模型名称。
        """
        logger.debug(f"初始化 LLMService，provider_config: {provider_config}")
        logger.debug(f"模型名称: {model_name}")
        
        self.provider = provider_config.get('provider')
        self.model_name = model_name
        self.api_key = provider_config.get('api_key')
        self.api_endpoint = provider_config.get('api_endpoint')

        logger.debug(f"提供商: {self.provider}")
        logger.debug(f"模型名称: {self.model_name}")
        logger.debug(f"API 密钥: {'***' if self.api_key else 'None'}")
        logger.debug(f"API 端点: {self.api_endpoint}")

        if not self.provider or not self.model_name:
            raise ValueError(f"提供商 '{provider_config.get('name')}' 的配置不完整。")

        if self.provider == 'openai':
            logger.debug("初始化 OpenAI 官方客户端")
            self.client = openai.OpenAI(api_key=self.api_key)
        elif self.provider == 'gemini':
            logger.debug("初始化 Gemini 官方客户端")
            logger.debug("注意: Google官方库不支持自定义端点，将使用官方API")
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
        elif self.provider == 'custom':
            if not self.api_endpoint:
                raise ValueError(f"自定义提供商 '{provider_config.get('name')}' 需要 'api_endpoint' 配置。")
            
            # 检查是否为Gemini兼容的自定义端点
            if 'gemini' in self.model_name.lower():
                logger.debug("检测到Gemini模型，但Google官方库不支持自定义端点")
                logger.debug("将使用OpenAI兼容格式尝试连接，但可能存在兼容性问题")
                self.is_gemini_compatible = True
            else:
                self.is_gemini_compatible = False
            
            # 所有自定义端点都使用 OpenAI 兼容格式
            logger.debug(f"初始化自定义端点客户端，URL: {self.api_endpoint}")
            logger.debug("使用 OpenAI 兼容格式连接自定义端点")
            self.client = openai.OpenAI(
                base_url=self.api_endpoint,
                api_key=self.api_key or "not-needed"
            )
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    @staticmethod
    def configure_proxy(proxy_url: str = None):
        """
        配置HTTP代理设置。
        
        Args:
            proxy_url (str, optional): 代理服务器URL，格式为 http://[user:password@]host:port
                                     如果为None，则清除现有的代理设置。
        
        Note:
            - 这会影响所有使用底层HTTP客户端的库（包括OpenAI和Google库）
            - 对于Google Gemini，这是访问官方API的唯一代理方式
            - 对于OpenAI，也可以使用客户端级别的代理配置
        """
        if proxy_url:
            logger.debug(f"设置HTTP代理: {proxy_url}")
            os.environ['HTTPS_PROXY'] = proxy_url
            os.environ['HTTP_PROXY'] = proxy_url
        else:
            logger.debug("清除HTTP代理设置")
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('HTTP_PROXY', None)

    def generate(self, prompt: str, max_retries: int = 3, stream: bool = False) -> str:
        """
        使用配置的 LLM 生成内容。

        Args:
            prompt (str): 发送给 LLM 的提示。
            max_retries (int): 失败时的最大重试次数。
            stream (bool): 是否使用流式输出。

        Returns:
            str: 从 LLM 返回的完整生成文本。
        """
        logger.debug(f"开始生成内容，提供商: {self.provider}, 模型: {self.model_name}")
        logger.debug(f"提示内容长度: {len(prompt)} 字符")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"尝试 {attempt + 1}/{max_retries}")
                
                if self.provider == 'gemini':
                    logger.debug("使用 Gemini 官方 API")
                    response = self.client.generate_content(prompt, stream=stream)
                    if stream:
                        full_response = ""
                        for chunk in response:
                            # print(chunk.text, end="", flush=True) # Removed to prevent console output
                            full_response += chunk.text
                        # print() # Removed to prevent console output
                        return full_response
                    else:
                        return response.text
                else: # OpenAI 和所有自定义端点
                    logger.debug(f"使用 OpenAI 兼容 API，提供商: {self.provider}")
                    if self.provider == 'custom':
                        logger.debug(f"自定义端点: {self.api_endpoint}")
                        if getattr(self, 'is_gemini_compatible', False):
                            logger.debug("尝试连接Gemini兼容的自定义端点")
                            logger.debug("注意: 由于Google官方库限制，使用OpenAI兼容格式")
                    logger.debug(f"请求参数 - 模型: {self.model_name}, 流式: {stream}")
                    
                    response = self.client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=self.model_name,
                        stream=stream
                    )
                    if stream:
                        full_response = ""
                        for chunk in response:
                            content = chunk.choices[0].delta.content or ""
                            # print(content, end="", flush=True) # Removed to prevent console output
                            full_response += content
                        # print() # Removed to prevent console output
                        return full_response
                    else:
                        return response.choices[0].message.content
            except Exception as e:
                logger.error(f"LLM 生成失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                logger.error(f"异常类型: {type(e).__name__}")
                logger.error(f"异常详情:", exc_info=True)
                
                # 针对不同提供商的特定错误处理
                if self.provider == 'gemini':
                    logger.error("Gemini API 错误 - 检查API密钥和网络连接")
                    logger.error("注意: Gemini API 不支持自定义端点")
                elif self.provider == 'openai':
                    logger.error("OpenAI API 错误 - 检查API密钥和模型名称")
                elif self.provider == 'custom':
                    logger.error(f"自定义端点错误 - 检查端点URL: {self.api_endpoint}")
                    logger.error("确保自定义端点支持OpenAI兼容格式")
                    if getattr(self, 'is_gemini_compatible', False):
                        logger.error("Gemini兼容端点可能需要特定的配置或代理服务")
                
                if attempt + 1 == max_retries:
                    logger.error("LLM 生成达到最大重试次数，放弃。")
                    raise
        return ""

if __name__ == '__main__':
    # 测试代码
    # 需要在项目根目录创建一个临时的 test_config.yaml 来运行此测试
    
    # 示例: 创建 test_config.yaml
    # api_keys:
    #   openai: "..."
    #   gemini: "..."
    # llm_providers:
    #   query_generator:
    #     provider: "gemini"
    #     model_name: "gemini-1.5-flash"
    #   summarizer:
    #     provider: "openai"
    #     model_name: "gpt-3.5-turbo"
    #   custom_provider:
    #     provider: "custom"
    #     model_name: "gemini-pro"
    #     api_endpoint: "https://your-proxy.com/v1"

    from config import load_config
    try:
        # 假设从根目录运行
        config = load_config('config.yaml')
        
        print("--- 测试代理配置 ---")
        # 示例：配置代理（如果需要）
        # LLMService.configure_proxy("http://your-proxy.com:8080")
        
        print("--- 测试 Gemini 查询生成器 ---")
        gemini_service = LLMService(config['llm_providers']['query_generator'], config['api_keys'])
        gemini_prompt = "为 PubMed 创建一个关于 'cancer immunotherapy' 的高级搜索查询"
        print(f"提示: {gemini_prompt}")
        print("注意: Gemini 仅支持官方API，不支持自定义端点")
        # gemini_response = gemini_service.generate(gemini_prompt)
        # print(f"响应: {gemini_response}")

        print("\n--- 测试 OpenAI 总结器 ---")
        openai_service = LLMService(config['llm_providers']['summarizer'], config['api_keys'])
        openai_prompt = "总结以下文本: [这里是文章摘要]"
        print(f"服务已为模型 '{openai_service.model_name}' 正确配置。")
        print("注意: OpenAI 支持自定义端点")
        # openai_response = openai_service.generate(openai_prompt)
        # print(f"响应: {openai_response}")
        
        print("\n--- 测试自定义端点（如果配置了） ---")
        if 'custom_provider' in config.get('llm_providers', {}):
            custom_service = LLMService(config['llm_providers']['custom_provider'], config['api_keys'])
            print(f"自定义端点服务已配置: {custom_service.api_endpoint}")
            print("注意: 自定义端点必须支持OpenAI兼容格式")
            if getattr(custom_service, 'is_gemini_compatible', False):
                print("检测到Gemini兼容的自定义端点")
                print("警告: 由于Google官方库限制，使用OpenAI兼容格式连接")

    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"测试失败: {e}")
        print("请确保您的 config.yaml 文件已正确配置 API 密钥和提供商。")