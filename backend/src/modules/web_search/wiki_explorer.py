#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiki 探索器 — 名字链条式深度搜索。

B站wiki 的特性是"名字即编号"：wiki.biligame.com/bh3/{名字} 直接定位页面。
页面内部包含大量内链（其他 wiki 页面），形成天然的知识图谱。

BilibiliExplorer 利用这个特性：
1. 按名字打开页面 → 提取正文 + 所有内部链接（相关名字）
2. 对相关名字评分排序 → 选择最值得深入的
3. 逐个深入 → 再发现新名字 → 循环
4. 2-3 层后停止，返回结构化探索结果

这样一次探索就能覆盖一个主题的完整知识网。
"""
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import unquote

logger = logging.getLogger(__name__)


@dataclass
class WikiPage:
    """一个 wiki 页面的探索结果。"""
    name: str
    url: str
    title: str = ""
    content_snippet: str = ""  # 正文片段 (前 800 字符)
    related_names: List[str] = field(default_factory=list)  # 发现的相关名字
    depth: int = 0  # 发现深度
    error: str = ""


class BilibiliExplorer:
    """B站wiki 探索器 — 名字链条式深度搜索。

    使用方式:
        explorer = BilibiliExplorer()
        result = explorer.explore("薇塔", max_depth=2, max_pages=6)
    """

    BASE = "https://wiki.biligame.com/bh3"

    # 内容提取时忽略的页面标题模式（非实体页面）
    SKIP_TITLE_PATTERNS = [
        "搜索结果", "特殊:", "分类:", "帮助:", "模板:", "崩坏3WIKI",
        "文件:", "模块:", "Widget:", "Gadget", "Topic",
        "首页", "导航", "最近更改", "关于本站",
    ]

    # 链接过滤：忽略这些 namespace 前缀
    SKIP_LINK_PREFIXES = [
        "/bh3/特殊:", "/bh3/分类:", "/bh3/帮助:", "/bh3/模板:",
        "/bh3/文件:", "/bh3/模块:", "/bh3/Widget:", "/bh3/Gadget",
        "/bh3/Topic", "/bh3/首页", "/bh3/讨论",
    ]

    # 高价值链接关键词（出现在链接文本或 URL 中时加分）
    HIGH_VALUE_KEYWORDS = [
        "角色", "武器", "圣痕", "女武神", "装甲", "律者",
        "主线", "剧情", "编年史", "活动", "BOSS", "敌人",
        "套装", "人偶", "设定", "世界观",
    ]

    # 目录/索引页关键词（虽然是崩坏3相关，但是巨型列表页，对单个查询关联度低）
    CATALOG_PATTERNS = [
        "图鉴", "列表", "索引", "导航", "目录", "合集", "汇总",
    ]

    def __init__(self, timeout: int = 12, content_chars: int = 800):
        self.timeout = timeout
        self.content_chars = content_chars

    # ── public API ──

    # 常见游戏前缀（查询时剥离）
    _GAME_PREFIXES = ["崩坏3 ", "崩坏三 ", "崩坏3", "崩坏三", "bh3 ", "honkai ", "bh3", "honkai"]

    @classmethod
    def _resolve_query(cls, query: str) -> str:
        """从复合查询中提取最佳搜索词。

        "崩坏3 符华" → "符华"
        "琪亚娜 崩坏3" → "琪亚娜"
        "符华 攻略" → "符华"（取第一个词尝试）

        B站wiki 是崩坏3专属站点（URL含 /bh3/），查询中的"崩坏3"是噪音，
        只对百度这种通用搜索引擎才有消歧意义。
        """
        name = query.strip()
        # 剥离游戏前缀和后缀
        for prefix in cls._GAME_PREFIXES:
            pfx = prefix.lower().rstrip()
            low = name.lower()
            if low.startswith(pfx):
                name = name[len(pfx):].strip()
                break
            if low.endswith(pfx):
                name = name[:-len(pfx)].strip()
                break
        return name

    def explore(self, query: str, max_depth: int = 2, max_pages: int = 6) -> str:
        """探索入口：从一个名字出发，链条式深挖。

        Args:
            query: 起始搜索词（角色名/事物名）
            max_depth: 最大探索深度 (1-3)
            max_pages: 总访问页面上限

        Returns:
            格式化的探索结果文本
        """
        if not query or not query.strip():
            return "[B站wiki探索] 查询为空。"

        name = self._resolve_query(query.strip())
        start_time = time.time()
        visited: set = set()
        pages: List[WikiPage] = []

        # ── 第一层：打开起始页面 ──
        root = self._fetch_page(name, depth=0)
        if root.error:
            # 回退：尝试用原始查询的每个词（空格分割）
            for word in query.strip().split():
                word = word.strip()
                if len(word) < 2 or word == name:
                    continue
                root = self._fetch_page(word, depth=0)
                if not root.error:
                    name = word
                    break
            if root.error:
                return f"[B站wiki探索] 未找到「{name}」的相关页面。\n  {root.url}"

        visited.add(self._normalize(name))
        pages.append(root)

        # ── 收集候选 ──
        candidates = self._score_links(root.related_names, query, visited)

        # ── 第二层：深入高价值候选 ──
        depth = 1
        while depth <= max_depth and len(pages) < max_pages and candidates:
            next_candidates = []
            for cname, _score in candidates:
                if len(pages) >= max_pages:
                    break
                if self._normalize(cname) in visited:
                    continue
                visited.add(self._normalize(cname))
                page = self._fetch_page(cname, depth=depth)
                if page.error:
                    continue
                pages.append(page)

                # 从新页面收集更深层候选
                if depth < max_depth:
                    new_links = self._score_links(
                        page.related_names, query, visited
                    )
                    next_candidates.extend(new_links)

            candidates = sorted(
                set(next_candidates), key=lambda x: x[1], reverse=True
            )
            depth += 1

        elapsed = time.time() - start_time
        return self._format_result(query, pages, elapsed)

    # ── 页面抓取 ──

    def _fetch_page(self, name: str, depth: int = 0) -> WikiPage:
        """抓取并解析一个 wiki 页面。"""
        import urllib.parse
        import requests as _requests

        encoded = urllib.parse.quote(name)
        url = f"{self.BASE}/{encoded}"

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            resp = _requests.get(url, headers=headers, timeout=self.timeout)
            resp.raise_for_status()

            from bs4 import BeautifulSoup as _BS
            soup = _BS(resp.text, "html.parser")

            # 标题
            title = name
            if soup.title:
                raw_title = soup.title.get_text(strip=True)
                # B站wiki 标题格式: "页面名 - 崩坏3WIKI_BWIKI_哔哩哔哩"
                title = raw_title.split(" - ")[0].strip() if " - " in raw_title else raw_title

            # 跳过非实体页面
            for pat in self.SKIP_TITLE_PATTERNS:
                if pat in title:
                    return WikiPage(
                        name=name, url=url, title=title,
                        depth=depth, error=f"非实体页面 (匹配: {pat})",
                    )

            # 提取正文
            content = self._extract_content(soup)
            content_snippet = content[:self.content_chars] if content else ""

            # 空内容也视为无效
            if not content_snippet or len(content_snippet) < 30:
                return WikiPage(
                    name=name, url=url, title=title,
                    depth=depth, error="页面内容过短",
                )

            # 提取内部链接（相关名字）
            related = self._extract_links(soup)

            return WikiPage(
                name=name,
                url=url,
                title=title,
                content_snippet=content_snippet,
                related_names=related,
                depth=depth,
            )

        except Exception as e:
            err_str = str(e)
            if "404" in err_str:
                return WikiPage(name=name, url=url, depth=depth, error="404")
            logger.debug(f"BilibiliExplorer: 获取「{name}」失败: {e}")
            return WikiPage(name=name, url=url, depth=depth, error=err_str[:100])

    # ── 内容提取 ──

    def _extract_content(self, soup) -> str:
        """提取 wiki 页面的正文内容。"""
        # 移除噪音
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        # 优先主内容区
        selectors = [
            ".mw-parser-output", "#bodyContent", "#mw-content-text",
            "main", "article", ".content", "#content",
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(separator="\n", strip=True)
                lines = [ln.strip() for ln in text.splitlines() if ln.strip() and len(ln.strip()) > 2]
                return "\n".join(lines)

        # 回退 body
        if soup.body:
            text = soup.body.get_text(separator="\n", strip=True)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip() and len(ln.strip()) > 2]
            return "\n".join(lines)

        return ""

    # ── 链接提取 ──

    def _extract_links(self, soup) -> List[str]:
        """提取 wiki 内部链接作为相关名字列表。

        MediaWiki 内链格式: <a href="/bh3/页面名" ...>链接文本</a>
        返回去重后的相关名字列表。
        """
        names = []
        seen = set()

        # 找到所有指向 /bh3/ 的内部链接
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("/bh3/"):
                continue

            # 跳过特殊 namespace（先解码再比较，因为B站wiki的href可能被URL编码）
            _decoded_href = unquote(href)
            skip = False
            for prefix in self.SKIP_LINK_PREFIXES:
                if _decoded_href.startswith(prefix):
                    skip = True
                    break
            if skip:
                continue

            # 从 URL 解码名字
            raw = href[len("/bh3/"):]
            if "?" in raw or "#" in raw:
                continue
            try:
                name = unquote(raw).strip()
            except Exception:
                continue

            if not name or len(name) < 2:
                continue
            if name in seen:
                continue

            # 额外检查：解码后的名字也不应匹配噪音模式
            _noise_name_prefixes = ("特殊:", "分类:", "帮助:", "模板:", "文件:",
                                    "模块:", "Widget:", "Gadget", "Topic", "讨论:")
            if any(name.startswith(p) for p in _noise_name_prefixes):
                continue
            # 精确噪音名（MediaWiki 系统页面 / 工具页面）
            _noise_exact_names = {
                "首页", "创建", "最近更改", "帮助", "讨论", "导航",
                "关于本站", "上传文件", "MediaWiki", "沙盒", "待审核",
            }
            if name in _noise_exact_names:
                continue

            # 也收集链接文本作为潜在名字（有时链接文本和 URL 名不同）
            link_text = a.get_text(strip=True)
            seen.add(name)
            names.append(name)
            if link_text and link_text not in seen and len(link_text) >= 2:
                names.append(link_text)
                seen.add(link_text)

        return names

    # ── 链接评分 ──

    def _score_links(
        self, names: List[str], query: str, visited: set
    ) -> List[Tuple[str, int]]:
        """对相关名字评分排序，选出最值得深入的。

        评分因素:
        - 是否含高价值关键词 (角色/武器/圣痕/剧情...)
        - 是否与原始查询有文本重叠
        - 是否已经访问过
        返回: [(name, score), ...] 按分降序
        """
        scored = []
        query_lower = query.lower()

        for name in names:
            if self._normalize(name) in visited:
                continue

            score = 1  # 基础分

            # 高价值关键词加分
            for kw in self.HIGH_VALUE_KEYWORDS:
                if kw in name:
                    score += 3
                    break

            # 目录/索引页降权（巨型列表页，对单个查询关联度低）
            for pat in self.CATALOG_PATTERNS:
                if pat in name:
                    score -= 4
                    break

            # 与查询的文本重叠加分
            name_lower = name.lower()
            # 字符级重叠
            overlap = len(set(query_lower) & set(name_lower))
            score += min(overlap, 5)

            # 与查询无字符重叠 → 大概率是不相关的泛化/导航页面
            # 高价值关键词（如"主线""活动"）可部分抵消，但仍排在具体条目之后
            if overlap == 0:
                score -= 3

            # 排除过短/过长/明显非实体的名字
            if len(name) < 2 or len(name) > 40:
                score -= 5
            if any(c in name for c in ["#", "?", "&", "=", "%"]):
                score -= 10

            if score > 0:
                scored.append((name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ── 输出格式化 ──

    def _format_result(self, query: str, pages: List[WikiPage], elapsed: float) -> str:
        """格式化探索结果为 LLM 可读文本。"""
        if not pages:
            return f"[B站wiki探索] 未找到与「{query}」相关的结果。"

        lines = [
            f"## B站wiki 探索: 「{query}」",
            f"探索 {len(pages)} 个页面, 耗时 {elapsed:.1f}s\n",
        ]

        for i, page in enumerate(pages):
            depth_label = "起始" if page.depth == 0 else f"深度{page.depth}"
            lines.append(
                f"### [{i+1}] {page.title} ({depth_label})\n"
                f"  {page.url}\n"
                f"  {page.content_snippet}"
            )
            if page.related_names and page.depth == 0:
                # 只在起始页显示发现的相关名字
                top_related = page.related_names[:10]
                if top_related:
                    lines.append(
                        f"  🔗 相关: {', '.join(top_related)}"
                    )
            lines.append("")

        return "\n".join(lines)

    # ── 工具 ──

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().lower()
