"""
知识库数据索引脚本
================
用于将知识库数据索引到向量数据库和精确索引中

使用方法:
    python index_knowledge.py                    # 索引所有数据
    python index_knowledge.py --category 图鉴    # 只索引特定分类
    python index_knowledge.py --force            # 强制重新索引
    python index_knowledge.py --test             # 测试检索功能
    python index_knowledge.py --interactive      # 交互式测试
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.rag import RAGEngine, RAGConfig, SearchMode
from src.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def index_knowledge(
    category: str = None,
    force_reindex: bool = False,
    batch_size: int = 50
):
    """
    索引知识库数据
    
    Args:
        category: 指定分类，None表示全部
        force_reindex: 是否强制重新索引
        batch_size: 批量处理大小
    """
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
    
    engine = RAGEngine(config)
    
    logger.info("正在初始化RAG引擎...")
    if not await engine.initialize():
        logger.error("RAG引擎初始化失败")
        return False
    
    logger.info("RAG引擎初始化成功")
    
    logger.info("开始索引知识库数据...")
    if category:
        logger.info(f"指定分类: {category}")
    if force_reindex:
        logger.info("强制重新索引模式")
    
    stats = await engine.index_knowledge_base(
        category=category,
        batch_size=batch_size,
        force_reindex=force_reindex
    )
    
    logger.info(f"索引完成! 统计信息:")
    logger.info(f"  - 处理文档数: {stats['total_processed']}")
    logger.info(f"  - 向量索引数: {stats['vector_indexed']}")
    logger.info(f"  - 精确索引数: {stats['precise_indexed']}")
    logger.info(f"  - 错误数: {stats['errors']}")
    
    return stats['errors'] == 0


async def test_search(query: str, mode: str = "hybrid", top_k: int = 5):
    """
    测试检索功能
    
    Args:
        query: 查询字符串
        mode: 检索模式
        top_k: 返回数量
    """
    settings = get_settings()
    
    config = RAGConfig(
        data_path=settings.rag_data_path,
        index_path=settings.rag_index_path,
        chroma_persist_directory=settings.chroma_persist_directory,
        chroma_collection=settings.chroma_collection,
        embedding_model=settings.embedding_model,
        embedding_model_path=settings.embedding_model_path,
        embedding_device=settings.embedding_device,
        embedding_offline_mode=settings.embedding_offline_mode
    )
    
    engine = RAGEngine(config)
    
    logger.info("正在初始化RAG引擎...")
    if not await engine.initialize():
        logger.error("RAG引擎初始化失败")
        return
    
    search_mode = SearchMode(mode)
    logger.info(f"测试检索: '{query}' (模式: {mode})")
    
    results = await engine.search(
        query=query,
        mode=search_mode,
        top_k=top_k
    )
    
    logger.info(f"找到 {len(results)} 条结果:")
    for i, r in enumerate(results, 1):
        logger.info(f"\n--- 结果 {i} ---")
        logger.info(f"名称: {r.name}")
        logger.info(f"分类: {r.category}/{r.subcategory or 'N/A'}")
        logger.info(f"分数: {r.score:.4f}")
        logger.info(f"匹配类型: {r.match_type}")
        logger.info(f"内容预览: {r.content[:200]}...")


async def show_stats():
    """显示索引统计信息"""
    settings = get_settings()
    
    config = RAGConfig(
        data_path=settings.rag_data_path,
        index_path=settings.rag_index_path,
        chroma_persist_directory=settings.chroma_persist_directory,
        chroma_collection=settings.chroma_collection,
        embedding_model=settings.embedding_model,
        embedding_model_path=settings.embedding_model_path,
        embedding_device=settings.embedding_device,
        embedding_offline_mode=settings.embedding_offline_mode
    )
    
    engine = RAGEngine(config)
    
    if not await engine.initialize():
        logger.error("RAG引擎初始化失败")
        return
    
    stats = await engine.get_stats()
    
    logger.info("=== RAG系统统计信息 ===")
    logger.info(f"初始化状态: {stats['initialized']}")
    
    if 'vector_store' in stats:
        vs = stats['vector_store']
        logger.info(f"\n向量存储 (ChromaDB):")
        logger.info(f"  - 集合名称: {vs.get('name', 'N/A')}")
        logger.info(f"  - 向量数量: {vs.get('vectors_count', 0)}")
        logger.info(f"  - 向量维度: {vs.get('dimension', 'N/A')}")
        logger.info(f"  - 持久化目录: {vs.get('persist_directory', 'N/A')}")
    
    if 'index' in stats:
        idx = stats['index']
        logger.info(f"\n精确索引:")
        logger.info(f"  - 文档数量: {idx.get('total_documents', 0)}")
        logger.info(f"  - 关键词数量: {idx.get('total_keywords', 0)}")
        logger.info(f"  - 别名数量: {idx.get('aliases', 0)}")
        if 'categories' in idx:
            logger.info(f"  - 分类统计:")
            for cat, count in idx['categories'].items():
                logger.info(f"      {cat}: {count}")
    
    if 'embedding' in stats:
        emb = stats['embedding']
        logger.info(f"\n嵌入模型:")
        logger.info(f"  - 模型类型: {emb.get('model_type', 'N/A')}")
        logger.info(f"  - 模型名称: {emb.get('model_name', 'N/A')}")
        logger.info(f"  - 向量维度: {emb.get('dimension', 'N/A')}")
        logger.info(f"  - 缓存大小: {emb.get('cache_size', 0)}")


async def interactive_test():
    """交互式测试"""
    settings = get_settings()
    
    config = RAGConfig(
        data_path=settings.rag_data_path,
        index_path=settings.rag_index_path,
        chroma_persist_directory=settings.chroma_persist_directory,
        chroma_collection=settings.chroma_collection,
        embedding_model=settings.embedding_model,
        embedding_model_path=settings.embedding_model_path,
        embedding_device=settings.embedding_device,
        embedding_offline_mode=settings.embedding_offline_mode
    )
    
    engine = RAGEngine(config)
    
    logger.info("正在初始化RAG引擎...")
    if not await engine.initialize():
        logger.error("RAG引擎初始化失败")
        return
    
    logger.info("RAG引擎初始化成功")
    logger.info("输入查询进行测试，输入 'quit' 退出")
    logger.info("可用模式: fast, precise, hybrid")
    logger.info("命令格式: [mode:]query (例如: fast:琪亚娜)")
    print()
    
    while True:
        try:
            user_input = input("查询> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            mode = SearchMode.HYBRID
            if ':' in user_input:
                mode_str, query = user_input.split(':', 1)
                mode_str = mode_str.strip().lower()
                if mode_str in ['fast', 'precise', 'hybrid']:
                    mode = SearchMode(mode_str)
                    user_input = query.strip()
            
            results = await engine.search(query=user_input, mode=mode, top_k=5)
            
            print(f"\n找到 {len(results)} 条结果 (模式: {mode.value}):\n")
            
            for i, r in enumerate(results, 1):
                print(f"【{i}】{r.name} ({r.category}/{r.subcategory or '-'})")
                print(f"    分数: {r.score:.4f} | 匹配: {r.match_type}")
                print(f"    内容: {r.content[:150]}...")
                print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"查询失败: {e}")
    
    logger.info("退出交互式测试")


def main():
    parser = argparse.ArgumentParser(description="知识库数据索引工具")
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="指定要索引的分类"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新索引"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="批量处理大小"
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="测试检索功能，指定查询字符串"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="hybrid",
        choices=["fast", "precise", "hybrid"],
        help="检索模式"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="返回结果数量"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示索引统计信息"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互式测试模式"
    )
    
    args = parser.parse_args()
    
    if args.stats:
        asyncio.run(show_stats())
    elif args.test:
        asyncio.run(test_search(args.test, args.mode, args.top_k))
    elif args.interactive:
        asyncio.run(interactive_test())
    else:
        success = asyncio.run(index_knowledge(
            category=args.category,
            force_reindex=args.force,
            batch_size=args.batch_size
        ))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
