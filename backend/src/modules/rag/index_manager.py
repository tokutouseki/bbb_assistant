"""
索引管理器 - 准确模式
===================
提供精确的索引和检索功能：
- 关键词倒排索引
- 元数据索引
- 名称精确匹配
- 分类索引
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import asyncio
import jieba
import jieba.analyse

logger = logging.getLogger(__name__)


@dataclass
class IndexDocument:
    """索引文档"""
    id: str
    name: str
    content: str
    category: str
    subcategory: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)


@dataclass
class PreciseSearchResult:
    """精确搜索结果"""
    id: str
    name: str
    content: str
    category: str
    subcategory: Optional[str]
    match_type: str
    match_score: float
    metadata: Dict[str, Any]


class IndexManager:
    """
    索引管理器
    
    实现准确模式的索引和检索：
    1. 名称精确匹配索引
    2. 关键词倒排索引
    3. 分类索引
    4. 别名索引
    """
    
    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path
        
        self._name_index: Dict[str, IndexDocument] = {}
        self._keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self._category_index: Dict[str, Set[str]] = defaultdict(set)
        self._subcategory_index: Dict[str, Set[str]] = defaultdict(set)
        self._alias_index: Dict[str, str] = {}
        
        self._id_counter = 0
        self._initialized = False
        
        self._stop_words = set([
            "的", "是", "在", "了", "和", "与", "或", "有", "一", "个",
            "这", "那", "之", "为", "以", "及", "等", "中", "上", "下"
        ])
    
    async def initialize(self) -> bool:
        """初始化索引管理器"""
        try:
            logger.info("正在初始化索引管理器...")
            
            if self.index_path and Path(self.index_path).exists():
                await self._load_index()
            
            self._initialized = True
            logger.info(f"索引管理器初始化完成，共 {len(self._name_index)} 条索引")
            return True
            
        except Exception as e:
            logger.error(f"初始化索引管理器失败: {e}")
            return False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        self._id_counter += 1
        return f"doc_{self._id_counter}"
    
    def _extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """提取关键词"""
        if not text:
            return []
        
        keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
        
        filtered = [kw for kw in keywords if kw not in self._stop_words and len(kw) > 1]
        
        return filtered
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []
        tokens = list(jieba.cut(text.lower()))
        return [t for t in tokens if t.strip() and t not in self._stop_words]
    
    async def add_document(self, document: IndexDocument) -> str:
        """
        添加文档到索引
        
        Args:
            document: 索引文档
            
        Returns:
            文档ID
        """
        doc_id = document.id or self._generate_id()
        document.id = doc_id
        
        if not document.keywords:
            document.keywords = self._extract_keywords(document.content)
        
        self._name_index[doc_id] = document
        
        name_lower = document.name.lower()
        self._keyword_index[name_lower].add(doc_id)
        
        for keyword in document.keywords:
            self._keyword_index[keyword.lower()].add(doc_id)
        
        tokens = self._tokenize(document.content)
        for token in tokens:
            self._keyword_index[token].add(doc_id)
        
        self._category_index[document.category].add(doc_id)
        
        if document.subcategory:
            key = f"{document.category}/{document.subcategory}"
            self._subcategory_index[key].add(doc_id)
        
        for alias in document.aliases:
            self._alias_index[alias.lower()] = doc_id
        
        logger.debug(f"添加文档到索引: {document.name} (ID: {doc_id})")
        return doc_id
    
    async def add_documents(self, documents: List[IndexDocument]) -> List[str]:
        """批量添加文档"""
        ids = []
        for doc in documents:
            doc_id = await self.add_document(doc)
            ids.append(doc_id)
        return ids
    
    async def remove_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id not in self._name_index:
            return False
        
        doc = self._name_index[doc_id]
        
        del self._name_index[doc_id]
        
        for keyword in doc.keywords:
            self._keyword_index[keyword.lower()].discard(doc_id)
        
        self._category_index[doc.category].discard(doc_id)
        
        if doc.subcategory:
            key = f"{doc.category}/{doc.subcategory}"
            self._subcategory_index[key].discard(doc_id)
        
        for alias in doc.aliases:
            if alias.lower() in self._alias_index and self._alias_index[alias.lower()] == doc_id:
                del self._alias_index[alias.lower()]
        
        return True
    
    async def search_by_name(
        self,
        name: str,
        exact_match: bool = True
    ) -> List[PreciseSearchResult]:
        """
        按名称搜索
        
        Args:
            name: 名称
            exact_match: 是否精确匹配
            
        Returns:
            搜索结果
        """
        results = []
        name_lower = name.lower()
        
        if exact_match:
            for doc_id, doc in self._name_index.items():
                if doc.name.lower() == name_lower:
                    results.append(PreciseSearchResult(
                        id=doc_id,
                        name=doc.name,
                        content=doc.content,
                        category=doc.category,
                        subcategory=doc.subcategory,
                        match_type="name_exact",
                        match_score=1.0,
                        metadata=doc.metadata
                    ))
        else:
            for doc_id, doc in self._name_index.items():
                if name_lower in doc.name.lower():
                    score = len(name_lower) / len(doc.name)
                    results.append(PreciseSearchResult(
                        id=doc_id,
                        name=doc.name,
                        content=doc.content,
                        category=doc.category,
                        subcategory=doc.subcategory,
                        match_type="name_partial",
                        match_score=score,
                        metadata=doc.metadata
                    ))
        
        return results
    
    async def search_by_alias(self, alias: str) -> Optional[PreciseSearchResult]:
        """按别名搜索"""
        alias_lower = alias.lower()
        
        if alias_lower in self._alias_index:
            doc_id = self._alias_index[alias_lower]
            doc = self._name_index.get(doc_id)
            if doc:
                return PreciseSearchResult(
                    id=doc_id,
                    name=doc.name,
                    content=doc.content,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    match_type="alias",
                    match_score=1.0,
                    metadata=doc.metadata
                )
        
        return None
    
    async def search_by_keywords(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        top_k: int = 10
    ) -> List[PreciseSearchResult]:
        """
        按关键词搜索 — TF词频加权

        解决 binary 匹配的缺陷: "提到过芽衣" 和 "芽衣是主题" 得分不再相同。
        TF (词频) 越高 → 文档越以此为主题 → 得分越高。
        名称命中额外加分。
        """
        doc_scores: Dict[str, float] = defaultdict(float)

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self._keyword_index:
                for doc_id in self._keyword_index[keyword_lower]:
                    doc = self._name_index.get(doc_id)
                    if doc:
                        # TF: 关键词在文档内容中出现的次数
                        tf = doc.content.lower().count(keyword_lower)
                        # 基础匹配 + TF加成(cap 10) + 名称命中加成
                        score = 1.0 + min(tf * 0.5, 5.0)
                        if keyword_lower in doc.name.lower():
                            score += 3.0
                        doc_scores[doc_id] += score

        if category:
            category_docs = self._category_index.get(category, set())
            doc_scores = {
                k: v for k, v in doc_scores.items()
                if k in category_docs
            }

        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_id, score in sorted_docs:
            doc = self._name_index.get(doc_id)
            if doc:
                results.append(PreciseSearchResult(
                    id=doc_id,
                    name=doc.name,
                    content=doc.content,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    match_type="keyword_tf",
                    match_score=min(score / max(1, len(keywords)), 1.0),
                    metadata=doc.metadata
                ))

        return results
    
    async def search_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
        limit: int = 100
    ) -> List[PreciseSearchResult]:
        """
        按分类搜索
        
        Args:
            category: 分类
            subcategory: 子分类
            limit: 返回数量限制
            
        Returns:
            搜索结果
        """
        results = []
        
        if subcategory:
            key = f"{category}/{subcategory}"
            doc_ids = self._subcategory_index.get(key, set())
        else:
            doc_ids = self._category_index.get(category, set())
        
        for doc_id in list(doc_ids)[:limit]:
            doc = self._name_index.get(doc_id)
            if doc:
                results.append(PreciseSearchResult(
                    id=doc_id,
                    name=doc.name,
                    content=doc.content,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    match_type="category",
                    match_score=1.0,
                    metadata=doc.metadata
                ))
        
        return results
    
    async def precise_search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10
    ) -> List[PreciseSearchResult]:
        """
        精确搜索（综合搜索）
        
        优先级：
        1. 名称精确匹配
        2. 别名匹配
        3. 名称部分匹配
        4. 关键词匹配
        
        Args:
            query: 查询字符串
            category: 限定分类
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        results = []
        seen_ids = set()
        
        name_results = await self.search_by_name(query, exact_match=True)
        for r in name_results:
            if category and r.category != category:
                continue
            if r.id not in seen_ids:
                results.append(r)
                seen_ids.add(r.id)
        
        alias_result = await self.search_by_alias(query)
        if alias_result:
            if not category or alias_result.category == category:
                if alias_result.id not in seen_ids:
                    results.append(alias_result)
                    seen_ids.add(alias_result.id)
        
        if len(results) < top_k:
            partial_results = await self.search_by_name(query, exact_match=False)
            for r in partial_results:
                if category and r.category != category:
                    continue
                if r.id not in seen_ids:
                    results.append(r)
                    seen_ids.add(r.id)
        
        if len(results) < top_k:
            keywords = self._extract_keywords(query, top_k=5)
            if keywords:
                keyword_results = await self.search_by_keywords(keywords, category=category)
                for r in keyword_results:
                    if r.id not in seen_ids:
                        results.append(r)
                        seen_ids.add(r.id)
        
        return results[:top_k]
    
    def get_document(self, doc_id: str) -> Optional[IndexDocument]:
        """获取文档"""
        return self._name_index.get(doc_id)
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self._category_index.keys())
    
    def get_subcategories(self, category: str) -> List[str]:
        """获取子分类"""
        prefix = f"{category}/"
        subcategories = []
        for key in self._subcategory_index.keys():
            if key.startswith(prefix):
                subcategories.append(key[len(prefix):])
        return subcategories
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计"""
        return {
            "total_documents": len(self._name_index),
            "total_keywords": len(self._keyword_index),
            "categories": dict((k, len(v)) for k, v in self._category_index.items()),
            "aliases": len(self._alias_index)
        }
    
    async def _load_index(self):
        """加载索引"""
        try:
            index_file = Path(self.index_path) / "precise_index.json"
            if not index_file.exists():
                return
            
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for doc_data in data.get("documents", []):
                doc = IndexDocument(
                    id=doc_data["id"],
                    name=doc_data["name"],
                    content=doc_data["content"],
                    category=doc_data["category"],
                    subcategory=doc_data.get("subcategory"),
                    keywords=doc_data.get("keywords", []),
                    metadata=doc_data.get("metadata", {}),
                    aliases=doc_data.get("aliases", [])
                )
                self._name_index[doc.id] = doc
                
                for keyword in doc.keywords:
                    self._keyword_index[keyword.lower()].add(doc.id)
                
                self._category_index[doc.category].add(doc.id)
                
                if doc.subcategory:
                    key = f"{doc.category}/{doc.subcategory}"
                    self._subcategory_index[key].add(doc.id)
                
                for alias in doc.aliases:
                    self._alias_index[alias.lower()] = doc.id
            
            self._id_counter = data.get("id_counter", len(self._name_index))
            logger.info(f"从 {index_file} 加载了 {len(self._name_index)} 条索引")
            
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
    
    async def save_index(self) -> bool:
        """保存索引"""
        if not self.index_path:
            return False
        
        try:
            Path(self.index_path).mkdir(parents=True, exist_ok=True)
            
            documents = []
            for doc in self._name_index.values():
                documents.append({
                    "id": doc.id,
                    "name": doc.name,
                    "content": doc.content,
                    "category": doc.category,
                    "subcategory": doc.subcategory,
                    "keywords": doc.keywords,
                    "metadata": doc.metadata,
                    "aliases": doc.aliases
                })
            
            data = {
                "documents": documents,
                "id_counter": self._id_counter
            }
            
            index_file = Path(self.index_path) / "precise_index.json"
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"索引已保存到 {index_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
            return False
    
    def clear(self):
        """清空索引"""
        self._name_index.clear()
        self._keyword_index.clear()
        self._category_index.clear()
        self._subcategory_index.clear()
        self._alias_index.clear()
        self._id_counter = 0
        logger.info("索引已清空")
