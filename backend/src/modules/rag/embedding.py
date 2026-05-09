"""
向量嵌入服务
===========
提供文本向量化功能，支持多种嵌入模型
- sentence-transformers: 本地模型，速度快
- OpenAI embeddings: 云端API，效果好
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class EmbeddingModelType(Enum):
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OPENAI = "openai"
    LOCAL_CACHE = "local_cache"
    ZHIPU = "zhipu"
    MOCK = "mock"


class EmbeddingService:
    """
    向量嵌入服务
    
    支持多种嵌入模型，提供统一的向量化接口
    """
    
    def __init__(
        self,
        model_type: EmbeddingModelType = EmbeddingModelType.SENTENCE_TRANSFORMER,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir: Optional[str] = None,
        device: str = "cpu",
        offline_mode: bool = False,
        api_key: Optional[str] = None
    ):
        self.model_type = model_type
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device
        self.offline_mode = offline_mode
        self.api_key = api_key
        
        self._model = None
        self._dimension = 384
        self._initialized = False
        
        self._embedding_cache: Dict[str, List[float]] = {}
        
    async def initialize(self) -> bool:
        """
        初始化嵌入模型
        
        Returns:
            是否初始化成功
        """
        try:
            if self.model_type == EmbeddingModelType.SENTENCE_TRANSFORMER:
                return await self._init_sentence_transformer()
            elif self.model_type == EmbeddingModelType.OPENAI:
                return await self._init_openai()
            elif self.model_type == EmbeddingModelType.ZHIPU:
                return await self._init_zhipu()
            elif self.model_type == EmbeddingModelType.MOCK:
                return await self._init_mock()
            else:
                logger.warning("使用本地缓存模式，不加载模型")
                self._initialized = True
                return True
                
        except Exception as e:
            logger.error(f"初始化嵌入模型失败: {e}")
            return False
    
    async def _init_sentence_transformer(self) -> bool:
        """初始化sentence-transformers模型"""
        try:
            from sentence_transformers import SentenceTransformer
            import os
            
            logger.info(f"正在加载嵌入模型: {self.model_name}")
            
            if self.offline_mode:
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                os.environ['HF_HUB_OFFLINE'] = '1'
            
            model_kwargs = {
                "device": self.device
            }
            
            if self.cache_dir:
                model_kwargs["cache_folder"] = self.cache_dir
            
            self._model = await asyncio.to_thread(
                SentenceTransformer,
                self.model_name,
                **model_kwargs
            )
            
            self._dimension = self._model.get_sentence_embedding_dimension()
            self._initialized = True
            
            logger.info(f"嵌入模型加载完成，维度: {self._dimension}")
            return True
            
        except ImportError:
            logger.error("未安装sentence-transformers，请运行: pip install sentence-transformers")
            return False
        except Exception as e:
            logger.error(f"加载sentence-transformers模型失败: {e}")
            return False
    
    async def _init_openai(self) -> bool:
        """初始化OpenAI嵌入模型"""
        try:
            import openai
            
            self._model = openai
            self._dimension = 1536
            self._initialized = True
            
            logger.info("OpenAI嵌入服务初始化完成")
            return True
            
        except ImportError:
            logger.error("未安装openai，请运行: pip install openai")
            return False
    
    async def _init_zhipu(self) -> bool:
        """初始化智谱AI嵌入模型"""
        try:
            from zhipuai import ZhipuAI
            
            if not self.api_key:
                logger.error("智谱AI需要提供api_key")
                return False
            
            self._model = ZhipuAI(api_key=self.api_key)
            self._dimension = 1024
            self._initialized = True
            
            logger.info("智谱AI嵌入服务初始化完成")
            return True
            
        except ImportError:
            logger.error("未安装zhipuai，请运行: pip install zhipuai")
            return False
    
    async def _init_mock(self) -> bool:
        """初始化Mock嵌入模型（用于测试）"""
        import numpy as np
        
        self._dimension = 384
        self._initialized = True
        logger.info("Mock嵌入服务初始化完成（仅用于测试）")
        return True
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        return self._dimension
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()
    
    async def embed_single(self, text: str, use_cache: bool = True) -> List[float]:
        """
        将单个文本转换为向量
        
        Args:
            text: 输入文本
            use_cache: 是否使用缓存
            
        Returns:
            向量列表
        """
        if not self._initialized:
            raise RuntimeError("嵌入服务未初始化，请先调用initialize()")
        
        cache_key = self._get_cache_key(text)
        
        if use_cache and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        if self.model_type == EmbeddingModelType.SENTENCE_TRANSFORMER:
            embedding = await self._embed_sentence_transformer([text])
            result = embedding[0]
        elif self.model_type == EmbeddingModelType.OPENAI:
            result = await self._embed_openai_single(text)
        else:
            raise RuntimeError(f"不支持的模型类型: {self.model_type}")
        
        if use_cache:
            self._embedding_cache[cache_key] = result
        
        return result
    
    async def embed_batch(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """
        批量将文本转换为向量
        
        Args:
            texts: 输入文本列表
            use_cache: 是否使用缓存
            
        Returns:
            向量列表的列表
        """
        if not self._initialized:
            raise RuntimeError("嵌入服务未初始化，请先调用initialize()")
        
        results = []
        uncached_texts = []
        uncached_indices = []
        
        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._embedding_cache:
                    results.append((i, self._embedding_cache[cache_key]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        if uncached_texts:
            if self.model_type == EmbeddingModelType.SENTENCE_TRANSFORMER:
                batch_embeddings = await self._embed_sentence_transformer(uncached_texts)
            elif self.model_type == EmbeddingModelType.OPENAI:
                batch_embeddings = await self._embed_openai_batch(uncached_texts)
            else:
                raise RuntimeError(f"不支持的模型类型: {self.model_type}")
            
            for idx, embedding in zip(uncached_indices, batch_embeddings):
                results.append((idx, embedding))
                if use_cache:
                    cache_key = self._get_cache_key(uncached_texts[uncached_indices.index(idx)])
                    self._embedding_cache[cache_key] = embedding
        
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]
    
    async def _embed_sentence_transformer(self, texts: List[str]) -> List[List[float]]:
        """使用sentence-transformers生成嵌入"""
        try:
            embeddings = await asyncio.to_thread(
                self._model.encode,
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"sentence-transformers嵌入失败: {e}")
            raise
    
    async def _embed_openai_single(self, text: str) -> List[float]:
        """使用OpenAI生成单个嵌入"""
        try:
            response = await asyncio.to_thread(
                self._model.Embedding.create,
                model="text-embedding-ada-002",
                input=text
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"OpenAI嵌入失败: {e}")
            raise
    
    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """使用OpenAI批量生成嵌入"""
        try:
            response = await asyncio.to_thread(
                self._model.Embedding.create,
                model="text-embedding-ada-002",
                input=texts
            )
            return [item['embedding'] for item in response['data']]
        except Exception as e:
            logger.error(f"OpenAI批量嵌入失败: {e}")
            raise
    
    def clear_cache(self):
        """清空嵌入缓存"""
        self._embedding_cache.clear()
        logger.info("嵌入缓存已清空")
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._embedding_cache)
    
    async def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            相似度分数 (0-1)
        """
        import numpy as np
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_type": self.model_type.value,
            "model_name": self.model_name,
            "dimension": self._dimension,
            "device": self.device,
            "initialized": self._initialized,
            "cache_size": len(self._embedding_cache)
        }
