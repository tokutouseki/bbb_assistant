# 崩坏3专属AI陪伴助手 (bbb-assistant)

崩坏3游戏AI陪伴助手，提供游戏辅助自动化、知识问答、角色扮演对话等功能。

## 技术栈

- **后端**: Python FastAPI + LangChain ReAct Agent
- **前端**: Vue 3 + Vite
- **LLM**: DeepSeek API / LM Studio (Qwen) / Ollama / 本地 GGUF
- **RAG**: ChromaDB + SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- **视觉**: YOLO 目标检测 (游戏UI识别) + OCR
- **语音**: TTS (qwen3语音合成 / voxcpm声音克隆) + ASR (FunASR)
- **自动化**: PowerShell 脚本 (游戏窗口操作、按键模拟)

## 目录结构

```
bbb_assistant/
├── backend/
│   └── src/
│       ├── api/chat.py              # 聊天API (/api/chat/stream, /cancel, /clear)
│       ├── config/cancel_signal.py  # 请求取消信号机制
│       ├── modules/
│       │   ├── agent/react_agent.py # ReAct Agent (核心)
│       │   ├── skill/skill_manager.py # 技能管理 (SKILL.md解析、阶段提取)
│       │   ├── tool_integration.py  # 工具注册 (YOLO, OCR, web_search, TTS等)
│       │   ├── web_search/          # 联网搜索 (百度主引擎 + Playwright兜底)
│       │   ├── rag/                 # RAG检索引擎
│       │   ├── llm/                 # LLM路由 (多模型切换)
│       │   └── yolo/                # YOLO管理 (加载/卸载/检测/分类)
│       └── services/                # 聊天服务、游戏监控
├── frontend/src/
│   ├── views/ChatView.vue           # 聊天主界面 (SSE流式、TODO卡片、步骤展示)
│   └── stores/chat.js               # 聊天状态管理
├── skills/                          # 技能定义 (每个技能一个目录)
│   ├── material_expedition_one_click/ # 材料远征一键减负
│   ├── club_consignment_recovery/    # 家园委托找回
│   ├── find_direction/              # 方向查找
│   ├── game_navigation/             # 游戏导航
│   └── elysia-perspective/          # 爱莉希雅视角角色扮演
├── outputs/
│   ├── asr_transcriptions/          # ASR转录输出
│   ├── tts_outputs/                 # TTS语音输出
│   └── task_checkpoint.json         # 任务检查点 (分阶段执行状态)
├── data/
│   ├── chroma_db/                   # ChromaDB向量库
│   └── rag_index/                   # RAG索引
└── user_preferences.md              # 用户偏好 (Agent启动时读取并嵌入系统prompt)
```

## 核心架构

### ReAct Agent (react_agent.py)
- 严格遵循 ReAct 范式: Thought → Action → Action Input → Observation 循环
- 支持流式输出 (run_streaming) 和非流式输出 (run)
- 透明分阶段执行: 当技能定义了 `phases` 时自动切换到分阶段模式
- 系统 prompt 中嵌入用户偏好 (user_preferences.md)
- 对话记忆使用 ConversationBufferMemory (max 2000 tokens)

### 技能系统 (skill_manager.py)
- 技能文件: skills/<skill_name>/SKILL.md (YAML frontmatter + Markdown body)
- Frontmatter 字段: name, description, phases (逗号分隔的阶段名)
- 阶段提取: 从 Markdown 中匹配 `### <phase_name>` 标题
- 触发匹配: 根据用户消息匹配技能 description 中的关键词

### API 接口
- `POST /api/chat` — 非流式对话
- `POST /api/chat/stream` — SSE 流式对话 (主要接口)
- `POST /api/chat/cancel` — 取消运行中的请求
- `POST /api/chat/clear` — 清除对话上下文、删除检查点、重建Agent
- `GET /api/chat/history/{user_id}` — 聊天历史

### SSE 事件类型
前端通过 EventSource 接收以下事件:
- `thought` — Agent 思考步骤
- `action` — 工具调用
- `observation` — 工具结果
- `phase_start / phase_complete / phase_resume` — 阶段生命周期
- `todo_update` — TODO列表更新
- `cancelled / error / warning` — 状态事件
- `done` — 完成

## 当前工作状态

### 已提交
- **718c735** (2026-05-14): 分阶段执行机制、上下文清除、用户偏好注入、项目文档 (CLAUDE.md)
- **4647651** (2026-05-13): SSE流式对话、TTS语音合成、任务规划与取消机制、爱莉希雅视角技能

### 未提交 (2026-05-15)

**联网搜索重构 (web_searcher.py, +373/-361)**:
- 搜索引擎从 必应中国 切换为 **百度直搜** (requests + Session/Cookie)
- 两级回退机制: 百度HTTP请求 → Playwright 真实浏览器兜底
- 百度反爬对抗: Session 持久化 (预访问首页获取 BAIDUID Cookie)、安全验证自动重试
- Playwright 反检测: 伪造 navigator.webdriver/plugins/languages、zh-CN locale
- 短角色名消歧: ≤2字角色名 (芽衣/希儿/符华等) 自动追加 "崩坏3" 前缀
- 无关结果过滤: 过滤星穹铁道/原神/绝区零、官网首页URL
- **fetch_page 工具**: 新增 `fetch_page_content(url, use_browser)` — `use_browser=False` 用 requests 直抓，`use_browser=True` 用 Playwright 渲染 SPA 站点 (米游社等)
- 正文截断改为 100000 字符兜底 (仅安全保护，实际不可达)

**Agent 工具改进 (react_agent.py, +59/-31)**:
- `web_search` 工具: 引擎切换为 BAIDU、`enable_content_fetch=False`、URL 截断到 200 字符、使用 `search_with_fallback` 两级回退
- 新增 `fetch_page(url, use_browser)` 工具: Agent 可从搜索结果中选择性抓取全文
- `rag_search` 工具增强: RRF 分数阈值过滤 (<0.015 视为噪声)、[直接匹配] 标签、低相关性警告
- max_iterations 从 1000 降为 8 (防止无限循环)
- 解析错误恢复: 工具调用成功但格式错误时直接从输出提取答案，不再重试
- 取消信号: QueueStreamingHandler 增加 `_cancelled` 标记，防止取消后继续推送事件

**RAG 检索增强 (retriever.py + index_manager.py)**:
- 混合检索算法从加权平均改为 **RRF (Reciprocal Rank Fusion, k=60)**: 不依赖原始分数只看排名，解决向量和关键词分数不可比问题
- 名称匹配加权: 文档名精确命中查询词 +0.5，部分匹配 +0.15
- 关键词检索从 binary 匹配改为 **TF 词频加权**: `1.0 + min(tf * 0.5, 5.0)` + 名称命中 +3.0
- 噪声过滤: RRF 最低阈值 0.01

**前端 (ChatView.vue)**:
- 引入 `marked` 库，助手消息支持 Markdown 渲染 (v-html)
- 完整的 Markdown CSS 样式: 标题/h/p/li/strong/hr/code/pre/a/blockquote

## 可用工具列表

Agent 可调用的工具: rag_search, list_skills, view_skill, yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image, ocr_recognize, get_runtime_status, focus_bh3_window, click_coordinates, tts_qwen3, tts_voxcpm, play_audio, todo_write, web_search, fetch_page
