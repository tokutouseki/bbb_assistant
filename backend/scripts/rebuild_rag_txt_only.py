"""
RAG向量库重置与重建脚本
=======================
功能：
1. 重置现有的向量数据库（ChromaDB）和精确索引
2. 仅索引指定目录下的txt文件内容

目标目录：
- 档案/故事/*.txt
- 档案/角色/*.txt
- 第二部探索指南/成就/*.txt
- 第二部探索指南/道具/*.txt
- 第二部探索指南/收藏品/*.txt
- 第二部探索指南/星之环/*.txt
- 后崩坏书2专章/成就/*.txt
- 后崩坏书2专章/怪物/*.txt
- 后崩坏书2专章/角色/*.txt
- 后崩坏书2专章/文件/*.txt
- 后崩坏书2专章/月之环系统/*.txt
- 世界观/**/*.txt
- 图鉴/**/*.txt
- 往世乐土/**/*.txt
- 主线故事/**/*.txt
"""

import asyncio
import sys
import shutil
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.rag import RAGEngine, RAGConfig, SearchMode
from src.modules.rag.data_processor import KnowledgeDocument
from src.modules.rag.index_manager import IndexDocument
from src.modules.rag.vector_store import VectorDocument
from src.config.settings import get_settings


# 需要索引的txt文件路径配置（相对于data目录）
TARGET_DIRS = [
    ("档案/故事", "档案", "故事"),
    ("档案/角色", "档案", "角色"),
    ("第二部探索指南/成就", "第二部探索指南", "成就"),
    ("第二部探索指南/道具", "第二部探索指南", "道具"),
    ("第二部探索指南/收藏品", "第二部探索指南", "收藏品"),
    ("第二部探索指南/星之环", "第二部探索指南", "星之环"),
    ("后崩坏书2专章/成就", "后崩坏书2专章", "成就"),
    ("后崩坏书2专章/怪物", "后崩坏书2专章", "怪物"),
    ("后崩坏书2专章/角色", "后崩坏书2专章", "角色"),
    ("后崩坏书2专章/文件", "后崩坏书2专章", "文件"),
    ("后崩坏书2专章/月之环系统", "后崩坏书2专章", "月之环系统"),
    ("世界观", "世界观", None),
    ("图鉴", "图鉴", None),  # 包含所有子目录
    ("往世乐土", "往世乐土", None),  # 包含所有子目录
    ("主线故事", "主线故事", None),  # 包含所有子目录
]


def reset_vector_database(settings):
    """重置向量数据库和索引"""
    print("=" * 60)
    print("步骤 1: 重置现有向量数据库")
    print("=" * 60)
    
    chroma_dir = Path(settings.chroma_persist_directory)
    index_dir = Path(settings.rag_index_path)
    
    if chroma_dir.exists():
        print(f"  删除ChromaDB目录: {chroma_dir}")
        shutil.rmtree(chroma_dir)
        print("  ChromaDB目录已删除")
    else:
        print(f"  ChromaDB目录不存在: {chroma_dir}")
    
    if index_dir.exists():
        print(f"  删除索引目录: {index_dir}")
        shutil.rmtree(index_dir)
        print("  索引目录已删除")
    else:
        print(f"  索引目录不存在: {index_dir}")
    
    print("  重置完成\n")


async def load_txt_files(data_path: Path) -> list:
    """加载所有目标txt文件，返回KnowledgeDocument列表"""
    print("=" * 60)
    print("步骤 2: 加载txt文件内容")
    print("=" * 60)
    
    documents = []
    total_files = 0
    processed_files = 0
    error_files = 0
    
    for dir_path, category, subcategory in TARGET_DIRS:
        full_dir = data_path / dir_path
        
        if not full_dir.exists():
            print(f"  警告: 目录不存在 - {full_dir}")
            continue
        
        # 根据subcategory决定搜索方式
        if subcategory:
            # 精确子目录
            target_dir = full_dir
            txt_files = list(target_dir.glob("*.txt"))
        else:
            # 递归搜索所有子目录
            txt_files = list(full_dir.rglob("*.txt"))
        
        if not txt_files:
            print(f"  目录 {dir_path} 下未找到txt文件")
            continue
        
        total_files += len(txt_files)
        print(f"\n  处理目录: {dir_path} ({len(txt_files)} 个txt文件)")
        
        for txt_file in txt_files:
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                
                if not content:
                    print(f"    跳过空文件: {txt_file.name}")
                    continue
                
                # 从文件名提取名称（去掉.txt后缀）
                name = txt_file.stem
                
                # 计算实际子目录
                if subcategory:
                    actual_subcat = subcategory
                else:
                    # 对于递归目录，获取相对于主目录的父路径
                    try:
                        relative = txt_file.parent.relative_to(full_dir)
                        actual_subcat = str(relative) if str(relative) != "." else ""
                    except ValueError:
                        actual_subcat = ""
                
                doc_id = hashlib_doc_id(name, category, actual_subcat)
                
                doc = KnowledgeDocument(
                    id=doc_id,
                    name=name,
                    content=content,
                    category=category,
                    subcategory=actual_subcat if actual_subcat else None,
                    source_file=str(txt_file),
                    metadata={"file_path": str(txt_file)},
                    aliases=[]
                )
                
                documents.append(doc)
                processed_files += 1
                
            except Exception as e:
                error_files += 1
                print(f"    错误: 读取文件失败 {txt_file.name}: {e}")
    
    print(f"\n  统计:")
    print(f"    找到txt文件总数: {total_files}")
    print(f"    成功处理: {processed_files}")
    print(f"    失败: {error_files}")
    print(f"    有效文档数: {len(documents)}")
    
    return documents


def hashlib_doc_id(name: str, category: str, subcategory: str = None) -> str:
    """生成文档ID"""
    import hashlib
    key = f"{category}/{subcategory}/{name}" if subcategory else f"{category}/{name}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


async def rebuild_rag_index(engine: RAGEngine, documents: list, batch_size: int = 50):
    """重建RAG索引"""
    print("\n" + "=" * 60)
    print("步骤 3: 重建RAG索引")
    print("=" * 60)
    
    stats = {
        "total_processed": 0,
        "vector_indexed": 0,
        "precise_indexed": 0,
        "errors": 0
    }
    
    total_docs = len(documents)
    
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i + batch_size]
        
        # 批量生成embeddings
        texts_to_embed = [doc.content for doc in batch]
        embeddings = await engine._embedding_service.embed_batch(texts_to_embed)
        
        index_docs = []
        vector_docs = []
        
        for doc, embedding in zip(batch, embeddings):
            # 创建索引文档
            index_doc = IndexDocument(
                id=doc.id,
                name=doc.name,
                content=doc.content,
                category=doc.category,
                subcategory=doc.subcategory,
                keywords=[],
                metadata=doc.metadata,
                aliases=doc.aliases
            )
            index_docs.append(index_doc)
            
            # 创建向量文档
            vector_doc = VectorDocument(
                id=doc.id,
                vector=embedding,
                content=doc.content,
                metadata={
                    "name": doc.name,
                    "category": doc.category,
                    "subcategory": doc.subcategory,
                    "source_file": doc.source_file,
                    **doc.metadata
                }
            )
            vector_docs.append(vector_doc)
        
        # 批量添加到索引和向量库
        await engine._index_manager.add_documents(index_docs)
        stats["precise_indexed"] += len(index_docs)
        
        await engine._vector_store.upsert_vectors(vector_docs)
        stats["vector_indexed"] += len(vector_docs)
        
        stats["total_processed"] += len(batch)
        
        progress = stats["total_processed"] / total_docs * 100
        print(f"  进度: {stats['total_processed']}/{total_docs} ({progress:.1f}%)")
    
    # 保存索引
    await engine._index_manager.save_index()
    
    print(f"\n  索引完成统计:")
    print(f"    总处理文档: {stats['total_processed']}")
    print(f"    向量索引: {stats['vector_indexed']}")
    print(f"    精确索引: {stats['precise_indexed']}")
    print(f"    错误: {stats['errors']}")
    
    return stats


async def main():
    """主函数"""
    print("=" * 60)
    print("RAG向量库重置与重建工具")
    print("=" * 60)
    print()
    
    settings = get_settings()
    
    # 步骤1: 重置向量数据库
    reset_vector_database(settings)
    
    # 步骤2: 创建并初始化RAG引擎
    print("=" * 60)
    print("步骤 1.5: 初始化RAG引擎")
    print("=" * 60)
    
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
        context_max_length=settings.rag_context_max_length,
    )
    
    engine = RAGEngine(config)
    
    print("  正在初始化RAG引擎...")
    if not await engine.initialize():
        print("  错误: RAG引擎初始化失败!")
        return False
    print("  RAG引擎初始化成功\n")
    
    # 步骤3: 加载txt文件
    data_path = Path(settings.rag_data_path)
    documents = await load_txt_files(data_path)
    
    if not documents:
        print("\n警告: 未找到任何txt文档，退出")
        return False
    
    # 步骤4: 重建索引
    stats = await rebuild_rag_index(engine, documents)
    
    # 步骤5: 验证
    print("\n" + "=" * 60)
    print("步骤 4: 验证重建结果")
    print("=" * 60)
    
    health = await engine.health_check()
    print(f"  系统健康: {health['healthy']}")
    for component, status in health['components'].items():
        print(f"    - {component}: {status}")
    
    stats_info = await engine.get_stats()
    print(f"\n  系统统计:")
    print(f"    向量库文档数: {stats_info.get('vector_store', {}).get('vectors_count', 0)}")
    print(f"    精确索引文档数: {stats_info.get('index', {}).get('total_documents', 0)}")
    print(f"    嵌入模型: {stats_info.get('embedding', {}).get('model_name', 'N/A')}")
    
    # 快速测试搜索
    print("\n  快速测试搜索...")
    test_queries = ["琪亚娜", "武器", "成就"]
    for query in test_queries:
        results = await engine.search(query, mode=SearchMode.HYBRID, top_k=2)
        print(f"    搜索 '{query}': 找到 {len(results)} 条结果")
        if results:
            print(f"      - {results[0].name} ({results[0].category})")
    
    print("\n" + "=" * 60)
    print("RAG向量库重置与重建完成!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n所有操作成功完成!")
        sys.exit(0)
    else:
        print("\n操作失败!")
        sys.exit(1)
