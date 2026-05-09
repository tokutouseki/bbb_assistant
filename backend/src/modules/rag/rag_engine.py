"""
RAG引擎主类
==========
整合所有RAG组件，提供统一的检索增强生成接口
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from pathlib import Path

from .embedding import EmbeddingService, EmbeddingModelType
from .vector_store import ChromaDBVectorStore, VectorDocument
from .index_manager import IndexManager, IndexDocument
from .data_processor import DataProcessor, KnowledgeDocument
from .retriever import Retriever, SearchMode, UnifiedSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """RAG配置"""
    data_path: str = "./data"
    index_path: str = "./data/rag_index"
    chroma_persist_directory: str = "./data/chroma_db"
    chroma_collection: str = "bbb_knowledge"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_model_path: Optional[str] = None
    embedding_device: str = "cpu"
    embedding_offline_mode: bool = True
    vector_size: int = 384
    default_top_k: int = 5
    default_mode: SearchMode = SearchMode.HYBRID
    context_max_length: int = 2000


class RAGEngine:
    """
    RAG引擎
    
    提供两种检索模式：
    1. 快速模式 (FAST): 基于向量相似度，适合语义搜索
    2. 准确模式 (PRECISE): 基于关键词索引，适合精确查询
    
    使用示例:
        engine = RAGEngine(config)
        await engine.initialize()
        
        # 快速检索
        results = await engine.search("琪亚娜的技能", mode=SearchMode.FAST)
        
        # 准确检索
        results = await engine.search("炽翎", mode=SearchMode.PRECISE)
        
        # 获取上下文
        context = await engine.retrieve("如何培养炽翎")
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        
        self._embedding_service: Optional[EmbeddingService] = None
        self._vector_store: Optional[ChromaDBVectorStore] = None
        self._index_manager: Optional[IndexManager] = None
        self._data_processor: Optional[DataProcessor] = None
        self._retriever: Optional[Retriever] = None
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        初始化RAG引擎
        
        Returns:
            是否初始化成功
        """
        try:
            logger.info("正在初始化RAG引擎...")
            
            model_name = self.config.embedding_model
            if self.config.embedding_model_path:
                model_name = self.config.embedding_model_path
                logger.info(f"使用本地模型路径: {model_name}")
            
            self._embedding_service = EmbeddingService(
                model_type=EmbeddingModelType.SENTENCE_TRANSFORMER,
                model_name=model_name,
                device=self.config.embedding_device,
                offline_mode=self.config.embedding_offline_mode
            )
            
            if not await self._embedding_service.initialize():
                logger.error("初始化嵌入服务失败")
                return False
            
            logger.info("嵌入服务初始化完成")
            
            self._vector_store = ChromaDBVectorStore(
                persist_directory=self.config.chroma_persist_directory,
                collection_name=self.config.chroma_collection,
                vector_size=self.config.vector_size
            )
            
            if not await self._vector_store.initialize():
                logger.error("初始化向量存储失败")
                return False
            
            logger.info("向量存储初始化完成")
            
            self._index_manager = IndexManager(
                index_path=self.config.index_path
            )
            
            if not await self._index_manager.initialize():
                logger.error("初始化索引管理器失败")
                return False
            
            logger.info("索引管理器初始化完成")
            
            self._data_processor = DataProcessor(
                data_path=self.config.data_path
            )
            
            self._retriever = Retriever(
                embedding_service=self._embedding_service,
                vector_store=self._vector_store,
                index_manager=self._index_manager,
                fast_top_k=self.config.default_top_k,
                precise_top_k=self.config.default_top_k
            )
            
            self._initialized = True
            logger.info("RAG引擎初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化RAG引擎失败: {e}")
            return False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def search(
        self,
        query: str,
        mode: Optional[SearchMode] = None,
        category: Optional[str] = None,
        top_k: Optional[int] = None,
        score_threshold: float = 0.0
    ) -> List[UnifiedSearchResult]:
        """
        搜索知识库
        
        Args:
            query: 查询字符串
            mode: 搜索模式 (FAST/PRECISE/HYBRID)
            category: 限定分类
            top_k: 返回数量
            score_threshold: 分数阈值
            
        Returns:
            搜索结果列表
        """
        if not self._initialized:
            raise RuntimeError("RAG引擎未初始化，请先调用initialize()")
        
        search_mode = mode or self.config.default_mode
        k = top_k or self.config.default_top_k
        
        return await self._retriever.search(
            query=query,
            mode=search_mode,
            category=category,
            top_k=k,
            score_threshold=score_threshold
        )
    
    async def retrieve(
        self,
        query: str,
        mode: Optional[SearchMode] = None,
        category: Optional[str] = None,
        top_k: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> str:
        """
        检索并生成上下文
        
        Args:
            query: 查询字符串
            mode: 搜索模式
            category: 限定分类
            top_k: 返回数量
            max_length: 上下文最大长度
            
        Returns:
            格式化的上下文文本
        """
        results = await self.search(
            query=query,
            mode=mode,
            category=category,
            top_k=top_k
        )
        
        max_len = max_length or self.config.context_max_length
        return self._retriever.format_results_for_context(results, max_len)
    
    async def search_by_name(self, name: str, exact: bool = True) -> List[UnifiedSearchResult]:
        """按名称搜索"""
        if not self._initialized:
            raise RuntimeError("RAG引擎未初始化")
        return await self._retriever.search_by_name(name, exact)
    
    async def search_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
        limit: int = 100
    ) -> List[UnifiedSearchResult]:
        """按分类搜索"""
        if not self._initialized:
            raise RuntimeError("RAG引擎未初始化")
        return await self._retriever.search_by_category(category, subcategory, limit)
    
    async def get_document(self, doc_id: str) -> Optional[UnifiedSearchResult]:
        """根据ID获取文档"""
        if not self._initialized:
            raise RuntimeError("RAG引擎未初始化")
        return await self._retriever.get_document_by_id(doc_id)
    
    async def index_knowledge_base(
        self,
        category: Optional[str] = None,
        batch_size: int = 100,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        索引知识库数据
        
        Args:
            category: 指定分类，None表示全部
            batch_size: 批量处理大小
            force_reindex: 是否强制重新索引
            
        Returns:
            索引统计信息
        """
        if not self._initialized:
            raise RuntimeError("RAG引擎未初始化")
        
        stats = {
            "total_processed": 0,
            "vector_indexed": 0,
            "precise_indexed": 0,
            "errors": 0
        }
        
        try:
            if force_reindex:
                await self._vector_store.clear_collection()
                self._index_manager.clear()
            
            documents = []
            async for doc in self._data_processor.load_all_documents():
                if category and doc.category != category:
                    continue
                documents.append(doc)
            
            logger.info(f"共加载 {len(documents)} 个文档")
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                index_docs = []
                vector_docs = []
                
                texts_to_embed = [doc.content for doc in batch]
                embeddings = await self._embedding_service.embed_batch(texts_to_embed)
                
                for doc, embedding in zip(batch, embeddings):
                    index_docs.append(self._data_processor.to_index_document(doc))
                    vector_docs.append(self._data_processor.to_vector_document(doc, embedding))
                
                await self._index_manager.add_documents(index_docs)
                stats["precise_indexed"] += len(index_docs)
                
                await self._vector_store.upsert_vectors(vector_docs)
                stats["vector_indexed"] += len(vector_docs)
                
                stats["total_processed"] += len(batch)
                logger.info(f"已处理 {stats['total_processed']}/{len(documents)} 个文档")
            
            await self._index_manager.save_index()
            
            logger.info(f"知识库索引完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"索引知识库失败: {e}")
            stats["errors"] += 1
            return stats
    
    async def add_document(
        self,
        name: str,
        content: str,
        category: str,
        subcategory: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None
    ) -> str:
        """
        添加单个文档
        
        Args:
            name: 文档名称
            content: 文档内容
            category: 分类
            subcategory: 子分类
            metadata: 元数据
            aliases: 别名列表
            
        Returns:
            文档ID
        """
        if not self._initialized:
            raise RuntimeError("RAG引擎未初始化")
        
        doc = KnowledgeDocument(
            id=self._data_processor._generate_doc_id(name, category, subcategory),
            name=name,
            content=content,
            category=category,
            subcategory=subcategory,
            source_file="manual",
            metadata=metadata or {},
            aliases=aliases or []
        )
        
        embedding = await self._embedding_service.embed_single(doc.content)
        
        index_doc = self._data_processor.to_index_document(doc)
        await self._index_manager.add_document(index_doc)
        
        vector_doc = self._data_processor.to_vector_document(doc, embedding)
        await self._vector_store.upsert_single(vector_doc)
        
        return doc.id
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if not self._initialized:
            return False
        
        await self._index_manager.remove_document(doc_id)
        await self._vector_store.delete_by_ids([doc_id])
        
        return True
    
    async def get_categories(self) -> List[str]:
        """获取所有分类"""
        if not self._initialized:
            return []
        return await self._retriever.get_categories()
    
    async def get_subcategories(self, category: str) -> List[str]:
        """获取子分类"""
        if not self._initialized:
            return []
        return await self._retriever.get_subcategories(category)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._initialized:
            return {"initialized": False}
        
        vector_stats = await self._vector_store.get_stats()
        index_stats = self._index_manager.get_stats()
        embedding_info = self._embedding_service.get_model_info()
        
        return {
            "initialized": True,
            "vector_store": vector_stats,
            "index": index_stats,
            "embedding": embedding_info
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        result = {
            "healthy": True,
            "components": {}
        }
        
        if self._embedding_service and self._embedding_service.is_initialized:
            result["components"]["embedding"] = "ok"
        else:
            result["components"]["embedding"] = "error"
            result["healthy"] = False
        
        if self._vector_store and self._vector_store.is_initialized:
            result["components"]["vector_store"] = "ok"
        else:
            result["components"]["vector_store"] = "error"
            result["healthy"] = False
        
        if self._index_manager and self._index_manager.is_initialized:
            result["components"]["index_manager"] = "ok"
        else:
            result["components"]["index_manager"] = "error"
            result["healthy"] = False
        
        return result


def create_rag_engine(
    data_path: str = "./data",
    chroma_persist_directory: str = "./data/chroma_db",
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    **kwargs
) -> RAGEngine:
    """
    创建RAG引擎的便捷函数
    
    Args:
        data_path: 数据路径
        chroma_persist_directory: ChromaDB持久化目录
        embedding_model: 嵌入模型名称
        **kwargs: 其他配置参数
        
    Returns:
        RAG引擎实例
    """
    config = RAGConfig(
        data_path=data_path,
        chroma_persist_directory=chroma_persist_directory,
        embedding_model=embedding_model,
        **kwargs
    )
    return RAGEngine(config)
