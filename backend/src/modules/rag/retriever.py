"""
统一检索器
=========
整合快速模式和准确模式的检索功能
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

from .embedding import EmbeddingService
from .vector_store import QdrantVectorStore, SearchResult
from .index_manager import IndexManager, PreciseSearchResult

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """搜索模式"""
    FAST = "fast"
    PRECISE = "precise"
    HYBRID = "hybrid"


@dataclass
class UnifiedSearchResult:
    """统一搜索结果"""
    id: str
    name: str
    content: str
    category: str
    subcategory: Optional[str]
    score: float
    match_type: str
    source: str
    metadata: Dict[str, Any]


class Retriever:
    """
    统一检索器
    
    提供三种检索模式：
    1. FAST: 快速向量相似度检索
    2. PRECISE: 精确关键词匹配检索
    3. HYBRID: 混合检索，结合两种模式
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
        index_manager: IndexManager,
        fast_top_k: int = 10,
        precise_top_k: int = 10,
        hybrid_alpha: float = 0.5
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.index_manager = index_manager
        self.fast_top_k = fast_top_k
        self.precise_top_k = precise_top_k
        self.hybrid_alpha = hybrid_alpha
    
    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        category: Optional[str] = None,
        top_k: int = 10,
        score_threshold: float = 0.0
    ) -> List[UnifiedSearchResult]:
        """
        统一搜索接口
        
        Args:
            query: 查询字符串
            mode: 搜索模式
            category: 限定分类
            top_k: 返回数量
            score_threshold: 分数阈值
            
        Returns:
            统一搜索结果列表
        """
        if mode == SearchMode.FAST:
            return await self._fast_search(query, category, top_k, score_threshold)
        elif mode == SearchMode.PRECISE:
            return await self._precise_search(query, category, top_k)
        else:
            return await self._hybrid_search(query, category, top_k, score_threshold)
    
    async def _fast_search(
        self,
        query: str,
        category: Optional[str],
        top_k: int,
        score_threshold: float
    ) -> List[UnifiedSearchResult]:
        """快速向量检索"""
        try:
            query_vector = await self.embedding_service.embed_single(query)
            
            filter_conditions = {}
            if category:
                filter_conditions["category"] = category
            
            results = await self.vector_store.search(
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=score_threshold,
                filter_conditions=filter_conditions if filter_conditions else None
            )
            
            unified_results = []
            for r in results:
                unified_results.append(UnifiedSearchResult(
                    id=r.id,
                    name=r.metadata.get("name", ""),
                    content=r.content,
                    category=r.metadata.get("category", ""),
                    subcategory=r.metadata.get("subcategory"),
                    score=r.score,
                    match_type="vector_similarity",
                    source="fast",
                    metadata=r.metadata
                ))
            
            return unified_results
            
        except Exception as e:
            logger.error(f"快速检索失败: {e}")
            return []
    
    async def _precise_search(
        self,
        query: str,
        category: Optional[str],
        top_k: int
    ) -> List[UnifiedSearchResult]:
        """精确关键词检索"""
        try:
            results = await self.index_manager.precise_search(
                query=query,
                category=category,
                top_k=top_k
            )
            
            unified_results = []
            for r in results:
                unified_results.append(UnifiedSearchResult(
                    id=r.id,
                    name=r.name,
                    content=r.content,
                    category=r.category,
                    subcategory=r.subcategory,
                    score=r.match_score,
                    match_type=r.match_type,
                    source="precise",
                    metadata=r.metadata
                ))
            
            return unified_results
            
        except Exception as e:
            logger.error(f"精确检索失败: {e}")
            return []
    
    async def _hybrid_search(
        self,
        query: str,
        category: Optional[str],
        top_k: int,
        score_threshold: float
    ) -> List[UnifiedSearchResult]:
        """混合检索"""
        try:
            fast_task = self._fast_search(query, category, top_k * 2, score_threshold)
            precise_task = self._precise_search(query, category, top_k * 2)
            
            fast_results, precise_results = await asyncio.gather(
                fast_task, precise_task
            )
            
            combined_scores: Dict[str, Dict[str, Any]] = {}
            
            for r in fast_results:
                combined_scores[r.id] = {
                    "result": r,
                    "fast_score": r.score,
                    "precise_score": 0.0,
                    "count": 1
                }
            
            for r in precise_results:
                if r.id in combined_scores:
                    combined_scores[r.id]["precise_score"] = r.score
                    combined_scores[r.id]["count"] += 1
                else:
                    combined_scores[r.id] = {
                        "result": r,
                        "fast_score": 0.0,
                        "precise_score": r.score,
                        "count": 1
                    }
            
            final_results = []
            for doc_id, data in combined_scores.items():
                fast_score = data["fast_score"]
                precise_score = data["precise_score"]
                
                hybrid_score = (
                    self.hybrid_alpha * fast_score +
                    (1 - self.hybrid_alpha) * precise_score
                )
                
                if data["count"] > 1:
                    hybrid_score *= 1.2
                
                result = data["result"]
                result.score = hybrid_score
                result.match_type = "hybrid"
                result.source = "hybrid"
                
                final_results.append(result)
            
            final_results.sort(key=lambda x: x.score, reverse=True)
            
            return final_results[:top_k]
            
        except Exception as e:
            logger.error(f"混合检索失败: {e}")
            return []
    
    async def search_by_name(self, name: str, exact: bool = True) -> List[UnifiedSearchResult]:
        """按名称搜索"""
        results = await self.index_manager.search_by_name(name, exact_match=exact)
        
        unified_results = []
        for r in results:
            unified_results.append(UnifiedSearchResult(
                id=r.id,
                name=r.name,
                content=r.content,
                category=r.category,
                subcategory=r.subcategory,
                score=r.match_score,
                match_type=r.match_type,
                source="precise",
                metadata=r.metadata
            ))
        
        return unified_results
    
    async def search_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
        limit: int = 100
    ) -> List[UnifiedSearchResult]:
        """按分类搜索"""
        results = await self.index_manager.search_by_category(category, subcategory, limit)
        
        unified_results = []
        for r in results:
            unified_results.append(UnifiedSearchResult(
                id=r.id,
                name=r.name,
                content=r.content,
                category=r.category,
                subcategory=r.subcategory,
                score=r.match_score,
                match_type=r.match_type,
                source="precise",
                metadata=r.metadata
            ))
        
        return unified_results
    
    async def get_document_by_id(self, doc_id: str) -> Optional[UnifiedSearchResult]:
        """根据ID获取文档"""
        doc = self.index_manager.get_document(doc_id)
        if doc:
            return UnifiedSearchResult(
                id=doc.id,
                name=doc.name,
                content=doc.content,
                category=doc.category,
                subcategory=doc.subcategory,
                score=1.0,
                match_type="id_lookup",
                source="precise",
                metadata=doc.metadata
            )
        return None
    
    async def get_categories(self) -> List[str]:
        """获取所有分类"""
        return self.index_manager.get_all_categories()
    
    async def get_subcategories(self, category: str) -> List[str]:
        """获取子分类"""
        return self.index_manager.get_subcategories(category)
    
    def format_results_for_context(
        self,
        results: List[UnifiedSearchResult],
        max_length: int = 2000
    ) -> str:
        """
        将搜索结果格式化为上下文文本
        
        Args:
            results: 搜索结果
            max_length: 最大长度
            
        Returns:
            格式化的上下文文本
        """
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, r in enumerate(results):
            entry = f"【{r.name}】({r.category}"
            if r.subcategory:
                entry += f"/{r.subcategory}"
            entry += f")\n{r.content}\n"
            
            if current_length + len(entry) > max_length:
                break
            
            context_parts.append(entry)
            current_length += len(entry)
        
        return "\n".join(context_parts)
