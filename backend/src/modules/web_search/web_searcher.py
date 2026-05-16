#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联网搜索模块
百度 (requests+Session) → Playwright 真实浏览器 两级回退
支持游戏相关内容过滤和页面内容抓取
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
    BAIDU = "baidu"
    BING = "bing"
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BING_CHINA = "bing_china"  # 保留兼容，映射到 BING
    MIYOUSHE = "miyoushe"
    HONKAI_OFFICIAL = "honkai_official"


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
    """联网搜索器 — 百度主引擎，Playwright 真实浏览器兜底"""

    _IRRELEVANT_PATTERNS = [
        '星穹铁道', 'star rail', 'hsr',
        '原神', 'genshin', '绝区零', 'zenless',
        '未定事件簿', 'tears of themis',
    ]

    _HOMEPAGE_URLS = {
        'https://www.hoyoverse.com/zh-cn', 'https://www.hoyoverse.com',
        'https://www.mihoyo.com', 'https://sr.mihoyo.com',
        'https://www.bh3.com', 'https://bh3.mihoyo.com',
    }

    def __init__(
        self,
        engine: SearchEngine = SearchEngine.BAIDU,
        timeout: int = 15,
        max_results: int = 10,
        enable_content_fetch: bool = True
    ):
        self.engine = engine
        self.timeout = timeout
        self.max_results = max_results
        self.enable_content_fetch = enable_content_fetch

        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        logger.info(f"联网搜索器初始化完成，引擎: {engine.value}")

    # ── 主搜索接口 ──────────────────────────────────────────────

    def search(self, query: str, **kwargs) -> List[SearchResult]:
        logger.info(f"执行搜索: '{query}'，引擎: {self.engine.value}")

        try:
            engine = self.engine
            if engine == SearchEngine.BING_CHINA:
                engine = SearchEngine.BING

            if engine in (SearchEngine.BAIDU, SearchEngine.BING, SearchEngine.BING_CHINA):
                results = self._search_baidu_direct(query, **kwargs)
            elif engine == SearchEngine.DUCKDUCKGO:
                results = self._search_duckduckgo(query, **kwargs)
            elif engine == SearchEngine.MIYOUSHE:
                results = self._search_miyoushe(query, **kwargs)
            elif engine == SearchEngine.HONKAI_OFFICIAL:
                results = self._search_honkai_official(query, **kwargs)
            else:
                raise ValueError(f"不支持的搜索引擎: {self.engine}")

            if self.enable_content_fetch:
                for result in results:
                    try:
                        content = self._fetch_page_requests(result.url)
                        result.content = content[:100000]
                    except Exception as e:
                        logger.warning(f"获取页面内容失败 {result.url}: {e}")

            logger.info(f"搜索完成，找到 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise

    def search_with_fallback(self, query: str, **kwargs) -> List[SearchResult]:
        """两级回退搜索: 百度 (requests) → Playwright 真实浏览器"""
        original = self.engine
        try:
            # 第一级: 百度 (requests + Session/Cookie)
            try:
                self.engine = SearchEngine.BAIDU
                results = self.search(query, **kwargs)
                if results:
                    return results
                logger.warning("百度返回0条结果，回退到Playwright浏览器")
            except Exception as e:
                logger.warning(f"百度搜索失败: {e}，回退到Playwright浏览器")

            # 第二级: Playwright 真实浏览器 (兜底，绕过所有反爬)
            try:
                results = self._search_playwright(query, **kwargs)
                if results:
                    return results
            except Exception as e:
                logger.error(f"Playwright搜索也失败了: {e}")

            return []
        finally:
            self.engine = original

    # ── 百度搜索 (直接 HTTP 请求) ──────────────────────────────

    # 短角色名(<=2字)在搜索引擎中易被拆成单字 → 追加"崩坏3"消歧
    _SHORT_NAMES = ['芽衣', '希儿', '符华', '樱', '卡莲', '姬子', '罗莎莉亚', '莉莉娅']

    def _disambiguate_query(self, query: str) -> str:
        """短角色名追加游戏上下文，避免被搜索引擎拆成单字"""
        has_game = any(kw in query.lower() for kw in ['崩坏3', '崩坏三', 'bh3', 'honkai'])
        if has_game:
            return query
        if any(name in query for name in self._SHORT_NAMES):
            return f'崩坏3 {query}'
        return query

    def _search_baidu_direct(self, query: str, **kwargs) -> List[SearchResult]:
        """直接 HTTP 请求 baidu.com，解析 HTML 结果页

        使用 Session + Cookie 机制规避百度的安全验证:
        1. 先访问首页获取 BAIDUID 等 Cookie
        2. 带着 Cookie 发起搜索请求
        3. 检测安全验证页面并自动重试
        """
        query = self._disambiguate_query(query)
        params = {'wd': query, 'rn': min(self.max_results, 15)}

        session = self._get_baidu_session()

        try:
            response = session.get(
                'https://www.baidu.com/s',
                params=params,
                headers={'Referer': 'https://www.baidu.com/'},
                timeout=self.timeout
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"百度HTTP请求失败: {e}")
            raise

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检测安全验证页面
        title_tag = soup.select_one('title')
        if title_tag and '安全验证' in (title_tag.get_text() or ''):
            logger.warning("百度返回安全验证页面，刷新Cookie后重试")
            self._baidu_session = None
            session = self._get_baidu_session()
            response = session.get(
                'https://www.baidu.com/s',
                params=params,
                headers={'Referer': 'https://www.baidu.com/'},
                timeout=self.timeout
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

        results = []

        for item in soup.select('div.c-container'):
            h3_a = item.select_one('h3 a')
            if not h3_a:
                continue
            title = h3_a.get_text(strip=True)
            url_text = h3_a.get('href', '')
            if not title:
                continue

            snippet = ''
            snippet_elem = item.select_one('div.c-abstract')
            if snippet_elem:
                snippet = snippet_elem.get_text(strip=True)
            else:
                full_text = item.get_text(separator=' ', strip=True)
                full_text = full_text.replace(title, '', 1).strip()
                snippet = full_text[:300]

            if self._is_irrelevant_result(title, url_text):
                continue

            results.append(SearchResult(
                title=title,
                url=url_text,
                snippet=snippet[:300],
                source="baidu",
                relevance=1.0 - (len(results) * 0.07)
            ))

        logger.info(f"百度搜索完成: '{query}' -> {len(results)} 条有效结果")
        return results

    _baidu_session = None

    def _get_baidu_session(self):
        """获取或创建百度 Session（带 Cookie 持久化）"""
        if self._baidu_session is not None:
            return self._baidu_session
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        })
        try:
            session.get('https://www.baidu.com/', timeout=self.timeout)
        except Exception as e:
            logger.warning(f"百度首页预访问失败: {e}")
        self._baidu_session = session
        return session

    # ── DuckDuckGo ──────────────────────────────────────────────────

    def _search_duckduckgo(self, query: str, **kwargs) -> List[SearchResult]:
        try:
            from ddgs import DDGS

            results = []
            with DDGS() as ddgs:
                for i, item in enumerate(ddgs.text(
                    query, max_results=self.max_results, safesearch='moderate', region='cn-zh',
                )):
                    title = item.get('title', '')
                    url = item.get('href', '')
                    if self._is_irrelevant_result(title, url):
                        continue
                    results.append(SearchResult(
                        title=title, url=url,
                        snippet=item.get('body', ''),
                        source="duckduckgo",
                        relevance=1.0 - (i * 0.1)
                    ))
            return results

        except ImportError:
            logger.warning("ddgs库不可用")
            raise
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
            raise

    # ── Playwright 浏览器搜索 (兜底) ──────────────────────────

    def _search_playwright(self, query: str, **kwargs) -> List[SearchResult]:
        """使用 Playwright 真实浏览器搜索百度

        当 requests 被百度安全验证拦截时，用真实 Chromium 浏览器绕过。
        通过伪造浏览器上下文（locale/时区/navigator）来规避 headless 检测。
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright 库不可用")
            return []

        query = self._disambiguate_query(query)
        results = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.user_agent,
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai',
                )
                page = context.new_page()

                # 隐藏自动化特征
                page.add_init_script('''
                    Object.defineProperty(navigator, 'webdriver', {get: () => false});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                    window.chrome = {runtime: {}};
                ''')

                page.goto(
                    f'https://www.baidu.com/s?wd={query}&rn={min(self.max_results, 15)}',
                    timeout=self.timeout * 1000,
                    wait_until='domcontentloaded'
                )

                # 检测安全验证页
                if '安全验证' in (page.title() or ''):
                    logger.warning("Playwright也遇到百度安全验证")
                    browser.close()
                    return []

                page.wait_for_selector('div.c-container', timeout=self.timeout * 1000)

                for item in page.query_selector_all('div.c-container')[:self.max_results]:
                    title_el = item.query_selector('h3 a')
                    if not title_el:
                        continue
                    title = title_el.inner_text().strip()
                    url_text = title_el.get_attribute('href') or ''

                    snippet = ''
                    snippet_el = item.query_selector('div.c-abstract')
                    if snippet_el:
                        snippet = snippet_el.inner_text().strip()

                    if not title:
                        continue
                    if self._is_irrelevant_result(title, url_text):
                        continue

                    results.append(SearchResult(
                        title=title,
                        url=url_text,
                        snippet=snippet[:300],
                        source="baidu_playwright",
                        relevance=1.0 - (len(results) * 0.07)
                    ))

                browser.close()

            logger.info(f"Playwright百度搜索完成: '{query}' -> {len(results)} 条有效结果")
            return results

        except Exception as e:
            logger.error(f"Playwright搜索失败: {e}")
            return []

    # ── 米游社 / 官网 ──────────────────────────────────────────────

    def _search_miyoushe(self, query: str, **kwargs) -> List[SearchResult]:
        from urllib.parse import quote
        miyoushe_url = f"https://www.miyoushe.com/bh3/search?keyword={quote(query)}"
        return [SearchResult(
            title=f"米游社搜索: {query}",
            url=miyoushe_url,
            snippet="米游社崩坏3社区搜索结果。建议使用浏览器访问该链接查看详细内容。",
            source="miyoushe",
            relevance=1.0
        )]

    def _search_honkai_official(self, query: str, **kwargs) -> List[SearchResult]:
        return [SearchResult(
            title="崩坏3官网",
            url="https://bh3.mihoyo.com/main",
            snippet="崩坏3官方网站，可查看最新版本信息、活动公告、游戏资讯等内容。",
            source="honkai_official",
            relevance=1.0
        )]

    # ── 结果过滤 ──────────────────────────────────────────────────

    def _is_irrelevant_result(self, title: str, url: str) -> bool:
        """过滤其他米哈游游戏、官网首页等无关结果"""
        title_lower = title.lower()
        url_lower = url.lower()

        for p in self._IRRELEVANT_PATTERNS:
            if p in title_lower or p in url_lower:
                return True

        return url.rstrip('/') in self._HOMEPAGE_URLS

    # ── 页面内容获取 ──────────────────────────────────────────────

    def fetch_page_content(self, url: str, use_browser: bool = False) -> str:
        """获取网页完整文本内容。

        Args:
            url: 网页地址
            use_browser: True=Playwright渲染(SPA站点), False=requests直抓

        Returns:
            清洗后的页面文本，失败返回空字符串
        """
        if use_browser:
            return self._fetch_page_playwright(url)
        return self._fetch_page_requests(url)

    def _fetch_page_requests(self, url: str) -> str:
        """requests 直接抓取静态页面"""
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
            return ' '.join(chunk for chunk in chunks if chunk)

        except requests.HTTPError as e:
            logger.debug(f"获取页面内容 HTTP 错误 {url}: {e}")
            return ""
        except Exception as e:
            logger.debug(f"获取页面内容失败 {url}: {e}")
            return ""

    def _fetch_page_playwright(self, url: str) -> str:
        """Playwright 渲染 JS 页面后提取文本（用于 SPA 站点）"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright 库不可用，回退到 requests")
            return self._fetch_page_requests(url)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.user_agent,
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai',
                )
                page = context.new_page()
                page.add_init_script('''
                    Object.defineProperty(navigator, 'webdriver', {get: () => false});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                    window.chrome = {runtime: {}};
                ''')

                page.goto(url, timeout=self.timeout * 1000, wait_until='domcontentloaded')
                page.wait_for_timeout(2000)  # 等 JS 渲染

                text = page.inner_text('body')
                browser.close()

                # 清洗：合并空白行
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                return '\n'.join(lines)

        except Exception as e:
            logger.debug(f"Playwright获取页面失败 {url}: {e}")
            return ""

    # ── 带上下文搜索 ──────────────────────────────────────────────

    def search_with_context(
        self, query: str, context: str = "", include_context: bool = True
    ) -> Dict[str, Any]:
        if context and include_context:
            enhanced_query = f"{query} {context}"
        else:
            enhanced_query = query

        results = self.search(enhanced_query)

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
                formatted_result['content'] = result.content[:100000]
            formatted_results.append(formatted_result)

        return {
            'query': query,
            'enhanced_query': enhanced_query if enhanced_query != query else None,
            'context_used': context if include_context else None,
            'total_results': len(results),
            'results': formatted_results,
            'timestamp': time.time()
        }

    # ── 答案提取 ──────────────────────────────────────────────────

    def extract_answers(self, query: str, results: List[SearchResult]) -> str:
        if not results:
            return f"未找到关于'{query}'的搜索结果。"

        answer_parts = []
        for i, result in enumerate(results[:3]):
            content = result.content or result.snippet
            if not content:
                continue
            relevant_part = self._extract_relevant_part(query, content)
            if relevant_part:
                answer_parts.append(f"【来源 {i+1}】{relevant_part}")

        if answer_parts:
            return "\n\n".join(answer_parts) + \
                   f"\n\n以上信息来自网络搜索，共参考了 {len(answer_parts)} 个来源。"
        return f"已搜索到相关信息，但未能提取出直接答案。建议查看原始链接：{results[0].url}"

    def _extract_relevant_part(self, query: str, content: str) -> str:
        query_words = query.lower().split()
        sentences = re.split(r'[.!?。！？]+', content)
        relevant_sentences = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            matches = sum(1 for word in query_words if word in sentence_lower)
            if matches > 0:
                relevant_sentences.append(sentence.strip())

        if relevant_sentences:
            return ' '.join(relevant_sentences[:3])
        return content[:200] + "..." if len(content) > 200 else content

    # ── 测试 ──────────────────────────────────────────────────────

    @classmethod
    def test_search(cls, query: str = "崩坏3薪炎之律者"):
        print(f"测试搜索: '{query}'")
        print("=" * 60)

        print(f"\n百度搜索:")
        try:
            searcher = cls(engine=SearchEngine.BAIDU, max_results=3)
            results = searcher.search(query)
            for i, r in enumerate(results):
                print(f"\n结果 {i+1}:")
                print(f"  标题: {r.title}")
                print(f"  URL: {r.url}")
                print(f"  摘要: {r.snippet[:100]}...")
                if r.content:
                    print(f"  内容预览: {r.content[:150]}...")
        except Exception as e:
            print(f"  搜索失败: {e}")

        print("\n" + "=" * 60)
        print("搜索测试完成")


def create_web_search_tool():
    """创建用于LLM的搜索工具"""
    def search_tool(query: str, context: str = "") -> str:
        searcher = WebSearcher(engine=SearchEngine.BAIDU)

        try:
            response = searcher.search_with_context(query, context)
            results = response['results']

            if not results:
                return "未找到相关搜索结果。"

            search_results = []
            for r in results:
                search_results.append(SearchResult(
                    title=r['title'], url=r['url'], snippet=r['snippet'],
                    source=r['source'], relevance=r['relevance']
                ))

            return searcher.extract_answers(query, search_results)

        except Exception as e:
            return f"搜索过程中发生错误: {str(e)}"

    return search_tool


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    WebSearcher.test_search("崩坏3薪炎之律者攻击方式")
