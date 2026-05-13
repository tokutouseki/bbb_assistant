#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联网搜索模块
提供实时网络搜索功能，支持Google搜索和DuckDuckGo搜索
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SearchEngine(Enum):
    """搜索引擎类型"""
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BING_CHINA = "bing_china"  # 必应中国 (cn.bing.com, 国内可访问)
    BING = "bing"  # 国际版Bing
    MIYOUSHE = "miyoushe"  # 米游社搜索
    HONKAI_OFFICIAL = "honkai_official"  # 崩坏3官网


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    snippet: str
    source: str
    content: str = ""
    relevance: float = 0.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class WebSearcher:
    """联网搜索器"""
    
    def __init__(
        self,
        engine: SearchEngine = SearchEngine.GOOGLE,
        timeout: int = 15,
        max_results: int = 10,
        enable_content_fetch: bool = True
    ):
        """
        初始化搜索器
        
        Args:
            engine: 搜索引擎
            timeout: 超时时间（秒）
            max_results: 最大结果数
            enable_content_fetch: 是否获取页面内容
        """
        self.engine = engine
        self.timeout = timeout
        self.max_results = max_results
        self.enable_content_fetch = enable_content_fetch
        
        # 用户代理
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        logger.info(f"联网搜索器初始化完成，引擎: {engine.value}")
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        logger.info(f"执行搜索: '{query}'，引擎: {self.engine.value}")
        
        try:
            if self.engine == SearchEngine.GOOGLE:
                results = self._search_google(query, **kwargs)
            elif self.engine == SearchEngine.DUCKDUCKGO:
                results = self._search_duckduckgo(query, **kwargs)
            elif self.engine == SearchEngine.BING_CHINA:
                results = self._search_bing_china(query, **kwargs)
            elif self.engine == SearchEngine.MIYOUSHE:
                results = self._search_miyoushe(query, **kwargs)
            elif self.engine == SearchEngine.HONKAI_OFFICIAL:
                results = self._search_honkai_official(query, **kwargs)
            else:
                raise ValueError(f"不支持的搜索引擎: {self.engine}")
            
            # 获取页面内容（如果需要）
            if self.enable_content_fetch:
                for result in results:
                    try:
                        content = self._fetch_page_content(result.url)
                        result.content = content[:5000]  # 限制内容长度
                    except Exception as e:
                        logger.warning(f"获取页面内容失败 {result.url}: {e}")
            
            logger.info(f"搜索完成，找到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise
    
    def _search_google(self, query: str, **kwargs) -> List[SearchResult]:
        """使用Google搜索"""
        try:
            # 尝试使用googlesearch-python库
            from googlesearch import search as google_search
            
            results = []
            search_results = google_search(
                query,
                num_results=self.max_results,
                advanced=True,
                timeout=self.timeout
            )
            
            for i, item in enumerate(search_results):
                result = SearchResult(
                    title=item.title or "",
                    url=item.url or "",
                    snippet=item.description or "",
                    source="google",
                    relevance=1.0 - (i * 0.1)  # 简单相关性评分
                )
                results.append(result)
            
            return results
            
        except ImportError:
            logger.warning("googlesearch-python不可用")
            raise
    
    def _search_duckduckgo(self, query: str, **kwargs) -> List[SearchResult]:
        """使用DuckDuckGo搜索"""
        try:
            from ddgs import DDGS

            results = []
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query,
                    max_results=self.max_results,
                    safesearch='moderate'
                )

                for i, item in enumerate(search_results):
                    result = SearchResult(
                        title=item.get('title', ''),
                        url=item.get('href', ''),
                        snippet=item.get('body', ''),
                        source="duckduckgo",
                        relevance=1.0 - (i * 0.1)
                    )
                    results.append(result)

            return results

        except ImportError:
            logger.warning("ddgs库不可用")
            raise
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
            raise

    def _search_bing_china(self, query: str, **kwargs) -> List[SearchResult]:
        """使用必应中国搜索 (cn.bing.com, 国内可访问)

        ensearch=1 是关键参数：不加此参数时 Bing 中文分词会把"崩坏3"
        拆成"崩"单独匹配，导致返回词典释义和星穹铁道。加上后启用增强搜索，
        正确识别完整词组。
        """
        headers = {'User-Agent': self.user_agent}
        params = {'q': query, 'count': min(self.max_results, 15), 'ensearch': '1'}
        response = requests.get(
            'https://cn.bing.com/search',
            headers=headers,
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        for item in soup.select('li.b_algo')[:self.max_results]:
            title_elem = item.select_one('h2 a')
            if not title_elem:
                continue
            snippet_elem = item.select_one('.b_caption p, .b_lineclamp2, .b_algoSlug')
            result = SearchResult(
                title=title_elem.get_text(strip=True),
                url=title_elem.get('href', ''),
                snippet=snippet_elem.get_text(strip=True) if snippet_elem else '',
                source="bing_china",
                relevance=1.0 - (len(results) * 0.1)
            )
            results.append(result)

        logger.info(f"必应中国搜索完成: '{query}' -> {len(results)} 条结果")
        return results

    def _search_miyoushe(self, query: str, **kwargs) -> List[SearchResult]:
        """使用米游社搜索"""
        try:
            from urllib.parse import quote
            
            miyoushe_url = f"https://www.miyoushe.com/bh3/search?keyword={quote(query)}"
            
            results = []
            results.append(SearchResult(
                title=f"米游社搜索: {query}",
                url=miyoushe_url,
                snippet=f"米游社崩坏3社区搜索结果。建议使用浏览器访问该链接查看详细内容。",
                source="miyoushe",
                relevance=1.0
            ))
            
            logger.info(f"米游社搜索链接已生成: {miyoushe_url}")
            return results
            
        except Exception as e:
            logger.error(f"米游社搜索失败: {e}")
            raise
    
    def _search_honkai_official(self, query: str, **kwargs) -> List[SearchResult]:
        """使用崩坏3官网搜索"""
        try:
            from urllib.parse import quote
            
            official_url = f"https://bh3.mihoyo.com/main"
            
            results = []
            results.append(SearchResult(
                title=f"崩坏3官网",
                url=official_url,
                snippet="崩坏3官方网站，可查看最新版本信息、活动公告、游戏资讯等内容。",
                source="honkai_official",
                relevance=1.0
            ))
            
            logger.info(f"崩坏3官网链接已生成: {official_url}")
            return results
            
        except Exception as e:
            logger.error(f"崩坏3官网搜索失败: {e}")
            raise
    
    def _fetch_page_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text = soup.get_text(separator='\n', strip=True)

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text

        except requests.HTTPError as e:
            # 403/404 等 HTTP 错误很常见，很多网站反爬，不影响搜索结果使用
            logger.debug(f"获取页面内容 HTTP 错误 {url}: {e}")
            return ""
        except Exception as e:
            logger.debug(f"获取页面内容失败 {url}: {e}")
            return ""
    

    def search_with_context(
        self,
        query: str,
        context: str = "",
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        带上下文的搜索
        
        Args:
            query: 搜索查询
            context: 上下文信息
            include_context: 是否在结果中包含上下文
            
        Returns:
            包含搜索结果的字典
        """
        # 如果有上下文，优化查询
        if context and include_context:
            enhanced_query = f"{query} {context}"
        else:
            enhanced_query = query
        
        # 执行搜索
        results = self.search(enhanced_query)
        
        # 格式化结果
        formatted_results = []
        for result in results:
            formatted_result = {
                'title': result.title,
                'url': result.url,
                'snippet': result.snippet,
                'source': result.source,
                'relevance': result.relevance
            }
            
            if result.content:
                formatted_result['content'] = result.content[:1000]  # 限制长度
            
            formatted_results.append(formatted_result)
        
        # 构建响应
        response = {
            'query': query,
            'enhanced_query': enhanced_query if enhanced_query != query else None,
            'context_used': context if include_context else None,
            'total_results': len(results),
            'results': formatted_results,
            'timestamp': time.time()
        }
        
        return response
    
    def extract_answers(self, query: str, results: List[SearchResult]) -> str:
        """
        从搜索结果中提取答案
        
        Args:
            query: 原始查询
            results: 搜索结果列表
            
        Returns:
            提取的答案文本
        """
        if not results:
            return f"未找到关于'{query}'的搜索结果。"
        
        # 合并相关内容
        answer_parts = []
        
        for i, result in enumerate(results[:3]):  # 只使用前3个结果
            if result.content:
                content = result.content
            elif result.snippet:
                content = result.snippet
            else:
                continue
            
            # 提取与查询相关的部分
            relevant_part = self._extract_relevant_part(query, content)
            if relevant_part:
                answer_parts.append(f"【来源 {i+1}】{relevant_part}")
        
        if answer_parts:
            answer = "\n\n".join(answer_parts)
            answer += f"\n\n以上信息来自网络搜索，共参考了 {len(answer_parts)} 个来源。"
        else:
            answer = f"已搜索到相关信息，但未能提取出直接答案。建议查看原始链接：{results[0].url}"
        
        return answer
    
    def _extract_relevant_part(self, query: str, content: str) -> str:
        """提取相关内容部分"""
        # 简单实现：查找包含查询关键词的句子
        query_words = query.lower().split()
        
        sentences = re.split(r'[.!?。！？]+', content)
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # 计算匹配度
            matches = sum(1 for word in query_words if word in sentence_lower)
            if matches > 0:
                relevant_sentences.append(sentence.strip())
        
        # 取最相关的前3个句子
        if relevant_sentences:
            return ' '.join(relevant_sentences[:3])
        
        # 如果没有匹配的句子，返回开头部分
        return content[:200] + "..." if len(content) > 200 else content
    
    @classmethod
    def test_search(cls, query: str = "崩坏3薪炎之律者"):
        """测试搜索功能"""
        print(f"测试搜索: '{query}'")
        print("=" * 60)
        
        # 测试Google搜索
        print("\n1. Google搜索:")
        try:
            google_searcher = cls(engine=SearchEngine.GOOGLE, max_results=3)
            results = google_searcher.search(query)
            
            for i, result in enumerate(results):
                print(f"\n结果 {i+1}:")
                print(f"  标题: {result.title}")
                print(f"  URL: {result.url}")
                print(f"  摘要: {result.snippet[:100]}...")
                if result.content:
                    print(f"  内容预览: {result.content[:150]}...")
        except Exception as e:
            print(f"  Google搜索失败: {e}")
        
        # 测试DuckDuckGo搜索
        print("\n2. DuckDuckGo搜索:")
        try:
            ddg_searcher = cls(engine=SearchEngine.DUCKDUCKGO, max_results=3)
            results = ddg_searcher.search(query)
            
            for i, result in enumerate(results):
                print(f"\n结果 {i+1}:")
                print(f"  标题: {result.title}")
                print(f"  URL: {result.url}")
                print(f"  摘要: {result.snippet[:100]}...")
                if result.content:
                    print(f"  内容预览: {result.content[:150]}...")
        except Exception as e:
            print(f"  DuckDuckGo搜索失败: {e}")
        
        # 测试米游社搜索
        print("\n3. 米游社搜索:")
        try:
            miyoushe_searcher = cls(engine=SearchEngine.MIYOUSHE)
            results = miyoushe_searcher.search(query)
            
            for i, result in enumerate(results):
                print(f"\n结果 {i+1}:")
                print(f"  标题: {result.title}")
                print(f"  URL: {result.url}")
                print(f"  摘要: {result.snippet}")
        except Exception as e:
            print(f"  米游社搜索失败: {e}")
        
        # 测试崩坏3官网搜索
        print("\n4. 崩坏3官网搜索:")
        try:
            official_searcher = cls(engine=SearchEngine.HONKAI_OFFICIAL)
            results = official_searcher.search(query)
            
            for i, result in enumerate(results):
                print(f"\n结果 {i+1}:")
                print(f"  标题: {result.title}")
                print(f"  URL: {result.url}")
                print(f"  摘要: {result.snippet}")
        except Exception as e:
            print(f"  崩坏3官网搜索失败: {e}")
        
        print("\n" + "=" * 60)
        print("搜索测试完成")


def create_web_search_tool():
    """创建用于LLM的搜索工具"""
    def search_tool(query: str, context: str = "") -> str:
        """
        网络搜索工具
        
        Args:
            query: 搜索查询
            context: 上下文信息
            
        Returns:
            搜索结果摘要
        """
        searcher = WebSearcher(engine=SearchEngine.BING_CHINA)
        
        try:
            # 执行搜索
            response = searcher.search_with_context(query, context)
            results = response['results']
            
            if not results:
                return "未找到相关搜索结果。"
            
            # 提取答案
            search_results = []
            for r in results:
                result = SearchResult(
                    title=r['title'],
                    url=r['url'],
                    snippet=r['snippet'],
                    source=r['source'],
                    relevance=r['relevance']
                )
                search_results.append(result)
            
            answer = searcher.extract_answers(query, search_results)
            return answer
            
        except Exception as e:
            return f"搜索过程中发生错误: {str(e)}"
    
    return search_tool


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试搜索
    WebSearcher.test_search("崩坏3薪炎之律者攻击方式")