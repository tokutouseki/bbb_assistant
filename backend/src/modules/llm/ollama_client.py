"""
Ollama 客户端
使用 Ollama HTTP API 进行本地模型推理
"""

import logging
from typing import Dict, List, Any, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:7b",
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()

    def test_connection(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Ollama连接失败: {e}")
            return False

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        resp = self._session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result.get("message", {}).get("content", "")

        return {
            "content": content,
            "model": result.get("model", self.model),
            "usage": {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            },
            "raw_response": result,
        }


def create_ollama_client(
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> OllamaClient:
    cfg = config or {}
    return OllamaClient(
        base_url=base_url or cfg.get("base_url", "http://127.0.0.1:11434"),
        model=model or cfg.get("model", "qwen2.5:7b"),
        timeout=cfg.get("timeout", 120),
    )
