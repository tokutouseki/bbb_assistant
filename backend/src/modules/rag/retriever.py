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
        """混合检索 — 使用 RRF (Reciprocal Rank Fusion) + 名称匹配加权"""
        try:
            fast_task = self._fast_search(query, category, top_k * 2, score_threshold)
            precise_task = self._precise_search(query, category, top_k * 2)

            fast_results, precise_results = await asyncio.gather(
                fast_task, precise_task
            )

            # RRF: Reciprocal Rank Fusion, k=60 是行业标准
            # 不依赖原始分数只看排名，避免向量端和关键词端分数不可比的问题
            K = 60
            rrf_scores: Dict[str, float] = {}
            result_map: Dict[str, UnifiedSearchResult] = {}

            for rank, r in enumerate(fast_results):
                rrf_scores[r.id] = rrf_scores.get(r.id, 0.0) + 1.0 / (K + rank + 1)
                if r.id not in result_map:
                    result_map[r.id] = r

            for rank, r in enumerate(precise_results):
                rrf_scores[r.id] = rrf_scores.get(r.id, 0.0) + 1.0 / (K + rank + 1)
                if r.id not in result_map:
                    result_map[r.id] = r

            # 名称匹配加权: 文档名精确命中查询词时给予大幅加分
            # 解决 "芽衣" 查询返回无关圣痕/故事的根本问题
            # 精确匹配 +0.5 (≈在两边都排第一), 部分匹配 +0.15
            query_lower = query.lower().strip()
            for doc_id, r in result_map.items():
                name_lower = r.name.lower()
                if query_lower == name_lower:
                    rrf_scores[doc_id] += 0.5
                elif query_lower in name_lower or name_lower in query_lower:
                    rrf_scores[doc_id] += 0.15

            # 最低阈值过滤纯噪声 (单边排名60+才≈0.008, 两边第一≈0.032)
            min_rrf = 0.01
            sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

            final_results = []
            for doc_id, score in sorted_items[:top_k]:
                if score < min_rrf:
                    continue
                r = result_map[doc_id]
                r.score = score
                r.match_type = "hybrid_rrf"
                r.source = "hybrid"
                final_results.append(r)

            return final_results

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
