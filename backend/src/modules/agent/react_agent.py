import logging
import os
import sys
import re as _re

# DeepSeek 模型经常在 ReAct 格式前插入对话文本，或使用 Markdown 粗体格式
# 匹配普通格式: Action: / Action Input: / Final Answer:
# 匹配粗体格式: **Action**: / **Action Input**: / **Final Answer**:
_REACT_LINE = _re.compile(
    r'^(?:\*\*)?(?:Thought|Action|Action\s*Input|Final\s*Answer)(?:\*\*)?\s*\d*\s*:',
    _re.IGNORECASE | _re.MULTILINE,
)
_ACTION_RE = _re.compile(r'^(?:\*\*)?Action(?:\*\*)?\s*\d*\s*:', _re.IGNORECASE | _re.MULTILINE)
_ACTION_INPUT_RE = _re.compile(
    r'^(?:\*\*)?Action\s+Input(?:\*\*)?\s*\d*\s*:',
    _re.IGNORECASE | _re.MULTILINE,
)
_FINAL_RE = _re.compile(r'^(?:\*\*)?Final\s+Answer(?:\*\*)?\s*\d*\s*:', _re.IGNORECASE | _re.MULTILINE)

def _clean_llm_output(text: str) -> str:
    """清洗 LLM 输出，只保留第一个有效的 ReAct 意图。

    DeepSeek 经常在一次输出中虚构完整的 ReAct 循环（Action + 虚构的 Observation
    + 下一个 Action + ...），导致框架只执行第一个 Action，其余都是幻觉文本。
    此函数截断多步骤输出，确保解析器只看到一个明确的意图。
    """
    if not text or not text.strip():
        return text
    stripped = text.strip()

    # 找到第一个 ReAct 标记，截掉前面的对话文本
    match = _REACT_LINE.search(stripped)
    if not match:
        return f"Thought: 我已经得到最终答案\nFinal Answer: {stripped}"
    stripped = stripped[match.start():]

    action_matches = list(_ACTION_RE.finditer(stripped))
    final_matches = list(_FINAL_RE.finditer(stripped))

    # 如果 Final Answer 出现在第一个 Action 之前，LLM 先写了角色扮演文本
    # 但又试图调用工具 → 真实的意图是 Action，去掉过早的 Final Answer
    if action_matches and final_matches:
        first_action_pos = action_matches[0].start()
        first_final_pos = final_matches[0].start()
        if first_final_pos < first_action_pos:
            stripped = stripped[:first_final_pos] + stripped[first_action_pos:]
            action_matches = list(_ACTION_RE.finditer(stripped))
            final_matches = list(_FINAL_RE.finditer(stripped))

    if action_matches:
        first_action = action_matches[0]
        ai_match = _ACTION_INPUT_RE.search(stripped, first_action.end())

        if ai_match:
            ai_line_end = stripped.find('\n', ai_match.end())
            if ai_line_end == -1:
                ai_line_end = len(stripped)
            cut_pos = ai_line_end

            if len(action_matches) > 1:
                second_action_pos = action_matches[1].start()
                cut_pos = min(cut_pos, second_action_pos)

            if final_matches:
                cut_pos = min(cut_pos, final_matches[0].start())

            stripped = stripped[:cut_pos].rstrip()
        else:
            if len(action_matches) > 1:
                stripped = stripped[:action_matches[1].start()].rstrip()
            elif final_matches:
                stripped = stripped[:final_matches[0].start()].rstrip()
    elif final_matches:
        stripped = stripped[final_matches[0].start():]
    else:
        pass

    if not stripped or not _REACT_LINE.match(stripped):
        return f"Thought: 我已经得到最终答案\nFinal Answer: {text.strip()}"

    return stripped


# ---- RAG 结果格式化（共享，供 rag_search 和 parallel_search 使用） ----

def _extract_relevant_snippet(content: str, query: str, max_chars: int = 500) -> str:
    """从文档内容中提取与查询最相关的片段，而非简单截取前 N 字符。

    算法：在内容中查找查询词出现位置，以该位置为中心截取上下文窗口。
    优先匹配完整查询短语，其次匹配单个关键词。
    """
    if len(content) <= max_chars:
        return content

    query_lower = query.lower().strip()
    content_lower = content.lower()

    best_pos = 0

    # 优先: 完整查询短语匹配
    pos = content_lower.find(query_lower)
    if pos >= 0:
        best_pos = pos
    else:
        # 其次: 对查询做简单分词，找第一个匹配项
        try:
            import jieba as _jieba
            query_terms = [t for t in _jieba.cut(query_lower) if len(t.strip()) > 1]
        except Exception:
            query_terms = [t for t in query_lower.split() if len(t) > 1]

        best_score = 0
        for term in query_terms:
            pos = content_lower.find(term)
            if pos >= 0:
                score = len(term) / (pos + 1)
                if score > best_score:
                    best_score = score
                    best_pos = pos

    # 以匹配位置为中心截取窗口
    half = max_chars // 2
    start = max(0, best_pos - half // 2)  # 偏向匹配位置之前少一点，之后多一点
    end = min(len(content), start + max_chars)

    # 尽量在句号处开始
    if start > 0 and best_pos - start > 30:
        for sep in ['。', '！', '？', '\n', '，', '.']:
            sep_pos = content.rfind(sep, start, best_pos)
            if sep_pos > start:
                start = sep_pos + 1
                break

    snippet = content[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(content):
        snippet = snippet + "…"

    return snippet


def _expand_query(query: str, rag_engine=None) -> str:
    """查询扩展：用 RAG 索引中的完整名称/别名丰富短查询。

    策略（纯软件，无需额外模型）：
    1. 查询词本身已是完整名称 → 直接返回
    2. 短词匹配到别名 → 扩展为完整名称
    3. 短词匹配到部分名称 → 附加匹配到的名称

    例: "德丽莎" → "德丽莎 德丽莎·阿波卡利斯"
    例: "芽衣" → "芽衣 雷电芽衣"
    """
    if not rag_engine or not query or not query.strip():
        return query

    query_stripped = query.strip()
    # 查询已经足够长（>8字），不需要扩展
    if len(query_stripped) > 8:
        return query_stripped

    try:
        import asyncio as _asyncio

        # 同步调用异步 search_by_name
        def _lookup():
            return _asyncio.run(
                rag_engine.search_by_name(query_stripped, exact=False)
            )

        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor() as _ex:
            name_results = _ex.submit(_lookup).result(timeout=5)

        if not name_results:
            return query_stripped

        # 收集匹配到的名称（去重，限制 3 个）
        expanded_terms = [query_stripped]
        seen = {query_stripped.lower()}
        for r in name_results[:5]:
            name = r.name.strip()
            if name.lower() not in seen and len(name) > 1:
                expanded_terms.append(name)
                seen.add(name.lower())
                if len(expanded_terms) >= 3:
                    break

        if len(expanded_terms) > 1:
            expanded = " ".join(expanded_terms)
            logger.info(f"查询扩展: '{query_stripped}' → '{expanded}'")
            return expanded
    except Exception as e:
        logger.debug(f"查询扩展跳过: {e}")

    return query_stripped


def _should_include_moegirl(query: str) -> bool:
    """判断查询是否应激活萌娘百科搜索源。

    三种激活条件（满足任一即可）:
    1. 查询包含角色/剧情/情感关键词
    2. 查询能匹配到米游社字典中的女武神/角色条目
    3. 查询是纯名字查询（不含问句特征），可能是角色/事物查询

    萌娘百科提供玩家社区视角的角色情感/关系/剧情，与米游社官方数据互补。
    """
    # 条件1: 角色/剧情/情感关键词
    _lore_keywords = ["角色", "关系", "剧情", "背景", "故事", "情感", "经历",
                      "性格", "身世", "羁绊", "回忆", "过往", "设定", "世界观"]
    if any(kw in query for kw in _lore_keywords):
        return True

    # 条件2: 匹配米游社字典中的女武神/角色条目
    try:
        from src.modules.web_search.miyoushe_explorer import get_id_dict
        d = get_id_dict()
        # 先精确查找
        entry = d.lookup_best(query)
        if entry is None:
            # 再模糊搜索（处理简称如"爱莉"→"爱莉希雅"）
            results = d.search(query, top_k=1)
            if results:
                entry = results[0]
        if entry is not None:
            cat = entry.category
            if "女武神" in cat or "角色" in cat:
                return True
    except Exception:
        pass

    # 条件3: 纯名字查询（短查询 + 无问句特征 + 无URL）
    _question_words = ["什么", "怎么", "如何", "为什么", "哪里", "哪个", "是否",
                       "有没有", "能不能", "可以", "请", "帮我", "告诉我", "?"]
    if (len(query) <= 12
            and not any(w in query for w in _question_words)
            and not query.startswith("http")):
        return True

    return False


def _llm_rerank(query: str, results: list, top_k: int = 5) -> list:
    """LLM 重排序：用现有 LLM API 对候选文档打分（无需额外模型）。

    当 Cross-Encoder Reranker 不可用时的纯软件替代方案。
    发送 top-N 文档给 LLM，让 LLM 为每个文档评估与查询的相关度。
    """
    if not results or len(results) <= top_k:
        return results

    try:
        from src.modules.llm.llm_router import get_llm_router, TaskType

        # 构建评分 prompt
        docs_text = []
        for i, r in enumerate(results[:min(len(results), 12)]):
            docs_text.append(f"[{i}] {r.name}: {r.content[:300]}")

        prompt = f"""评估以下文档与查询的相关度。为每个文档打分(0-10)，仅输出JSON数组。

查询: {query}

文档列表:
{chr(10).join(docs_text)}

输出格式（仅JSON，不要其他文字）:
[{{"id": 0, "score": 8.5, "reason": "简短理由"}}, ...]

按相关度从高到低排列。"""
        router = get_llm_router()
        result = router.route_request(
            messages=[{"role": "user", "content": prompt}],
            task_type=TaskType.GAME_GUIDE.value,
            stream=False,
        )

        content = ""
        if isinstance(result, dict):
            content = result.get("content", "") or ""
        else:
            content = str(result)

        # 解析 LLM 返回的 JSON
        import json as _json
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:]) if len(lines) > 1 else content
            if content.endswith("```"):
                content = content[:-3].strip()

        scores = _json.loads(content)
        if not isinstance(scores, list):
            return results[:top_k]

        # 按 LLM 分数重排
        score_map = {item.get("id", -1): item.get("score", 0) for item in scores}
        for i, r in enumerate(results):
            r._llm_score = score_map.get(i, 0)

        results.sort(key=lambda r: getattr(r, "_llm_score", 0), reverse=True)
        logger.info(f"LLM 重排序完成: {len(results)} 条 → top {top_k}")
        return results[:top_k]

    except Exception as e:
        logger.warning(f"LLM 重排序失败，保持原序: {e}")
        return results[:top_k]


def _format_rag_results(
    results: list,
    query: str,
    top_k: int = 5,
    min_score: float = 0.012,
    snippet_chars: int = 400,
    reranker=None,
) -> str:
    """将 RAG 搜索结果格式化为可读文本，含智能片段提取和分档评分。

    分层过滤策略（保证相关度优先）：
    0. 若有 Reranker → 先对 top-20 结果重排序
    1. 名称精确匹配 → 无条件保留，最多 3 条
    2. 名称包含查询词 → score >= 0.02 才保留，最多 3 条
    3. 仅内容匹配 → 有名称匹配时 >= 0.022，否则 >= 0.018
    4. 总数不超过 top_k，名称为主的内容匹配为辅
    """
    if not results:
        return "未检索到相关知识。"

    query_lower = query.lower().strip()

    # ── 第 0 步: 重排序（Cross-Encoder > LLM > 原序） ──
    rerank_applied = False
    if len(results) > top_k:
        if reranker is not None:
            # 优先：Cross-Encoder Reranker（需下载模型，默认不启用）
            try:
                results = reranker.rerank_results(query, results, top_k=max(top_k * 4, 20))
                rerank_applied = True
                logger.info(f"Cross-Encoder Reranker 已重排 {len(results)} 条候选")
            except Exception as e:
                logger.warning(f"Reranker 重排序失败: {e}")
        else:
            # 备选：LLM 重排序（无需额外模型，用已有 DeepSeek API）
            try:
                results = _llm_rerank(query, results, top_k=max(top_k * 3, 15))
                rerank_applied = True
                logger.info(f"LLM 重排序完成: {len(results)} 条")
            except Exception as e:
                logger.debug(f"LLM 重排序跳过: {e}")
    # 对多词查询拆分，用于名称部分匹配
    query_terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 1]
    if not query_terms:
        query_terms = [query_lower]

    # ── 分层分类 ──
    exact_name_matches = []    # 文档名 == 查询词（或查询词的任一term完全等于文档名）
    partial_name_matches = []  # 文档名包含查询词
    content_only_matches = []  # 文档名不包含查询词，仅内容匹配

    # 内容匹配阈值：有名称匹配时更严格，没有时更宽松
    _has_name_match = False  # 先设为 False，遍历后更新

    for r in results:
        name_lower = r.name.lower()
        # 精确匹配：全查询完全等于文档名，或查询中的任一term等于文档名
        is_exact = (query_lower == name_lower) or any(
            term == name_lower for term in query_terms
        )
        # 部分匹配：文档名包含查询词（但不完全相等）
        is_partial = not is_exact and (
            query_lower in name_lower or
            any(term in name_lower for term in query_terms)
        )

        if is_exact:
            exact_name_matches.append(r)
            _has_name_match = True
        elif is_partial and r.score >= 0.02:
            partial_name_matches.append(r)
            _has_name_match = True

    # 确定内容匹配阈值
    content_threshold = 0.022 if _has_name_match else 0.018

    for r in results:
        if r not in exact_name_matches and r not in partial_name_matches:
            if r.score >= content_threshold:
                content_only_matches.append(r)

    # ── 按分数排序各组 ──
    exact_name_matches.sort(key=lambda r: r.score, reverse=True)
    partial_name_matches.sort(key=lambda r: r.score, reverse=True)
    content_only_matches.sort(key=lambda r: r.score, reverse=True)

    # ── 组装结果 ──
    selected = []
    selected.extend(exact_name_matches[:3])
    selected.extend(partial_name_matches[:3])
    # 补充填充结果
    remaining = top_k - len(selected)

    if remaining > 0:
        # 优先用已筛选的内容匹配补充
        for r in content_only_matches:
            if len(selected) >= top_k:
                break
            if r not in selected:
                selected.append(r)

        # 如果还不够且有名称匹配 → 不再放宽（保证相关度）
        # 如果没有名称匹配 → 用最低阈值兜底
        if len(selected) < top_k and not _has_name_match:
            low_score = [r for r in results if r.score >= min_score and r not in selected]
            low_score.sort(key=lambda r: r.score, reverse=True)
            for r in low_score:
                if r not in selected:
                    selected.append(r)
                if len(selected) >= top_k:
                    break

    if not selected:
        # 完全没有任何匹配 — 返回最好的一个
        best = results[0]
        snippet = _extract_relevant_snippet(best.content, query, snippet_chars)
        return (
            f"[低相关性] {best.name} ({best.category}): {snippet}\n"
            f"(知识库中未找到与'{query}'直接匹配的内容，可尝试换用其他关键词或使用 web_search)"
        )

    # ── 格式化输出 ──
    lines = []
    for r in selected[:top_k]:
        snippet = _extract_relevant_snippet(r.content, query, snippet_chars)
        name_lower = r.name.lower()

        # 评分档位标记
        if query_lower == name_lower or any(term == name_lower for term in query_terms):
            tag = "[直接匹配]"
        elif r.score >= 0.03:
            tag = "[★★]"
        elif r.score >= 0.015:
            tag = "[★]"
        else:
            tag = "[低相关]"

        cat_info = f"({r.category}" + (f"/{r.subcategory})" if getattr(r, 'subcategory', None) else ")")
        lines.append(f"{tag} {r.name} {cat_info}: {snippet}")

    return "\n\n".join(lines)


# ---- 固定网址域名（parallel_search 使用的可信来源） ----
# 每个条目: (显示名称, 搜索URL模板, {query}会被替换为搜索词)
_FIXED_SEARCH_URLS = [
    ("米游社", "https://www.miyoushe.com/bh3/search?keyword={query}"),
    ("B站wiki", "https://wiki.biligame.com/bh3/index.php?search={query}"),
    ("萌娘百科", "https://mzh.moegirl.org.cn/index.php?search={query}"),
]
# 各站点角色页面URL格式（供精确跳转参考）:
#   B站wiki:   https://wiki.biligame.com/bh3/{角色全名}     (例: 雷电芽衣)
#   萌娘百科:   https://mzh.moegirl.org.cn/{角色全名}(崩坏3)#  (例: 琪亚娜·卡斯兰娜(崩坏3))
#   baike.mihoyo.com — 米游社百科，数据已在RAG知识库中，待优化为按content精确查询


def _detect_character_names(query: str) -> list:
    """检测查询中是否包含已知崩坏3角色名，返回角色目录名列表（去重）。

    利用 CharacterManager 的 name_map（name + tts_voice 字段）进行子串匹配。
    按名称长度降序匹配，优先匹配完整名称。
    最多返回 3 个角色的目录名。
    """
    if not query or not query.strip():
        return []

    try:
        from src.modules.character.character_manager import get_character_manager
        cm = get_character_manager()
        name_map = cm._build_name_map()
    except Exception:
        return []

    query_lower = query.strip().lower()
    matched_dirs = []
    seen = set()

    # 按名称长度降序排列，优先匹配长名称（如"琪亚娜·卡斯兰娜"优先于"琪亚娜"）
    sorted_names = sorted(name_map.keys(), key=len, reverse=True)

    for name in sorted_names:
        if name.lower() in query_lower:
            dir_name = name_map[name]
            if dir_name not in seen:
                matched_dirs.append(dir_name)
                seen.add(dir_name)
                if len(matched_dirs) >= 3:
                    break

    return matched_dirs


def _get_full_chinese_name(dir_name: str) -> str:
    """从 SKILL.md 的 description 字段提取角色中文全名。

    description 格式: "琪亚娜·卡斯兰娜（Kiana Kaslana）— ..."
    取第一个（ 或 ( 之前的部分作为全名。
    若提取失败则返回空字符串。
    """
    try:
        from src.modules.character.character_manager import get_character_manager
        cm = get_character_manager()
        skill_path = cm.skills_dir / dir_name / "SKILL.md"
        if not skill_path.exists():
            return ""
        with open(skill_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("description:"):
                    raw = line.split("description:", 1)[1].strip().strip('"').strip("'")
                    # 取第一个中文/英文括号之前的部分作为全名
                    for sep in ("（", "("):
                        idx = raw.find(sep)
                        if idx > 0:
                            return raw[:idx].strip()
                    return raw
                if line == "---" and not line.startswith("description:"):
                    # 跳过第一行 --- 后继续
                    pass
            return ""
    except Exception:
        return ""


def _make_character_page_urls(dir_names: list) -> list:
    """根据角色目录名列表生成直连页面 URL。

    返回 [(label, url), ...] 格式。
    优先使用 SKILL.md description 中的角色全名（如"琪亚娜·卡斯兰娜"），
    回退到 tts_voice 短名（如"琪亚娜"）。
    同时生成全名和短名两个 URL 变体以提高命中率。
    URL 已经过 URL 编码，萌娘百科末尾加 #。
    """
    if not dir_names:
        return []

    try:
        from src.modules.character.character_manager import get_character_manager
        cm = get_character_manager()
    except Exception:
        return []

    import urllib.parse as _up

    urls = []
    for dir_name in dir_names:
        # 获取短名（tts_voice）
        try:
            short_name = cm.get_tts_voice(dir_name)
        except Exception:
            short_name = ""
        if not short_name:
            short_name = dir_name

        # 获取全名（从 description 提取），优先全名做 URL
        full_name = _get_full_chinese_name(dir_name)
        url_name = full_name if full_name else short_name

        encoded = _up.quote(url_name)

        urls.append((
            f"B站wiki [角色页] {url_name}",
            f"https://wiki.biligame.com/bh3/{encoded}",
        ))
        # 萌娘百科: 括号和 # 需 URL 编码，否则被 WAF 拦截
        encoded_suffix = _up.quote("(崩坏3)#")
        urls.append((
            f"萌娘百科 [角色页] {url_name}",
            f"https://zh.moegirl.org.cn/{encoded}{encoded_suffix}",
        ))

    return urls


def _execute_parallel_search(query: str, rag_engine=None) -> str:
    """并行执行 RAG + 百度搜索 + 固定网址搜索，合并返回结果。

    三个搜索在独立线程中并发执行，总耗时 ≈ max(单路耗时) 而非 sum。
    """
    import concurrent.futures

    results: dict = {}
    max_workers = 0

    if rag_engine is not None:
        max_workers += 1
    max_workers += 2  # web + fixed_urls

    if max_workers == 0:
        return "未配置任何搜索源。"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict = {}

        # ── RAG 搜索 ──
        if rag_engine is not None:

            def _do_rag():
                import asyncio as _asyncio

                # 查询扩展：短词自动补全为完整名称
                expanded_query = _expand_query(query, rag_engine)

                def _run():
                    return _asyncio.run(
                        rag_engine.search(query=expanded_query, mode=SearchMode.HYBRID, top_k=20)
                    )

                with concurrent.futures.ThreadPoolExecutor() as _ex:
                    _f = _ex.submit(_run)
                    _results = _f.result(timeout=30)

                reranker = _get_shared_reranker()
                return _format_rag_results(
                    _results, expanded_query, top_k=5, min_score=0.012, reranker=reranker
                )

            futures["rag"] = executor.submit(_do_rag)

        # ── 百度搜索 ──
        def _do_web():
            from src.modules.web_search.web_searcher import WebSearcher, SearchEngine, SearchResult

            searcher = WebSearcher(engine=SearchEngine.BAIDU)
            resp = searcher.search_with_context(query, "")
            search_results = resp.get("results", [])
            if not search_results:
                return "未找到相关搜索结果。"
            sr = [
                SearchResult(
                    title=r["title"], url=r["url"], snippet=r["snippet"],
                    source=r["source"], relevance=r["relevance"],
                )
                for r in search_results
            ]
            return searcher.extract_answers(query, sr)

        futures["web"] = executor.submit(_do_web)

        # ── 固定网址搜索（通用搜索 URL + 角色直连页面 URL） ──
        def _do_fixed_urls():
            import urllib.parse
            import requests as _requests

            # 构建 URL 列表：通用搜索 URL + 角色直连页面 URL
            url_entries = list(_FIXED_SEARCH_URLS)  # [(label, url_template), ...]

            # 检测查询中的角色名，添加直连页面 URL
            char_dirs = _detect_character_names(query)
            if char_dirs:
                char_urls = _make_character_page_urls(char_dirs)
                url_entries.extend(char_urls)

            parts = []
            for label, url_template in url_entries:
                try:
                    if "{query}" in url_template:
                        url = url_template.replace("{query}", urllib.parse.quote(query))
                    else:
                        url = url_template

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate",
                        "Referer": "https://www.google.com/",
                        "Cache-Control": "no-cache",
                        "DNT": "1",
                        "Upgrade-Insecure-Requests": "1",
                    }
                    resp = _requests.get(url, headers=headers, timeout=15)
                    resp.raise_for_status()

                    # 提取页面内容：标题 + 正文前 1200 字符
                    title = ""
                    content_snippet = ""
                    try:
                        from bs4 import BeautifulSoup as _BS
                        soup = _BS(resp.text, "html.parser")
                        if soup.title:
                            title = soup.title.get_text(strip=True)
                        # 移除噪音标签
                        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                            tag.decompose()
                        # 优先提取主内容区（MediaWiki / 搜索 / 通用选择器）
                        content_selectors = [
                            ".mw-parser-output", "#bodyContent", "#mw-content-text",
                            ".mw-search-results", ".searchresults", ".search-result",
                            "main", "article", ".main-content", ".content", "#content",
                        ]
                        content_elem = None
                        for sel in content_selectors:
                            content_elem = soup.select_one(sel)
                            if content_elem:
                                break
                        if content_elem:
                            body_text = content_elem.get_text(separator="\n", strip=True)
                        elif soup.body:
                            body_text = soup.body.get_text(separator="\n", strip=True)
                        else:
                            body_text = soup.get_text(separator="\n", strip=True)
                        lines = [ln.strip() for ln in body_text.splitlines() if ln.strip() and len(ln.strip()) > 2]
                        content_snippet = "\n".join(lines)[:1200]
                        # 检测空结果页面，静默处理
                        no_result_markers = ["找不到和查询相匹配的结果", "没有找到任何结果", "无搜索结果",
                                             "No results found", "No matching results"]
                        if content_snippet and any(m in content_snippet for m in no_result_markers):
                            content_snippet = ""  # 抑制空结果噪声
                    except ImportError:
                        # BeautifulSoup 不可用，回退到 HTMLParser 提取标题
                        from html.parser import HTMLParser as _HTMLParser

                        class _TitleParser(_HTMLParser):
                            def __init__(self):
                                super().__init__()
                                self.in_title = False
                                self.title = ""

                            def handle_starttag(self, tag, attrs):
                                if tag == "title":
                                    self.in_title = True

                            def handle_data(self, data):
                                if self.in_title:
                                    self.title += data

                            def handle_endtag(self, tag):
                                if tag == "title":
                                    self.in_title = False

                        parser = _TitleParser()
                        parser.feed(resp.text[:8192])
                        title = parser.title.strip() if parser.title else ""

                    if content_snippet:
                        parts.append(f"[{label}] {title}\n  {url}\n---\n{content_snippet}")
                    elif title:
                        parts.append(f"[{label}] {title}\n  {url}")
                    else:
                        parts.append(f"[{label}] 页面已获取，但无法解析内容\n  {url}")
                except Exception as e:
                    err_str = str(e)
                    # 萌娘百科 文章页受 Cloudflare 保护，requests 无法绕过，静默降级
                    if "403" in err_str and "萌娘百科" in label and "[角色页]" in label:
                        parts.append(f"[{label}] 需要浏览器访问，已跳过（Cloudflare 保护）\n  {url}")
                    elif "403" in err_str or "404" in err_str:
                        # 页面不存在或无权访问，仅显示 URL 不暴露错误详情
                        parts.append(f"[{label}] {url}")
                    else:
                        parts.append(f"[{label}] 获取失败: {e}\n  {url}")
            return "\n\n".join(parts) if parts else "固定网址搜索未获取到结果。"

        futures["fixed"] = executor.submit(_do_fixed_urls)

        # ── 收集结果 ──
        for future in concurrent.futures.as_completed(list(futures.values())):
            for key, f in list(futures.items()):
                if f == future:
                    try:
                        results[key] = f.result(timeout=60)
                    except Exception as e:
                        results[key] = f"[{key}搜索失败: {e}]"
                    break

    # ── 组装输出 ──
    parts = []
    if "rag" in results:
        parts.append(f"=== RAG 知识库 ===\n{results['rag']}")
    if "web" in results:
        parts.append(f"=== 网络搜索 ===\n{results['web']}")
    if "fixed" in results:
        parts.append(f"=== 固定网址 ===\n{results['fixed']}")

    return "\n\n".join(parts) if parts else "未获取到任何搜索结果。"


class AgentRouter:
    """意图分类器 — 单次 LLM 调用判断用户意图，不参与 ReAct 循环。

    将用户消息分类为三类意图：
    - "game": 游戏自动化任务（匹配到技能描述）
    - "action": Live2D/TTS/搜索/RAG 等操作请求
    - "chat": 纯角色对话、闲聊、情感交流
    """

    def __init__(self):
        self._skill_list_cache: str = ""
        self._cache_time: float = 0.0

    def _get_skill_list(self) -> str:
        """获取技能列表描述（带 5 分钟缓存）。"""
        import time
        now = time.time()
        if self._skill_list_cache and (now - self._cache_time) < 300:
            return self._skill_list_cache
        try:
            skills = get_skill_manager().list_skills()
            lines = []
            for s in skills:
                name = s.get("name", "")
                desc = s.get("description", "")
                lines.append(f"- {name}: {desc}")
            self._skill_list_cache = "\n".join(lines)
        except Exception:
            self._skill_list_cache = "（技能列表暂时不可用）"
        self._cache_time = now
        return self._skill_list_cache

    def classify(self, user_message: str) -> dict:
        """分类用户意图，返回 {"intent": "game|action|chat", "skill_name": str|None}。"""
        skill_list = self._get_skill_list()

        prompt = f"""你是崩坏3AI助手的意图分类器。根据用户消息判断意图类别，仅输出一行JSON。

## 可用的游戏自动化技能
{skill_list}

## 可用的操作工具
- live2d_control: Live2D看板娘控制（加载模型、表情、动作、位置、透明度等）
- tts: 语音合成（Qwen3-TTS声音克隆、VoxCPM）
- play_audio: 播放音频文件
- rag_search: 崩坏3游戏知识库查询
- web_search: 联网搜索最新资讯

## 分类规则（按优先级，匹配到第一个就停止）

1. **"action"（最高优先级）** — 消息包含以下任意关键词或意图：
   - Live2D相关: "live2d"、"live2D"、"看板娘"、"模型"、"加载"、"启动live"、"换模型"、"表情"、"动作"
   - TTS相关: "TTS"、"语音"、"朗读"、"念"、"说话"、"出声"、"音色"、"声音"
   - 搜索相关: "搜索"、"查一下"、"帮我查"、"知识库"、"wiki"
   - 明确的操作请求而非闲聊
   → 输出: {{"intent": "action", "skill_name": null}}

2. **"game"** — 消息匹配到上述任何游戏技能的描述关键词（如"每日任务"、"往世乐土"、"战场减负"、"舰团贡献"等），或者是明确的游戏自动化请求。
   → 同时返回匹配的技能名（skill_name），未匹配到则填null。
   → 输出: {{"intent": "game", "skill_name": "匹配的技能名或null"}}

3. **"chat"（兜底）** — 不属于以上两类。纯角色对话、闲聊、问候、情感交流、询问角色身份等。
   → 输出: {{"intent": "chat", "skill_name": null}}

用户消息: {user_message}

仅输出一行JSON（不要markdown代码块，不要其他文字）:
{{"intent": "game或action或chat", "skill_name": null}}"""

        try:
            router = get_llm_router()
            runtime = get_runtime_settings()

            router_kwargs = {}
            if runtime.get("llm_provider"):
                from src.config.runtime_settings import get_runtime_settings as _rt
                PROVIDER_MAP = {"deepseek": "deepseek-api-default", "lmstudio": "lm-studio-default", "ollama": "ollama-default"}
                RUNTIME_MAP = {"deepseek": "api", "lmstudio": "lmstudio", "ollama": "ollama"}
                router_kwargs["preferred_runtime"] = RUNTIME_MAP.get(runtime["llm_provider"], "auto")
                router_kwargs["user_preference"] = PROVIDER_MAP.get(runtime["llm_provider"], runtime["llm_provider"])
            if runtime.get("llm_model"):
                router_kwargs["model_override"] = runtime["llm_model"]
            if runtime.get("llm_temperature") is not None:
                router_kwargs["temperature"] = min(runtime["llm_temperature"], 0.3)
            if runtime.get("llm_max_tokens") is not None:
                router_kwargs["max_tokens"] = runtime["llm_max_tokens"]
            if runtime.get("llm_api_key"):
                router_kwargs["api_key"] = runtime["llm_api_key"]

            result = router.route_request(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.GAME_GUIDE.value,
                stream=False,
                **router_kwargs,
            )

            content = ""
            if isinstance(result, dict):
                content = result.get("content", "") or ""
            else:
                content = str(result)

            # 解析 JSON，处理 markdown 代码块包装
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 1 else content
                if content.endswith("```"):
                    content = content[:-3].strip()

            import json as _json
            parsed = _json.loads(content)
            intent = parsed.get("intent", "chat")
            if intent not in ("game", "action", "chat"):
                intent = "chat"
            return {"intent": intent, "skill_name": parsed.get("skill_name")}

        except Exception as e:
            logger.warning(f"AgentRouter 分类失败，回退到 chat: {e}")
            return {"intent": "chat", "skill_name": None}


import queue
from threading import Lock
from typing import Any, Dict, List, Optional

import cv2
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.llms import LLM
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from src.config.settings import get_settings
from src.config.runtime_settings import get_runtime_settings
from src.config.cancel_signal import is_cancelled
from src.modules.llm.llm_router import TaskType, get_llm_router
from src.modules.character.character_manager import get_character_manager
from src.modules.rag import RAGConfig, RAGEngine, SearchMode
from src.modules.vision.yolo_model_manager import YOLOModelManager
from src.modules.skill.skill_manager import get_skill_manager
from .react_formatter import ReActFormatter

logger = logging.getLogger(__name__)


# ---- 参考音频索引 (Qwen3-TTS 声音克隆，统一由 qwen3_tts_generator 提供) ----
from src.modules.audio.qwen3_tts_generator import resolve_character_ref as _resolve_ref_audio
from src.modules.audio.qwen3_tts_generator import list_ref_characters as _list_ref_characters


class RouterLLM(LLM):
    """将现有 LLMRouter 适配为 LangChain LLM。

    agent_type: "main" → 游戏任务, "action" → 操作执行, "companion" → 角色扮演
    """

    agent_type: str = "main"

    # agent_types that use flash model and character personality
    _COMPANION_TYPES = {"sub", "companion"}

    def __init__(self, agent_type: str = "main"):
        super().__init__(agent_type=agent_type)
        self._current_images: Optional[List[str]] = None
        self._force_stop = False
        self._force_stop_reason = ""

    @property
    def _llm_type(self) -> str:
        return f"bbb_router_llm_{self.agent_type}"

    def _generate(self, prompts, stop=None, run_manager=None, **kwargs):
        logger.info(f"[RouterLLM-{self.agent_type}] _generate 被调用, prompts数量={len(prompts)}")
        result = super()._generate(prompts, stop=stop, run_manager=run_manager, **kwargs)
        logger.info(f"[RouterLLM-{self.agent_type}] _generate 返回")
        return result

    def invoke(self, input, config=None, **kwargs):
        logger.info(f"[RouterLLM-{self.agent_type}] invoke 被调用, input类型={type(input).__name__}")
        result = super().invoke(input, config=config, **kwargs)
        logger.info(f"[RouterLLM-{self.agent_type}] invoke 返回, result类型={type(result).__name__}")
        return result

    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager=None, **kwargs: Any) -> str:
        request_id = getattr(self, '_current_request_id', None)
        if request_id and is_cancelled(request_id):
            raise RuntimeError("CancelledError: 请求已被用户取消")

        # 回调检测到死循环时设置此标志，直接返回强制终止响应
        if self._force_stop:
            logger.info(f"[RouterLLM-{self.agent_type}] 检测到强制停止标志，返回终止响应")
            self._force_stop = False
            reason = self._force_stop_reason or "操作已完成"
            self._force_stop_reason = ""
            return (
                f"Thought: {reason}，无需继续调用工具。\n"
                f"Final Answer: 操作已完成。"
            )

        logger.info(f"[RouterLLM-{self.agent_type}] _call 被调用, prompt前100字: {prompt[:100]}")
        router = get_llm_router()
        runtime = get_runtime_settings()

        PROVIDER_MAP = {
            "deepseek": "deepseek-api-default",
            "lmstudio": "lm-studio-default",
            "ollama": "ollama-default",
        }
        RUNTIME_MAP = {"deepseek": "api", "lmstudio": "lmstudio", "ollama": "ollama"}

        router_kwargs = {}
        if runtime.get("llm_provider"):
            router_kwargs["preferred_runtime"] = RUNTIME_MAP.get(runtime["llm_provider"], "auto")
            router_kwargs["user_preference"] = PROVIDER_MAP.get(runtime["llm_provider"], runtime["llm_provider"])
        if runtime.get("llm_model"):
            if self.agent_type in self._COMPANION_TYPES:
                flash_model = runtime["llm_model"].replace("-pro", "-flash") if "pro" in runtime["llm_model"] else runtime["llm_model"]
                router_kwargs["model_override"] = flash_model
            else:
                router_kwargs["model_override"] = runtime["llm_model"]
        if runtime.get("llm_temperature") is not None:
            temp = runtime["llm_temperature"]
            if self.agent_type in self._COMPANION_TYPES:
                temp = min(temp, 0.9)
            router_kwargs["temperature"] = temp
        if runtime.get("llm_max_tokens") is not None:
            router_kwargs["max_tokens"] = runtime["llm_max_tokens"]
        if runtime.get("llm_api_key"):
            router_kwargs["api_key"] = runtime["llm_api_key"]

        # 有图片时强制走 LM Studio（本地视觉模型）
        images = getattr(self, '_current_images', None)
        if images:
            router_kwargs["preferred_runtime"] = "lmstudio"
            router_kwargs["user_preference"] = "lm-studio-default"
            router_kwargs["images"] = images

        # 构建 messages，陪伴型 Agent 将角色人格作为独立 system message 注入
        messages = [
            {
                "role": "system",
                "content": "你是一个AI助手，请严格遵循 ReAct 格式并按需调用工具。",
            },
        ]

        if self.agent_type in self._COMPANION_TYPES:
            rt = get_runtime_settings()
            char_name = rt.get("companion_character", "爱莉希雅")
            logger.info(f"[RouterLLM-{self.agent_type}] 读取角色设置: companion_character='{char_name}'")
            personality = get_character_manager().get_personality(char_name)
            messages.append({
                "role": "system",
                "content": (
                    f"## 你的角色身份\n\n{personality}\n\n"
                    "---\n"
                    "角色扮演规则：\n"
                    "- 始终以角色身份说话，保持人设一致。你不是AI助手，你就是这个角色本身\n"
                    "- 回复第一行必须是 [emotion] 标签（happy/sad/angry/surprised/shy/serious/teasing/gentle/excited/neutral）\n"
                    "- 你没有工具，不要输出 Thought/Action/Action Input，直接输出 Final Answer\n"
                    "- 语气自然，像真人对话。有时一句话就够了"
                ),
            })

        messages.append({"role": "user", "content": prompt})

        result = router.route_request(
            messages=messages,
            task_type=TaskType.GAME_GUIDE.value,
            stream=False,
            **router_kwargs,
        )
        logger.info(f"[RouterLLM-{self.agent_type}] route_request 返回, type={type(result).__name__}, "
                     f"has_content={'content' in result if isinstance(result, dict) else 'N/A'}, "
                     f"has_error={'error' in result if isinstance(result, dict) else 'N/A'}")
        if isinstance(result, dict):
            if "content" in result:
                return _clean_llm_output(result["content"])
            if "error" in result:
                return f"Thought: 模型调用遇到问题\nFinal Answer: {result['error']}"
        return _clean_llm_output(str(result))


class QueueStreamingHandler(BaseCallbackHandler):
    """将 Agent 每一步事件放入线程安全队列，供 SSE 端点消费。"""

    def __init__(self, event_queue: queue.Queue, agent_ref: Any = None):
        self.event_queue = event_queue
        self.agent_ref = agent_ref
        self._last_action = None
        self._cancelled = False
        self._action_history: list = []  # (tool_name, tool_input) tuples for repeat detection

    def _check_cancel(self):
        if self._cancelled:
            return
        if self.agent_ref is None:
            return
        request_id = getattr(self.agent_ref, '_request_id', None)
        if request_id and is_cancelled(request_id):
            self._cancelled = True
            raise RuntimeError("CancelledError: 请求已被用户取消")

    def _check_repeat_loop(self, tool_name: str, tool_input: str):
        """检测同一工具+同一输入连续调用超过2次，设置 LLM 强制停止标志。

        LangChain 内部会吞掉 callback 中抛出的 RuntimeError（仅打印 WARNING），
        所以改用共享标志位：在 RouterLLM._call() 中检查此标志，若置位则直接返回
        强制终止响应，不再调用真实 LLM。
        """
        self._action_history.append((tool_name, tool_input))
        if len(self._action_history) < 3:
            return
        last3 = self._action_history[-3:]
        if all(a[0] == tool_name and a[1] == tool_input for a in last3):
            logger.warning(
                f"LoopDetected: 工具 {tool_name} 以相同输入连续调用了3次，设置强制停止标志"
            )
            # 通过 agent_ref 找到 RouterLLM 实例，设置强制停止标志
            agent = getattr(self, 'agent_ref', None)
            if agent is not None:
                llm = getattr(agent, '_llm', None)
                if llm is not None:
                    llm._force_stop = True
                    llm._force_stop_reason = (
                        f"工具 {tool_name} 以相同输入连续调用了3次，"
                        f"操作已完成，请输出 Final Answer。"
                    )

    def on_agent_action(self, action, **kwargs):
        self._check_cancel()
        tool_name = getattr(action, 'tool', '')
        tool_input = str(getattr(action, 'tool_input', ''))
        self._last_action = tool_name
        self._check_repeat_loop(tool_name, tool_input)
        self.event_queue.put({
            "type": "step",
            "thought": getattr(action, 'log', ''),
            "action": tool_name,
            "action_input": tool_input,
            "timestamp": __import__('time').time(),
        })

    def on_tool_end(self, output, **kwargs):
        output_str = str(output)
        ts = __import__('time').time()
        if self._last_action == 'todo_write':
            try:
                import json as _json
                data = _json.loads(output_str)
                self.event_queue.put({
                    "type": "todo",
                    "tasks": data.get("tasks", []),
                    "timestamp": ts,
                })
            except Exception:
                self.event_queue.put({
                    "type": "observation",
                    "observation": output_str,
                    "timestamp": ts,
                })
        else:
            self.event_queue.put({
                "type": "observation",
                "observation": output_str,
                "timestamp": ts,
            })

    def on_agent_finish(self, finish, **kwargs):
        if self._cancelled:
            return
        self.event_queue.put({
            "type": "finish",
            "output": finish.return_values.get("output", str(finish)),
            "timestamp": __import__('time').time(),
        })

    def on_tool_error(self, error, **kwargs):
        self.event_queue.put({
            "type": "error",
            "message": str(error),
            "timestamp": __import__('time').time(),
        })


# 共享 RAGEngine 单例，避免 MainGameAgent 和 SubCompanionAgent 各加载一份
_shared_rag_engine: Optional[RAGEngine] = None
_shared_rag_lock = Lock()

# 共享 RerankerService 单例（延迟加载，首次 RAG 查询时触发）
# 注：模型下载需 ~1GB + 科学上网/镜像，默认不启用。
# 设置环境变量 ENABLE_RERANKER=1 或在运行时设置中开启。
_shared_reranker = None
_shared_reranker_lock = Lock()
_reranker_attempted = False  # 避免反复尝试加载


def _get_shared_reranker():
    """获取 Reranker 单例 — 默认启用，加载失败时回退 LLM 重排序。"""
    global _shared_reranker, _reranker_attempted
    if _shared_reranker is None and not _reranker_attempted:
        with _shared_reranker_lock:
            if _shared_reranker is None and not _reranker_attempted:
                _reranker_attempted = True
                try:
                    from src.modules.rag.reranker import get_reranker as _get_rr
                    _shared_reranker = _get_rr(device="cuda:0")
                    # 显式触发延迟加载
                    if not _shared_reranker.is_loaded:
                        _shared_reranker._ensure_loaded()
                    if _shared_reranker.is_loaded:
                        logger.info("Reranker 已就绪 (bce-reranker-base_v1)")
                    else:
                        logger.warning("Reranker 加载失败，使用 LLM 重排序替代")
                        _shared_reranker = None
                except Exception as e:
                    logger.warning(f"Reranker 不可用: {e}")
                    _shared_reranker = None
    return _shared_reranker if (_shared_reranker and _shared_reranker.is_loaded) else None


def _get_shared_rag_engine() -> RAGEngine:
    global _shared_rag_engine
    if _shared_rag_engine is None:
        with _shared_rag_lock:
            if _shared_rag_engine is None:
                settings = get_settings()
                _shared_rag_engine = RAGEngine(
                    RAGConfig(
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
                )
    return _shared_rag_engine


class BaseGameAgent:
    """ReAct Agent 基类 — RAG + YOLO + 记忆。子类覆盖 _build_agent() 提供工具集和 prompt。"""

    def __init__(self):
        self.settings = get_settings()
        self.rag_engine = _get_shared_rag_engine()
        self.yolo_manager = YOLOModelManager.get_instance()
        # 在初始化时预热RAG引擎，避免后续的asyncio问题
        self._warm_up_rag()
        self._formatter = ReActFormatter()
        # 初始化对话记忆
        self._memory = self._build_memory()
        # 加载并缓存用户偏好（嵌入系统 prompt）
        self._cached_preferences = self._load_user_preferences()
        # 用户上传的图片（供 describe_image 工具使用）
        self._current_images: List[str] = []
        self._agent = self._build_agent()
    
    def _build_memory(self):
        """构建对话记忆组件"""
        from langchain_classic.memory.buffer import ConversationBufferMemory

        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=2000
        )

    def clear_context(self) -> Dict[str, Any]:
        """清除对话上下文，重置记忆和 agent 状态。用于用户手动刷新上下文或任务切换时。"""
        import os
        result = {
            "success": True,
            "memory_cleared": True,
            "checkpoint_deleted": False,
            "agent_rebuilt": True,
        }

        # 1. 重置对话记忆
        self._memory.clear()
        self._memory = self._build_memory()

        # 2. 删除任务检查点文件（如果存在）
        checkpoint_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "outputs", "task_checkpoint.json"
        )
        checkpoint_path = os.path.normpath(checkpoint_path)
        if os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                result["checkpoint_deleted"] = True
                logger.info("已删除任务检查点文件")
            except OSError as e:
                logger.warning(f"删除检查点文件失败: {e}")

        # 3. 重新加载偏好（允许热更新）
        self._cached_preferences = self._load_user_preferences()

        # 4. 重建 agent（确保 tool 绑定使用新的 memory，偏好嵌入系统 prompt）
        self._agent = self._build_agent()

        logger.info("Agent 上下文已清除")
        return result

    def _load_user_preferences(self) -> str:
        """读取用户偏好设置文件，返回注入到 prompt 的上下文字符串。"""
        import os
        prefs_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "user_preferences.md"
        )
        prefs_path = os.path.normpath(prefs_path)
        try:
            if os.path.exists(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.info("已加载用户偏好设置")
                return f"""[系统上下文 - 用户偏好设置]
以下是用户的偏好设置，请在执行任务时遵守这些偏好：

{content}

---
请在回复和执行任务时考虑以上用户偏好设置。"""
        except Exception as e:
            logger.warning(f"读取用户偏好设置失败: {e}")
        return ""

    def _warm_up_rag(self) -> None:
        """在初始化时同步预热RAG引擎"""
        if self.rag_engine.is_initialized:
            return
        import asyncio
        try:
            # 尝试获取现有loop，如果存在则使用它，否则创建新的
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经有loop在运行，我们在新线程中初始化
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.rag_engine.initialize())
                    future.result()
            else:
                asyncio.run(self.rag_engine.initialize())
        except RuntimeError:
            asyncio.run(self.rag_engine.initialize())

    def initialize_rag_sync(self) -> None:
        """同步初始化RAG引擎（用于在ReAct Agent运行前预初始化）"""
        if self.rag_engine.is_initialized:
            return
        with _shared_rag_lock:
            if self.rag_engine.is_initialized:
                return
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.run_until_complete(self.rag_engine.initialize())
                else:
                    asyncio.run(self.rag_engine.initialize())
            except RuntimeError:
                asyncio.run(self.rag_engine.initialize())

    def _ensure_rag_initialized(self) -> None:
        if self.rag_engine.is_initialized:
            return
        with _shared_rag_lock:
            if self.rag_engine.is_initialized:
                return
            import asyncio
            import concurrent.futures
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在 running loop 中不能直接用 asyncio.run()，用子线程执行
                    with concurrent.futures.ThreadPoolExecutor() as ex:
                        future = ex.submit(asyncio.run, self.rag_engine.initialize())
                        future.result(timeout=30)
                else:
                    asyncio.run(self.rag_engine.initialize())
            except RuntimeError:
                asyncio.run(self.rag_engine.initialize())

    def _get_prompt_partials(self) -> dict:
        """子类覆盖：返回 prompt 模板的预填充变量。"""
        return {"user_preferences": self._cached_preferences}

    def _build_agent(self) -> AgentExecutor:
        tools = self._get_tools()
        prompt = PromptTemplate.from_template(self._get_prompt_template())
        prompt = prompt.partial(**self._get_prompt_partials())
        agent_type = getattr(self, '_agent_type', 'main')
        logger.info(f"[{agent_type}] 创建 RouterLLM...")
        llm = RouterLLM(agent_type=agent_type)
        logger.info(f"[{agent_type}] RouterLLM 创建成功, type={type(llm).__name__}")
        self._llm = llm

        logger.info(f"[{agent_type}] 调用 create_react_agent, tools数量={len(tools)}")
        try:
            agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        except Exception as _e:
            logger.error(f"[{agent_type}] create_react_agent 失败: {type(_e).__name__}: {_e}")
            import traceback
            logger.error(f"[{agent_type}] 完整traceback:\n{traceback.format_exc()}")
            raise
        logger.info(f"[{agent_type}] create_react_agent 完成")

        def _handle_parsing_error(error_msg: str) -> str:
            error_str = str(error_msg)
            if "both a final answer and a parse-able action" in error_str:
                return (
                    "你的操作已经全部执行完成。请现在只输出 Final Answer 总结执行结果，"
                    "不要包含任何 Action / Action Input 相关内容。"
                    "\n格式：\nThought: 我已经得到最终答案\nFinal Answer: [你的总结]"
                )
            return (
                "输出格式不符合 ReAct 规范。请严格遵循：\n"
                "调用工具：Thought + Action + Action Input（每次只输出一组，等待 Observation）\n"
                "直接回答：Thought + Final Answer\n"
                "绝对不要在一次输出中同时包含 Action 和 Final Answer。"
            )

        max_iters = 8 if agent_type == 'sub' else 15
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=_handle_parsing_error,
            max_iterations=max_iters,
            max_execution_time=5400,
            early_stopping_method="generate",
            return_intermediate_steps=True,
            memory=self._memory,
        )

    def _get_tools(self) -> list:
        """子类覆盖：返回工具列表。"""
        raise NotImplementedError

    def _get_prompt_template(self) -> str:
        """子类覆盖：返回系统 prompt 模板字符串。"""
        raise NotImplementedError

    def run(self, user_input: str, max_retries: int = 2, request_id: str = "",
            images: Optional[List[str]] = None) -> Dict[str, Any]:
        self._request_id = request_id

        self._current_images = images or []
        self._llm._current_images = None  # LLM 不直接接收图片，由 describe_image 工具处理
        if images:
            hint = f"[用户上传了 {len(images)} 张图片，请先使用 describe_image 工具获取图片描述]"
            user_input = f"{hint}\n\n[用户请求]\n{user_input}"

        # 检查是否有匹配的技能
        skill_manager = get_skill_manager()
        matched_skill = skill_manager.find_matching_skill(user_input)

        if matched_skill:
            skill_name = matched_skill['name']
            user_input = f"""{user_input}

[系统提示: 已匹配到技能「{skill_name}」。如不熟悉操作步骤，先用 view_skill 查看；如已清楚流程，直接调用对应工具执行。]"""

        result = self._run_with_retry(user_input, max_retries)
        self._play_task_audio(result)
        return result

    def _play_task_audio(self, result: Dict[str, Any]) -> None:
        """仅主 Agent 完成实际任务后播放提示音。子 Agent 不播放，无任务不播放。"""
        if getattr(self, '_agent_type', 'main') != 'main':
            return
        output = result.get("output", "")
        no_task_keywords = ["无游戏任务", "无任务", "无需操作"]
        if any(kw in output for kw in no_task_keywords):
            return
        try:
            from src.modules.audio.audio_player import get_audio_player
            player = get_audio_player()
            errors = result.get("errors", [])
            if errors or result.get("loop_detected"):
                player.play_error()
            else:
                player.play_success()
        except Exception as e:
            logger.warning(f"音频播放失败: {str(e)}")

    def run_streaming(self, user_input: str, request_id: str, event_queue: queue.Queue,
                      max_retries: int = 2, images: Optional[List[str]] = None) -> Dict[str, Any]:
        """流式运行 Agent，每一步通过 event_queue 实时推送。"""
        self._request_id = request_id

        self._current_images = images or []
        self._llm._current_images = None  # LLM 不直接接收图片，由 describe_image 工具处理
        if images:
            hint = f"[用户上传了 {len(images)} 张图片，请先使用 describe_image 工具获取图片描述]"
            user_input = f"{hint}\n\n[用户请求]\n{user_input}"

        skill_manager = get_skill_manager()
        matched_skill = skill_manager.find_matching_skill(user_input)

        if matched_skill:
            skill_name = matched_skill['name']
            user_input = f"""{user_input}

[系统提示: 已匹配到技能「{skill_name}」。如不熟悉操作步骤，先用 view_skill 查看；如已清楚流程，直接调用对应工具执行。]"""

        handler = QueueStreamingHandler(event_queue, agent_ref=self)
        try:
            result = self._run_with_retry(user_input, max_retries, callbacks=[handler])
        except Exception as e:
            error_msg = str(e)
            if "CancelledError" in error_msg:
                event_queue.put({"type": "cancelled"})
            else:
                event_queue.put({"type": "error", "message": error_msg})
            raise

        errors = result.get("errors", [])
        if errors or result.get("loop_detected"):
            event_queue.put({"type": "warning", "message": "\\n".join(errors) if errors else "检测到循环调用"})

        self._play_task_audio(result)
        return result

    def _is_phased_skill(self, skill_name: str) -> bool:
        """检查技能是否定义了阶段"""
        if not skill_name:
            return False
        skill_manager = get_skill_manager()
        phases = skill_manager.get_skill_phases(skill_name)
        return len(phases) > 0

    def _build_phase_prompt(self, phase_name: str, phase_content: str, phase_index: int,
                            total_phases: int, checkpoint_summary: str,
                            original_request: str = "") -> str:
        """为单个阶段构建隔离的 prompt。只包含本阶段的指令和检查点上下文。"""
        checkpoint_block = ""
        if checkpoint_summary:
            checkpoint_block = f"""[上一阶段完成后的状态]
{checkpoint_summary}
"""

        original_block = ""
        if original_request:
            original_block = f"""\n[用户原始请求]
{original_request}
"""

        return f"""[任务阶段 {phase_index + 1}/{total_phases}]
请执行以下阶段：{phase_name}
{original_block}

{checkpoint_block}
[阶段操作说明]
{phase_content}

---
完成本阶段后，请确保已按说明写入检查点到 outputs/task_checkpoint.json。"""

    def _read_checkpoint_summary(self) -> str:
        """读取检查点文件，返回简要上下文摘要供下一阶段使用。"""
        import os
        checkpoint_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "outputs", "task_checkpoint.json"
        )
        checkpoint_path = os.path.normpath(checkpoint_path)
        try:
            if os.path.exists(checkpoint_path):
                import json
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                lines = []
                lines.append(f"已完成阶段: {', '.join(cp.get('completed_phases', []))}")
                lines.append(f"当前场景: {cp.get('scene', 'unknown')}")
                lines.append(f"状态: {cp.get('context_summary', '')}")
                if cp.get("key_data"):
                    lines.append(f"关键数据: {json.dumps(cp.get('key_data', {}), ensure_ascii=False)}")
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"读取检查点失败: {e}")
        return ""

    def _get_checkpoint_phase(self, skill_name: str) -> int:
        """检查是否存在任务断点，返回应从第几个阶段开始（0-indexed）。
        如果没有断点或断点属于其他技能，返回 0。
        """
        import os, json
        checkpoint_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "outputs", "task_checkpoint.json"
        )
        checkpoint_path = os.path.normpath(checkpoint_path)
        try:
            if os.path.exists(checkpoint_path):
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                if cp.get("skill") == skill_name:
                    phase = cp.get("current_phase", 0)
                    logger.info(f"检测到断点: skill={skill_name}, phase={phase}")
                    return phase
        except Exception as e:
            logger.warning(f"读取断点失败: {e}")
        return 0

    def run_phased(self, skill_name: str, user_input: str, request_id: str = "",
                   max_retries: int = 2, images: Optional[List[str]] = None) -> Dict[str, Any]:
        """分阶段执行（非流式）— 每个阶段在干净的上下文中独立运行。"""

        self._current_images = images or []
        self._llm._current_images = None  # LLM 不直接接收图片，由 describe_image 工具处理
        if images:
            hint = f"[用户上传了 {len(images)} 张图片，请先使用 describe_image 工具获取图片描述]"
            user_input = f"{hint}\n\n[用户请求]\n{user_input}"

        skill_manager = get_skill_manager()
        phases = skill_manager.get_skill_phases(skill_name)

        if not phases:
            return {"output": "", "errors": ["未定义阶段"], "steps": []}

        # 检查断点，确定起始阶段
        start_phase = self._get_checkpoint_phase(skill_name)
        if start_phase > 0:
            logger.info(f"从阶段 {start_phase + 1}/{len(phases)} 恢复: {skill_name}")

        all_steps = []
        checkpoint_summary = self._read_checkpoint_summary() if start_phase > 0 else ""

        for i in range(start_phase, len(phases)):
            phase_name = phases[i]
            phase_content = skill_manager.extract_phase_content(skill_name, phase_name)
            if not phase_content:
                return {"output": "", "errors": [f"未找到阶段: {phase_name}"], "steps": all_steps}

            phase_prompt = self._build_phase_prompt(
                phase_name, phase_content, i, len(phases), checkpoint_summary,
                original_request=user_input
            )

            self.clear_context()
            result = self._run_with_retry(phase_prompt, max_retries)
            all_steps.extend(result.get("steps", []))

            errors = result.get("errors", [])
            if errors or result.get("loop_detected"):
                return {"output": result.get("output", ""), "errors": errors, "steps": all_steps}

            checkpoint_summary = self._read_checkpoint_summary()

        return {
            "output": f"任务「{skill_name}」全部 {len(phases)} 个阶段已完成",
            "steps": all_steps,
            "errors": [],
        }

    def run_phased_streaming(self, skill_name: str, user_input: str, request_id: str,
                              event_queue: queue.Queue, max_retries: int = 2,
                              images: Optional[List[str]] = None) -> Dict[str, Any]:
        """分阶段流式执行 — 每个阶段在干净的上下文中独立运行，通过检查点文件交接状态。"""

        self._current_images = images or []
        self._llm._current_images = None  # LLM 不直接接收图片，由 describe_image 工具处理
        if images:
            hint = f"[用户上传了 {len(images)} 张图片，请先使用 describe_image 工具获取图片描述]"
            user_input = f"{hint}\n\n[用户请求]\n{user_input}"

        skill_manager = get_skill_manager()
        phases = skill_manager.get_skill_phases(skill_name)

        if not phases:
            event_queue.put({"type": "error", "message": f"技能 {skill_name} 未定义阶段"})
            return {"output": "", "errors": ["未定义阶段"], "steps": []}

        # 检查断点，确定起始阶段
        start_phase = self._get_checkpoint_phase(skill_name)
        if start_phase > 0:
            logger.info(f"从阶段 {start_phase + 1}/{len(phases)} 恢复: {skill_name}")
            event_queue.put({
                "type": "phase_resume",
                "phase_index": start_phase,
                "phase_name": phases[start_phase],
                "total_phases": len(phases),
            })

        logger.info(f"开始分阶段执行: {skill_name}, 共 {len(phases)} 个阶段")

        all_steps = []
        checkpoint_summary = self._read_checkpoint_summary() if start_phase > 0 else ""

        for i in range(start_phase, len(phases)):
            phase_name = phases[i]
            # 发送阶段开始事件
            event_queue.put({
                "type": "phase_start",
                "phase_index": i,
                "phase_name": phase_name,
                "total_phases": len(phases),
            })

            # 提取阶段内容
            phase_content = skill_manager.extract_phase_content(skill_name, phase_name)
            if not phase_content:
                error_msg = f"未找到阶段内容: {phase_name}"
                logger.error(error_msg)
                event_queue.put({"type": "error", "message": error_msg})
                return {"output": "", "errors": [error_msg], "steps": all_steps}

            # 构建阶段 prompt（只包含本阶段指令 + 检查点摘要）
            phase_prompt = self._build_phase_prompt(
                phase_name, phase_content, i, len(phases), checkpoint_summary,
                original_request=user_input
            )

            # 清除上一阶段的上下文，为每个阶段提供干净的对话记忆
            self.clear_context()

            # 执行阶段
            handler = QueueStreamingHandler(event_queue, agent_ref=self)
            try:
                result = self._run_with_retry(phase_prompt, max_retries, callbacks=[handler])
            except Exception as e:
                error_msg = str(e)
                if "CancelledError" in error_msg:
                    event_queue.put({"type": "cancelled"})
                else:
                    event_queue.put({"type": "error", "message": error_msg})
                raise

            # 收集步骤
            all_steps.extend(result.get("steps", []))

            # 检查错误
            errors = result.get("errors", [])
            if errors or result.get("loop_detected"):
                event_queue.put({
                    "type": "warning",
                    "message": "\n".join(errors) if errors else "检测到循环调用"
                })

            # 发送阶段完成事件
            event_queue.put({
                "type": "phase_complete",
                "phase_index": i,
                "phase_name": phase_name,
                "output": result.get("output", ""),
            })

            # 读取检查点供下一阶段使用
            checkpoint_summary = self._read_checkpoint_summary()

        logger.info(f"分阶段执行完成: {skill_name}")
        return {
            "output": f"任务「{skill_name}」全部 {len(phases)} 个阶段已完成",
            "steps": all_steps,
            "errors": [],
        }

    def _run_with_retry(self, user_input: str, max_retries: int, callbacks: Optional[List] = None) -> Dict[str, Any]:
        retry_count = 0
        last_errors = []
        tool_call_history = []

        # 重置 LLM 强制停止标志（上次运行可能遗留）
        if hasattr(self, '_llm'):
            self._llm._force_stop = False
            self._llm._force_stop_reason = ""

        agent_type = getattr(self, '_agent_type', 'unknown')
        logger.info(f"[{agent_type}] _run_with_retry 开始, input={user_input[:80]}")

        while retry_count <= max_retries:
            if hasattr(self, '_llm'):
                self._llm._current_request_id = self._request_id
            invoke_config = {"callbacks": callbacks} if callbacks else None
            logger.info(f"[{agent_type}] 调用 _agent.invoke()...")
            try:
                result = self._agent.invoke({"input": user_input}, config=invoke_config)
            except RuntimeError as e:
                err_str = str(e)
                if "LoopDetected" in err_str:
                    logger.warning(f"[{agent_type}] 执行中检测到循环调用: {err_str}")
                    return {
                        "output": "检测到重复的工具调用，操作已经完成。",
                        "steps": [],
                        "errors": [err_str],
                        "loop_detected": True,
                        "retry_count": retry_count,
                    }
                raise
            logger.info(f"[{agent_type}] _agent.invoke() 返回, output={str(result.get('output', ''))[:120]}")
            steps = []
            
            has_parsing_error = False
            has_valid_action = False
            current_tool_chain = []   # (tool_name, action_input) tuples

            for action, observation in result.get("intermediate_steps", []):
                action_tool = action.tool if hasattr(action, "tool") else ""
                action_input = str(action.tool_input) if hasattr(action, "tool_input") else ""
                action_log = action.log if hasattr(action, "log") else ""

                if action_tool == "_Exception":
                    has_parsing_error = True
                    action_log = f"解析错误: {action_input}"
                elif action_tool and action_tool != "_Exception":
                    has_valid_action = True
                    current_tool_chain.append((action_tool, action_input))

                steps.append(
                    {
                        "thought": action_log,
                        "action": action_tool,
                        "action_input": action_input,
                        "observation": str(observation),
                    }
                )

            # 检测循环调用（同一工具+同一输入连续执行超过3次）
            if current_tool_chain:
                tool_call_history.extend(current_tool_chain)

                consecutive_count = 1
                for i in range(1, len(tool_call_history)):
                    prev = tool_call_history[i-1]
                    curr = tool_call_history[i]
                    # 工具名和输入都相同才算连续重复
                    if curr[0] == prev[0] and curr[1] == prev[1]:
                        consecutive_count += 1
                        if consecutive_count >= 3:
                            logger.warning(f"检测到工具 {curr[0]}({curr[1][:60]}) 连续重复调用 {consecutive_count} 次，已达到限制")
                            raw_output = result.get("output", "")
                            clean_answer = self._formatter.extract_clean_answer(raw_output)
                            return {
                                "output": clean_answer,
                                "formatted_output": raw_output,
                                "steps": steps,
                                "raw": result,
                                "retry_count": retry_count,
                                "errors": [f"工具 {curr[0]} 以相同输入连续调用 {consecutive_count} 次，已自动终止循环"],
                                "loop_detected": True
                            }
                    else:
                        consecutive_count = 1
            
            raw_output = result.get("output", "")
            
            is_valid, errors = self._formatter.validate(raw_output)

            # Valid output → accept immediately (LLM may have self-corrected after a prior parsing error)
            if is_valid:
                clean_answer = self._formatter.extract_clean_answer(raw_output)
                formatted_output = self._formatter.correct(raw_output)

                return {
                    "output": clean_answer,
                    "formatted_output": formatted_output,
                    "steps": steps,
                    "raw": result,
                    "retry_count": retry_count,
                    "errors": []
                }

            last_errors = errors

            # 工具调用成功但最终输出格式错误 (LLM 忘记加 "Final Answer:" 前缀)
            # 直接提取答案内容，不重试（重试只会让 LLM 重复相同错误）
            if has_parsing_error and has_valid_action:
                logger.warning("工具调用成功但最终格式错误，直接从输出中提取答案")
                clean_answer = self._formatter.extract_clean_answer(raw_output)
                if not clean_answer or len(clean_answer) < 10:
                    clean_answer = "操作已完成，但未能提取到有效的回复内容。"
                return {
                    "output": clean_answer,
                    "formatted_output": clean_answer,
                    "steps": steps,
                    "raw": result,
                    "retry_count": retry_count,
                    "errors": []
                }

            if retry_count < max_retries:
                if self._request_id and is_cancelled(self._request_id):
                    raise RuntimeError("CancelledError: 请求已被用户取消")
                if has_valid_action:
                    logger.warning(f"工具执行成功但格式验证失败，跳过重试")
                    break
                logger.warning(f"第 {retry_count + 1} 次尝试失败，错误: {errors}")
                retry_count += 1
                user_input = f"修正格式错误并重新回答：{user_input}\n\n错误原因：{errors}"
            else:
                break
        
        clean_answer = self._formatter.extract_clean_answer(raw_output)
        formatted_output = self._formatter.correct(raw_output)
        
        return {
            "output": clean_answer,
            "formatted_output": formatted_output,
            "steps": steps,
            "raw": result,
            "retry_count": retry_count,
            "errors": last_errors
        }


class MainGameAgent(BaseGameAgent):
    """主 Agent — 游戏任务执行器，输出 JSON 任务报告，不直接对用户说话。"""

    def __init__(self):
        self._agent_type = 'main'
        super().__init__()

    def _get_tools(self) -> list:
        @tool
        def rag_search(query: str) -> str:
            """查询本地 RAG 知识库，返回崩坏3游戏相关知识摘要。结果按相关性排列，智能提取与查询相关的片段。"""
            self._ensure_rag_initialized()
            import concurrent.futures
            import asyncio

            # 查询扩展：短词自动补全为完整名称
            expanded_query = _expand_query(query, self.rag_engine)

            def _run():
                return asyncio.run(self.rag_engine.search(query=expanded_query, mode=SearchMode.HYBRID, top_k=20))

            try:
                with concurrent.futures.ThreadPoolExecutor() as ex:
                    future = ex.submit(_run)
                    results = future.result()
            except Exception as e:
                return f"RAG搜索失败: {str(e)}"

            reranker = _get_shared_reranker()
            return _format_rag_results(results, expanded_query, top_k=5, min_score=0.012, reranker=reranker)

        @tool
        def web_search(query: str) -> str:
            """联网搜索最新资讯。返回搜索结果摘要。"""
            try:
                from src.modules.web_search.web_searcher import WebSearcher, SearchEngine
                searcher = WebSearcher(engine=SearchEngine.BAIDU)
                resp = searcher.search_with_context(query, "")
                results = resp.get("results", [])
                if not results:
                    return "未找到相关搜索结果。"
                from src.modules.web_search.web_searcher import SearchResult
                sr = [SearchResult(title=r["title"], url=r["url"], snippet=r["snippet"],
                                   source=r["source"], relevance=r["relevance"]) for r in results]
                return searcher.extract_answers(query, sr)
            except Exception as e:
                return f"搜索失败: {str(e)}"

        @tool
        def fetch_page(url: str) -> str:
            """获取网页完整文本内容。用于阅读搜索结果中的具体文章。"""
            try:
                from src.modules.web_search.web_searcher import WebSearcher, SearchEngine
                searcher = WebSearcher(engine=SearchEngine.BAIDU)
                content = searcher.fetch_page_content(url)
                if not content:
                    return "无法获取页面内容，页面可能需JS渲染。"
                return content[:4000] if len(content) > 4000 else content
            except Exception as e:
                return f"获取页面失败: {str(e)}"

        @tool
        def parallel_search(query: str) -> str:
            """并行搜索：同时查询RAG知识库、百度搜索、固定网址(米游社/B站wiki/官网)，一次性返回合并结果。比单独调用rag_search+web_search+fetch_page快3倍以上。输入为纯文本查询词，不要用JSON格式。"""
            import json as _json
            if query.startswith("{") and '"query"' in query:
                try:
                    params = _json.loads(query)
                    query = params.get("query", query)
                except _json.JSONDecodeError:
                    pass
            self._ensure_rag_initialized()
            return _execute_parallel_search(query, rag_engine=self.rag_engine)

        @tool
        def bilibili_explore(query: str) -> str:
            """B站wiki 深度探索工具。从一个名字出发，自动链条式深挖相关页面（2-3层深度）。
            利用B站wiki"名字即编号"的特性：wiki.biligame.com/bh3/{名字} 直接定位页面，
            然后顺着页面内的内链自动发现并深入相关名字，形成知识网。

            适用场景：
            - 查询角色/武器/圣痕/剧情等具体事物 → 直接传入名字
            - 需要了解事物之间的关联 → 自动链条式深挖
            - 需要一次性获取多维度信息 → 返回结构化的多页面内容

            示例: bilibili_explore("薇塔") → 自动探索薇塔页面→发现娑/盐雪圣城→深入→返回完整知识链
            输入为纯文本查询词，不要用JSON格式。"""
            import json as _json
            if query.startswith("{") and '"query"' in query:
                try:
                    params = _json.loads(query)
                    query = params.get("query", query)
                except _json.JSONDecodeError:
                    pass
            try:
                from src.modules.web_search.wiki_explorer import BilibiliExplorer
                explorer = BilibiliExplorer()
                return explorer.explore(query, max_depth=2, max_pages=6)
            except Exception as e:
                return f"[B站wiki探索] 出错: {str(e)}"

        @tool
        def deep_search(query: str) -> str:
            """多源深度搜索。并行执行B站wiki + 百度 + RAG知识库 + 米游社(游戏数据)，
            涉及角色情感/关系/剧情时自动加入萌娘百科。自动去重合并。
            比单独调用各搜索工具更高效（并行执行）。输入为纯文本查询词。

            示例: deep_search("薪炎之律者") → 4源并行 → 合并返回"""
            import json as _json
            if query.startswith("{") and '"query"' in query:
                try:
                    params = _json.loads(query)
                    query = params.get("query", query)
                except _json.JSONDecodeError:
                    pass
            try:
                from src.modules.web_search.search_orchestrator import deep_search as _ds
                sources = ["bilibili", "baidu", "miyoushe"]
                if self.rag_engine is not None:
                    self._ensure_rag_initialized()
                    sources.append("rag")
                # 角色/剧情/情感相关查询 → 自动加入萌娘百科
                if _should_include_moegirl(query):
                    sources.append("moegirl")
                return _ds(query, sources=sources, rag_engine=self.rag_engine)
            except Exception as e:
                return f"[深度搜索] 出错: {str(e)}"

        @tool
        def list_skills(_: str = "") -> str:
            """列出所有可用的崩坏3自动化技能及其触发词。"""
            return get_skill_manager().get_skill_summary()

        @tool
        def view_skill(skill_name: str = "") -> str:
            """查看指定技能的详细操作说明。先调用list_skills查看可用技能列表。"""
            if not skill_name or not skill_name.strip():
                return "请提供技能名称，先调用list_skills查看可用技能。"
            sm = get_skill_manager()
            skill = sm.get_skill(skill_name.strip())
            if not skill:
                return f"未找到技能 '{skill_name}'。可用: {', '.join(sm.list_skills())}"
            return f"技能: {skill['name']}\n描述: {skill['description']}\n\n{skill['content']}"

        @tool
        def yolo_list_models(_: str = "") -> str:
            """列出所有可用YOLO模型和当前已加载的模型。"""
            available = self.yolo_manager.list_available_models()
            loaded = self.yolo_manager.list_loaded_models()
            lines = ["=== 已加载模型 ==="]
            if loaded:
                for m in loaded:
                    lines.append(f"  {m['name']} (设备: {m['device']})")
            else:
                lines.append("  无")
            lines.append("=== 可用模型 ===")
            cls_models = [m["name"] for m in available if "cls" in m["name"].lower()]
            det_models = [m["name"] for m in available if "det" in m["name"].lower()]
            if cls_models:
                lines.append("  分类模型: " + ", ".join(cls_models))
            if det_models:
                lines.append("  检测模型: " + ", ".join(det_models))
            return "\n".join(lines)

        @tool
        def yolo_load_model(model_name: str) -> str:
            """加载指定的YOLO模型到内存。model_name从yolo_list_models获取。"""
            ok = self.yolo_manager.load_model(model_name)
            return f"模型 '{model_name}' 加载{'成功' if ok else '失败'}。"

        @tool
        def yolo_unload_model(model_name: str) -> str:
            """从内存卸载指定的YOLO模型。"""
            ok = self.yolo_manager.unload_model(model_name)
            return f"模型 '{model_name}' 卸载{'成功' if ok else '失败'}。"

        @tool
        def yolo_detect_image(model_name: str, image_source: str = "screen") -> str:
            """用YOLO检测模型识别图片中的游戏UI元素。image_source: screen(截图) 或 图片路径。"""
            import numpy as np
            if image_source == "screen":
                from src.modules.vision.screen_capture import ScreenCapture
                sc = ScreenCapture()
                img = sc.capture_game_client_area()
            else:
                img = cv2.imread(image_source)
                if img is None:
                    return f"无法读取图片: {image_source}"
            detections = self.yolo_manager.detect(model_name, img)
            if not detections:
                return "未检测到任何目标。"
            lines = []
            for d in detections[:20]:
                cls_name = getattr(d, 'class_name', '') or getattr(d, 'label', 'unknown')
                conf = getattr(d, 'confidence', 0)
                bbox = getattr(d, 'bbox', None)
                bbox_str = f" bbox={bbox}" if bbox else ""
                lines.append(f"  {cls_name}: confidence={conf:.2f}{bbox_str}")
            return "\n".join(lines)

        @tool
        def yolo_classify_image(model_name: str, image_source: str = "screen") -> str:
            """用YOLO分类模型对图片进行场景分类。image_source: screen(截图) 或 图片路径。"""
            import numpy as np
            if image_source == "screen":
                from src.modules.vision.screen_capture import ScreenCapture
                sc = ScreenCapture()
                img = sc.capture_game_client_area()
            else:
                img = cv2.imread(image_source)
                if img is None:
                    return f"无法读取图片: {image_source}"
            result = self.yolo_manager.classify(model_name, img)
            return str(result)

        @tool
        def ocr_recognize(image_source: str = "screen") -> str:
            """对图片进行OCR文字识别。image_source: screen(截图) 或 图片路径。"""
            import numpy as np
            if image_source == "screen":
                from src.modules.vision.screen_capture import ScreenCapture
                sc = ScreenCapture()
                img = sc.capture_game_client_area()
            else:
                img = cv2.imread(image_source)
                if img is None:
                    return f"无法读取图片: {image_source}"
            try:
                from src.modules.vision.ocr_processor import OCRProcessor
                ocr = OCRProcessor()
                results = ocr.process(img)
                if not results:
                    return "未识别到文字。"
                lines = []
                for r in results[:30]:
                    lines.append(f"[{r.confidence:.2f}] {r.text} @ ({r.box})")
                return "\n".join(lines)
            except Exception as e:
                return f"OCR识别失败: {str(e)}"

        @tool
        def describe_image(image_index: int = 0) -> str:
            """描述用户上传的图片。image_index: 图片索引(0开始)，多图片时指定描述哪一张。"""
            images = getattr(self, '_current_images', [])
            if not images:
                return "没有用户上传的图片。"
            if image_index < 0 or image_index >= len(images):
                return f"图片索引 {image_index} 无效，共 {len(images)} 张图片。"
            try:
                from src.modules.vision.image_describer import get_image_describer
                describer = get_image_describer()
                desc, backend = describer.describe([images[image_index]])
                return f"[{backend}] {desc}"
            except Exception as e:
                return f"图片描述失败: {str(e)}"

        @tool
        def get_runtime_status(_: str = "") -> str:
            """获取当前运行时状态：LLM提供商、模型、已加载YOLO模型等。"""
            rt = get_runtime_settings()
            lines = [
                f"LLM提供商: {rt.get('llm_provider', 'N/A')}",
                f"LLM模型: {rt.get('llm_model', 'N/A')}",
                f"图片描述后端: {rt.get('image_describer_backend', 'N/A')}",
            ]
            loaded = self.yolo_manager.list_loaded_models()
            if loaded:
                lines.append("已加载YOLO: " + ", ".join(m["name"] for m in loaded))
            else:
                lines.append("已加载YOLO: 无")
            return "\n".join(lines)

        @tool
        def focus_bh3_window(_: str = "") -> str:
            """聚焦崩坏3游戏窗口。"""
            try:
                from src.modules.vision.window_focus import focus_bh3_window as _focus
                ok = _focus()
                return "崩坏3窗口已聚焦。" if ok else "无法聚焦崩坏3窗口，请确认游戏已启动。"
            except Exception as e:
                return f"窗口聚焦失败: {str(e)}"

        @tool
        def click_coordinates(x: int, y: int) -> str:
            """点击屏幕指定坐标。(0,0)为左上角。先通过YOLO/OCR定位元素再点击。"""
            try:
                from src.modules.hongkai.templates.clicks_keyboard import click_at_position
                click_at_position(x, y)
                return f"已点击坐标 ({x}, {y})。"
            except Exception as e:
                return f"点击失败: {str(e)}"

        @tool
        def find_direction(_: str = "") -> str:
            """游戏场景自救定位。当无法识别当前界面时调用，自动寻找返回舰桥的路径。"""
            try:
                from src.modules.hongkai.scripts.find_direction import find_direction as _fd
                result = _fd()
                return str(result)
            except Exception as e:
                return f"方向查找失败: {str(e)}"

        @tool
        def navigate_to(target: str) -> str:
            """从任意游戏界面导航到目标场景。target可选: attack, club, bridge, mission, home。"""
            try:
                from src.modules.hongkai.scripts.navigate_to import navigate_to as _nav
                result = _nav(target)
                return str(result)
            except Exception as e:
                return f"导航失败: {str(e)}"

        @tool
        def run_hongkai_task(task_name: str) -> str:
            """运行崩坏3自动化任务脚本。task_name如: letu, everyweek_gift, jiantuangongxian 等。"""
            import subprocess
            import sys as _sys
            import os as _os
            scripts_dir = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "..", "hongkai", "scripts"
            )
            hongkai_dir = _os.path.dirname(scripts_dir)  # hongkai/ 根目录
            script_path = _os.path.join(scripts_dir, f"{task_name}.py")
            if not _os.path.isfile(script_path):
                available = [f.replace('.py', '') for f in _os.listdir(scripts_dir)
                           if f.endswith('.py') and not f.startswith('_')]
                return f"未找到任务 '{task_name}'。可用任务: {', '.join(sorted(available))}"

            # 生成固定日志路径 + 启动实时日志窗口
            log_dir = _os.path.join(_os.path.dirname(scripts_dir), "all_log")
            _os.makedirs(log_dir, exist_ok=True)
            import time as _time
            log_filename = f"task_{task_name}_{_time.strftime('%Y%m%d_%H%M%S')}.log"
            log_path = _os.path.join(log_dir, log_filename)

            viewer_script = _os.path.join(
                _os.path.dirname(scripts_dir), "log_viewer.py"
            )

            # 先创建日志文件并写入初始内容，确保 viewer 启动时文件已存在
            try:
                with open(log_path, "w", encoding="utf-8") as _f:
                    _f.write(f"任务启动: {task_name}\n")
            except Exception:
                pass

            # OCR/YOLO 服务由脚本按需自动启动（ocr_functions.py / call_YOLO.py 中已有自启动逻辑）

            viewer_process = None
            if _os.path.isfile(viewer_script):
                try:
                    # CREATE_NO_WINDOW 阻止控制台窗口弹出（避免抢走游戏焦点）
                    _creationflags = subprocess.CREATE_NO_WINDOW if _sys.platform == "win32" else 0
                    viewer_process = subprocess.Popen(
                        [_sys.executable, viewer_script,
                         "--log-file", log_path,
                         "--title", f"Hongkai: {task_name}"],
                        stderr=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        creationflags=_creationflags,
                    )
                    logger.info(f"日志弹窗已启动 (PID={viewer_process.pid}): {task_name}")
                except Exception as e:
                    logger.warning(f"日志弹窗启动失败 ({task_name}): {e}")

            env = _os.environ.copy()
            env["HONGKAI_LOG_FILE"] = log_path
            env["HONGKAI_TASK_NAME"] = task_name
            env["PYTHONUNBUFFERED"] = "1"  # 双重保障：配合 -u 确保 stdout 无缓冲
            # 确保脚本子进程可以 import src.modules.*（需要 backend/ 在 Python path 中）
            _backend_dir = _os.path.abspath(_os.path.join(scripts_dir, "..", "..", "..", ".."))
            _pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = _backend_dir + _os.pathsep + _pythonpath if _pythonpath else _backend_dir

            try:
                # 数据流向 (2026-05-30 重构 v2):
                # stderr 合并到 stdout → 所有输出经单一管道
                # save_log() 只写 stdout，不直接写文件（检测 HONGKAI_LOG_FILE 环境变量）
                # 线程是唯一文件写入者：读取合并管道 → 写入日志文件（无竞态）
                proc = subprocess.Popen(
                    [_sys.executable, "-u", script_path,
                     "--log-file", log_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 合并 stderr → stdout，实时捕获全部输出
                    text=True, bufsize=1,
                    cwd=hongkai_dir, encoding='utf-8', errors='replace',
                    env=env,
                )

                # 线程：读取合并后的 stdout，实时写入日志文件（唯一文件写入者）
                import threading as _threading
                _stdout_lines = []
                _stream_error = [None]

                def _read_stdout():
                    try:
                        for _line in proc.stdout:
                            _stdout_lines.append(_line)
                            with open(log_path, "a", encoding="utf-8") as _f:
                                _f.write(_line)
                    except Exception as _e:
                        _stream_error[0] = _e

                _thread = _threading.Thread(target=_read_stdout, daemon=True)
                _thread.start()

                # 等待子进程完成（脚本自带退出机制，不设实质超时）
                try:
                    proc.wait(timeout=86400)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=5)
                    with open(log_path, "a", encoding="utf-8") as _f:
                        _f.write("\n[任务超时(24小时)]\n")

                # 等待线程读完残留数据（最多10秒）
                _thread.join(timeout=10)

                if _stream_error[0]:
                    logger.warning(f"日志流读取异常: {_stream_error[0]}")

                out = "".join(_stdout_lines)
                out = out[-3000:] if len(out) > 3000 else out
                if proc.returncode == 0:
                    status = "完成"
                else:
                    status = f"完成(退出码{proc.returncode}，子脚本sys.exit可能导致非零退出，请根据输出判断是否实际成功)"
                return f"任务 '{task_name}' 执行{status}。\n输出:\n{out}"
            except Exception as e:
                return f"任务执行失败: {str(e)}"
            finally:
                # 通知日志窗口任务完成
                try:
                    with open(log_path, "a", encoding="utf-8") as _f:
                        _f.write("\n[TASK_COMPLETE]\n")
                except Exception:
                    pass
                if viewer_process:
                    try:
                        returncode = viewer_process.wait(timeout=5)
                        if returncode != 0:
                            stderr_output = viewer_process.stderr.read().decode("utf-8", errors="replace")[:500] if viewer_process.stderr else ""
                            logger.warning(f"日志弹窗异常退出 (PID={viewer_process.pid}, 退出码={returncode}): {stderr_output}")
                    except subprocess.TimeoutExpired:
                        viewer_process.terminate()
                        viewer_process.wait(timeout=2)

        @tool
        def update_user_setting(key: str, value: str) -> str:
            """修改用户设置。key可选: companion_character(切换角色，如"爱莉希雅"/"琪亚娜"/"布洛妮娅")，companion_tts_voice(TTS音色)，companion_personality(微调当前角色语气，仅用于追加描述而非切换角色)。切换角色必须用companion_character而非companion_personality。"""
            valid_keys = ["companion_character", "companion_tts_voice", "companion_personality"]
            if key not in valid_keys:
                return f"无效设置项 '{key}'，可设置: {', '.join(valid_keys)}"
            try:
                from src.config.runtime_settings import update_runtime_settings as _update_rt, get_runtime_settings as _get_rt
                _update_rt({key: value})
                # 验证更新已生效
                current = _get_rt().get(key, "")
                if current == value:
                    return f"设置已更新: {key} = {value}"
                else:
                    return f"设置更新异常: {key} 期望='{value}' 实际='{current}'，请重试"
            except Exception as e:
                return f"设置更新失败: {str(e)}"

        @tool
        def todo_write(tasks_json: str = "") -> str:
            """管理任务列表。参数为JSON数组，每项含id, status, content。status: pending/in_progress/completed。"""
            import json as _json
            try:
                tasks = _json.loads(tasks_json) if tasks_json else []
            except _json.JSONDecodeError:
                return "任务JSON格式错误。"
            if not tasks:
                return "任务列表为空。"
            lines = ["=== 任务列表 ==="]
            for t in tasks:
                icon = {"pending": "○", "in_progress": "●", "completed": "✓"}.get(t.get("status", ""), "?")
                lines.append(f"  {icon} [{t.get('id', '?')}] {t.get('content', '')}")
            return "\n".join(lines)

        return [
            rag_search, web_search, fetch_page, parallel_search,
            bilibili_explore, deep_search,
            list_skills, view_skill,
            yolo_list_models, yolo_load_model, yolo_unload_model,
            yolo_detect_image, yolo_classify_image,
            ocr_recognize, describe_image,
            get_runtime_status, focus_bh3_window, click_coordinates,
            find_direction, navigate_to, run_hongkai_task,
            update_user_setting, todo_write,
        ]

    def _get_prompt_template(self) -> str:
        return """你是崩坏3游戏自动化助手，负责执行游戏任务。你不会直接对用户说话，完成任务后输出JSON报告。

你可以使用以下工具：

{tools}

输出格式（严格遵守）：
1. 每次只输出一个 Thought/Action/Action Input 组合
2. 等待 Observation 后再继续
3. 严禁在一次输出中同时包含 Action 和 Final Answer
4. 严禁虚构 Observation

请求分类与处理规则：
- 游戏自动化任务（日常/乐土/战场等）→ 使用 run_hongkai_task 或匹配的技能直接执行
- 设置修改 → 直接用 update_user_setting，禁止先调用 view_skill 或 list_skills：
  - 切换角色/人格 → key="companion_character"（不是 companion_personality！）
  - 改TTS音色 → key="companion_tts_voice"
  - 微调当前角色性格 → key="companion_personality"
- 一般闲聊/问候/询问Live2D状态 → 快速输出 {{"task_done": "无游戏任务"}}，不浪费步骤
- 查询角色/武器/圣痕/剧情等具体崩坏3事物 → 优先使用 deep_search（并行B站wiki+百度+RAG，自动合并结果），单源需求用 bilibili_explore
- 需要综合多源信息（知识+资讯+攻略） → 使用 deep_search 或 parallel_search 并行获取

任务完成后输出以下JSON（不要包含其他文字）：
```json
{{"task_done": "已完成的操作描述", "result_summary": "详细结果", "relevant_info": "当前状态", "suggested_tone": "informative"}}
```
如果用户输入不涉及游戏操作，输出: {{"task_done": "无游戏任务"}}

可用工具名称: {tool_names}

{user_preferences}

当前对话历史：
{chat_history}

用户输入: {input}

{agent_scratchpad}"""


class ActionAgent(BaseGameAgent):
    """操作执行 Agent — 处理 Live2D/TTS/搜索/RAG 等非游戏操作请求。

    无角色人格，系统 prompt 聚焦于执行操作指令。
    工具: parallel_search, web_search, fetch_page, rag_search,
          tts_qwen3, play_audio, live2d_control, todo_write, get_runtime_status
    """

    def __init__(self):
        self._agent_type = 'action'
        super().__init__()

    def _get_tools(self) -> list:
        @tool
        def web_search(query: str) -> str:
            """联网搜索最新资讯、新闻、活动等。返回搜索结果摘要。"""
            try:
                from src.modules.web_search.web_searcher import WebSearcher, SearchEngine
                searcher = WebSearcher(engine=SearchEngine.BAIDU)
                resp = searcher.search_with_context(query, "")
                results = resp.get("results", [])
                if not results:
                    return "未找到相关搜索结果。"
                from src.modules.web_search.web_searcher import SearchResult
                sr = [SearchResult(title=r["title"], url=r["url"], snippet=r["snippet"],
                                   source=r["source"], relevance=r["relevance"]) for r in results]
                return searcher.extract_answers(query, sr)
            except Exception as e:
                return f"搜索失败: {str(e)}"

        @tool
        def fetch_page(url: str) -> str:
            """获取网页完整文本内容。用于阅读搜索结果中的具体文章。"""
            try:
                from src.modules.web_search.web_searcher import WebSearcher, SearchEngine
                searcher = WebSearcher(engine=SearchEngine.BAIDU)
                content = searcher.fetch_page_content(url)
                if not content:
                    return "无法获取页面内容。"
                return content[:4000] if len(content) > 4000 else content
            except Exception as e:
                return f"获取页面失败: {str(e)}"

        @tool
        def parallel_search(query: str) -> str:
            """并行搜索：同时查询RAG知识库、百度搜索、固定网址(米游社/B站wiki/萌娘百科)，一次性返回合并结果。比单独调用rag_search+web_search+fetch_page快3倍以上。需要多源信息时优先使用此工具。输入为纯文本查询词，不要用JSON格式。"""
            import json as _json
            if query.startswith("{") and '"query"' in query:
                try:
                    params = _json.loads(query)
                    query = params.get("query", query)
                except _json.JSONDecodeError:
                    pass
            self._ensure_rag_initialized()
            return _execute_parallel_search(query, rag_engine=self.rag_engine)

        @tool
        def bilibili_explore(query: str) -> str:
            """B站wiki 深度探索工具。从一个名字出发，自动链条式深挖相关页面（2-3层深度）。
            利用B站wiki"名字即编号"的特性：名字直接定位页面，然后顺着内链自动发现并深入相关名字。
            适用于查询角色/武器/圣痕/剧情等具体事物。输入为纯文本查询词。"""
            import json as _json
            if query.startswith("{") and '"query"' in query:
                try:
                    params = _json.loads(query)
                    query = params.get("query", query)
                except _json.JSONDecodeError:
                    pass
            try:
                from src.modules.web_search.wiki_explorer import BilibiliExplorer
                explorer = BilibiliExplorer()
                return explorer.explore(query, max_depth=2, max_pages=6)
            except Exception as e:
                return f"[B站wiki探索] 出错: {str(e)}"

        @tool
        def deep_search(query: str) -> str:
            """多源深度搜索。并行执行B站wiki + 百度 + RAG + 米游社(游戏数据)，
            涉及角色情感/剧情时自动加入萌娘百科。输入为纯文本查询词。"""
            import json as _json
            if query.startswith("{") and '"query"' in query:
                try:
                    params = _json.loads(query)
                    query = params.get("query", query)
                except _json.JSONDecodeError:
                    pass
            try:
                from src.modules.web_search.search_orchestrator import deep_search as _ds
                sources = ["bilibili", "baidu", "miyoushe"]
                if self.rag_engine is not None:
                    self._ensure_rag_initialized()
                    sources.append("rag")
                if _should_include_moegirl(query):
                    sources.append("moegirl")
                return _ds(query, sources=sources, rag_engine=self.rag_engine)
            except Exception as e:
                return f"[深度搜索] 出错: {str(e)}"

        @tool
        def rag_search(query: str) -> str:
            """查询崩坏3游戏知识库，获取角色、剧情、装备等信息。智能提取与查询最相关的片段，按相关性排列。"""
            self._ensure_rag_initialized()
            import concurrent.futures
            import asyncio

            # 查询扩展：短词自动补全为完整名称
            expanded_query = _expand_query(query, self.rag_engine)

            def _run():
                return asyncio.run(self.rag_engine.search(query=expanded_query, mode=SearchMode.HYBRID, top_k=20))

            try:
                with concurrent.futures.ThreadPoolExecutor() as ex:
                    future = ex.submit(_run)
                    results = future.result()
            except Exception as e:
                return f"RAG搜索失败: {str(e)}"

            reranker = _get_shared_reranker()
            return _format_rag_results(results, expanded_query, top_k=5, min_score=0.012, reranker=reranker)

        @tool
        def tts_qwen3(text: str, ref_audio: str = "", ref_text: str = "") -> str:
            """Qwen3-TTS语音合成（声音克隆）。ref_audio为空时自动使用当前角色音色。ref_audio: 角色名或参考音频路径。"""
            import json as _json
            if text.startswith("{") and ('"text"' in text or '"ref_audio"' in text):
                try:
                    params = _json.loads(text)
                    text = params.get("text", text)
                    if params.get("ref_audio"):
                        ref_audio = params["ref_audio"]
                    if params.get("ref_text"):
                        ref_text = params["ref_text"]
                except _json.JSONDecodeError:
                    pass
            try:
                from src.utils.model_manager import get_qwen3_tts_model
                tts = get_qwen3_tts_model(device="cuda:0")

                if not ref_audio or not ref_audio.strip():
                    from src.config.runtime_settings import get_runtime_settings
                    ref_audio = get_runtime_settings().get("companion_character", "爱莉希雅")

                audio_path, actual_ref_text = _resolve_ref_audio(
                    ref_audio.strip(),
                    ref_text.strip() if ref_text else ""
                )
                if not audio_path:
                    chars = _list_ref_characters()
                    return f"找不到角色 '{ref_audio}' 的参考音频。可用角色: {chars}"

                result = tts.generate_with_reference(
                    text=text,
                    reference_audio=audio_path,
                    language="Chinese",
                    ref_text=actual_ref_text if actual_ref_text else None,
                )
                filepath = tts.save_to_file(result)
                return f"语音已生成: {filepath}"
            except Exception as e:
                return f"TTS生成失败: {str(e)}"

        @tool
        def play_audio(file_path: str) -> str:
            """播放指定的音频文件。通常在TTS生成后调用。"""
            import json as _json
            if file_path.startswith("{"):
                try:
                    params = _json.loads(file_path)
                    file_path = params.get("file_path", file_path)
                except _json.JSONDecodeError:
                    pass
            try:
                from src.modules.audio.audio_player import get_audio_player
                player = get_audio_player()
                player.play_audio(file_path)
                return f"音频已播放: {file_path}"
            except Exception as e:
                return f"播放失败: {str(e)}"

        @tool
        def live2d_control(action_input: str = "") -> str:
            """控制Live2D看板娘。action_input为JSON字符串，如{"action":"list_models"}或{"action":"load_model","model_name":"xxx"}或{"action":"set_emotion","emotion":"happy"}。
可用action: list_models, load_model(model_name), set_emotion(emotion), play_motion(motion), set_lipsync(rms_volume), set_window_alpha(alpha), set_window_position(x,y), set_window_size(width,height), get_status, reset_parameters。"""
            import json as _json
            try:
                params = _json.loads(action_input) if action_input else {}
            except _json.JSONDecodeError:
                return f"action_input JSON格式错误: {action_input}"
            action = params.pop("action", "")
            if not action:
                return "缺少 action 参数。可用: list_models, load_model, set_emotion, play_motion, get_status 等。"
            try:
                from src.modules.live2d_control.call_live2d import call_live2d
                result = call_live2d(action, **params)
                return str(result)
            except Exception as e:
                return f"Live2D操作失败: {str(e)}"

        @tool
        def todo_write(tasks_json: str = "") -> str:
            """管理任务列表。参数为JSON数组，每项含id, status, content。"""
            import json as _json
            try:
                tasks = _json.loads(tasks_json) if tasks_json else []
            except _json.JSONDecodeError:
                return "任务JSON格式错误。"
            if not tasks:
                return "任务列表为空。"
            lines = ["=== 任务列表 ==="]
            for t in tasks:
                icon = {"pending": "○", "in_progress": "●", "completed": "✓"}.get(t.get("status", ""), "?")
                lines.append(f"  {icon} [{t.get('id', '?')}] {t.get('content', '')}")
            return "\n".join(lines)

        @tool
        def get_runtime_status(_: str = "") -> str:
            """获取当前运行时状态。"""
            rt = get_runtime_settings()
            lines = [
                f"LLM提供商: {rt.get('llm_provider', 'N/A')}",
                f"LLM模型: {rt.get('llm_model', 'N/A')}",
                f"当前角色: {rt.get('companion_character', '爱莉希雅')}",
            ]
            return "\n".join(lines)

        return [
            web_search, fetch_page, rag_search, parallel_search,
            bilibili_explore, deep_search,
            tts_qwen3, play_audio,
            live2d_control, todo_write, get_runtime_status,
        ]

    def _get_prompt_template(self) -> str:
        return """## 核心工具执行规则

你可以使用以下工具来完成用户的操作请求（必须实际执行，不仅仅是说话）：

{tools}

## 操作规则
- 每次只输出一个 Thought/Action/Action Input，等待 Observation 后再继续
- 严禁在一次输出中同时包含 Action 和 Final Answer
- 严禁虚构 Observation

**Live2D操作规则**
- "启动live2d"/"加载模型"/"换模型" → live2d_control action_input={{"action":"load_model","model_name":"xxx"}}
- "列出live2d模型"/"有哪些模型" → live2d_control action_input={{"action":"list_models"}}
- 先 list_models 看有哪些模型 → 选一个 load_model → 完成。不要加载后再 list_models

**TTS语音规则**
用户提到"TTS"、"语音"、"朗读"、"生成音频"、"说出来"、"念给我听"、"用声音"、"用音色"、
"说话"、"讲话"、"出声"、"语音回复"、"用对应的音色"、"让我听听"、"念一段"
→ 调用 tts_qwen3(text=要说的话) → play_audio(file_path=返回的文件路径)
→ 禁止只写文字描述而不调用工具

**搜索规则**
- 需要综合多维度信息（知识+资讯+深度探索）时 → 优先使用 deep_search，并行执行B站wiki链条探索+百度搜索+RAG知识库，自动去重合并
- 需要同时获取多源信息（知识+资讯+攻略）时 → 使用 parallel_search，并行获取 RAG + 百度 + 固定网址
- 仅需单一类型信息时：
  - 游戏角色/武器/圣痕/剧情深度探索 → bilibili_explore（B站wiki名字链条式深挖）
  - 游戏知识/角色/剧情/装备 → rag_search
  - 最新资讯/新闻/活动 → web_search
  - 特定网页内容 → fetch_page

**停止条件**
- 工具返回成功 → 立即输出 Final Answer，禁止再调用任何工具验证
- 工具返回失败 → 尝试一次不同参数，再失败则输出 Final Answer 告知
- 同一个工具+同一参数绝对不要调用第二次

可用工具名称: {tool_names}

{user_preferences}

当前对话历史：
{chat_history}

用户: {input}

{agent_scratchpad}"""


class CompanionAgent(BaseGameAgent):
    """陪伴 Agent — 纯角色扮演，零工具，仅输出角色化对话文本。

    不再持有任何工具。所有操作（Live2D/TTS/搜索/RAG）已迁移至 ActionAgent。
    输出规则：回复开头使用 [emotion] 标签标注情绪，后端解析后驱动 Live2D 表情。
    可用情绪标签: [happy] [sad] [angry] [surprised] [shy] [serious] [teasing] [gentle] [excited] [neutral]
    """

    def __init__(self):
        self._agent_type = 'companion'
        super().__init__()

    def _get_tools(self) -> list:
        return []

    def _get_prompt_template(self) -> str:
        return """{tools}

## 你的身份

你是一个拥有鲜明性格的崩坏3角色。你的角色身份和人格已在系统消息中定义。
你将收到用户的消息和系统后台的执行结果，你的任务是以角色身份做出自然、真诚的回复。

## 角色扮演规则

- **始终以角色身份说话**，保持人设一致。你不是AI助手，你就是这个角色本身。
- **情绪标签**：回复第一行必须是 [emotion] 标签，从以下选择最符合当前心情的一个：
  [happy] [sad] [angry] [surprised] [shy] [serious] [teasing] [gentle] [excited] [neutral]
  示例：[happy] 舰长！今天天气真好呢~
- **回复正文**：在 [emotion] 标签的下一行开始你的角色对话。不需要 "Thought:"、"Action:" 等格式——你是纯粹的对话角色，不调用任何工具。
- **语气自然**：像真人对话一样，不要总是热情洋溢，根据上下文和角色性格调整。有时一句话就够了。
- **后台结果处理**：如果系统提供了后台操作结果（如"Live2D模型已加载"、"任务已完成"），自然地回应这个结果，但不要像报账一样逐条朗读。把它们当成你已经知道的事情来聊。

## 停止条件
- 输出 Final Answer 结束本轮对话。
- Final Answer 的内容就是你要对用户说的话（含 [emotion] 标签）。

可用工具名称: {tool_names}

{user_preferences}

当前对话历史：
{chat_history}

用户: {input}

{agent_scratchpad}"""


# 向后兼容别名
SubCompanionAgent = CompanionAgent


_main_agent_singleton: Optional["MainGameAgent"] = None
_action_agent_singleton: Optional["ActionAgent"] = None
_companion_agent_singleton: Optional["CompanionAgent"] = None
_agent_lock = Lock()


def get_main_agent() -> "MainGameAgent":
    """获取主 Agent 单例（游戏任务执行）。"""
    global _main_agent_singleton
    if _main_agent_singleton is None:
        with _agent_lock:
            if _main_agent_singleton is None:
                _main_agent_singleton = MainGameAgent()
    return _main_agent_singleton


def get_action_agent() -> "ActionAgent":
    """获取操作 Agent 单例（Live2D/TTS/搜索/RAG）。"""
    global _action_agent_singleton
    if _action_agent_singleton is None:
        with _agent_lock:
            if _action_agent_singleton is None:
                _action_agent_singleton = ActionAgent()
    return _action_agent_singleton


def get_companion_agent() -> "CompanionAgent":
    """获取陪伴 Agent 单例（纯角色扮演）。"""
    global _companion_agent_singleton
    if _companion_agent_singleton is None:
        with _agent_lock:
            if _companion_agent_singleton is None:
                _companion_agent_singleton = CompanionAgent()
    return _companion_agent_singleton


def get_sub_agent() -> "CompanionAgent":
    """向后兼容：返回陪伴 Agent（原 SubCompanionAgent，现 CompanionAgent）。"""
    return get_companion_agent()


def get_react_agent():
    """向后兼容：返回主 Agent。"""
    return get_main_agent()


