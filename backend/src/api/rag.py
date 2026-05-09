"""
RAG API接口
==========
提供RAG检索的HTTP接口
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..modules.rag import RAGEngine, RAGConfig, SearchMode
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG检索"])

_rag_engine: Optional[RAGEngine] = None


async def get_rag_engine() -> RAGEngine:
    """获取RAG引擎实例"""
    global _rag_engine
    
    if _rag_engine is None:
        settings = get_settings()
        config = RAGConfig(
            data_path=settings.rag_data_path,
            index_path=settings.rag_index_path,
            chroma_persist_directory=settings.chroma_persist_directory,
            chroma_collection=settings.chroma_collection,
            embedding_model=settings.embedding_model,
            embedding_model_path=settings.embedding_model_path,
            embedding_device=settings.embedding_device,
            embedding_offline_mode=settings.embedding_offline_mode,
            default_top_k=settings.rag_default_top_k,
            default_mode=SearchMode(settings.rag_default_mode),
            context_max_length=settings.rag_context_max_length
        )
        _rag_engine = RAGEngine(config)
        await _rag_engine.initialize()
    
    return _rag_engine


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询字符串")
    mode: str = Field(default="hybrid", description="检索模式: fast, precise, hybrid")
    category: Optional[str] = Field(default=None, description="限定分类")
    top_k: int = Field(default=5, description="返回数量")
    score_threshold: float = Field(default=0.0, description="分数阈值")


class SearchResult(BaseModel):
    """搜索结果"""
    id: str
    name: str
    content: str
    category: str
    subcategory: Optional[str]
    score: float
    match_type: str
    source: str
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    query: str
    mode: str
    results: List[SearchResult]
    total: int
    context: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    initialized: bool
    vector_store: Dict[str, Any]
    index: Dict[str, Any]
    embedding: Dict[str, Any]


class IndexRequest(BaseModel):
    """索引请求"""
    category: Optional[str] = Field(default=None, description="指定分类")
    force_reindex: bool = Field(default=False, description="强制重新索引")
    batch_size: int = Field(default=50, description="批量大小")


class IndexResponse(BaseModel):
    """索引响应"""
    success: bool
    message: str
    stats: Dict[str, Any]


class AddDocumentRequest(BaseModel):
    """添加文档请求"""
    name: str = Field(..., description="文档名称")
    content: str = Field(..., description="文档内容")
    category: str = Field(..., description="分类")
    subcategory: Optional[str] = Field(default=None, description="子分类")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    aliases: Optional[List[str]] = Field(default=None, description="别名列表")


class AddDocumentResponse(BaseModel):
    """添加文档响应"""
    success: bool
    document_id: str
    message: str


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """
    搜索知识库
    
    - **fast**: 快速向量检索，适合语义搜索
    - **precise**: 精确关键词匹配，适合精确查询
    - **hybrid**: 混合检索，结合两种模式
    """
    try:
        engine = await get_rag_engine()
        
        mode = SearchMode(request.mode)
        
        results = await engine.search(
            query=request.query,
            mode=mode,
            category=request.category,
            top_k=request.top_k,
            score_threshold=request.score_threshold
        )
        
        search_results = [
            SearchResult(
                id=r.id,
                name=r.name,
                content=r.content,
                category=r.category,
                subcategory=r.subcategory,
                score=r.score,
                match_type=r.match_type,
                source=r.source,
                metadata=r.metadata
            )
            for r in results
        ]
        
        context = engine._retriever.format_results_for_context(
            results,
            engine.config.context_max_length
        ) if results else None
        
        return SearchResponse(
            success=True,
            query=request.query,
            mode=request.mode,
            results=search_results,
            total=len(search_results),
            context=context
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse)
async def search_knowledge_get(
    query: str = Query(..., description="查询字符串"),
    mode: str = Query("hybrid", description="检索模式"),
    category: Optional[str] = Query(None, description="限定分类"),
    top_k: int = Query(5, description="返回数量")
):
    """GET方式搜索知识库"""
    request = SearchRequest(
        query=query,
        mode=mode,
        category=category,
        top_k=top_k
    )
    return await search_knowledge(request)


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """获取RAG系统统计信息"""
    try:
        engine = await get_rag_engine()
        stats = await engine.get_stats()
        
        return StatsResponse(
            initialized=stats.get("initialized", False),
            vector_store=stats.get("vector_store", {}),
            index=stats.get("index", {}),
            embedding=stats.get("embedding", {})
        )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        engine = await get_rag_engine()
        result = await engine.health_check()
        return result
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }


@router.get("/categories")
async def get_categories():
    """获取所有分类"""
    try:
        engine = await get_rag_engine()
        categories = await engine.get_categories()
        return {
            "success": True,
            "categories": categories
        }
    except Exception as e:
        logger.error(f"获取分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category}/subcategories")
async def get_subcategories(category: str):
    """获取子分类"""
    try:
        engine = await get_rag_engine()
        subcategories = await engine.get_subcategories(category)
        return {
            "success": True,
            "category": category,
            "subcategories": subcategories
        }
    except Exception as e:
        logger.error(f"获取子分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=IndexResponse)
async def index_knowledge(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    索引知识库数据
    
    注意：大量数据索引可能需要较长时间，建议在后台执行
    """
    try:
        engine = await get_rag_engine()
        
        stats = await engine.index_knowledge_base(
            category=request.category,
            batch_size=request.batch_size,
            force_reindex=request.force_reindex
        )
        
        return IndexResponse(
            success=stats["errors"] == 0,
            message="索引完成" if stats["errors"] == 0 else "索引完成但有错误",
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"索引失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents", response_model=AddDocumentResponse)
async def add_document(request: AddDocumentRequest):
    """添加单个文档"""
    try:
        engine = await get_rag_engine()
        
        doc_id = await engine.add_document(
            name=request.name,
            content=request.content,
            category=request.category,
            subcategory=request.subcategory,
            metadata=request.metadata,
            aliases=request.aliases
        )
        
        return AddDocumentResponse(
            success=True,
            document_id=doc_id,
            message="文档添加成功"
        )
        
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    try:
        engine = await get_rag_engine()
        success = await engine.delete_document(doc_id)
        
        return {
            "success": success,
            "message": "文档删除成功" if success else "文档删除失败"
        }
        
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """获取单个文档"""
    try:
        engine = await get_rag_engine()
        result = await engine.get_document(doc_id)
        
        if result is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return {
            "success": True,
            "document": {
                "id": result.id,
                "name": result.name,
                "content": result.content,
                "category": result.category,
                "subcategory": result.subcategory,
                "score": result.score,
                "match_type": result.match_type,
                "metadata": result.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
