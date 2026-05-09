"""
ChromaDB向量存储服务
=================
提供向量存储和检索功能，支持：
- 向量索引和存储
- 相似度搜索
- 元数据过滤
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
import os

logger = logging.getLogger(__name__)


@dataclass
class VectorDocument:
    """向量文档数据结构"""
    id: str
    vector: List[float]
    content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class ChromaDBVectorStore:
    """
    ChromaDB向量存储
    
    提供高效的向量存储和检索功能，支持本地持久化
    """
    
    DEFAULT_COLLECTION_NAME = "bbb_knowledge"
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = DEFAULT_COLLECTION_NAME,
        vector_size: int = 384,
        distance: str = "cosine"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        
        self._client = None
        self._collection = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        初始化ChromaDB连接
        
        Returns:
            是否初始化成功
        """
        try:
            import chromadb
            from chromadb.config import Settings
            
            logger.info(f"正在初始化ChromaDB: {self.persist_directory}")
            
            os.makedirs(self.persist_directory, exist_ok=True)
            
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            await self._ensure_collection()
            
            self._initialized = True
            logger.info("ChromaDB向量存储初始化完成")
            return True
            
        except ImportError:
            logger.error("未安装chromadb，请运行: pip install chromadb")
            return False
        except Exception as e:
            logger.error(f"初始化ChromaDB失败: {e}")
            return False
    
    async def _ensure_collection(self):
        """确保集合存在"""
        try:
            import chromadb
            
            distance_map = {
                "cosine": "cosine",
                "l2": "l2",
                "ip": "ip"
            }
            
            metadata = {
                "hnsw:space": distance_map.get(self.distance.lower(), "cosine")
            }
            
            try:
                self._collection = self._client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"集合 {self.collection_name} 已存在，向量数: {self._collection.count()}")
            except Exception:
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    metadata=metadata
                )
                logger.info(f"创建集合 {self.collection_name} 成功")
            
        except Exception as e:
            logger.error(f"确保集合存在失败: {e}")
            raise
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def upsert_vectors(
        self,
        documents: List[VectorDocument],
        batch_size: int = 100
    ) -> bool:
        """
        批量插入或更新向量
        
        Args:
            documents: 文档列表
            batch_size: 批量大小
            
        Returns:
            是否成功
        """
        if not self._initialized:
            raise RuntimeError("向量存储未初始化，请先调用initialize()")
        
        try:
            ids = []
            embeddings = []
            metadatas = []
            documents_content = []
            
            for doc in documents:
                ids.append(doc.id)
                embeddings.append(doc.vector)
                metadatas.append({
                    **doc.metadata,
                    "created_at": datetime.now().isoformat()
                })
                documents_content.append(doc.content)
            
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_documents = documents_content[i:i + batch_size]
                
                self._collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas,
                    documents=batch_documents
                )
                logger.debug(f"已插入 {len(batch_ids)} 条向量")
            
            logger.info(f"总共插入 {len(documents)} 条向量")
            return True
            
        except Exception as e:
            logger.error(f"插入向量失败: {e}")
            return False
    
    async def upsert_single(self, document: VectorDocument) -> bool:
        """插入单个向量"""
        return await self.upsert_vectors([document])
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        向量相似度搜索
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            score_threshold: 分数阈值
            filter_conditions: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self._initialized:
            raise RuntimeError("向量存储未初始化，请先调用initialize()")
        
        try:
            where_filter = None
            if filter_conditions:
                where_filter = {}
                for key, value in filter_conditions.items():
                    where_filter[key] = value
            
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            if results and results['ids'] and len(results['ids']) > 0:
                for i, doc_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1 - distance
                    
                    if score_threshold > 0 and score < score_threshold:
                        continue
                    
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    content = results['documents'][0][i] if results['documents'] else ""
                    
                    search_results.append(SearchResult(
                        id=doc_id,
                        score=score,
                        content=content,
                        metadata=metadata
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    async def delete_by_ids(self, ids: List[str]) -> bool:
        """根据ID删除向量"""
        if not self._initialized:
            raise RuntimeError("向量存储未初始化")
        
        try:
            self._collection.delete(ids=ids)
            logger.info(f"已删除 {len(ids)} 条向量")
            return True
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
    
    async def delete_by_filter(self, filter_conditions: Dict[str, Any]) -> int:
        """根据条件删除向量"""
        if not self._initialized:
            raise RuntimeError("向量存储未初始化")
        
        try:
            where_filter = {}
            for key, value in filter_conditions.items():
                where_filter[key] = value
            
            self._collection.delete(where=where_filter)
            
            logger.info(f"已按条件删除向量")
            return True
        except Exception as e:
            logger.error(f"按条件删除向量失败: {e}")
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        if not self._initialized:
            return {"error": "未初始化"}
        
        try:
            count = self._collection.count()
            return {
                "name": self.collection_name,
                "vectors_count": count,
                "dimension": self.vector_size,
                "distance": self.distance,
                "persist_directory": self.persist_directory,
                "status": "ready"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def clear_collection(self) -> bool:
        """清空集合"""
        if not self._initialized:
            return False
        
        try:
            self._client.delete_collection(self.collection_name)
            await self._ensure_collection()
            logger.info(f"集合 {self.collection_name} 已清空")
            return True
        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        info = await self.get_collection_info()
        return {
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
            "backend": "ChromaDB",
            **info
        }


QdrantVectorStore = ChromaDBVectorStore
