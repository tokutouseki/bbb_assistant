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
│       │   ├── web_search/          # 联网搜索 (必应中国)
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

### 已提交 (commit 4647651, 2026-05-13 13:23)
SSE流式对话、TTS语音合成、任务规划与取消机制、web_search必应中国、爱莉希雅视角技能、RAG重建脚本

### 未提交 (2026-05-13 22:14~22:59)
**分阶段执行机制**:
- react_agent.py 新增 342 行: run_phased(), run_phased_streaming(), clear_context(), _load_user_preferences(), _build_phase_prompt(), _get_checkpoint_phase(), _read_checkpoint_summary()
- 每个阶段在干净的上下文中独立运行，通过 outputs/task_checkpoint.json 交接状态
- 支持断点续传 (从上次中断的阶段恢复)

**上下文清除功能**:
- chat.py 新增 POST /api/chat/clear 接口
- ChatView.vue 头部新增"刷新上下文"按钮
- clear_context() 方法: 重置记忆 → 删除检查点 → 重新加载偏好 → 重建Agent

**用户偏好注入**:
- user_preferences.md 内容在 Agent 初始化时通过 _load_user_preferences() 嵌入系统 prompt
- 技能 SKILL.md frontmatter 新增 `phases` 字段支持

**技能更新**:
- 4个技能 (material_expedition_one_click, club_consignment_recovery, find_direction, game_navigation) 重写为分阶段结构

**YOLO卸载工具**:
- 新增 yolo_unload_model 工具释放 GPU 内存

**前端**:
- ChatView.vue 新增清除上下文按钮和 clearContext() 方法

## 可用工具列表

Agent 可调用的工具: rag_search, list_skills, view_skill, yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image, ocr_recognize, get_runtime_status, focus_bh3_window, click_coordinates, tts_qwen3, tts_voxcpm, play_audio, todo_write, web_search
