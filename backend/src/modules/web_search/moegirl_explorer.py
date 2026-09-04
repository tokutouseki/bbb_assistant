#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
萌娘百科探索器 — Playwright 浏览器 + 内链探索。

萌娘百科 (zh.moegirl.org.cn) 受 Cloudflare 保护，requests 直接 403。
必须使用 Playwright 真实浏览器绕过。本模块复用项目已有的 Playwright
反检测基础设施，实现从名字出发的内链链条式深度搜索。

特性:
- Playwright 真实浏览器 (绕过 Cloudflare)
- 浏览器复用: 一次 launch → 多页面探索 (避免重复启动开销)
- 双入口: 名字搜索 + 直连页面
- 内链链条: 页面 → 提取 wiki 内链 → 评分 → 深入 → 循环
- 角色/非角色 URL 自动区分

URL 规则:
- 搜索: https://mzh.moegirl.org.cn/index.php?search={query}
- 角色页: https://zh.moegirl.org.cn/{角色全名}(崩坏3)#
- 非角色: https://zh.moegirl.org.cn/{事物名}
"""

import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MoegirlPage:
    """萌娘百科页面探索结果。"""
    name: str
    url: str
    title: str = ""
    content_snippet: str = ""        # 正文片段 (前 1000 字符)
    related_names: List[str] = field(default_factory=list)  # 页面内链名字
    depth: int = 0
    is_character: bool = False
    error: str = ""


class MoegirlExplorer:
    """萌娘百科探索器 — Playwright 驱动的链条式深度搜索。

    使用方式:
        explorer = MoegirlExplorer()
        result = explorer.explore("无量塔姬子", max_depth=2, max_pages=5)

    浏览器管理:
        每次 explore() 调用会启动一个新浏览器实例，探索完成后自动关闭。
        这是为了避免长时间持有浏览器资源。
    """

    BASE = "https://zh.moegirl.org.cn"
    SEARCH_URL = "https://mzh.moegirl.org.cn/index.php"

    # 要跳过的页面标题模式
    SKIP_TITLE_PATTERNS = [
        "搜索结果", "Special:", "特殊:", "Category:", "分类:", "Help:", "帮助:",
        "Template:", "模板:", "File:", "文件:", "Module:", "模块:",
        "Widget:", "Gadget:", "Topic:", "Talk:", "讨论:",
        "首页", "Main Page", "萌娘百科:",
        "User:", "用户:", "Project:", "项目:",
    ]

    # 要跳过的链接前缀
    SKIP_LINK_PREFIXES = [
        "/Special:", "/特殊:", "/Category:", "/分类:", "/Help:", "/帮助:",
        "/Template:", "/模板:", "/File:", "/文件:", "/Module:", "/模块:",
        "/User:", "/用户:", "/Project:", "/项目:", "/Talk:", "/讨论:",
        "/Main_Page", "/首页",
    ]

    # 高价值关键词 (用于链接评分)
    HIGH_VALUE_KEYWORDS = [
        "角色", "武器", "圣痕", "女武神", "装甲", "律者",
        "主线", "剧情", "编年史", "活动", "BOSS", "敌人",
        "套装", "人偶", "设定", "世界观", "崩坏",
        "卡斯兰娜", "雷电", "逆熵", "天命", "世界蛇",
    ]

    # 角色名后缀检测 (判断是否为崩坏3角色页)
    CHARACTER_SUFFIX = "(崩坏3)"

    # 常见游戏前缀/后缀（查询时剥离，B站wiki/米游社/萌娘百科均为崩坏3专属站点）
    _GAME_PREFIXES = ["崩坏3 ", "崩坏三 ", "崩坏3", "崩坏三", "bh3 ", "honkai ", "bh3", "honkai"]

    @classmethod
    def _resolve_query(cls, query: str) -> str:
        """从复合查询中剥离游戏前缀/后缀。

        "崩坏3 琪亚娜" → "琪亚娜"
        "琪亚娜 崩坏3" → "琪亚娜"

        萌娘百科角色页 URL 已含 (崩坏3) 后缀，搜索词中的"崩坏3"是噪音。
        """
        name = query.strip()
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

    def __init__(
        self,
        timeout: int = 20,
        content_chars: int = 1000,
        headless: bool = True,
    ):
        self.timeout = timeout
        self.content_chars = content_chars
        self.headless = headless

        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    # ── 主入口 ──

    def explore(
        self,
        query: str,
        max_depth: int = 2,
        max_pages: int = 5,
        is_character: Optional[bool] = None,
    ) -> str:
        """从名字出发，探索萌娘百科。

        Args:
            query: 搜索词 (角色名/事物名)
            max_depth: 最大探索深度 (1-3)
            max_pages: 总页面数上限
            is_character: 是否为角色 (None=自动检测)

        Returns:
            格式化的探索结果文本
        """
        if not query or not query.strip():
            return "[萌娘百科探索] 查询为空。"

        name = self._resolve_query(query.strip())
        start_time = time.time()
        visited: set = set()
        pages: List[MoegirlPage] = []

        # ── 启动浏览器 ──
        browser, context = self._launch_browser()
        if not browser:
            return "[萌娘百科探索] 无法启动 Playwright 浏览器。请确认 playwright 已安装: pip install playwright && playwright install chromium"

        try:
            # ── 第一层: 找到起始页面 ──
            root = self._find_page(name, context, is_character=is_character, depth=0)
            if root.error:
                return f"[萌娘百科探索] 未找到「{name}」的相关页面。\n  尝试: {self.BASE}/index.php?search={urllib.parse.quote(name)}"

            visited.add(self._normalize(root.name))
            visited.add(self._normalize(root.url))
            pages.append(root)

            # ── 收集候选 ──
            candidates = self._score_links(root.related_names, name, visited)

            # ── 深层探索 ──
            depth = 1
            while depth <= max_depth and len(pages) < max_pages and candidates:
                next_candidates = []
                for cname, _score in candidates:
                    if len(pages) >= max_pages:
                        break
                    norm_name = self._normalize(cname)
                    if norm_name in visited:
                        continue
                    visited.add(norm_name)

                    page = self._find_page(cname, context, is_character=False, depth=depth)
                    if page.error:
                        visited.add(norm_name)  # 标记失败避免重试
                        continue
                    visited.add(self._normalize(page.url))
                    pages.append(page)

                    if depth < max_depth:
                        new_links = self._score_links(
                            page.related_names, name, visited
                        )
                        next_candidates.extend(new_links)

                candidates = sorted(
                    set(next_candidates), key=lambda x: x[1], reverse=True
                )
                depth += 1

            elapsed = time.time() - start_time
            return self._format_result(name, pages, elapsed)

        finally:
            # ── 关闭浏览器 ──
            try:
                context.close()
                browser.close()
            except Exception:
                pass

    # ── 页面查找 (直连 → API → 搜索) ──

    def _find_page(
        self,
        name: str,
        context,
        is_character: Optional[bool] = None,
        depth: int = 0,
    ) -> MoegirlPage:
        """三级查找: 直连页面 → MediaWiki API 回退 → 搜索。

        Playwright 浏览器可能被 Cloudflare 阻挡（如薇塔），
        MediaWiki API 端点不受影响，作为可靠回退。
        """
        # 第一级: 直连页面 (Playwright)
        page = self._try_direct_page(name, context, is_character, depth)
        if not page.error:
            return page

        # 第二级: MediaWiki API 回退（绕过 Cloudflare）
        api_page = self._fetch_via_api(name, is_character=is_character, depth=depth)
        if api_page and not api_page.error:
            logger.info(f"萌娘百科: 「{name}」通过 API 回退获取成功")
            return api_page

        # 第三级: 搜索 (Playwright)
        return self._search_page(name, context, depth)

    def _try_direct_page(
        self,
        name: str,
        context,
        is_character: Optional[bool] = None,
        depth: int = 0,
    ) -> MoegirlPage:
        """尝试直连萌娘百科页面。

        策略（从常见到罕见）:
        1. 先尝试 /{name} — 大多数崩坏3原创角色（薇塔/希娜狄雅等）无(崩坏3)后缀
        2. 命中消歧义页 → 提取崩坏3内链 → 重定向到 /{name}(崩坏3)
        3. /{name} 404 → 回退尝试 /{name}(崩坏3) — 跨作品同名角色（雷电芽衣等）
        4. 都失败 → 走搜索

        URL 规则:
        - 崩坏3原创角色: /{角色名} （无后缀）
        - 跨作品同名角色: /{角色名}(崩坏3) （消歧义后缀）
        - 非角色事物: /{事物名}
        """
        # ── 第一步：尝试 /{name}（覆盖大多数崩坏3角色）──
        if is_character is not False:
            encoded = urllib.parse.quote(name)
            url = f"{self.BASE}/{encoded}"
            page = self._fetch_page(name, url, context, depth)
            if not page.error:
                # 消歧义页 → 提取崩坏3专属链接
                if self._is_disambiguation(page):
                    bh3_link = self._find_bh3_link(page.related_names)
                    if bh3_link:
                        logger.info(
                            f"萌娘百科: 「{name}」命中消歧义页，重定向到「{bh3_link}」"
                        )
                        bh3_page = self._fetch_page(bh3_link,
                            f"{self.BASE}/{urllib.parse.quote(bh3_link)}",
                            context, depth)
                        if not bh3_page.error:
                            bh3_page.is_character = True
                            return bh3_page
                    # 消歧义页且无崩坏3链接 → 回退到搜索
                    return MoegirlPage(
                        name=name, url=url, depth=depth,
                        error="消歧义页，未找到崩坏3条目",
                    )
                # 非消歧义页 → 直接使用（薇塔等崩坏3原创角色走这里）
                return page

        # ── 第二步：回退尝试 /{name}(崩坏3)（跨作品同名角色）──
        if is_character is not True:
            encoded = urllib.parse.quote(f"{name}{self.CHARACTER_SUFFIX}")
            url = f"{self.BASE}/{encoded}"
            page = self._fetch_page(name, url, context, depth)
            if not page.error:
                page.is_character = True
                return page

        return MoegirlPage(
            name=name, url="", depth=depth,
            error="直连页面和搜索均未找到",
        )

    @staticmethod
    def _is_disambiguation(page: 'MoegirlPage') -> bool:
        """检测页面是否为萌娘百科消歧义页。

        仅使用 MediaWiki 消歧义模板的强特征，避免误判：
        - "可以指：" 在角色介绍中极其常见（"XX可以指：装甲A/装甲B"），不能作为判断依据
        - 真消歧义页必有 "这是一个消歧义页" 或 "罗列了有相同或相近的标题" 模板标记
        """
        if not page.content_snippet:
            return False
        snippet = page.content_snippet
        title = page.title or ""
        # 仅 MediaWiki 消歧义模板的强特征（"可以指："太常见，刻意排除）
        _disambig_markers = [
            "这是一个消歧义页",
            "罗列了有相同或相近的标题",
        ]
        if any(m in snippet for m in _disambig_markers):
            return True
        # 标题含"消歧义"（如"雷电芽衣(消歧义)"）
        if "消歧义" in title:
            return True
        return False

    @staticmethod
    def _is_disambiguation_from_text(snippet: str, title: str = "") -> bool:
        """与 _is_disambiguation 相同逻辑，但直接接受文本（用于 API 返回内容）。"""
        if not snippet:
            return False
        _disambig_markers = [
            "这是一个消歧义页",
            "罗列了有相同或相近的标题",
        ]
        if any(m in snippet for m in _disambig_markers):
            return True
        if "消歧义" in (title or ""):
            return True
        return False

    @staticmethod
    def _find_bh3_link(related_names: List[str]) -> Optional[str]:
        """从相关名字列表中查找崩坏3条目。"""
        for name in related_names:
            if "崩坏3" in name or "(崩坏3)" in name:
                return name
        # 备选：包含括号但非崩坏学园2的条目（如"雷电芽衣(崩坏3)"）
        for name in related_names:
            if "(" in name and "崩坏学园" not in name and "崩坏2" not in name:
                return name
        return None

    def _fetch_via_api(
        self,
        name: str,
        is_character: Optional[bool] = None,
        depth: int = 0,
    ) -> Optional['MoegirlPage']:
        """通过 MediaWiki API 获取页面内容（绕过 Cloudflare）。

        Playwright 浏览器访问萌娘百科可能被 Cloudflare JS 挑战阻挡，
        但 API 端点 (zh.moegirl.org.cn/api.php) 通常不受影响。
        此方法作为 Playwright 失败后的可靠回退。

        返回 None 表示 API 也不可用（网络错误等）。
        """
        import requests as _requests

        # 尝试的页面标题列表
        titles_to_try = [name]
        if is_character is not False:
            titles_to_try.append(f"{name}{self.CHARACTER_SUFFIX}")

        for title in titles_to_try:
            try:
                resp = _requests.get(
                    f"{self.BASE}/api.php",
                    params={
                        "action": "query",
                        "titles": title,
                        "prop": "extracts|info",
                        "explaintext": "1",
                        "inprop": "url",
                        "format": "json",
                    },
                    headers={
                        "User-Agent": self._user_agent,
                        "Accept": "application/json; charset=utf-8",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                pages = data.get("query", {}).get("pages", {})
                for pageid, info in pages.items():
                    if str(pageid) == "-1" or "missing" in info:
                        continue  # 页面不存在

                    page_title = info.get("title", title)
                    extract = info.get("extract", "")
                    full_url = info.get("fullurl", "")
                    canonical_url = info.get("canonicalurl", full_url)

                    if not extract or len(extract) < 30:
                        logger.debug(
                            f"萌娘百科 API: 「{title}」返回内容过短 "
                            f"({len(extract)} chars)，跳过"
                        )
                        continue

                    snippet = extract[:self.content_chars]

                    # 消歧义检测：API 也可能返回消歧义页
                    if self._is_disambiguation_from_text(snippet, page_title):
                        logger.debug(
                            f"萌娘百科 API: 「{page_title}」为消歧义页，尝试崩坏3变体"
                        )
                        continue

                    logger.info(
                        f"萌娘百科 API 获取成功: 「{page_title}」"
                        f"({len(extract)} chars)"
                    )
                    return MoegirlPage(
                        name=page_title,
                        url=canonical_url or f"{self.BASE}/{urllib.parse.quote(title)}",
                        title=page_title,
                        content_snippet=snippet,
                        related_names=[],
                        depth=depth,
                        is_character=("崩坏3" in page_title or is_character is True),
                    )

            except Exception as e:
                logger.warning(
                    f"萌娘百科 API 获取「{title}」失败: "
                    f"{type(e).__name__}: {e}"
                )
                continue

        return None

    def _search_page(
        self,
        name: str,
        context,
        depth: int = 0,
    ) -> MoegirlPage:
        """通过萌娘百科搜索找到最佳匹配页面。

        搜索 URL 使用移动版 (mzh.moegirl.org.cn)，需要匹配移动版 HTML 结构。
        多级回退: 特定选择器 → 通用链接提取 → 直接跳转检测。
        """
        search_url = f"{self.SEARCH_URL}?search={urllib.parse.quote(name)}"
        page_obj = None

        try:
            page_obj = context.new_page()
            page_obj.goto(search_url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            page_obj.wait_for_timeout(2000)  # 等 JS 渲染 + Cloudflare

            # ── 第一级：精确选择器（桌面 + 移动版）──
            _search_selectors = [
                ".mw-search-result-heading a",      # 桌面版
                ".mw-search-results .mw-search-result a",  # 桌面版备选
                "ul.mw-search-results li a",         # 桌面版旧式
                ".search-result .mw-search-result-heading a",  # 移动版
                ".mw-search-result a",               # 移动版简化
                ".searchresults .mw-search-result a", # 移动版备选
            ]
            result_links = []
            for sel in _search_selectors:
                try:
                    links = page_obj.query_selector_all(sel)
                    if links:
                        result_links = links
                        break
                except Exception:
                    continue

            # ── 第二级：通用回退（从搜索结果区域提取任何 wiki 链接）──
            if not result_links:
                # 取所有指向 /zh.moegirl.org.cn/ 或以 / 开头的链接，过滤噪音
                all_links = page_obj.query_selector_all("a[href]")
                for link in all_links:
                    href = link.get_attribute("href") or ""
                    if not href:
                        continue
                    # 只取指向 wiki 页面的内部链接
                    if not (href.startswith("/") or "zh.moegirl.org.cn" in href or "mzh.moegirl.org.cn" in href):
                        continue
                    title = link.inner_text().strip()
                    if not title or len(title) < 2:
                        continue
                    # 过滤噪音
                    skip = False
                    for pat in self.SKIP_TITLE_PATTERNS:
                        if pat.lower() in title.lower():
                            skip = True
                            break
                    if skip:
                        continue
                    result_links.append(link)

            if result_links:
                for link in result_links:
                    href = link.get_attribute("href")
                    title = link.inner_text().strip()
                    if href and title:
                        # 补全相对 URL
                        if href.startswith("/"):
                            full_url = self.BASE + href
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            continue

                        # 跳过非实体页面
                        skip = False
                        for pat in self.SKIP_TITLE_PATTERNS:
                            if pat.lower() in title.lower():
                                skip = True
                                break
                        if skip:
                            continue

                        page_obj.close()
                        page_obj = None
                        return self._fetch_page(title, full_url, context, depth)

            # ── 第三级：检查是否直接跳转到页面 ──
            current_title = page_obj.title()
            if current_title and "搜索" not in current_title:
                current_url = page_obj.url
                if current_url.startswith(self.BASE):
                    title = current_title.split(" - ")[0].strip()
                    page_obj.close()
                    page_obj = None
                    return self._fetch_page(title, current_url, context, depth)

            page_obj.close()
            page_obj = None
            return MoegirlPage(
                name=name, url=search_url, depth=depth,
                error="搜索无结果",
            )

        except Exception as e:
            if page_obj:
                try:
                    page_obj.close()
                except Exception:
                    pass
            logger.debug(f"MoegirlExplorer: 搜索「{name}」失败: {e}")
            return MoegirlPage(
                name=name, url=search_url, depth=depth,
                error=str(e)[:100],
            )

    # ── 页面抓取与解析 ──

    def _fetch_page(
        self,
        name: str,
        url: str,
        context,
        depth: int = 0,
    ) -> MoegirlPage:
        """抓取并解析一个萌娘百科页面。"""
        page_obj = None
        try:
            page_obj = context.new_page()
            page_obj.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            page_obj.wait_for_timeout(1500)

            # 提取标题
            title = name
            try:
                page_title = page_obj.title()
                if page_title:
                    title = page_title.split(" - ")[0].strip()
            except Exception:
                pass

            # 跳过非实体页面
            for pat in self.SKIP_TITLE_PATTERNS:
                if pat.lower() in title.lower():
                    page_obj.close()
                    return MoegirlPage(
                        name=name, url=url, title=title, depth=depth,
                        error=f"非实体页面 (匹配: {pat})",
                    )

            # 提取正文
            content = self._extract_content(page_obj)
            content_snippet = content[:self.content_chars] if content else ""

            if not content_snippet or len(content_snippet) < 30:
                page_obj.close()
                return MoegirlPage(
                    name=name, url=url, title=title, depth=depth,
                    error="页面内容过短",
                )

            # 检测 MediaWiki 软 404（页面不存在但返回 200 + "创建此页面"提示）
            _soft_404_markers = [
                "找不到这个页面", "没有权限创建本页面",
                "如您曾通过一个URL链接跳转至此却找不到页面",
                "您可以搜索本页标题或搜索相关日志",
            ]
            if any(m in content_snippet for m in _soft_404_markers):
                page_obj.close()
                return MoegirlPage(
                    name=name, url=url, title=title, depth=depth,
                    error="页面不存在 (软404)",
                )

            # 提取内部链接
            related = self._extract_links(page_obj)

            page_obj.close()
            return MoegirlPage(
                name=name,
                url=url,
                title=title,
                content_snippet=content_snippet,
                related_names=related,
                depth=depth,
            )

        except Exception as e:
            if page_obj:
                try:
                    page_obj.close()
                except Exception:
                    pass
            err_str = str(e)
            if "404" in err_str or "net::ERR" in err_str:
                return MoegirlPage(name=name, url=url, depth=depth, error="404")
            logger.debug(f"MoegirlExplorer: 获取「{name}」失败: {e}")
            return MoegirlPage(name=name, url=url, depth=depth, error=err_str[:100])

    # ── 内容提取 ──

    def _extract_content(self, page_obj) -> str:
        """提取萌娘百科页面的正文内容 (MediaWiki 结构)。"""
        try:
            # 优先 MediaWiki 主内容区
            selectors = [
                ".mw-parser-output",
                "#bodyContent",
                "#mw-content-text",
                "main",
                "article",
                ".content",
            ]
            for sel in selectors:
                try:
                    elem = page_obj.query_selector(sel)
                    if elem:
                        text = elem.inner_text()
                        lines = [
                            ln.strip() for ln in text.splitlines()
                            if ln.strip() and len(ln.strip()) > 2
                        ]
                        return "\n".join(lines)
                except Exception:
                    continue

            # 回退 body
            text = page_obj.inner_text("body")
            lines = [
                ln.strip() for ln in text.splitlines()
                if ln.strip() and len(ln.strip()) > 2
            ]
            return "\n".join(lines)

        except Exception as e:
            logger.debug(f"MoegirlExplorer: 内容提取失败: {e}")
            return ""

    # ── 链接提取 ──

    def _extract_links(self, page_obj) -> List[str]:
        """提取萌娘百科页面内的 wiki 链接作为相关名字。

        萌娘百科内链格式:
        - <a href="/wiki/页面名" ...>链接文本</a>
        - <a href="/{页面名}" ...>链接文本</a>
        返回去重后的相关名字列表。
        """
        names = []
        seen = set()

        try:
            links = page_obj.query_selector_all("a[href]")
        except Exception:
            return names

        for link in links:
            try:
                href = link.get_attribute("href") or ""
            except Exception:
                continue

            if not href:
                continue

            # 只处理指向 /wiki/ 或 /{页面名} 的内部链接
            is_wiki = False
            raw = ""

            if href.startswith("/wiki/"):
                raw = href[len("/wiki/"):]
                is_wiki = True
            elif href.startswith("/"):
                # 可能是短链接 /{页面名}
                candidate = href[1:]
                # 排除明显非页面路径
                if not any(p in candidate for p in ("?", "#", ".php", ".html", ".jpg", ".png")):
                    if candidate and len(candidate) >= 2:
                        raw = candidate
                        is_wiki = True

            if not is_wiki or not raw:
                continue

            # 跳过特殊 namespace
            skip = False
            for prefix in self.SKIP_LINK_PREFIXES:
                if href.startswith(prefix):
                    skip = True
                    break
            if skip:
                continue

            # 从 URL 解码名字
            try:
                name = urllib.parse.unquote(raw).strip()
            except Exception:
                continue

            if not name or len(name) < 2:
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)

            # 同时收集链接文本作为候选名字
            try:
                link_text = link.inner_text().strip()
                if link_text and link_text not in seen and len(link_text) >= 2:
                    names.append(link_text)
                    seen.add(link_text)
            except Exception:
                pass

        return names

    # ── 链接评分 ──

    def _score_links(
        self, names: List[str], query: str, visited: set
    ) -> List[Tuple[str, int]]:
        """对相关名字评分排序，选出最值得深入的。"""
        scored = []
        query_lower = query.lower()

        for name in names:
            if self._normalize(name) in visited:
                continue

            score = 1

            # 高价值关键词加分
            for kw in self.HIGH_VALUE_KEYWORDS:
                if kw in name:
                    score += 3
                    break

            # 与查询文本重叠加分
            name_lower = name.lower()
            overlap = len(set(query_lower) & set(name_lower))
            score += min(overlap, 5)

            # 崩坏3相关加分
            if "崩坏" in name or "bh3" in name_lower or "honkai" in name_lower:
                score += 2

            # 排除过短/过长/非实体
            if len(name) < 2 or len(name) > 40:
                score -= 5
            if any(c in name for c in ("#", "?", "&", "=", "%", ":", "/", ".")):
                score -= 10
            # 排除明显的模板/帮助页面名
            if any(pat in name for pat in ("模板:", "帮助:", "文件:", "分类:")):
                score -= 10

            if score > 0:
                scored.append((name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ── 浏览器管理 ──

    def _launch_browser(self):
        """启动 Playwright 浏览器 (含反检测措施)。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright 库不可用，请安装: pip install playwright && playwright install chromium")
            return None, None

        try:
            p = sync_playwright()
            playwright = p.start()
            browser = playwright.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=self._user_agent,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            # 隐藏自动化特征 (绕过 Cloudflare)
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = {runtime: {}};
            """)

            # 首次访问: 预热域名 (建立 Cloudflare 信任) — 缩短超时避免阻塞
            warmup_page = context.new_page()
            try:
                warmup_page.goto(self.BASE, timeout=10000, wait_until="domcontentloaded")
                warmup_page.wait_for_timeout(1000)
            except Exception:
                pass
            finally:
                try:
                    warmup_page.close()
                except Exception:
                    pass

            return browser, context

        except Exception as e:
            logger.warning(f"Playwright 启动失败: {e}")
            return None, None

    # ── 输出格式化 ──

    def _format_result(self, query: str, pages: List[MoegirlPage], elapsed: float) -> str:
        """格式化探索结果为 LLM 可读文本。"""
        if not pages:
            return f"[萌娘百科探索] 未找到与「{query}」相关的结果。"

        lines = [
            f"## 萌娘百科 探索: 「{query}」",
            f"探索 {len(pages)} 个页面, 耗时 {elapsed:.1f}s\n",
        ]

        for i, page in enumerate(pages):
            depth_label = "起始" if page.depth == 0 else f"深度{page.depth}"
            char_tag = " [角色页]" if page.is_character else ""
            lines.append(
                f"### [{i+1}] {page.title} ({depth_label}){char_tag}\n"
                f"  {page.url}\n"
                f"  {page.content_snippet}"
            )
            if page.related_names and page.depth == 0:
                top_related = page.related_names[:10]
                if top_related:
                    lines.append(
                        f"  🔗 相关: {', '.join(top_related)}"
                    )
            lines.append("")

        return "\n".join(lines)

    # ── 工具 ──

    @staticmethod
    def _normalize(s: str) -> str:
        return s.strip().lower()


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

def test_moegirl():
    """测试 MoegirlExplorer 基本功能。"""
    print("MoegirlExplorer 测试")
    print("=" * 60)

    explorer = MoegirlExplorer(timeout=20)

    # 测试角色搜索
    print("\n[测试1] 探索角色: '无量塔姬子'")
    result = explorer.explore("无量塔姬子", max_depth=1, max_pages=3)
    print(result[:800])
    print("...")

    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_moegirl()
