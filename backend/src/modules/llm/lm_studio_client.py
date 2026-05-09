"""
LM Studio客户端
支持本地LM Studio服务器API（OpenAI兼容）
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
import requests

logger = logging.getLogger(__name__)


class LMStudioClient:
    """LM Studio客户端"""
    
    # LM Studio默认地址
    DEFAULT_BASE_URL = "http://localhost:1234"
    CHAT_COMPLETION_ENDPOINT = "/v1/chat/completions"
    MODELS_ENDPOINT = "/v1/models"
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,  # LM Studio可能需要更长时间
        max_retries: int = 3,
        enable_streaming: bool = True
    ):
        """
        初始化LM Studio客户端
        
        Args:
            base_url: LM Studio服务器地址，默认为http://localhost:1234
            model: 模型名称，如果为None则使用服务器上的第一个可用模型
            timeout: 请求超时时间（秒），LM Studio可能需要较长时间加载模型
            max_retries: 最大重试次数
            enable_streaming: 是否启用流式响应
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_streaming = enable_streaming
        
        self._session = requests.Session()
        self._setup_session()
        
        # 如果未指定模型，获取第一个可用模型
        if not self.model:
            self.model = self._get_default_model()
        
        logger.info(f"LM Studio客户端初始化完成，服务器: {self.base_url}, 模型: {self.model}")
    
    def _setup_session(self):
        """设置HTTP会话"""
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
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
                
                # LM Studio在模型未加载时可能返回503或其他错误
                if response.status_code == 503:
                    logger.warning(f"模型可能未加载 (尝试 {attempt + 1}/{self.max_retries})，等待后重试...")
                    time.sleep(2 * (attempt + 1))
                    continue
                    
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                # 等待后重试
                time.sleep(2 * (attempt + 1))
    
    def _get_default_model(self) -> str:
        """
        获取默认模型（服务器上的第一个可用模型）
        
        Returns:
            模型ID
        """
        try:
            models = self.get_available_models()
            if models:
                # 优先选择Qwen模型
                for model in models:
                    model_id = model.get("id", "").lower()
                    if "qwen" in model_id:
                        return model["id"]
                # 其次选择DeepSeek模型（向后兼容）
                for model in models:
                    model_id = model.get("id", "").lower()
                    if "deepseek" in model_id:
                        return model["id"]
                # 否则返回第一个模型
                return models[0]["id"]
            else:
                logger.warning("未找到可用模型，使用默认模型ID")
                return "qwen3.5-4b"
        except Exception as e:
            logger.error(f"获取默认模型失败: {e}")
            return "qwen3.5-4b"
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        
        Returns:
            模型列表
        """
        try:
            response = self._make_request("GET", self.MODELS_ENDPOINT)
            result = response.json()
            
            if "data" in result:
                return result["data"]
            else:
                logger.warning(f"获取模型列表响应格式错误: {result}")
                return []
                
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
    
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
    
    def load_model(self, model_id: str) -> bool:
        """
        加载指定模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            是否成功加载
        """
        try:
            # 使用LM Studio原生API加载模型
            load_payload = {
                "model_key": model_id,
                "config": {
                    "context_length": 4096,
                    "eval_batch_size": 512,
                    "flash_attention": True,
                    "offload_kv_cache_to_gpu": True
                }
            }
            
            response = self._session.post(
                f"{self.base_url}/api/v1/models/load",
                json=load_payload,
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info(f"模型加载成功: {model_id}")
                self.model = model_id
                return True
            else:
                logger.error(f"模型加载失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"模型加载请求失败: {e}")
            return False
    
    def unload_model(self, model_id: Optional[str] = None) -> bool:
        """
        卸载模型
        
        Args:
            model_id: 模型ID，如果为None则卸载当前模型
            
        Returns:
            是否成功卸载
        """
        # LM Studio没有直接的卸载API，但我们可以通过切换模型来实现
        logger.info(f"请求卸载模型: {model_id or self.model}")
        return True
    
    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model_id: 模型ID，如果为None则获取当前模型信息
            
        Returns:
            模型信息字典
        """
        model_to_check = model_id or self.model
        
        try:
            # 尝试从模型列表中查找
            models = self.get_available_models()
            for model in models:
                if model.get("id") == model_to_check:
                    return model
            
            # 如果未找到，返回基本信息
            return {
                "id": model_to_check,
                "object": "model",
                "owned_by": "lm-studio"
            }
            
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """
        测试与LM Studio服务器的连接
        
        Returns:
            连接是否成功
        """
        try:
            response = self._session.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def set_model(self, model_id: str):
        """
        设置当前使用的模型
        
        Args:
            model_id: 模型ID
        """
        old_model = self.model
        self.model = model_id
        logger.info(f"模型已从 {old_model} 切换到 {model_id}")
    
    def close(self):
        """关闭客户端"""
        self._session.close()
        logger.info("LM Studio客户端已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 工厂函数，便于使用
def create_lm_studio_client(
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> LMStudioClient:
    """
    创建LM Studio客户端
    
    Args:
        base_url: 服务器地址
        model: 模型名称
        config: 配置字典
        
    Returns:
        LMStudioClient实例
    """
    if config is None:
        config = {}
    
    # 从环境变量获取配置
    import os
    if not base_url:
        base_url = os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234")
    
    if not model:
        model = os.environ.get("LM_STUDIO_MODEL")
    
    return LMStudioClient(
        base_url=base_url,
        model=model,
        timeout=config.get("timeout", 120),
        max_retries=config.get("max_retries", 3),
        enable_streaming=config.get("enable_streaming", True)
    )