#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索编排器 — 多源深度搜索协调层。

协调多个 SourceAgent（B站wiki / 米游社 / 萌娘百科）并行执行，
合并去重结果，作为 LangChain Tool 供 MainGameAgent / ActionAgent 调用。

架构:
    SearchOrchestrator
    ├── SourceAgent (抽象基类)
    │   ├── BilibiliSourceAgent   → BilibiliExplorer (名字链条)
    │   ├── MiyousheSourceAgent   → 米游社编号字典 + 链条 (阶段3)
    │   └── MoegirlSourceAgent    → 萌娘百科 Playwright + 内链 (阶段4)
    └── 结果合并: 去重 + 按源标注 + 统一格式化

使用方式:
    orchestrator = SearchOrchestrator()
    result = orchestrator.deep_search("薇塔", sources=["bilibili", "baidu", "rag"])
"""

import time
import logging
import concurrent.futures
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class SourceResult:
    """单个搜索源的搜索结果。"""
    source: str                        # 源标识: "bilibili_wiki" / "miyoushe" / "moegirl" / "baidu" / "rag"
    success: bool                      # 搜索是否成功
    content: str = ""                  # 格式化后的搜索结果文本
    urls: List[str] = field(default_factory=list)  # 涉及的 URL 列表
    related_names: List[str] = field(default_factory=list)  # 发现的相关名字
    elapsed: float = 0.0               # 耗时 (秒)
    error: str = ""                    # 错误信息 (success=False 时)


@dataclass
class DeepSearchResult:
    """多源深度搜索的合并结果。"""
    query: str
    sources_used: List[str] = field(default_factory=list)
    source_results: List[SourceResult] = field(default_factory=list)
    merged_content: str = ""
    total_elapsed: float = 0.0
    total_pages_explored: int = 0


# ═══════════════════════════════════════════════════════════════
# SourceAgent 抽象基类
# ═══════════════════════════════════════════════════════════════

class SourceAgent(ABC):
    """搜索源 Agent 抽象基类。

    每个 SourceAgent 负责一个特定的搜索源，封装其搜索逻辑。
    子类只需实现 search() 方法，返回 SourceResult。
    """

    def __init__(self, name: str, timeout: int = 30):
        self.name = name
        self.timeout = timeout

    @abstractmethod
    def search(self, query: str) -> SourceResult:
        """执行搜索，返回结构化结果。

        Args:
            query: 搜索查询词

        Returns:
            SourceResult: 包含搜索内容、URL、耗时等
        """
        ...

    def search_with_timeout(self, query: str) -> SourceResult:
        """带超时保护的搜索包装器。

        在独立线程中执行 search()，超时则返回 error 结果。
        确保单个源卡死不阻塞整体搜索。
        """
        start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.search, query)
            try:
                result = future.result(timeout=self.timeout)
                result.elapsed = time.time() - start
                return result
            except concurrent.futures.TimeoutError:
                elapsed = time.time() - start
                logger.warning(f"[{self.name}] 搜索超时 ({self.timeout}s)")
                return SourceResult(
                    source=self.name,
                    success=False,
                    error=f"搜索超时 ({self.timeout}s)",
                    elapsed=elapsed,
                )
            except Exception as e:
                elapsed = time.time() - start
                logger.warning(f"[{self.name}] 搜索异常: {e}")
                return SourceResult(
                    source=self.name,
                    success=False,
                    error=str(e)[:200],
                    elapsed=elapsed,
                )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


# ═══════════════════════════════════════════════════════════════
# BilibiliSourceAgent — B站wiki 名字链条探索
# ═══════════════════════════════════════════════════════════════

class BilibiliSourceAgent(SourceAgent):
    """B站wiki 搜索源 Agent。

    利用 BilibiliExplorer 的名字链条机制：
    从一个名字出发 → 自动深挖相关页面 → 返回结构化知识网。

    特性:
    - "名字即编号": wiki.biligame.com/bh3/{名字} 直接定位
    - 链条式探索: 页面内链 → 评分 → 深入 → 再发现 → 循环
    - 2-3 层深度, 最多 6 个页面
    """

    def __init__(self, timeout: int = 30, max_depth: int = 2, max_pages: int = 6):
        super().__init__(name="bilibili_wiki", timeout=timeout)
        self.max_depth = max_depth
        self.max_pages = max_pages

    def search(self, query: str) -> SourceResult:
        """执行 B站wiki 链条式探索。"""
        from src.modules.web_search.wiki_explorer import BilibiliExplorer

        explorer = BilibiliExplorer(timeout=min(self.timeout, 12))
        content = explorer.explore(
            query,
            max_depth=self.max_depth,
            max_pages=self.max_pages,
        )

        # 解析探索结果的 URL 和名字
        urls, related_names = self._parse_result_metadata(content, query)

        return SourceResult(
            source=self.name,
            success=True,
            content=content,
            urls=urls,
            related_names=related_names,
        )

    # 相关名字过滤：排除 wiki 导航/管理页面
    _NOISE_NAMES = {
        "首页", "创建", "最近更改", "特殊:最近更改", "帮助", "讨论",
        "分类", "模板", "模块", "文件", "特殊", "Widget", "Gadget",
        "导航", "关于本站", "上传文件", "MediaWiki", "沙盒",
    }

    def _parse_result_metadata(self, content: str, query: str) -> Tuple[List[str], List[str]]:
        """从格式化的探索结果中提取 URL 和名字列表。"""
        urls = []
        related_names = []

        def _is_noise(name: str) -> bool:
            n = name.strip()
            if not n or len(n) < 2 or len(n) > 40:
                return True
            if n in self._NOISE_NAMES:
                return True
            if any(c in n for c in ("#", "?", "&", "=", "%", ":", "/")):
                return True
            return False

        for line in content.splitlines():
            line = line.strip()
            # URL 行: "  https://wiki.biligame.com/bh3/..."
            if line.startswith("https://wiki.biligame.com/bh3/"):
                urls.append(line)
            # 标题行: "### [1] 薇塔 (深度1)"
            elif line.startswith("### [") and "  " not in line:
                rest = line.split("] ", 1)
                if len(rest) > 1:
                    title_part = rest[1]
                    name = title_part.rsplit(" (", 1)[0].strip()
                    if name and name != query and not _is_noise(name):
                        related_names.append(name)
            # 相关标签行: "  🔗 相关: ..."
            elif "🔗 相关:" in line:
                names_str = line.split("🔗 相关:", 1)[1].strip()
                for n in names_str.split(", "):
                    n = n.strip()
                    if n and n not in related_names and not _is_noise(n):
                        related_names.append(n)

        return urls, related_names


# ═══════════════════════════════════════════════════════════════
# MoegirlSourceAgent — 萌娘百科 Playwright + 内链探索
# ═══════════════════════════════════════════════════════════════

class MoegirlSourceAgent(SourceAgent):
    """萌娘百科搜索源 Agent。

    使用 Playwright 真实浏览器绕过 Cloudflare 保护，
    从名字出发进行内链链条式深度搜索。

    特性:
    - Playwright 浏览器 (绕过 Cloudflare)
    - 双入口: 直连页面 + 站点搜索
    - 角色/非角色 URL 自动区分
    - 内链链条: 页面 → wiki 内链 → 评分 → 深入 → 循环
    - 2-3 层深度, 最多 5 个页面 (Playwright 较慢)
    """

    def __init__(self, timeout: int = 60, max_depth: int = 1, max_pages: int = 3):
        super().__init__(name="moegirl", timeout=timeout)
        self.max_depth = max_depth
        self.max_pages = max_pages

    def search(self, query: str) -> SourceResult:
        """执行萌娘百科链条式探索。"""
        from src.modules.web_search.moegirl_explorer import MoegirlExplorer

        explorer = MoegirlExplorer(
            timeout=min(self.timeout, 20),
            headless=True,
        )
        content = explorer.explore(
            query,
            max_depth=self.max_depth,
            max_pages=self.max_pages,
        )

        # 检测实际失败（内容为空或仅含错误信息）
        is_error = (
            not content
            or content.startswith("[萌娘百科探索] 未找到")
            or content.startswith("[萌娘百科探索] 查询为空")
            or content.startswith("[萌娘百科探索] 无法启动")
        )

        urls, related_names = self._parse_result_metadata(content, query)
        return SourceResult(
            source=self.name,
            success=not is_error,
            content=content,
            urls=urls,
            related_names=related_names,
            error="未找到相关页面" if is_error else "",
        )

    # 与 BilibiliSourceAgent 共享相同的噪音过滤
    _NOISE_NAMES = {
        "首页", "创建", "最近更改", "特殊:最近更改", "帮助", "讨论",
        "分类", "模板", "模块", "文件", "特殊", "Widget", "Gadget",
        "导航", "关于本站", "上传文件", "MediaWiki", "沙盒",
        "Main Page", "萌娘百科", "免责声明", "隐私权政策",
        "Cookie声明", "手机版视图", "知识共享", "社区首页",
        "方针", "帮助中心", "用户协议", "版权声明",
        "编辑帮助", "规范", "当前活动", "巡查",
    }

    def _parse_result_metadata(self, content: str, query: str) -> Tuple[List[str], List[str]]:
        """从格式化的探索结果中提取 URL 和名字列表。"""
        urls = []
        related_names = []

        def _is_noise(name: str) -> bool:
            n = name.strip()
            if not n or len(n) < 2 or len(n) > 40:
                return True
            if n in self._NOISE_NAMES:
                return True
            if any(c in n for c in ("#", "?", "&", "=", "%", ":", "/")):
                return True
            return False

        for line in content.splitlines():
            line = line.strip()
            # URL 行
            if line.startswith("https://zh.moegirl.org.cn/") or line.startswith("https://mzh.moegirl.org.cn/"):
                urls.append(line)
            # 标题行
            elif line.startswith("### [") and "  " not in line:
                rest = line.split("] ", 1)
                if len(rest) > 1:
                    title_part = rest[1]
                    name = title_part.rsplit(" (", 1)[0].strip()
                    if name and name != query and not _is_noise(name):
                        related_names.append(name)
            # 相关标签行
            elif "🔗 相关:" in line:
                names_str = line.split("🔗 相关:", 1)[1].strip()
                for n in names_str.split(", "):
                    n = n.strip()
                    if n and n not in related_names and not _is_noise(n):
                        related_names.append(n)

        return urls, related_names


# ═══════════════════════════════════════════════════════════════
# MiyousheSourceAgent — 米游社编号字典 + 内容ID精确搜索
# ═══════════════════════════════════════════════════════════════

class MiyousheSourceAgent(SourceAgent):
    """米游社百科搜索源 Agent。

    利用本地 3328 条 名称→content_id 字典实现精确搜索。
    米游社百科是游戏官方数据最完整的来源（武器/圣痕数值、角色详情）。

    特性:
    - 名称→content_id 字典 (3328 条, 覆盖全 data/ 目录树)
    - 精确匹配 + 模糊匹配
    - 本地缓存优先 (data/ JSON → HTTP 兜底)
    - 内容链条: 内容 → 匹配字典名 → 发现关联条目 → 深入
    - 分类标注: 图鉴/女武神, 图鉴/武器, 档案/角色, ...
    """

    def __init__(self, timeout: int = 20, max_depth: int = 1, max_pages: int = 4):
        super().__init__(name="miyoushe", timeout=timeout)
        self.max_depth = max_depth
        self.max_pages = max_pages

    def search(self, query: str) -> SourceResult:
        """执行米游社百科链条式探索。"""
        from src.modules.web_search.miyoushe_explorer import MiyousheExplorer

        explorer = MiyousheExplorer(timeout=min(self.timeout, 12))
        content = explorer.explore(
            query,
            max_depth=self.max_depth,
            max_pages=self.max_pages,
        )

        is_error = (
            not content
            or content.startswith("[米游社百科探索] 未找到")
            or content.startswith("[米游社百科探索] 查询为空")
        )

        urls, related_names = self._parse_result_metadata(content, query)
        return SourceResult(
            source=self.name,
            success=not is_error,
            content=content,
            urls=urls,
            related_names=related_names,
            error="未找到相关条目" if is_error else "",
        )

    _NOISE_NAMES = {
        "首页", "创建", "最近更改", "帮助", "讨论", "导航",
        "分类", "模板", "模块", "文件", "特殊", "MediaWiki",
    }

    def _parse_result_metadata(self, content: str, query: str) -> Tuple[List[str], List[str]]:
        urls = []
        related_names = []

        def _is_noise(name: str) -> bool:
            n = name.strip()
            if not n or len(n) < 2 or len(n) > 40:
                return True
            if n in self._NOISE_NAMES:
                return True
            if any(c in n for c in ("#", "?", "&", "=", "%", ":", "/")):
                return True
            return False

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("https://baike.mihoyo.com/bh3/wiki/content/"):
                urls.append(line)
            elif line.startswith("### [") and "  " not in line:
                rest = line.split("] ", 1)
                if len(rest) > 1:
                    title_part = rest[1]
                    # 格式: "薪炎之律者 [图鉴/女武神] (起始)"
                    name = title_part.rsplit(" [", 1)[0].rsplit(" (", 1)[0].strip()
                    if name and name != query and not _is_noise(name):
                        related_names.append(name)
            elif "🔗 相关:" in line:
                names_str = line.split("🔗 相关:", 1)[1].strip()
                for n in names_str.split(", "):
                    n = n.strip()
                    if n and n not in related_names and not _is_noise(n):
                        related_names.append(n)

        return urls, related_names


# ═══════════════════════════════════════════════════════════════
# SearchOrchestrator — 多源协调器
# ═══════════════════════════════════════════════════════════════

class SearchOrchestrator:
    """搜索编排器 — 协调多个 SourceAgent 并行执行。

    功能:
    1. 按需激活 SourceAgent（通过 sources 参数控制）
    2. 并行执行所有激活的源
    3. 合并去重结果
    4. 统一格式化输出

    使用方式:
        orchestrator = SearchOrchestrator()
        result = orchestrator.deep_search("薇塔", sources=["bilibili", "baidu", "rag"])
        print(result.merged_content)
    """

    # 所有已注册的源标识符
    KNOWN_SOURCES = {"bilibili", "miyoushe", "moegirl", "baidu", "rag"}

    def __init__(self):
        self._source_agents: Dict[str, SourceAgent] = {}

    # ── SourceAgent 注册 ──

    def _get_or_create_agent(self, source: str) -> Optional[SourceAgent]:
        """懒加载获取 SourceAgent 实例。"""
        if source in self._source_agents:
            return self._source_agents[source]

        agent: Optional[SourceAgent] = None

        if source == "bilibili":
            agent = BilibiliSourceAgent(timeout=30)
        elif source == "miyoushe":
            agent = MiyousheSourceAgent(timeout=20)
        elif source == "moegirl":
            agent = MoegirlSourceAgent(timeout=60)
        elif source == "baidu":
            # 百度搜索由 WebSearcher 直接处理，不走 SourceAgent 抽象
            # 这里创建一个内联的 SourceAgent 适配
            agent = _BaiduSourceAgent(timeout=25)
        elif source == "rag":
            # RAG 搜索需要 rag_engine，由外部注入
            logger.debug(f"RAG SourceAgent 需要 rag_engine 注入")
            return None
        else:
            logger.warning(f"未知搜索源: {source}")
            return None

        if agent:
            self._source_agents[source] = agent
        return agent

    def set_rag_engine(self, rag_engine):
        """注入 RAG 引擎（用于 RAG SourceAgent）。"""
        self._source_agents["rag"] = _RagSourceAgent(rag_engine, timeout=30)

    # ── 主入口 ──

    def deep_search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        rag_engine=None,
    ) -> DeepSearchResult:
        """执行多源深度搜索。

        Args:
            query: 搜索查询词
            sources: 要使用的源列表，默认 ["bilibili", "baidu"]
                     可选: "bilibili", "baidu", "rag", "miyoushe", "moegirl"
            rag_engine: RAG 引擎实例 (使用 "rag" 源时必需)

        Returns:
            DeepSearchResult: 包含各源结果和合并内容
        """
        if sources is None:
            sources = ["bilibili", "baidu"]

        if "rag" in sources and rag_engine is not None:
            self.set_rag_engine(rag_engine)

        start_time = time.time()
        source_results: List[SourceResult] = []
        sources_used: List[str] = []

        # ── 准备要执行的源 ──
        tasks: List[Tuple[str, SourceAgent]] = []
        for source in sources:
            if source not in self.KNOWN_SOURCES:
                logger.warning(f"跳过未知搜索源: {source}")
                continue
            # RAG 需要 rag_engine
            if source == "rag" and (rag_engine is None and "rag" not in self._source_agents):
                logger.debug("RAG 源跳过: rag_engine 未注入")
                continue
            # 所有源均已实现

            agent = self._get_or_create_agent(source)
            if agent is None:
                continue
            tasks.append((source, agent))

        if not tasks:
            return DeepSearchResult(
                query=query,
                sources_used=[],
                merged_content="[深度搜索] 没有可用的搜索源。",
                total_elapsed=time.time() - start_time,
            )

        # ── 并行执行 ──
        max_workers = min(len(tasks), 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map: dict = {}
            for source, agent in tasks:
                future = executor.submit(agent.search_with_timeout, query)
                future_map[future] = source

            for future in concurrent.futures.as_completed(future_map):
                source = future_map[future]
                try:
                    result = future.result(timeout=60)
                    source_results.append(result)
                    if result.success:
                        sources_used.append(source)
                except Exception as e:
                    logger.warning(f"[{source}] 搜索线程异常: {e}")
                    source_results.append(SourceResult(
                        source=source,
                        success=False,
                        error=str(e)[:200],
                    ))

        # ── 合并结果 ──
        merged = self._merge_results(query, source_results)
        total_elapsed = time.time() - start_time
        total_pages = sum(len(r.urls) for r in source_results if r.success)

        return DeepSearchResult(
            query=query,
            sources_used=sources_used,
            source_results=source_results,
            merged_content=merged,
            total_elapsed=total_elapsed,
            total_pages_explored=total_pages,
        )

    # ── 结果合并 ──

    def _merge_results(self, query: str, results: List[SourceResult]) -> str:
        """合并多个源的搜索结果，按优先级排列。"""
        if not results:
            return f"[深度搜索] 未找到与「{query}」相关的结果。"

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        if not successful:
            errors = "\n".join(f"  - {r.source}: {r.error}" for r in failed)
            return f"[深度搜索] 所有搜索源均失败:\n{errors}"

        lines = [
            f"## 深度搜索: 「{query}」",
            f"使用 {len(successful)} 个搜索源, 共探索 {sum(len(r.urls) for r in successful)} 个页面\n",
        ]

        for i, result in enumerate(successful):
            source_label = _SOURCE_LABELS.get(result.source, result.source)
            lines.append(f"---\n### 来源 {i+1}: {source_label}\n")
            lines.append(result.content)
            lines.append("")

        # 汇总发现的相关名字
        all_related = []
        seen_names = set()
        for r in successful:
            for name in r.related_names:
                if name not in seen_names and name != query:
                    all_related.append(name)
                    seen_names.add(name)

        if all_related:
            lines.append(f"---\n### 🔗 发现的相关事物 ({len(all_related)}):")
            lines.append(", ".join(all_related[:20]))

        # 失败源提示
        if failed:
            failed_names = [_SOURCE_LABELS.get(r.source, r.source) for r in failed]
            lines.append(f"\n> ⚠️ 以下源搜索失败: {', '.join(failed_names)}")

        return "\n".join(lines)


# ── 源标签映射 ──

_SOURCE_LABELS = {
    "bilibili_wiki": "📺 B站wiki 深度探索",
    "baidu": "🌐 百度搜索",
    "rag": "📚 RAG 知识库",
    "miyoushe": "🎮 米游社百科",
    "moegirl": "📖 萌娘百科",
}


# ═══════════════════════════════════════════════════════════════
# 内联 SourceAgent 适配器
# ═══════════════════════════════════════════════════════════════

class _BaiduSourceAgent(SourceAgent):
    """百度搜索适配器 — 将 WebSearcher 包装为 SourceAgent 接口。"""

    def __init__(self, timeout: int = 25):
        super().__init__(name="baidu", timeout=timeout)

    def search(self, query: str) -> SourceResult:
        from src.modules.web_search.web_searcher import WebSearcher, SearchEngine, SearchResult

        searcher = WebSearcher(engine=SearchEngine.BAIDU, timeout=min(self.timeout, 15))
        resp = searcher.search_with_context(query, "")
        results = resp.get("results", [])

        if not results:
            return SourceResult(
                source=self.name,
                success=True,
                content="未找到相关搜索结果。",
            )

        sr = [
            SearchResult(
                title=r["title"], url=r["url"], snippet=r["snippet"],
                source=r["source"], relevance=r["relevance"],
            )
            for r in results
        ]
        answer = searcher.extract_answers(query, sr)

        urls = [r["url"] for r in results[:5] if r.get("url")]
        titles = [r["title"] for r in results[:5] if r.get("title")]

        return SourceResult(
            source=self.name,
            success=True,
            content=answer,
            urls=urls,
            related_names=titles,
        )


class _RagSourceAgent(SourceAgent):
    """RAG 知识库适配器 — 将 RAGEngine 包装为 SourceAgent 接口。"""

    def __init__(self, rag_engine, timeout: int = 30):
        super().__init__(name="rag", timeout=timeout)
        self._rag_engine = rag_engine

    def search(self, query: str) -> SourceResult:
        import asyncio as _asyncio

        # 查询扩展
        try:
            from src.modules.agent.react_agent import _expand_query
            expanded_query = _expand_query(query, self._rag_engine)
        except Exception:
            expanded_query = query

        def _run():
            return _asyncio.run(
                self._rag_engine.search(query=expanded_query, mode="hybrid", top_k=20)
            )

        try:
            with concurrent.futures.ThreadPoolExecutor() as ex:
                future = ex.submit(_run)
                results = future.result(timeout=25)
        except Exception as e:
            return SourceResult(
                source=self.name,
                success=False,
                error=f"RAG搜索失败: {e}",
            )

        try:
            from src.modules.agent.react_agent import _format_rag_results, _get_shared_reranker
            reranker = _get_shared_reranker()
            content = _format_rag_results(results, expanded_query, top_k=5, min_score=0.012, reranker=reranker)
        except Exception:
            # 回退：使用原始 RAG 结果格式化
            lines = []
            for r in results[:5]:
                lines.append(f"- **{getattr(r, 'title', '未知')}**")
                snippet = getattr(r, 'content', '')[:300]
                if snippet:
                    lines.append(f"  {snippet}")
            content = "\n".join(lines) if lines else "无相关结果。"

        urls = [getattr(r, 'url', '') for r in results[:5] if getattr(r, 'url', '')]
        titles = [getattr(r, 'title', '') for r in results[:5] if getattr(r, 'title', '')]

        return SourceResult(
            source=self.name,
            success=True,
            content=content,
            urls=urls,
            related_names=titles,
        )


# ═══════════════════════════════════════════════════════════════
# 便捷函数 — 供 Agent Tool 直接调用
# ═══════════════════════════════════════════════════════════════

# 全局单例 (輕量级，无模型加载，安全使用单例)
_orchestrator: Optional[SearchOrchestrator] = None


def get_orchestrator() -> SearchOrchestrator:
    """获取 SearchOrchestrator 全局单例。"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SearchOrchestrator()
    return _orchestrator


def deep_search(
    query: str,
    sources: Optional[List[str]] = None,
    rag_engine=None,
) -> str:
    """执行多源深度搜索（便捷函数）。

    并行运行 B站wiki + 百度搜索 等源，合并返回结构化结果。
    供 LangChain Tool 直接调用。

    Args:
        query: 搜索查询词
        sources: 源列表，默认 ["bilibili", "baidu"]
        rag_engine: RAG 引擎 (使用 "rag" 源时提供)

    Returns:
        格式化的搜索结果文本
    """
    orchestrator = get_orchestrator()
    result = orchestrator.deep_search(
        query=query,
        sources=sources,
        rag_engine=rag_engine,
    )
    return result.merged_content


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

def test_orchestrator():
    """测试 SearchOrchestrator 基本功能。"""
    print("SearchOrchestrator 测试")
    print("=" * 60)

    orchestrator = SearchOrchestrator()

    # 测试 1: 基本搜索 (B站 + 百度)
    print("\n[测试1] 基本深度搜索: '薇塔'")
    result = orchestrator.deep_search("薇塔", sources=["bilibili", "baidu"])
    print(f"  耗时: {result.total_elapsed:.1f}s")
    print(f"  成功源: {result.sources_used}")
    print(f"  探索页面: {result.total_pages_explored}")
    print(f"  结果长度: {len(result.merged_content)} 字符")
    print(f"  结果预览:\n{result.merged_content[:500]}...")

    # 测试 2: 仅 B站
    print("\n[测试2] 仅B站wiki: '琪亚娜'")
    result = orchestrator.deep_search("琪亚娜", sources=["bilibili"])
    print(f"  耗时: {result.total_elapsed:.1f}s")
    print(f"  成功源: {result.sources_used}")
    print(f"  结果预览:\n{result.merged_content[:400]}...")

    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_orchestrator()
