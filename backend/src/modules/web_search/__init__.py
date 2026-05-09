"""
联网搜索模块
提供实时网络搜索功能，补充本地知识库的不足
"""

from .web_searcher import WebSearcher, SearchResult, SearchEngine

__all__ = ["WebSearcher", "SearchResult", "SearchEngine"]