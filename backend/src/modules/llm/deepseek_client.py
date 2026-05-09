"""
DeepSeek V3 API客户端
支持DeepSeek V3 API调用，兼容OpenAI格式
"""

import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
import requests

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek V3 API客户端"""
    
    # DeepSeek V3 API端点
    BASE_URL = "https://api.deepseek.com"
    CHAT_COMPLETION_ENDPOINT = "/chat/completions"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat",
        timeout: int = 30,
        max_retries: int = 3,
        enable_streaming: bool = True
    ):
        """
        初始化DeepSeek客户端
        
        Args:
            api_key: DeepSeek API密钥，如果为None则从环境变量读取
            base_url: API基础URL，默认为官方端点
            model: 模型名称，默认为deepseek-chat
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            enable_streaming: 是否启用流式响应
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_streaming = enable_streaming
        
        self._session = requests.Session()
        self._setup_session()
        
        logger.info(f"DeepSeek客户端初始化完成，模型: {model}")
    
    def _setup_session(self):
        """设置HTTP会话"""
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        if self.api_key:
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发送HTTP请求，支持重试
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            HTTP响应
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                # 等待后重试
                import time
                time.sleep(1 * (attempt + 1))
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        聊天补全
        
        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            stream: 是否流式输出
            **kwargs: 其他OpenAI兼容参数
            
        Returns:
            如果是流式输出，返回生成器；否则返回完整的响应字典
        """
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未设置")
        
        # 构建请求体
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream and self.enable_streaming,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if stream and self.enable_streaming:
            return self._stream_chat_completion(payload)
        else:
            return self._chat_completion_sync(payload)
    
    def _chat_completion_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """同步聊天补全"""
        response = self._make_request(
            method="POST",
            endpoint=self.CHAT_COMPLETION_ENDPOINT,
            json=payload
        )
        
        result = response.json()
        
        # 提取响应内容
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0]["message"]
            content = message.get("content", "") if isinstance(message, dict) else ""
            
            return {
                "content": content,
                "model": result.get("model", self.model),
                "usage": result.get("usage", {}),
                "raw_response": result
            }
        else:
            raise ValueError(f"API响应格式错误: {result}")
    
    def _stream_chat_completion(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        response = self._make_request(
            method="POST",
            endpoint=self.CHAT_COMPLETION_ENDPOINT,
            json=payload,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]  # 移除"data: "前缀
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析流式数据: {data}")
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        
        Returns:
            模型列表
        """
        if not self.api_key:
            return []
        
        try:
            response = self._make_request("GET", "/models")
            result = response.json()
            
            if "data" in result:
                return result["data"]
            else:
                logger.warning(f"获取模型列表响应格式错误: {result}")
                return []
                
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
    
    def get_usage(self) -> Dict[str, Any]:
        """
        获取API使用情况
        
        Returns:
            使用情况统计
        """
        if not self.api_key:
            return {"error": "API密钥未设置"}
        
        try:
            response = self._make_request("GET", "/usage")
            return response.json()
        except Exception as e:
            logger.error(f"获取使用情况失败: {e}")
            return {"error": str(e)}
    
    def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效
        
        Returns:
            是否有效
        """
        if not self.api_key:
            return False
        
        try:
            # 尝试获取模型列表来验证密钥
            models = self.get_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"API密钥验证失败: {e}")
            return False
    
    def set_api_key(self, api_key: str):
        """
        设置API密钥
        
        Args:
            api_key: DeepSeek API密钥
        """
        self.api_key = api_key
        self._setup_session()
        logger.info("API密钥已更新")
    
    def close(self):
        """关闭客户端"""
        self._session.close()
        logger.info("DeepSeek客户端已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 工厂函数，便于使用
def create_deepseek_client(
    api_key: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> DeepSeekClient:
    """
    创建DeepSeek客户端
    
    Args:
        api_key: API密钥
        config: 配置字典
        
    Returns:
        DeepSeekClient实例
    """
    if config is None:
        config = {}
    
    return DeepSeekClient(
        api_key=api_key,
        base_url=config.get("base_url"),
        model=config.get("model", "deepseek-chat"),
        timeout=config.get("timeout", 30),
        max_retries=config.get("max_retries", 3),
        enable_streaming=config.get("enable_streaming", True)
    )