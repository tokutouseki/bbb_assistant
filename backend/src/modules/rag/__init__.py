"""
RAG (Retrieval-Augmented Generation) 模块
========================================
提供两种检索模式：
1. 快速模式 (Fast): 基于向量相似度检索，适合模糊查询和语义搜索
2. 准确模式 (Precise): 基于关键词索引和元数据过滤，适合精确查询
3. 混合模式 (Hybrid): 结合快速和准确模式，提供最佳检索效果

使用方法:
    from modules.rag import RAGEngine, SearchMode, RAGConfig
    
    # 初始化引擎
    config = RAGConfig(data_path="./data")
    engine = RAGEngine(config)
    await engine.initialize()
    
    # 快速检索
    results = await engine.search("琪亚娜的技能", mode=SearchMode.FAST)
    
    # 准确检索
    results = await engine.search("炽翎", mode=SearchMode.PRECISE, category="图鉴")
    
    # 混合检索（推荐）
    results = await engine.search("如何培养炽翎", mode=SearchMode.HYBRID)
"""

from .rag_engine import RAGEngine, RAGConfig
from .retriever import Retriever, SearchMode, UnifiedSearchResult
from .embedding import EmbeddingService, EmbeddingModelType
from .vector_store import ChromaDBVectorStore, VectorDocument, SearchResult
from .index_manager import IndexManager, IndexDocument, PreciseSearchResult
from .data_processor import DataProcessor, KnowledgeDocument

__all__ = [
    "RAGEngine",
    "RAGConfig",
    "Retriever",
    "SearchMode",
    "UnifiedSearchResult",
    "EmbeddingService",
    "EmbeddingModelType",
    "ChromaDBVectorStore",
    "VectorDocument",
    "SearchResult",
    "IndexManager",
    "IndexDocument",
    "PreciseSearchResult",
    "DataProcessor",
    "KnowledgeDocument"
]

__version__ = "1.0.0"
