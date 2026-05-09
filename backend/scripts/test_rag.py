"""
RAG系统测试脚本
==============
快速测试RAG系统的各项功能
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.rag import RAGEngine, RAGConfig, SearchMode
from src.config.settings import get_settings


async def test_rag_system():
    """测试RAG系统"""
    print("=" * 60)
    print("RAG系统测试")
    print("=" * 60)
    
    settings = get_settings()
    
    config = RAGConfig(
        data_path=settings.rag_data_path,
        chroma_persist_directory=settings.chroma_persist_directory,
        chroma_collection=settings.chroma_collection,
        embedding_model=settings.embedding_model,
        embedding_model_path=settings.embedding_model_path,
        embedding_device=settings.embedding_device,
        embedding_offline_mode=settings.embedding_offline_mode
    )
    
    engine = RAGEngine(config)
    
    print("\n[1] 初始化RAG引擎...")
    if not await engine.initialize():
        print("❌ 初始化失败")
        return False
    print("✅ 初始化成功")
    
    print("\n[2] 获取系统统计信息...")
    stats = await engine.get_stats()
    print(f"   初始化状态: {stats['initialized']}")
    if 'vector_store' in stats:
        vs = stats['vector_store']
        print(f"   向量数量: {vs.get('vectors_count', 0)}")
    if 'index' in stats:
        idx = stats['index']
        print(f"   文档数量: {idx.get('total_documents', 0)}")
    
    print("\n[3] 测试快速检索模式...")
    results = await engine.search("炽翎", mode=SearchMode.FAST, top_k=3)
    print(f"   找到 {len(results)} 条结果")
    for i, r in enumerate(results[:2], 1):
        print(f"   [{i}] {r.name} ({r.category}) - 分数: {r.score:.4f}")
    
    print("\n[4] 测试精确检索模式...")
    results = await engine.search("琪亚娜", mode=SearchMode.PRECISE, top_k=3)
    print(f"   找到 {len(results)} 条结果")
    for i, r in enumerate(results[:2], 1):
        print(f"   [{i}] {r.name} ({r.category}) - 匹配: {r.match_type}")
    
    print("\n[5] 测试混合检索模式...")
    results = await engine.search("如何培养炽翎", mode=SearchMode.HYBRID, top_k=3)
    print(f"   找到 {len(results)} 条结果")
    for i, r in enumerate(results[:2], 1):
        print(f"   [{i}] {r.name} ({r.category}) - 分数: {r.score:.4f}")
    
    print("\n[6] 测试分类过滤...")
    results = await engine.search("武器", mode=SearchMode.PRECISE, category="图鉴", top_k=5)
    print(f"   找到 {len(results)} 条结果")
    categories = set(r.subcategory for r in results if r.subcategory)
    print(f"   子分类: {categories}")
    
    print("\n[7] 测试上下文生成...")
    context = await engine.retrieve("炽翎的技能和配装", top_k=3)
    print(f"   上下文长度: {len(context)} 字符")
    print(f"   预览: {context[:200]}...")
    
    print("\n[8] 测试健康检查...")
    health = await engine.health_check()
    print(f"   系统健康: {health['healthy']}")
    for component, status in health['components'].items():
        print(f"   - {component}: {status}")
    
    print("\n" + "=" * 60)
    print("✅ RAG系统测试完成!")
    print("=" * 60)
    
    return True


async def interactive_demo():
    """交互式演示"""
    print("=" * 60)
    print("RAG系统交互式演示")
    print("=" * 60)
    
    settings = get_settings()
    
    config = RAGConfig(
        data_path=settings.rag_data_path,
        chroma_persist_directory=settings.chroma_persist_directory,
        chroma_collection=settings.chroma_collection,
        embedding_model_path=settings.embedding_model_path,
        embedding_offline_mode=settings.embedding_offline_mode
    )
    
    engine = RAGEngine(config)
    
    print("\n初始化RAG引擎...")
    if not await engine.initialize():
        print("初始化失败")
        return
    
    print("初始化成功!")
    print("\n输入查询进行测试，输入 'quit' 退出")
    print("可用模式: fast, precise, hybrid")
    print("命令格式: [mode:]query (例如: fast:琪亚娜)")
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
            print(f"查询失败: {e}")
    
    print("\n退出交互式演示")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG系统测试")
    parser.add_argument("--interactive", action="store_true", help="交互式演示模式")
    
    args = parser.parse_args()
    
    if args.interactive:
        asyncio.run(interactive_demo())
    else:
        asyncio.run(test_rag_system())
