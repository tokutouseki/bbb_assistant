"""
本地模型客户端
支持GGUF格式的本地模型加载和推理
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LocalModelConfig:
    """本地模型配置"""
    model_path: str  # 模型文件路径
    model_name: str = "unknown"  # 模型名称
    context_length: int = 2048  # 上下文长度
    temperature: float = 0.7  # 温度参数
    top_p: float = 0.9  # top-p采样
    top_k: int = 40  # top-k采样
    repeat_penalty: float = 1.1  # 重复惩罚
    gpu_layers: int = 0  # GPU层数，0表示全CPU
    n_threads: int = 4  # CPU线程数
    verbose: bool = False  # 是否显示详细日志
    mmproj_path: Optional[str] = None  # 多模态投影模型路径（可选）


class LocalModelClient:
    """本地模型客户端（支持GGUF格式）"""
    
    def __init__(self, config: LocalModelConfig):
        """
        初始化本地模型客户端
        
        Args:
            config: 模型配置
        """
        self.config = config
        self._model = None
        self._is_loaded = False
        
        logger.info(f"初始化本地模型客户端，模型: {config.model_name}")
    
    def load_model(self) -> bool:
        """
        加载模型
        
        Returns:
            是否成功加载
        """
        try:
            if not os.path.exists(self.config.model_path):
                logger.error(f"模型文件不存在: {self.config.model_path}")
                return False
            
            # 尝试导入llama-cpp-python
            try:
                from llama_cpp import Llama
            except ImportError:
                logger.error("未安装llama-cpp-python库，请运行: pip install llama-cpp-python")
                return False
            
            logger.info(f"开始加载模型: {self.config.model_path}")

            llama_kwargs = {
                "model_path": self.config.model_path,
                "n_ctx": self.config.context_length,
                "n_gpu_layers": self.config.gpu_layers,
                "n_threads": self.config.n_threads,
                "verbose": self.config.verbose,
            }

            # 可选启用多模态mmproj（若依赖或文件不满足则自动降级为纯文本）
            if self.config.mmproj_path:
                if os.path.exists(self.config.mmproj_path):
                    try:
                        from llama_cpp.llama_chat_format import Llava15ChatHandler
                        chat_handler = Llava15ChatHandler(clip_model_path=self.config.mmproj_path)
                        llama_kwargs["chat_handler"] = chat_handler
                        logger.info(f"启用mmproj多模态支持: {self.config.mmproj_path}")
                    except Exception as e:
                        logger.warning(f"mmproj初始化失败，降级为文本模式: {e}")
                else:
                    logger.warning(f"mmproj文件不存在，降级为文本模式: {self.config.mmproj_path}")

            self._model = Llama(**llama_kwargs)
            
            self._is_loaded = True
            logger.info(f"模型加载成功: {self.config.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = 512,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        聊天补全
        
        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            temperature: 温度参数，如果为None则使用配置中的值
            max_tokens: 最大生成token数
            stream: 是否流式输出（本地模型暂不支持流式）
            **kwargs: 其他参数
            
        Returns:
            聊天响应
        """
        if not self._is_loaded or self._model is None:
            raise RuntimeError("模型未加载，请先调用load_model()")
        
        # 构建提示词
        prompt = self._format_messages(messages)
        
        # 设置生成参数
        gen_kwargs = {
            "prompt": prompt,
            "max_tokens": max_tokens or 512,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "top_p": kwargs.get("top_p", self.config.top_p),
            "top_k": kwargs.get("top_k", self.config.top_k),
            "repeat_penalty": kwargs.get("repeat_penalty", self.config.repeat_penalty),
            "echo": kwargs.get("echo", False),
            "stop": kwargs.get("stop", []),
        }
        
        try:
            if stream:
                # 流式生成（如果需要）
                return self._stream_generate(**gen_kwargs)
            else:
                # 同步生成
                result = self._model(**gen_kwargs)
                
                response_text = result["choices"][0]["text"].strip()
                
                return {
                    "content": response_text,
                    "model": self.config.model_name,
                    "usage": {
                        "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": result.get("usage", {}).get("total_tokens", 0)
                    },
                    "raw_response": result
                }
                
        except Exception as e:
            logger.error(f"生成失败: {e}")
            raise
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        将消息列表格式化为模型输入的提示词
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的提示词
        """
        formatted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"系统: {content}")
            elif role == "user":
                formatted.append(f"用户: {content}")
            elif role == "assistant":
                formatted.append(f"助手: {content}")
            else:
                formatted.append(f"{role}: {content}")
        
        # 添加助手前缀，引导模型生成响应
        formatted.append("助手:")
        
        return "\n".join(formatted)
    
    def _stream_generate(self, **kwargs) -> Dict[str, Any]:
        """
        流式生成（模拟实现，实际需要模型支持）
        
        Args:
            **kwargs: 生成参数
            
        Returns:
            包含流式生成器的字典
        """
        # 本地模型暂不支持真正的流式生成，这里返回一个模拟的生成器
        result = self._model(**{**kwargs, "stream": False})
        response_text = result["choices"][0]["text"].strip()
        
        def _stream_generator():
            words = response_text.split()
            for i, word in enumerate(words):
                yield {
                    "chunk": word + (" " if i < len(words) - 1 else ""),
                    "is_final": i == len(words) - 1
                }
        
        return {
            "stream_generator": _stream_generator(),
            "model": self.config.model_name,
            "total_tokens": result.get("usage", {}).get("total_tokens", 0)
        }
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本嵌入
        
        Args:
            text: 输入文本
            
        Returns:
            文本嵌入向量
        """
        if not self._is_loaded or self._model is None:
            raise RuntimeError("模型未加载")
        
        try:
            # 使用模型生成嵌入
            embedding = self._model.create_embedding(text)
            return embedding["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"生成嵌入失败: {e}")
            # 返回一个空的嵌入向量
            return [0.0] * 768  # 假设嵌入维度为768
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        if not self._is_loaded or self._model is None:
            return {"error": "模型未加载"}
        
        try:
            # 获取模型元数据
            model_info = {
                "name": self.config.model_name,
                "path": self.config.model_path,
                "context_length": self.config.context_length,
                "is_loaded": self._is_loaded,
                "file_size": os.path.getsize(self.config.model_path) if os.path.exists(self.config.model_path) else 0,
                "parameters": "unknown"  # GGUF文件中可能不包含参数数量信息
            }
            
            # 尝试从文件名推断参数数量
            filename = os.path.basename(self.config.model_path).lower()
            if "7b" in filename or "7B" in filename:
                model_info["parameters"] = "7B"
            elif "13b" in filename or "13B" in filename:
                model_info["parameters"] = "13B"
            elif "8b" in filename or "8B" in filename:
                model_info["parameters"] = "8B"
            elif "6b" in filename or "6B" in filename:
                model_info["parameters"] = "6B"
            
            return model_info
            
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            return {"error": str(e)}
    
    def unload_model(self):
        """卸载模型，释放内存"""
        if self._model is not None:
            # llama-cpp-python模型会自动清理，这里只需要重置引用
            self._model = None
            self._is_loaded = False
            logger.info(f"模型已卸载: {self.config.model_name}")
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._is_loaded
    
    def __del__(self):
        """析构函数，确保模型被正确清理"""
        self.unload_model()


# 工厂函数和工具函数
def create_local_model_client(
    model_path: str,
    model_name: Optional[str] = None,
    **kwargs
) -> LocalModelClient:
    """
    创建本地模型客户端
    
    Args:
        model_path: 模型文件路径
        model_name: 模型名称，如果为None则从文件名推断
        **kwargs: 其他配置参数
        
    Returns:
        LocalModelClient实例
    """
    if model_name is None:
        model_name = os.path.basename(model_path).split(".")[0]
    
    config = LocalModelConfig(
        model_path=model_path,
        model_name=model_name,
        **kwargs
    )
    
    return LocalModelClient(config)


def find_gguf_models(models_dir: str) -> List[Dict[str, str]]:
    """
    查找指定目录中的GGUF模型文件
    
    Args:
        models_dir: 模型目录
        
    Returns:
        模型文件列表
    """
    if not os.path.exists(models_dir):
        return []
    
    gguf_files = []
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.lower().endswith(".gguf"):
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                
                gguf_files.append({
                    "path": file_path,
                    "name": file,
                    "size": file_size,
                    "size_mb": file_size / (1024 * 1024),
                    "directory": root
                })
    
    # 按文件大小排序
    gguf_files.sort(key=lambda x: x["size"], reverse=True)
    
    return gguf_files


def detect_gguf_model_parameters(filename: str) -> Dict[str, Any]:
    """
    从GGUF文件名推断模型参数
    
    Args:
        filename: GGUF文件名
        
    Returns:
        推断的模型参数
    """
    filename_lower = filename.lower()
    
    info = {
        "quantization": "unknown",
        "parameters": "unknown",
        "architecture": "unknown"
    }
    
    # 检测量化级别
    quant_patterns = {
        "q2_k": "Q2_K",
        "q3_k_s": "Q3_K_S", "q3_k_m": "Q3_K_M", "q3_k_l": "Q3_K_L",
        "q4_k_s": "Q4_K_S", "q4_k_m": "Q4_K_M",
        "q5_k_s": "Q5_K_S", "q5_k_m": "Q5_K_M",
        "q6_k": "Q6_K",
        "q8_0": "Q8_0",
        "f16": "F16"
    }
    
    for pattern, quant_name in quant_patterns.items():
        if pattern in filename_lower:
            info["quantization"] = quant_name
            break
    
    # 检测参数量
    param_patterns = {
        "7b": "7B", "8b": "8B", "13b": "13B", "34b": "34B", 
        "70b": "70B", "6b": "6B", "3b": "3B", "1b": "1B"
    }
    
    for pattern, param_name in param_patterns.items():
        if pattern in filename_lower:
            info["parameters"] = param_name
            break
    
    # 检测架构
    arch_patterns = {
        "llama": "LLaMA", "mistral": "Mistral", "yi": "Yi", "qwen": "Qwen",
        "deepseek": "DeepSeek", "phi": "Phi", "gemma": "Gemma"
    }
    
    for pattern, arch_name in arch_patterns.items():
        if pattern in filename_lower:
            info["architecture"] = arch_name
            break
    
    return info