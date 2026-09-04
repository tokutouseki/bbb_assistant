"""
联网搜索模块
提供实时网络搜索功能，补充本地知识库的不足

搜索架构:
    SearchOrchestrator (多源协调器)
    ├── BilibiliSourceAgent  → BilibiliExplorer (名字链条)
    ├── _BaiduSourceAgent    → WebSearcher (百度搜索)
    ├── _RagSourceAgent      → RAGEngine (知识库)
    ├── MiyousheSourceAgent  → 米游社编号字典 (阶段3, 待实现)
    └── MoegirlSourceAgent   → 萌娘百科 Playwright (阶段4, 待实现)
"""

from .web_searcher import WebSearcher, SearchResult, SearchEngine
from .wiki_explorer import BilibiliExplorer
from .moegirl_explorer import MoegirlExplorer
from .miyoushe_explorer import MiyousheExplorer, MiyousheIdDict, get_id_dict
from .search_orchestrator import (
    SearchOrchestrator,
    SourceAgent,
    SourceResult,
    DeepSearchResult,
    BilibiliSourceAgent,
    MoegirlSourceAgent,
    MiyousheSourceAgent,
    deep_search,
    get_orchestrator,
)

__all__ = [
    "WebSearcher", "SearchResult", "SearchEngine",
    "BilibiliExplorer",
    "MoegirlExplorer",
    "MiyousheExplorer",
    "MiyousheIdDict",
    "get_id_dict",
    "SearchOrchestrator",
    "SourceAgent",
    "SourceResult",
    "DeepSearchResult",
    "BilibiliSourceAgent",
    "MoegirlSourceAgent",
    "MiyousheSourceAgent",
    "deep_search",
    "get_orchestrator",
]