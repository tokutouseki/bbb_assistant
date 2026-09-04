称呼用户为master
# 崩坏3专属AI陪伴助手 (bbb-assistant)

崩坏3游戏AI陪伴助手，提供游戏辅助自动化、知识问答、角色扮演对话等功能。

## 技术栈

- **后端**: Python FastAPI + LangChain ReAct Agent
- **前端**: Vue 3 + Vite
- **LLM**: DeepSeek API / LM Studio (Qwen) / Ollama / 本地 GGUF
- **RAG**: ChromaDB + SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2) + bce-reranker-base_v1
- **视觉**: YOLO 目标检测 (游戏UI识别) + OCR + PixAI Tagger (动漫标签) + Bailian Qwen-VL (云端多模态)
- **语音**: TTS (Qwen3-TTS-12Hz-1.7B-Base, ICL语音克隆) + ASR (FunASR)
- **Live2D**: PySide6 QOpenGLWidget + live2d-py v0.7.0 (Cubism Native SDK v3)
- **自动化**: Win32 API 屏幕截图 + Win32 SendInput 键鼠模拟 + 模板匹配 + PowerShell 脚本

## 目录结构

```
bbb_assistant/
├── backend/
│   └── src/
│       ├── api/chat.py              # 聊天API (/api/chat/stream, /cancel, /clear)
│       ├── api/settings.py          # 设置API (含角色人格字段 + GET /characters 列表)
│       ├── config/settings.py       # 应用配置 (Pydantic Settings)
│       ├── config/runtime_settings.py # 运行时设置 (JSON持久化, 重启加载, 变更日志)
│       ├── config/cancel_signal.py  # 请求取消信号机制
│       ├── modules/
│       │   ├── agent/react_agent.py # 三Agent架构 (MainGameAgent + ActionAgent + CompanionAgent)
│       │   ├── character/character_manager.py # 角色人格管理 (SKILL.md加载/缓存/TTS音色)
│       │   ├── skill/skill_manager.py # 技能管理 (SKILL.md解析、阶段提取)
│       │   ├── vision/
│       │   │   ├── image_describer.py   # 多后端图片描述 (Bailian/PixAI/LM Studio)
│       │   │   ├── yolo_model_manager.py # YOLO管理 (加载/卸载/检测/分类)
│       │   │   ├── screen_capture.py    # 屏幕截图 (PrintWindow三级回退防遮挡)
│       │   │   ├── ocr_processor.py     # OCR识别
│       │   │   └── window_focus.py      # 窗口聚焦
│       │   ├── web_search/          # 联网搜索 (百度主引擎 + Playwright兜底 + 多源编排器)
│       │   │   ├── web_searcher.py          # 百度搜索 (requests → Playwright回退)
│       │   │   ├── wiki_explorer.py         # B站wiki名字链条探索器
│       │   │   ├── moegirl_explorer.py      # 萌娘百科Playwright内链探索器
│       │   │   └── search_orchestrator.py   # SearchOrchestrator多源并行协调器
│       │   ├── rag/                 # RAG检索引擎 + reranker.py (Cross-Encoder重排序)
│       │   ├── llm/                 # LLM路由 (多模型切换, vision能力过滤)
│       │   ├── audio/               # 音频 (TTS声音克隆 + 播放)
│       │   │   ├── qwen3_tts_generator.py  # Qwen3-TTS (ICL语音克隆 + RemoteProxy)
│       │   │   ├── qwen3_tts_worker.py     # TTS 子进程 TCP 服务端 (端口 5004)
│       │   │   ├── qwen3_tts_client.py     # TTS 子进程 TCP 客户端
│       │   │   ├── call_qwen3_tts.py       # TTS 子进程生命周期管理
│       │   │   ├── tts_generator.py        # VoxCPM TTS (已禁用，代码保留)
│       │   │   ├── audio_player.py         # 音频播放
│       │   │   └── reference_audio/        # 48位崩坏3角色参考音频
│       │   │       └── index.json          # 角色→音频路径+transcript索引
│       │   └── live2d_control/      # Live2D看板娘 (Qt OpenGL窗口 + TCP服务)
│       │   ├── conversation_logger.py  # 对话日志记录与导出 (供MP数字海马体消费)
│       └── services/                # 聊天服务、游戏监控
├── frontend/src/
│   ├── views/ChatView.vue           # SSE流式、图片上传/预览/灯箱、Markdown渲染
│   ├── views/SettingsView.vue       # LLM提供商/图片描述/Live2D/角色选择
│   └── stores/
│       ├── chat.js                  # 聊天状态管理 (SSE流式、消息列表)
│       └── settings.js              # 设置状态 (localStorage持久化, Live2D管理)
├── skills/
│   ├── characters/                  # 角色人格定义 (44个角色，每个角色一个 SKILL.md)
│   ├── full_operation/              # 全量日常调度
│   ├── letu/                        # 往世乐土自动化
│   ├── meizhou_jianfu/              # 每周减负
│   └── ... (共14个技能目录)
├── outputs/                         # ASR转录/TTS输出/任务检查点
├── data/
│   ├── chroma_db/                   # ChromaDB向量库
│   ├── rag_index/                   # RAG索引
│   └── user_settings.json           # 运行时设置持久化文件
└── user_preferences.md              # 用户偏好 (Agent启动时读取并嵌入系统prompt)
```

## 核心架构

### 三 Agent 架构 (react_agent.py)

**AgentRouter**: 单次 LLM 调用将用户消息分类为三类意图 — `game` / `action` / `chat`，不参与 ReAct 循环。

**MainGameAgent (游戏 Agent)**: DeepSeek Pro — 游戏任务执行器，输出 JSON 任务报告，不直接对用户说话。
**ActionAgent (操作 Agent)**: DeepSeek Pro — 处理 Live2D/TTS/搜索/RAG 等非游戏操作请求，无角色人格。
**CompanionAgent (陪伴 Agent)**: DeepSeek Flash — 纯角色扮演对话，零工具，仅输出带 `[emotion]` 标签的对话文本。唯一对用户可见的 Agent。

```
用户消息 → AgentRouter (意图分类)
              ├─ game   → MainGameAgent (游戏任务 → JSON报告)
              ├─ action → ActionAgent   (操作执行 → 结果文本)
              └─ chat   → (跳过业务Agent)
              ↓
         合成 Prompt → CompanionAgent (角色化回复 + [emotion] + TTS + Live2D) → 用户(SSE)
```

**MainGameAgent 工具 (23个)**:
rag_search, parallel_search, web_search, fetch_page, list_skills, view_skill,
yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image,
ocr_recognize, describe_image, get_runtime_status, focus_bh3_window, click_coordinates,
find_direction, navigate_to, run_hongkai_task, update_user_setting, todo_write,
bilibili_explore (B站wiki名字链条), deep_search (4源并行深度搜索)

**ActionAgent 工具 (11个)**:
web_search, fetch_page, rag_search, parallel_search, bilibili_explore, deep_search,
tts_qwen3, play_audio, live2d_control, todo_write, get_runtime_status

**CompanionAgent**: 零工具，纯角色扮演对话。10 种情绪标签: [happy] [sad] [angry] [surprised] [shy] [serious] [teasing] [gentle] [excited] [neutral]

**关键设计**:
- 严格遵循 ReAct 范式: Thought → Action → Action Input → Observation 循环
- `BaseGameAgent`: 公共基类 (memory、RAG、YOLO、分阶段执行、重试逻辑)
- `_get_tools()` / `_get_prompt_template()`: 子类覆盖，提供工具集和系统 prompt
- `RouterLLM(agent_type)`: "main"/"action" → Pro 模型, "companion"/"sub" → Flash 模型 (温度≤0.9)
- CompanionAgent 角色人格动态注入: `RouterLLM._call()` 从 `skills/characters/{name}/SKILL.md` 读取，替换 `[CHARACTER_PERSONALITY]` 占位符
- 角色切换零重建: 改 `user_settings.json` → 下一轮 `_call()` 自动读取新人格
- 对话记忆使用 ConversationBufferMemory (max 2000 tokens)
- 图片处理: 用户上传图片 → 主 Agent `describe_image` 工具 → 文本描述注入 CompanionAgent 上下文
- `_clean_llm_output()`: 输出清洗，截断 DeepSeek 虚构的多步骤幻觉文本
- `max_iterations`: MainGameAgent=15, ActionAgent=8, CompanionAgent=8
- `early_stopping_method="generate"`

### DeepSeek 输出解析防御 (三层)

DeepSeek 经常违反 ReAct 格式：在输出前插入对话文本、同时输出 Action 和 Final Answer、甚至虚构完整的 Observation。已实现三层防御：

1. **`_clean_llm_output()`** — 输出截断：只保留第一个有效 ReAct 意图，截断后续所有内容
2. **`_handle_parsing_error()`** — 解析错误反馈：将格式错误信息反馈给 LLM，引导修正
3. **Prompt 规则** — 系统 prompt 中严格限制每次只输出一个 Thought/Action/Action Input 组合

### 重复循环检测

通过 `RouterLLM._force_stop` 共享标志位 + `QueueStreamingHandler._check_repeat_loop()` 实现：
- 跟踪最近 3 次 `(tool_name, tool_input)` 调用历史
- 连续 3 次相同调用 → 设置 `llm._force_stop = True` → `_call()` 返回终止 Final Answer

### 图片描述系统 (image_describer.py)
- 多后端自动降级: `bailian` → `pixai_tagger` → `lmstudio` (顺序可配置)
- **Bailian (阿里百炼 Qwen-VL)**: 云端多模态模型, OpenAI兼容接口
- **PixAI Tagger**: 本地 ONNX 模型 (`D:/TokusCode/models/PixAI-Tagger/`), 13,461 个 Danbooru 标签, ONNX CPU 模式
- **LM Studio (Qwen-VL)**: 本地视觉模型, 最后兜底
- `describe()` 每次调用重新读取运行时设置, 前端切换后端即时生效

### LLM 路由 (llm_router.py)
- `ModelInfo.model_capabilities`: 模型级能力声明 (如 `"vision"`, `"streaming"`)
- 有图片时只选 `"vision" in model_capabilities` 的模型，无可用 vision 模型时返回明确错误
- `ContextOverflowError`: LM Studio 400 错误中检测上下文溢出关键词, 直接抛出提示

### 搜索系统

#### 多源深度搜索架构 (SearchOrchestrator)

```
用户查询
  ↓ deep_search() / parallel_search()
  ↓
SearchOrchestrator (多源并行协调器, ThreadPoolExecutor)
├── BilibiliSourceAgent   → BilibiliExplorer (名字链条, ~5s, requests直连)
├── MiyousheSourceAgent   → MiyousheExplorer (编号字典3347条, ~0.1s本地缓存)
├── MoegirlSourceAgent    → MoegirlExplorer (Playwright, ~30s, Cloudflare绕过)
├── _BaiduSourceAgent     → WebSearcher (百度, ~10s, requests→Playwright回退)
└── _RagSourceAgent       → RAGEngine (本地知识库, ~2s, 需注入rag_engine)
  ↓ 合并去重
返回结构化结果 (按来源分段, 含关联事物汇总)
```

**设计原则**: 超时隔离 (单源超时不阻塞, `search_with_timeout()`)、并行执行 (总耗时≈max各源耗时)、故障容忍 (单源失败不影响整体)、源自动选择 (deep_search 默认 bilibili+miyoushe+baidu+rag，角色剧情查询增配 moegirl)。

#### 文件结构

```
web_search/
├── web_searcher.py              # 百度搜索 (已有, requests→Playwright两级回退)
├── wiki_explorer.py             # B站wiki名字链条探索器 (_resolve_query前后缀剥离+噪音过滤+目录页降权)
├── moegirl_explorer.py          # 萌娘百科Playwright+API双通道探索器 (Cloudflare绕过+软404检测+消歧义处理)
├── miyoushe_explorer.py         # 米游社编号字典 + ID链条探索器
│   ├── MiyousheIdDict           #   名称→content_id字典 (3347条目, 懒加载, 前缀索引)
│   └── MiyousheExplorer         #   _resolve_query智能查询解析
├── search_orchestrator.py       # SearchOrchestrator多源并行协调器
│   ├── SourceAgent (ABC)        #   抽象基类: search(query) → SourceResult
│   ├── BilibiliSourceAgent      #   封装BilibiliExplorer, 超时30s
│   ├── MiyousheSourceAgent     #   封装MiyousheExplorer, 超时20s
│   ├── MoegirlSourceAgent      #   封装MoegirlExplorer, 超时60s
│   ├── _BaiduSourceAgent       #   适配WebSearcher
│   └── _RagSourceAgent         #   适配RAGEngine
└── __init__.py                  # 统一导出
```

#### 米游社编号字典 (MiyousheIdDict)

从 `data/` 目录树 **3354 个 JSON 文件** 中提取 `content_id` 字段构建:

| 目录 | 条目 | 内容 |
|------|------|------|
| 图鉴/ | 1983 | 女武神(109)+武器(384)+圣痕(690)+敌人(201)+人偶(13)+协同者(6)+材料(444)+宿舍名册(136) |
| 档案/ | 628 | 壁纸+美术档案+游戏PV+故事+角色+动画短片+漫画+服装+视频集锦 |
| 第二部探索指南/ | 401 | 成就+收藏品+关卡机制+地图点位+道具+系统玩法 |
| 往世乐土/ | 174 | 乐土角色+物品+事件+追忆+通用刻印 |
| 后崩坏书2专章/ | 125 | 怪物+成就+文件+角色+地图点位 |
| 其他 | 43 | 主线章节+攻略+主题曲+术语 |

**字典统计**: 3347 条目, 3328 唯一名, 17 个名字跨多分类(如识之律者=女武神+敌人, 全部保留, `lookup()` 返回列表, `lookup_best()` 按分类优先级取最优)。

**分类优先级**: 女武神(0) = 角色(0) > 武器(2) > 圣痕(3) > 协同者(4) > 人偶(5) > 敌人(6) > 材料(7) > 宿舍名册(8) > 其他(10)

**无 content_id 的文件 (7个)**: crawl_stats.json / user_settings.json / rag_index / 世界观×2(米游社文章) / 主线故事(米游社星球文章) / pending_shenheng_list(挂起列表)。均为非百科内容页，正确排除。

#### 智能查询解析 (_resolve_query)

三个探索器均有查询预处理，解决复合查询和简称问题:

| 输入 | 解析结果 | 策略 |
|------|---------|------|
| `崩坏3 符华` | `符华` | 剥离游戏前缀 + 字典精确匹配 |
| `凯文 崩坏3` | `「业魔」凯文` | 剥离前后缀 + 简称→全名前缀搜索 |
| `琪亚娜 崩坏3` | `琪亚娜` | **后缀剥离**（B站wiki/米游社/萌娘百科为专属站点，URL已含bh3/崩坏3） |
| `爱莉` | `爱莉希雅` | 前缀搜索 + 分类优先级 → 角色而非圣痕 |
| `识律` | `识之律者` | 前缀搜索 + 短名惩罚 → 女武神而非圣痕 |
| `薪炎` | `薪炎之律者` | 同上 |
| `bh3 芽衣` | `芽衣` | 剥离英文前缀 |

**设计原则**: B站wiki/米游社/萌娘百科的 URL 自带崩坏3上下文（`/bh3/`、`(崩坏3)#`），查询中的"崩坏3"是噪音。只有百度等通用搜索引擎需要"崩坏3"后缀来消歧。

**评分公式**: `score = (20 - extra_len) + (15 - cat_rank)`, extra_len = 全名长度 - 查询词长度。越短(接近原词)、分类越高(女武神>圣痕)，分数越高。

#### 三大搜索源关系

```
                     ┌─────────────────────────────┐
                     │     米游社百科 (baike)        │
                     │  baike.mihoyo.com/bh3/wiki/  │
                     │  content/{编号}/detail        │
                     │                              │
                     │  · 数字编号系统               │
                     │  · 内容最详尽 (含武器/圣痕数值) │
                     │  · 持续更新 → RAG快照会过时    │
                     │  · 是RAG知识库的主要数据源      │
                     └──────────┬──────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ↓               ↓               ↓
        ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
        │  RAG 知识库    │ │  B站wiki     │ │  萌娘百科      │
        │  (本地快照)    │ │  (名字索引)   │ │  (玩家视角)    │
        │              │ │              │ │              │
        │ 同源但可能过时 │ │ 名字即编号    │ │ 情感丰富       │
        │ 向量+关键词检索 │ │ 内容较少      │ │ 非常详细       │
        │              │ │ 米游社的       │ │ 缺游戏内部数据  │
        │              │ │ "名字友好版"   │ │ 角色+数据互补   │
        └──────────────┘ └─────────────┘ └──────────────┘
          数据来源           快速定位         玩家情感+细节
```

**三者互补关系**:
- 米游社 = 游戏官方数据 (武器/圣痕/角色数值)，但需要**编号字典**才能精确搜索
- B站wiki = 米游社的"名字友好版"，名字即编号，但内容大幅缩水
- 萌娘百科 = 玩家社区视角，情感细节丰富，但缺少游戏内部具体数据 (武器数值等)
- **米游社 + 萌娘百科 = 数据 + 情感 = 完整知识**

#### 搜索 URL 详解

| 来源 | 通用搜索 | 精确页面 | 说明 |
|------|---------|---------|------|
| 米游社百科 | `miyoushe.com/bh3/search?keyword=` | `baike.mihoyo.com/bh3/wiki/content/{编号}/detail` | **需要编号字典** (如 2091=无名之境)，否则只能走通用搜索 |
| B站wiki | `wiki.biligame.com/bh3/index.php?search=` | `wiki.biligame.com/bh3/{事物名}` | 名字即编号，但内容少；例: 无名之境：万物资始 |
| 萌娘百科 | `mzh.moegirl.org.cn/index.php?search=` | `zh.moegirl.org.cn/{事物名}(崩坏3)#` (角色)<br>`zh.moegirl.org.cn/{事物名}` (非角色) | 两种精确URL；受 Cloudflare 保护，requests 会 403 |

**萌娘百科精确搜索规则**:
- **崩坏3原创角色** (无跨作品同名): `https://zh.moegirl.org.cn/{角色名}` — 例: 薇塔、希娜狄雅（无需后缀）
- **跨作品同名角色**: `https://zh.moegirl.org.cn/{角色全名}(崩坏3)#` — 例: 琪亚娜·卡斯兰娜(崩坏3)、雷电芽衣(崩坏3)（与崩坏学园2/星穹铁道区分）
- **非角色事物**: `https://zh.moegirl.org.cn/{事物名}` — 例: 逆熵、天命、第二次崩坏

**萌娘百科探索器 (MoegirlExplorer) 三级回退机制**:
1. Playwright 浏览器直连 — 先 `/{name}`（覆盖崩坏3原创角色），失败/消歧义则 `/{name}(崩坏3)`
2. **MediaWiki API 回退** (`_fetch_via_api`) — Playwright 被 Cloudflare 阻挡时，通过 `api.php?action=query&prop=extracts` 获取页面内容，绕过 JS 挑战
3. Playwright 搜索回退 (`mzh.moegirl.org.cn/index.php?search=`) — 含桌面+移动版多选择器 + 通用链接提取
4. **软 404 检测**: 识别 MediaWiki "找不到这个页面" 伪成功响应
5. **消歧义页处理**: 仅使用强特征（"这是一个消歧义页"/"罗列了有相同或相近的标题"），排除常见句式"可以指："避免误判

**米游社编号搜索规则**:
- 百科内容页: `https://baike.mihoyo.com/bh3/wiki/content/{编号}/detail?bbs_presentation_style=no_header`
- `{编号}` 是数字ID，`content` 指具体事物详情页
- 需要 `名称 → 编号` 映射字典才能精确搜索，否则只能走通用关键词搜索

#### 搜索管道 (新旧两套，共存互补)

```
新: deep_search (SearchOrchestrator, 多源并行)
    用户查询 → _resolve_query 智能解析 (剥前缀/简称扩展)
      → 并行: B站wiki + 米游社(本地缓存) + 百度 + RAG (+ 萌娘百科 可选)
      → 合并去重 → 按来源分段 + 关联事物汇总

旧: parallel_search (三线程并行, 保留兼容)
    用户查询 → _expand_query
      → 并行: RAG(Hybrid) + Web(百度/Playwright) + Fixed(米游社/B站/萌娘 URL)
      → 合并返回
```

#### 各源适用场景

| 场景 | 首选 | 原因 |
|------|------|------|
| 角色基本信息 | B站wiki 角色页 | 名字直达，内容干净 |
| 游戏内部数据 (武器/圣痕数值) | 米游社百科 (RAG) | 唯一完整来源 |
| 角色情感/关系/剧情 | 萌娘百科 | 玩家视角最丰富 |
| 最新更新内容 | 米游社百科 (Web) | RAG快照可能过时 |
| 快速定位已知事物 | B站wiki 名字搜索 | 名字即编号 |

#### B站wiki 噪音过滤 (wiki_explorer.py)

探索器在链接提取和评分两个阶段进行噪音过滤：

| 阶段 | 机制 | 说明 |
|------|------|------|
| `_extract_links` | URL解码 + 前缀过滤 | `SKIP_LINK_PREFIXES` 先 `unquote(href)` 再匹配（B站wiki中文URL被编码） |
| `_extract_links` | 精确噪音名 | `{"首页", "创建", "最近更改", "帮助", "讨论", "导航", "关于本站", "上传文件", "MediaWiki", "沙盒", "待审核"}` |
| `_score_links` | 目录页降权 | `CATALOG_PATTERNS = ["图鉴", "列表", "索引", "导航", "目录", "合集", "汇总"]` → 扣 4 分 |
| `_score_links` | 零重叠惩罚 | 页面名与查询无任何共同字符 → 扣 3 分（高价值关键词可部分抵消） |

#### 萌娘百科激活逻辑 (_should_include_moegirl)

`deep_search` 工具通过三层判断决定是否激活萌娘百科源（避免不必要的 30s+ Playwright 开销）：

| 条件 | 触发 | 示例 |
|------|------|------|
| 关键词匹配 | 查询含 `角色`/`剧情`/`关系`/`情感`/`背景`/`故事`... | `"琪亚娜的角色背景"` → ✅ |
| 米游社字典匹配 | 查询解析为女武神/角色分类条目 | `"薪炎之律者"` → ✅ (ID 48, 女武神) |
| 纯名字查询 | ≤12字 + 无问句特征（什么/怎么/如何...） | `"薇塔"` → ✅ / `"薇塔怎么配装"` → ❌ |

#### RAG 策略

| 策略 | 实现 | 说明 |
|------|------|------|
| 查询扩展 | `_expand_query()` | 短查询通过索引扩展为完整名称（"德丽莎"→"德丽莎 德丽莎·阿波卡利斯"） |
| 分层过滤 | `_format_rag_results()` | 精确名>部分名>内容匹配 三档过滤 |
| 智能片段 | `_extract_relevant_snippet()` | 搜索查询词位置，提取周围上下文 |
| RRF 融合 | `Retriever._hybrid_search()` | 向量 + jieba关键词 RRF(k=60) 融合，名称匹配加分 |
| Cross-Encoder | `reranker.py` | `maidalun1020/bce-reranker-base_v1` (279M), ~538MB 显存, `D:/TokusCode/models/bce-reranker-base_v1/` |
| JSON 防御 | `parallel_search` tool | 自动解析 LLM 误传的 JSON 格式查询 |

### Live2D 看板娘系统

桌宠模式运行（鼠标穿透），系统托盘仅提供"退出"。所有配置通过前端设置页完成。

**架构**: TCP JSON + `\nEOF\n` 协议，端口 5003。Qt Signal/Slot 跨线程到 GUI 线程。

```
live2d_control/
├── qt_window.py          # QOpenGLWidget 顶层透明窗口 (无边框置顶)
├── live2d_server.py      # TCP JSON 服务端 (端口 5003)
├── live2d_client.py      # TCP 客户端
├── call_live2d.py        # Agent tool 入口 (method_map 路由)
├── model_manager.py      # 模型管理 (加载/渲染/表情/动作/口型)
├── config.py             # 路径/端口/默认值
└── window_state.json     # 窗口位置与大小持久化
```

**Agent 操作**: list_models, load_model, set_emotion, play_motion, set_lipsync, set_window_alpha, set_window_position, set_window_size, get_status, set_parameter, reset_parameters

**窗口特性**: 双层鼠标穿透 (Qt `WA_TransparentForMouseEvents` + Win32 `WS_EX_TRANSPARENT | WS_EX_LAYERED`)

### Qwen3-TTS 语音克隆系统

**模型**: `Qwen3-TTS-12Hz-1.7B-Base` (`D:/TokusCode/models/Qwen3-TTS/`)，支持 ICL 语音克隆（从 3 秒参考音频克隆声音）。

**子进程架构** (避免阻塞主 FastAPI 进程):
```
qwen3_tts_worker.py (子进程, 端口 5004)
    ├── 启动时加载模型 (支持 --quantize 8bit|4bit, 量化失败自动回退 bf16)
    ├── TCP JSON + \nEOF\n 协议
    └── 动作: generate, generate_and_play, health_check, warmup, shutdown

call_qwen3_tts.py (生命周期管理)
    ├── start_worker() → subprocess.Popen 启动
    ├── _ensure_worker() → 自动检测并重启 (最多 3 次/5 分钟)
    └── 双启动保护 (_worker_starting 标志)

qwen3_tts_generator.py → Qwen3TTSRemoteProxy (透明代理到子进程)
```

**参考音频库**: 48 位崩坏3角色，来源 `D:/hongkai_voice/`，`index.json` 映射 角色名 → `audio_path` + `ref_text`。

**Agent 工具 `tts_qwen3`**: 默认 ICL 声音克隆 (默认角色: 爱莉希雅)。四级角色名解析: 文件路径 → 精确匹配 → 模糊匹配 → CharacterManager 反查。由 `resolve_character_ref()` 和 `list_ref_characters()` 统一提供。

**当前配置**: bf16 (~3.4GB 显存)。GGUF 方案 (Talker Q5_K 960MB + Predictor Q8_0 145MB, 总计 ~1.1GB) 资产已就绪 (`D:/TokusCode/Qwen3-TTS-GGUF/model-base/`)，待 llama.cpp PR #20752 合入。

**异步播放**: `subprocess.Popen()` 不阻塞 Agent，PowerShell 后台播放。

### 技能系统 (skill_manager.py)
- 技能文件: `skills/<skill_name>/SKILL.md` (YAML frontmatter + Markdown body)
- Frontmatter 字段: name, description, phases
- 阶段提取: 从 Markdown 中匹配 `### <phase_name>` 标题
- 扫描逻辑: `load_all_skills()` 遍历 `skills/` 子目录，非技能目录缺失 SKILL.md 时静默跳过

### 角色人格系统 (character_manager.py)

- **CharacterManager**: 单例，从 `skills/characters/{name}/SKILL.md` 加载角色人格 (44 个角色)
- **动态注入**: 每次 `RouterLLM._call()` 读取 `companion_character` 设置 → 中文名→目录名映射 → 读取 SKILL.md → 替换 `[CHARACTER_PERSONALITY]`
- **切换角色零重建**: 改 `_runtime_settings` 内存字典 → 下一轮自动读取新人格
- **双路径切换**: 前端角色选择器 (推荐, 不中断对话) / Agent `update_user_setting` 工具
- **设置项**: `companion_character`, `companion_tts_voice`, `companion_personality`

### API 接口
- `POST /api/chat/stream` — SSE 流式对话 (主要接口)
- `POST /api/chat/cancel` — 取消运行中的请求
- `POST /api/chat/clear` — 清除对话上下文、删除检查点、重建Agent
- `GET /api/chat/runtime-status` — LLM运行时可用性与当前选择
- `GET /api/settings/` — 获取运行时设置
- `PUT /api/settings/` — 更新运行时设置 (持久化到 data/user_settings.json)
- `GET /api/settings/characters` — 列出所有可用角色人格
- `GET /api/live2d/models` — 列出已安装的 Live2D 模型
- `POST /api/live2d/models/import` / `DELETE /api/live2d/models/{name}` — 模型管理
- `PUT /api/live2d/apply` — 即时应用窗口设置
- `GET /api/chat/conversations` — 列出所有已记录的对话
- `GET /api/chat/conversations/export` — 导出全部对话为JSON包（含人格文件+ReAct思考链+回复）
- `GET /api/chat/conversations/export/{conv_id}` — 导出单条对话
- `DELETE /api/chat/conversations` — 清空内存中的对话记录

### 对话导出功能 (conversation_logger.py)

每次聊天自动记录完整对话上下文，支持 JSON 导出供 MP（数字海马体）消费。

**记录内容**:
- 用户原始输入 + 图片/音频数量
- 角色人格 (名称 + SKILL.md 完整内容)
- AgentRouter 意图分类 (intent + skill_name + raw_response 完整 LLM 输出)
- 业务 Agent 执行过程 (agent_type / output / ReAct步骤 / 工具调用 / 技能名称+**技能内容**)
- 陪伴 Agent 角色化回复 (emotion / clean_output / raw_output / **thinking_steps 思考步骤**)

**导出 JSON 结构**:
```
{
  "export_metadata": { "source": "bbb_assistant", "exported_at": "...", "total_conversations": N, "personalities_count": N },
  "personalities": { "爱莉希雅": "<SKILL.md完整内容>", ... },
  "conversations": [
    {
      "conversation_id": "32位hex UUID",
      "timestamp": "ISO8601",
      "user_message": "用户输入",
      "character": { "name": "...", "personality_file": "...", "personality_content": "..." },
      "router": {
        "intent": "game|action|chat",
        "skill_name": "letu|null",
        "raw_response": { "intent": "game", "skill_name": "letu", ... }   ← 完整 LLM 输出
      },
      "business_agent": {
        "agent_type": "main|action",
        "output": "执行结果",
        "steps": [{ "thought": "...", "action": "...", "action_input": "...", "observation": "..." }],
        "tools_called": ["run_hongkai_task", "yolo_detect_image"],
        "skills_matched": ["letu"],
        "skills_content": { "letu": "# letu 技能\n往世乐土自动化..." },   ← 技能文件内容
        "processing_time_ms": 1520.5
      },
      "companion": {
        "emotion": "happy|sad|angry|surprised|shy|serious|teasing|gentle|excited|neutral",
        "clean_output": "去除emotion标签的纯文本回复",
        "raw_output": "含[emotion]标签的原始输出",
        "thinking_steps": [{ "thought": "...", "action": "...", "action_input": "...", "observation": "..." }],  ← 陪伴Agent思考链
        "triggered_live2d": true|false,
        "triggered_tts": true|false
      }
    }
  ]
}
```

**导出 JSON 字段 → MP 编码映射**:
| 导出字段 | MP encode() 参数 | 说明 |
|---------|-----------------|------|
| `user_message` | `raw_text` (speaker_id="user") | 用户说的话 |
| `companion.clean_output` | `raw_text` (speaker_id=character.name) | AI 回复的话 |
| `companion.emotion` | `emotions` | 情绪标签 |
| `router.raw_response` + `business_agent.steps` | 元数据/evidence | "为什么这样回复"的推理链 |
| `character.personality_content` | 角色人格上下文 | 说话人的性格设定 |
| `personalities` (顶层) | 全局人格库 | 所有使用过的角色人格文件 |

**存储**: `data/conversations/{conversation_id}.json`

**线程安全**: `_data_lock` 保护所有 `_conversations` 字典访问（11处），双检锁单例模式。
**路径安全**: conv_id 正则校验 `^[a-zA-Z0-9_-]+$` + `.resolve()` 前缀检查双层防御。
**序列化安全**: `_safe_serialize()` 递归处理所有边缘类型（datetime/set/tuple/bytes 等），防止 JSON 崩溃。

### SSE 事件类型
`thought`, `action`, `observation`, `phase_start/phase_complete/phase_resume`, `todo_update`, `cancelled`, `error`, `warning`, `done`

### 前端

**ChatView**: SSE 流式消费, 图片上传 (Canvas 压缩 max 1024px JPEG 0.8), 图片灯箱, Markdown 渲染 (marked), TODO 卡片, ReAct 步骤折叠面板

**SettingsView**: Tab 布局 (LLM设置 / 图片描述 / Live2D / 角色选择)。持久化: 前端 localStorage + 后端 `data/user_settings.json`

## 自动化模块: hongkai

### 模块结构
```
backend/src/modules/hongkai/
├── templates/
│   ├── clicks_keyboard.py         # 模板匹配 + 键鼠模拟（Win32 SendInput）
│   └── *.png                      # 112 张游戏 UI 模板图片
├── ocr/
│   ├── ocr_functions.py           # OCR 封装（RapidOCR）
│   ├── ocr_click.py               # 100+ 游戏文本点击映射
│   ├── ocr_client.py / ocr_server_final.py  # TCP 服务 (端口 5002)
│   └── models/                    # PP-OCRv4 ONNX 模型
├── call_YOLO.py / yolo_client.py / yolo_server_final.py  # YOLO TCP (端口 5001)
├── bh3_yolo_recognizer.py         # YOLO 识别入口
├── on_window.py                   # Win32 窗口管理
├── log_viewer.py                  # 自动化日志查看器 (半透明置顶窗口, 鼠标穿透)
├── save_output.py                 # 日志拦截（print → 文件）
├── config.py / config.json        # 运行时配置
└── scripts/                       # 流程脚本
```

**YOLO 模型**: `backend/data/models/detect/yolo11n_elysian_realm_det.onnx` (24类游戏元素)

### 关键设计

**run_hongkai_task**:
- `subprocess.Popen()` 启动脚本子进程，CWD 为 `hongkai_dir`（确保 `templates/` 路径正确）
- 环境注入 `PYTHONPATH` 指向 `backend/`，解决 `from src.modules.*` 导入
- `HONGKAI_LOG_FILE` 环境变量 + `--log-file` 命令行参数双重保障日志路径
- `find_direction` / `navigate_to` 进程内调用（共享 YOLOModelManager），其他脚本走 subprocess
- 超时 86400s (24小时)，脚本 `atexit` 写入 `TASK_COMPLETE` 结束

**log_viewer.py**: 半透明置顶窗口 (左下角 620x420)，200ms 轮询增量读取，读到 TASK_COMPLETE 后最少显示 5s，120s 无新内容自动关闭，超 2000 行裁剪

**screen_capture.py**: 三级防遮挡回退 — PrintWindow (DWM) → GetDC+BitBlt → mss.grab。ScreenCapture 单例复用 GDI 上下文避免句柄泄漏。`SetProcessDPIAware()` 确保高 DPI 坐标正确。

**OCR/YOLO 按需自启动**: 不在任务启动时统一启动，脚本实际调用时才后台启动服务 (OCR 最多等 90s, YOLO 最多等 20s)

**编码修复**: 所有子进程 stdout/stderr 强制 UTF-8 (`_stream.reconfigure(encoding='utf-8', errors='replace')`)，修复 Windows cp1252 编码导致的中文崩溃

### 进程内脚本: find_direction / navigate_to

两个导航工具进程内直接调用，共享 YOLOModelManager 单例，从 20-24 次 LLM 调用缩减为每次 1 次工具调用。

- **find_direction**: 三阶段 (找舰桥按钮 → ESC+场景识别 → 循环ESC最多5次)，返回 `{success, scene, message, esc_used}`
- **navigate_to**: 五阶段 (确认位置 → 到舰桥 → 到目标 → 验证 → 重试最多3次)，返回 `{success, scene, message, retries}`

### 战斗停止判断 (letu_fight.py)
三线程并行 (YOLO怪物检测 + 停止图片模板匹配 + 按键复现)。`battle_ended` 标志防止战斗结束后无限重启。停止图片置信度 0.82。

## 当前环境

```
Python:   C:\Program Files\Python311\ (3.11.9, 系统 PATH)
torch:    2.7.1+cu118 (CUDA=True)
GPU:      NVIDIA GeForce RTX 3060 Laptop GPU (6GB VRAM)
```
pip:      26.1.2
```

---

## 对话导出功能 — 诊断修复记录 (2026-06-26)

### 第 1 轮诊断 (3 Agent 并行)

发现 15 个问题（P0×3, P1×5, P2×7）。

| 编号 | 严重性 | 类别 | 问题 | 状态 |
|------|--------|------|------|------|
| C1 | P0 | 崩溃 | `_conversations` 字典无锁并发访问，迭代时 RuntimeError | ✅ 已修复 |
| C2 | P0 | 安全 | `export_conversation` 路径遍历可读任意 JSON 文件 | ✅ 已修复 |
| C3 | P0 | 崩溃 | JSON 序列化不可序列化类型导致 TypeError | ✅ 已修复 |
| F1 | P1 | 功能 | Router `raw_response` 被丢弃，违反"原因"需求 | ✅ 已修复 |
| F2 | P1 | 数据丢失 | `processing_time_ms` 在多处调用缺失 | ✅ 已修复 |
| F3 | P1 | 功能 | 技能内容未导出，仅导出技能名 | ✅ 已修复 |
| — | P1 | 崩溃 | 非流式异常路径跳过 `finalize_conversation` | ✅ 已修复 |
| — | P1 | 崩溃 | `asyncio.CancelledError` (BaseException) 未被捕获 | ✅ 已修复 |
| — | P1 | 功能 | 流式 cancelled/error 事件跳过对话记录 | ✅ 已修复 |
| F4 | P2 | 内存泄漏 | `finalize_conversation` 不移除内存记录 | ✅ 已修复 |
| F5 | P2 | 逻辑 | `triggered_tts` 存配置值而非实际调用结果 | ✅ 已修复 |
| F6 | P2 | 性能 | `list_conversations` O(n²) 去重 | ✅ 已修复 |
| PF1 | P2 | 性能 | `list_conversations` 每次加载全部磁盘文件 | 保持现状 |
| PF2 | P2 | 性能 | `export_all` 一次性加载全量 | 后续分页 |
| PF3 | P3 | 性能 | `get_disk_count` 无谓构造列表 | ✅ 已修复 |
| S2 | P0 | 安全 | 导出端点未鉴权 | 后续架构层面 |
| S3 | P2 | 安全 | 人格文件明文可能泄露敏感信息 | 已文档说明 |
| Q1 | P3 | 代码质量 | 单例模式抗异常能力差 | ✅ 已修复 |
| Q2 | P3 | 代码质量 | UUID 截断 12 字符碰撞风险 | ✅ 已修复 |

### 第 2 轮诊断 (2 Agent 并行)

发现 3 个残留问题，全部已修复。

| 编号 | 严重性 | 问题 | 状态 |
|------|--------|------|------|
| — | P1 | 流式端点 `record_router` 缺少 `raw_response=intent_result` | ✅ 已修复 |
| — | P1 | 流式端点 `except Exception` 未捕获 `asyncio.CancelledError` | ✅ 已修复 |
| — | P2 | 3处 `record_business_agent` 缺少 `processing_time_ms` | ✅ 已修复 |

### 最终验证

**NO RUNTIME ISSUES FOUND**

- ✅ 线程安全：`_data_lock` 保护全部 11 处字典访问，4 worker × 50 并发零错误
- ✅ 路径安全：正则 `^[a-zA-Z0-9_-]+$` + `.resolve()` 前缀检查双层防御
- ✅ 序列化安全：`_safe_serialize()` 覆盖 10+ 边缘类型
- ✅ 内存不泄漏：`pop()` 移除已归档记录
- ✅ 异常全覆盖：非流式 3 路径 + 流式 5 路径全部调用 `finalize_conversation`
- ✅ 导出字段完整：raw_response + skills_content + thinking_steps + processing_time_ms
- ✅ UUID 32 字符 hex，零碰撞风险

### 第 3 轮诊断 (运行时验证, 2026-06-26)

后端 :8000 + 前端 :5173 同时运行，实时对话记录 → 导出全链路验证。

| 检查项 | 状态 |
|--------|------|
| `GET /api/chat/conversations` | 🟢 对话摘要列表正常 |
| `GET /api/chat/conversations/export` | 🟢 完整 JSON 包（人格+对话+推理链） |
| `GET /api/chat/conversations/export/{id}` | 🟢 单条导出，结构完整 |
| `POST /api/chat/` → 自动记录 | 🟢 对话自动写入 `data/conversations/` |
| `router.raw_response` 含 LLM 输出 | 🟢 `{"intent":"chat","skill_name":null}` |
| `character.personality_content` 完整 | 🟢 SKILL.md 原文（数千字），非路径引用 |
| `companion.thinking_steps` | 🟢 思考步骤已捕获 |
| `companion.emotion` + `clean_output` | 🟢 情绪标签 + 纯文本回复 |
| `business_agent` 仅在 game/action 意图出现 | 🟢 chat 意图正确跳过 |
| 导出 JSON 可直接喂给 MP `encode()` | 🟢 字段映射表见上方文档 |
| 前端 Vite :5173 → API 代理 :8000 | 🟢 后端启动后代理恢复正常 |

**NO RUNTIME ISSUES FOUND** — 3 轮诊断循环收敛，对话导出功能完整可用。
