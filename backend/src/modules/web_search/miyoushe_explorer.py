#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
米游社百科探索器 — 编号字典 + 内容ID精确搜索。

米游社百科 (baike.mihoyo.com/bh3/wiki) 使用数字编号系统：
  content/{编号}/detail → 精确内容页

本模块利用 data/图鉴/ 中的 JSON 爬取数据构建 名称→content_id 字典，
实现从名字出发的精确搜索和链条式内容探索。

特性:
- 名称→content_id 字典 (1982 条, 覆盖女武神/武器/圣痕/敌人/人偶/材料等)
- 精确匹配 + 模糊匹配 (前缀/子串)
- 内容提取 (requests 直连, 无 Cloudflare)
- 链条探索: 页面内容 → 匹配字典中的名字 → 发现关联事物 → 深入
- 分类标注: 女武神/武器/圣痕/敌人/人偶/材料/...

URL 格式:
  精确页面: https://baike.mihoyo.com/bh3/wiki/content/{编号}/detail?bbs_presentation_style=no_header
"""

import os as _os
import json as _json
import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 名称→content_id 字典
# ═══════════════════════════════════════════════════════════════

@dataclass
class MiyousheEntry:
    """米游社百科条目。"""
    name: str                 # 中文名称
    content_id: int           # 内容编号
    category: str             # 分类: 女武神/武器/圣痕/敌人/人偶/材料/...
    url: str = ""             # 完整 URL
    title: str = ""           # 页面标题


class MiyousheIdDict:
    """米游社 名称→content_id 字典 — 单例，延迟加载。

    从 data/ 目录树中所有 JSON 文件构建索引。
    支持同名多分类（如"识之律者"同时是女武神和敌人），全部保留。

    覆盖 3347 条目，3328 个唯一名字（17 个名字跨多分类）。
    """

    # 分类优先级 (用于 lookup_best): 数字越小越优先
    _CAT_RANK = {
        "女武神": 0, "角色": 0, "武器": 2, "圣痕": 3, "协同者": 4,
        "人偶": 5, "敌人": 6, "材料": 7, "宿舍名册": 8,
    }

    def __init__(self):
        self._entries: Dict[str, List[MiyousheEntry]] = {}  # name → [entries] (一个名字可能有多个分类)
        self._id_to_entry: Dict[int, MiyousheEntry] = {}
        self._loaded = False
        self._lock = Lock()
        self._name_index: Dict[str, List[str]] = {}   # 前缀索引: 前2字 → names
        self._total_entries = 0

    @staticmethod
    def _resolve_data_dir() -> str:
        """解析 data/ 目录的绝对路径（工程根目录下的 data/）。"""
        candidates = []
        try:
            file_dir = _os.path.dirname(_os.path.abspath(__file__))
            proj_root = _os.path.normpath(_os.path.join(file_dir, "..", "..", "..", ".."))
            candidates.append(_os.path.join(proj_root, "data"))
        except Exception:
            pass
        candidates.append(_os.path.join(_os.getcwd(), "data"))
        env_root = _os.environ.get("BBB_ASSISTANT_ROOT", "")
        if env_root:
            candidates.append(_os.path.join(env_root, "data"))
        for path in candidates:
            normalized = _os.path.normpath(path)
            if _os.path.isdir(normalized):
                return normalized
        return _os.path.normpath(candidates[0]) if candidates else ""

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def size(self) -> int:
        """总条目数（含跨分类重复名）。"""
        self._ensure_loaded()
        return self._total_entries

    @property
    def unique_names(self) -> int:
        """唯一名字数。"""
        self._ensure_loaded()
        return len(self._entries)

    @classmethod
    def _cat_rank(cls, entry: MiyousheEntry) -> int:
        """获取条目的分类优先级数字（越小越优先）。"""
        leaf = entry.category.split("/")[-1] if "/" in entry.category else entry.category
        return cls._CAT_RANK.get(leaf, 10)

    def _ensure_loaded(self):
        """延迟加载索引 — 扫描整个 data/ 目录树，同名全保留。"""
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            data_dir = self._resolve_data_dir()
            if not data_dir or not _os.path.isdir(data_dir):
                logger.warning(f"数据目录不存在: {data_dir}")
                self._loaded = True
                return

            count = 0
            for root, dirs, files in _os.walk(data_dir):
                for fname in files:
                    if not fname.endswith(".json"):
                        continue
                    fpath = _os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = _json.load(f)
                    except Exception:
                        continue

                    content_id = data.get("content_id")
                    if not content_id:
                        continue

                    name = fname.replace(".json", "").strip()
                    if not name or len(name) < 1:
                        continue

                    # 分类层级: data/ 下的相对路径
                    rel_path = _os.path.relpath(root, data_dir)
                    if rel_path == ".":
                        category = "综合"
                    else:
                        parts = rel_path.replace("\\", "/").split("/")
                        category = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]

                    entry = MiyousheEntry(
                        name=name,
                        content_id=int(content_id),
                        category=category,
                        url=f"https://baike.mihoyo.com/bh3/wiki/content/{content_id}/detail?bbs_presentation_style=no_header",
                        title=data.get("title", ""),
                    )

                    # ★ 同名全保留，追加到列表
                    if name not in self._entries:
                        self._entries[name] = []
                    self._entries[name].append(entry)

                    self._id_to_entry[int(content_id)] = entry

                    # 前缀索引
                    prefix = name[:2]
                    if prefix not in self._name_index:
                        self._name_index[prefix] = []
                    if name not in self._name_index[prefix]:
                        self._name_index[prefix].append(name)

                    count += 1

            self._total_entries = count
            self._loaded = True
            multi = sum(1 for v in self._entries.values() if len(v) > 1)
            logger.info(
                f"米游社ID字典加载完成: {count} 条目, {len(self._entries)} 唯一名"
                + (f", {multi} 名跨多分类" if multi else "")
            )

    # ── 查找 ──

    def lookup(self, name: str) -> List[MiyousheEntry]:
        """精确查找名称 — 返回所有分类的条目列表。

        大多数名字只有 1 个条目；17 个跨分类名字（如识之律者=女武神+敌人）返回多个。
        """
        self._ensure_loaded()
        return self._entries.get(name, [])

    def lookup_best(self, name: str) -> Optional[MiyousheEntry]:
        """精确查找名称 — 返回优先级最高的条目。

        按分类优先级: 女武神 > 武器 > 圣痕 > 协同者 > 人偶 > 敌人 > 材料 > 其他
        用于只需要一个结果的场景。
        """
        entries = self.lookup(name)
        if not entries:
            return None
        if len(entries) == 1:
            return entries[0]
        # 按分类优先级排序，取最优
        return min(entries, key=self._cat_rank)

    def lookup_by_id(self, content_id: int) -> Optional[MiyousheEntry]:
        """通过 content_id 查找。"""
        self._ensure_loaded()
        return self._id_to_entry.get(content_id)

    def search(self, query: str, top_k: int = 5) -> List[MiyousheEntry]:
        """模糊搜索名称 — 返回去重后的条目列表。

        每个名字只返回优先级最高的条目，避免同名多分类占满结果。
        同名多分类信息可通过 lookup() 获取完整列表。
        """
        self._ensure_loaded()
        if not query:
            return []

        query_lower = query.lower().strip()
        scored: List[Tuple[MiyousheEntry, int]] = []
        seen_names = set()

        def _add(entry: MiyousheEntry, score: int):
            """添加条目，同名字只保留分数最高的。"""
            if entry.name in seen_names:
                # 更新已有条目的分数（取更高分）
                for i, (e, s) in enumerate(scored):
                    if e.name == entry.name:
                        if score > s:
                            scored[i] = (entry, score)
                        return
            scored.append((entry, score))
            seen_names.add(entry.name)

        # 第一轮: 精确匹配 — 返回该名字的所有条目中最优的
        exact_list = self._entries.get(query, [])
        if exact_list:
            best = min(exact_list, key=self._cat_rank)
            _add(best, 100)

        # 第二轮: 前缀/子串匹配
        for name, entries in self._entries.items():
            if name in seen_names:
                continue
            name_lower = name.lower()
            score = 0
            if name_lower.startswith(query_lower):
                score = 80 - min(len(name) - len(query), 20)
            elif query_lower in name_lower:
                score = 50
            elif query_lower[:2] in name_lower:
                score = 20
            if score > 0:
                best = min(entries, key=self._cat_rank)
                _add(best, score)

        # 第三轮: 字符重叠
        if len(scored) < top_k:
            query_chars = set(query_lower)
            for name, entries in self._entries.items():
                if name in seen_names:
                    continue
                overlap = len(query_chars & set(name.lower()))
                if overlap >= 2:
                    best = min(entries, key=self._cat_rank)
                    _add(best, overlap * 5)

        scored.sort(key=lambda x: x[1], reverse=True)
        return [e for e, _ in scored[:top_k]]

    def find_names_in_text(self, text: str, max_results: int = 15) -> List[str]:
        """在文本中查找已知的米游社条目名（用于发现关联事物）。

        按名称长度降序匹配。返回名字列表（去重）。
        """
        self._ensure_loaded()
        if not text:
            return []

        found = []
        seen = set()
        sorted_names = sorted(self._entries.keys(), key=len, reverse=True)

        for name in sorted_names:
            if len(found) >= max_results:
                break
            if name in seen or len(name) < 2:
                continue
            if name in text:
                found.append(name)
                seen.add(name)

        return found


# ── 全局单例 ──

_id_dict: Optional[MiyousheIdDict] = None
_id_dict_lock = Lock()


def get_id_dict() -> MiyousheIdDict:
    """获取 MiyousheIdDict 全局单例。"""
    global _id_dict
    if _id_dict is None:
        with _id_dict_lock:
            if _id_dict is None:
                _id_dict = MiyousheIdDict()
    return _id_dict


# ═══════════════════════════════════════════════════════════════
# MiyousheExplorer — 编号链条探索器
# ═══════════════════════════════════════════════════════════════

@dataclass
class MiyoushePage:
    """米游社页面探索结果。"""
    name: str
    content_id: int
    url: str
    title: str = ""
    content_snippet: str = ""
    category: str = ""
    related_names: List[str] = field(default_factory=list)
    depth: int = 0
    error: str = ""


class MiyousheExplorer:
    """米游社百科探索器 — ID 编号 + 内容链条式深度搜索。

    使用方式:
        explorer = MiyousheExplorer()
        result = explorer.explore("薪炎之律者", max_depth=1, max_pages=3)
    """

    BASE = "https://baike.mihoyo.com/bh3/wiki/content"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    def __init__(self, timeout: int = 12, content_chars: int = 1000):
        self.timeout = timeout
        self.content_chars = content_chars

    # ── 主入口 ──

    def explore(self, query: str, max_depth: int = 2, max_pages: int = 5) -> str:
        """从名字出发，探索米游社百科。

        Args:
            query: 搜索词 (角色名/武器名/圣痕名/...)
            max_depth: 最大探索深度 (1-3)
            max_pages: 总页面数上限

        Returns:
            格式化的探索结果文本
        """
        if not query or not query.strip():
            return "[米游社百科探索] 查询为空。"

        name = query.strip()
        start_time = time.time()
        id_dict = get_id_dict()
        visited_ids: set = set()
        pages: List[MiyoushePage] = []

        # ── 智能查询: 尝试从查询中提取已知实体名 ──
        search_name = self._resolve_query(name, id_dict)

        # ── 第一层: 查找起始条目 ──
        root = self._find_and_fetch(search_name, id_dict, depth=0)
        if root.error and search_name != name:
            # 回退到原始查询的模糊搜索（仅当智能解析失败时）
            candidates = id_dict.search(name, top_k=3)
            if candidates:
                root = self._fetch_page(candidates[0], id_dict, depth=0)

        if root.error:
            return f"[米游社百科探索] 未找到「{name}」的相关条目。"

        visited_ids.add(root.content_id)
        pages.append(root)

        # ── 收集候选 (从内容中提取已知名字) ──
        candidates = self._extract_candidates(
            root, id_dict, visited_ids, top_k=5
        )

        # ── 深层探索 ──
        depth = 1
        while depth <= max_depth and len(pages) < max_pages and candidates:
            next_candidates = []
            for entry in candidates:
                if len(pages) >= max_pages:
                    break
                if entry.content_id in visited_ids:
                    continue
                visited_ids.add(entry.content_id)

                page = self._fetch_page(entry, id_dict, depth=depth)
                if page.error:
                    continue
                pages.append(page)

                if depth < max_depth:
                    new_candidates = self._extract_candidates(
                        page, id_dict, visited_ids, top_k=3
                    )
                    next_candidates.extend(new_candidates)

            candidates = next_candidates
            depth += 1

        elapsed = time.time() - start_time
        return self._format_result(query, pages, elapsed)

    # ── 智能查询解析 ──

    # 常见游戏前缀（查询时剥离）
    _GAME_PREFIXES = ["崩坏3 ", "崩坏三 ", "崩坏3", "崩坏三", "bh3 ", "honkai ", "bh3", "honkai"]

    @classmethod
    def _resolve_query(cls, query: str, id_dict: MiyousheIdDict) -> str:
        """从复合查询中提取最佳搜索词。

        例如 "崩坏3 符华" → "符华"
            "凯文 崩坏3" → "凯文·卡斯兰娜"（简称扩展为全名）
            "薪炎之律者 攻略" → "薪炎之律者"

        策略:
        1. 原始查询精确命中 → 直接返回
        2. 剥离游戏前缀/后缀后精确命中 → 返回
        3. 对每个查询词做前缀搜索（简称扩展为全名）
        4. 用字典在查询文本中找已知名字
        5. 回退原文
        """
        name = query.strip()
        if not name:
            return name

        # 1) 精确命中
        if id_dict.lookup_best(name):
            return name

        # 2) 剥离游戏前后缀
        stripped = name
        for prefix in cls._GAME_PREFIXES:
            low = stripped.lower()
            pfx = prefix.lower().rstrip()
            if low.startswith(pfx):
                stripped = stripped[len(pfx):].strip()
                break
            if low.endswith(pfx):
                stripped = stripped[:-len(pfx)].strip()
                break
        if stripped and stripped != name and id_dict.lookup_best(stripped):
            return stripped

        # 3) 简称→全名扩展: 对每个查询词做前缀搜索
        words = [w.strip() for w in name.split() if len(w.strip()) >= 2]
        # 过滤游戏名等无意义词
        _noise = {"崩坏3", "崩坏三", "bh3", "honkai", "攻略", "剧情", "背景", "技能", "介绍", "什么", "如何", "怎么"}
        words = [w for w in words if w.lower() not in _noise]

        if words:
            best_candidate = None
            best_score = -1
            for word in words:
                # 前缀搜索: 找以该词开头的字典名字
                candidates = id_dict.search(word, top_k=5)
                for c in candidates:
                    # 评分: 名字越短越精确(接近原词), 分类越高越好
                    # 奖励完全匹配(名字就是该词本身)、惩罚过长名字(含后缀)
                    extra_len = len(c.name) - len(word)
                    score = (20 - min(extra_len, 15)) + (15 - MiyousheIdDict._cat_rank(c))
                    if score > best_score:
                        best_score = score
                        best_candidate = c.name

            if best_candidate:
                return best_candidate

        # 4) 在查询文本中匹配已知名字
        found = id_dict.find_names_in_text(name, max_results=10)
        if found:
            exact_contains = [n for n in found if n in name or name in n]
            if exact_contains:
                best = max(exact_contains, key=lambda n: (
                    len(set(n) & set(name)),
                    len(n),
                ))
                return best

        # 5) 回退
        return name

    # ── 页面查找与抓取 ──

    def _find_and_fetch(self, name: str, id_dict: MiyousheIdDict, depth: int = 0) -> MiyoushePage:
        """查找并抓取页面。同名多分类时取优先级最高的条目。"""
        entry = id_dict.lookup_best(name)
        if not entry:
            return MiyoushePage(
                name=name, content_id=0, url="", depth=depth,
                error=f"未找到条目: {name}",
            )
        return self._fetch_page(entry, id_dict, depth)

    def _fetch_page(
        self, entry: MiyousheEntry, id_dict: MiyousheIdDict, depth: int = 0
    ) -> MiyoushePage:
        """抓取并解析一个米游社百科页面。

        优先从本地 JSON 缓存读取 (data/图鉴/)，缓存未命中时发起 HTTP 请求。
        """
        import requests as _requests

        # ── 第一步: 尝试本地缓存 ──
        local_content = self._read_local_cache(entry)
        if local_content:
            related = id_dict.find_names_in_text(local_content, max_results=10)
            # 过滤掉自己
            related = [n for n in related if n != entry.name]
            return MiyoushePage(
                name=entry.name,
                content_id=entry.content_id,
                url=entry.url,
                title=entry.title or entry.name,
                content_snippet=local_content[:self.content_chars],
                category=entry.category,
                related_names=related,
                depth=depth,
            )

        # ── 第二步: HTTP 请求 ──
        try:
            resp = _requests.get(entry.url, headers=self.HEADERS, timeout=self.timeout)
            resp.raise_for_status()

            from bs4 import BeautifulSoup as _BS
            soup = _BS(resp.text, "html.parser")

            # 提取正文
            content = self._extract_content(soup)
            content_snippet = content[:self.content_chars] if content else ""

            if not content_snippet or len(content_snippet) < 20:
                return MiyoushePage(
                    name=entry.name, content_id=entry.content_id,
                    url=entry.url, title=entry.title or entry.name,
                    category=entry.category, depth=depth,
                    error="页面内容过短",
                )

            related = id_dict.find_names_in_text(content, max_results=10)
            related = [n for n in related if n != entry.name]

            return MiyoushePage(
                name=entry.name,
                content_id=entry.content_id,
                url=entry.url,
                title=entry.title or entry.name,
                content_snippet=content_snippet,
                category=entry.category,
                related_names=related,
                depth=depth,
            )

        except Exception as e:
            logger.debug(f"MiyousheExplorer: 获取「{entry.name}」(id={entry.content_id}) 失败: {e}")
            return MiyoushePage(
                name=entry.name, content_id=entry.content_id,
                url=entry.url, depth=depth,
                error=str(e)[:100],
            )

    def _read_local_cache(self, entry: MiyousheEntry) -> str:
        """从本地 JSON 缓存读取内容（搜索整个 data/ 目录）。"""
        data_dir = get_id_dict()._resolve_data_dir()

        for root, dirs, files in _os.walk(data_dir):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                name_no_ext = fname.replace(".json", "").strip()
                if name_no_ext != entry.name:
                    continue
                fpath = _os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = _json.load(f)
                    if data.get("content_id") == entry.content_id:
                        content = data.get("main_content", "")
                        if content and len(content) > 20:
                            return content
                except Exception:
                    continue

        return ""

    # ── 内容提取 ──

    def _extract_content(self, soup) -> str:
        """提取米游社百科页面的正文内容。"""
        # 移除噪音
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        # 优先主内容区
        selectors = [
            ".mhy-img-text-article__content",  # 米游社文章内容
            ".article-content",
            ".wiki-content",
            ".content",
            "main",
            "article",
            "#content",
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(separator="\n", strip=True)
                lines = [
                    ln.strip() for ln in text.splitlines()
                    if ln.strip() and len(ln.strip()) > 2
                ]
                return "\n".join(lines)

        # 回退 body
        if soup.body:
            text = soup.body.get_text(separator="\n", strip=True)
            lines = [
                ln.strip() for ln in text.splitlines()
                if ln.strip() and len(ln.strip()) > 2
            ]
            return "\n".join(lines)

        return ""

    # ── 候选提取 ──

    def _extract_candidates(
        self,
        page: MiyoushePage,
        id_dict: MiyousheIdDict,
        visited_ids: set,
        top_k: int = 5,
    ) -> List[MiyousheEntry]:
        """从页面的关联名字中提取高价值候选条目。"""
        entries = []
        seen_cat = set()
        for name in page.related_names[:top_k * 2]:
            # 获取该名字的所有条目（同名多分类时全部加入）
            all_entries = id_dict.lookup(name)
            if not all_entries:
                continue
            for entry in all_entries:
                if entry.content_id in visited_ids:
                    continue
                # 同名同分类去重
                cat_key = (entry.name, entry.category)
                if cat_key in seen_cat:
                    continue
                seen_cat.add(cat_key)
                entries.append(entry)
                if len(entries) >= top_k:
                    break
            if len(entries) >= top_k:
                break

        # 按分类优先级排序
        entries.sort(key=MiyousheIdDict._cat_rank)
        return entries[:top_k]

    # ── 输出格式化 ──

    def _format_result(self, query: str, pages: List[MiyoushePage], elapsed: float) -> str:
        """格式化探索结果为 LLM 可读文本。"""
        if not pages:
            return f"[米游社百科探索] 未找到与「{query}」相关的结果。"

        lines = [
            f"## 米游社百科 探索: 「{query}」",
            f"探索 {len(pages)} 个条目, 耗时 {elapsed:.1f}s\n",
        ]

        for i, page in enumerate(pages):
            depth_label = "起始" if page.depth == 0 else f"深度{page.depth}"
            cat_tag = f" [{page.category}]" if page.category else ""
            lines.append(
                f"### [{i+1}] {page.name}{cat_tag} ({depth_label})\n"
                f"  ID: {page.content_id}\n"
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


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

def test_miyoushe():
    """测试 MiyousheExplorer 基本功能。"""
    print("MiyousheExplorer 测试")
    print("=" * 60)

    # 测试字典
    print("\n[字典测试]")
    id_dict = get_id_dict()
    print(f"  条目总数: {id_dict.size}")

    # 精确查找 (返回列表)
    entries = id_dict.lookup("薪炎之律者")
    if entries:
        for e in entries:
            print(f"  薪炎之律者: content_id={e.content_id}, category={e.category}")

    # 同名多分类测试
    multi = id_dict.lookup("识之律者")
    print(f"  识之律者 ({len(multi)} 个分类):")
    for e in multi:
        print(f"    id={e.content_id} [{e.category}]")

    # 模糊搜索
    results = id_dict.search("爱莉", top_k=3)
    print(f"  搜索 '爱莉': {[(e.name, e.content_id, e.category) for e in results]}")

    # 内容中查找名字
    text = "薪炎之律者是琪亚娜·卡斯兰娜的炎之律者形态，使用武器为涤罪七雷"
    found = id_dict.find_names_in_text(text)
    print(f"  从文本提取名字: {found}")

    # 测试探索器
    print("\n[探索测试] 薪炎之律者")
    explorer = MiyousheExplorer(timeout=12)
    result = explorer.explore("薪炎之律者", max_depth=1, max_pages=3)
    for line in result.splitlines()[:10]:
        print(f"  {line[:130]}")

    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_miyoushe()
