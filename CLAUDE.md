# 崩坏3专属AI陪伴助手 (bbb-assistant)

崩坏3游戏AI陪伴助手，提供游戏辅助自动化、知识问答、角色扮演对话等功能。

## 技术栈

- **后端**: Python FastAPI + LangChain ReAct Agent
- **前端**: Vue 3 + Vite
- **LLM**: DeepSeek API / LM Studio (Qwen) / Ollama / 本地 GGUF
- **RAG**: ChromaDB + SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- **视觉**: YOLO 目标检测 (游戏UI识别) + OCR + PixAI Tagger (动漫标签) + Bailian Qwen-VL (云端多模态)
- **语音**: TTS (qwen3语音合成 / voxcpm声音克隆) + ASR (FunASR)
- **自动化**: PowerShell 脚本 (游戏窗口操作、按键模拟)

## 目录结构

```
bbb_assistant/
├── backend/
│   └── src/
│       ├── api/chat.py              # 聊天API (/api/chat/stream, /cancel, /clear)
│       ├── api/settings.py          # 设置API (LLM/图片描述配置持久化到 user_settings.json)
│       ├── config/settings.py       # 应用配置 (Pydantic Settings)
│       ├── config/runtime_settings.py # 运行时设置 (JSON持久化, 重启加载)
│       ├── config/cancel_signal.py  # 请求取消信号机制
│       ├── modules/
│       │   ├── agent/react_agent.py # ReAct Agent (核心, +describe_image工具)
│       │   ├── skill/skill_manager.py # 技能管理 (SKILL.md解析、阶段提取)
│       │   ├── vision/
│       │   │   ├── image_describer.py   # 多后端图片描述 (Bailian/PixAI/LM Studio)
│       │   │   ├── yolo_model_manager.py # YOLO管理 (加载/卸载/检测/分类)
│       │   │   ├── screen_capture.py    # 屏幕截图
│       │   │   ├── ocr_processor.py     # OCR识别
│       │   │   └── window_focus.py      # 窗口聚焦
│       │   ├── web_search/          # 联网搜索 (百度主引擎 + Playwright兜底)
│       │   ├── rag/                 # RAG检索引擎
│       │   ├── llm/                 # LLM路由 (多模型切换, vision能力过滤)
│       │   └── audio/               # 音频播放
│       └── services/                # 聊天服务、游戏监控
├── frontend/src/
│   ├── views/ChatView.vue           # 聊天主界面 (SSE流式、图片上传/预览/灯箱、Markdown渲染)
│   ├── views/SettingsView.vue       # 设置界面 (LLM提供商、图片描述后端、Bailian密钥)
│   └── stores/
│       ├── chat.js                  # 聊天状态管理
│       └── settings.js              # 设置状态 (localStorage持久化)
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
│   ├── rag_index/                   # RAG索引
│   └── user_settings.json           # 运行时设置持久化文件
└── user_preferences.md              # 用户偏好 (Agent启动时读取并嵌入系统prompt)
```

## 核心架构

### ReAct Agent (react_agent.py)
- 严格遵循 ReAct 范式: Thought → Action → Action Input → Observation 循环
- 支持流式输出 (run_streaming) 和非流式输出 (run)
- 透明分阶段执行: 当技能定义了 `phases` 时自动切换到分阶段模式
- 系统 prompt 中嵌入用户偏好 (user_preferences.md) 和图片分析流程示例
- 对话记忆使用 ConversationBufferMemory (max 2000 tokens)
- 图片处理: 用户上传图片 → Agent 存储到 `_current_images` → prompt 中提示调用 `describe_image` 工具 → 获得文本描述后分析回答
- RouterLLM 每次 `_call()` 重新读取运行时设置，确保用户配置即时生效

### 图片描述系统 (image_describer.py)
- 多后端自动降级: `bailian` → `pixai_tagger` → `lmstudio` (顺序可配置)
- **Bailian (阿里百炼 Qwen-VL)**: 云端多模态模型, OpenAI兼容接口, 约¥0.0015/千tokens
- **PixAI Tagger**: 本地 ONNX 模型, 13,461 个 Danbooru 标签, 角色识别 F1 0.86
  - 模型位置: `D:/TokusCode/models/PixAI-Tagger/` (model.onnx 1.2GB + selected_tags.csv + preprocess.json)
  - ONNX CPU 模式, 避免 CUDA 版本冲突
- **LM Studio (Qwen-VL)**: 本地视觉模型, 作为最后兜底
- `describe()` 每次调用重新读取运行时设置, 用户前端切换后端优先级即时生效
- `get_image_describer()` 单例工厂, 支持传入 `backend_order` 覆盖

### LLM 路由与 Vision 支持 (llm_router.py)
- `ModelInfo.model_capabilities`: 模型级能力声明 (如 `"vision"`, `"streaming"`)
- `TaskContext.has_images`: 图片检测, 当有图片时只选 `"vision" in model_capabilities` 的模型
- LM Studio 注册时标记 `model_capabilities=["vision", "streaming"]`
- 无可用 vision 模型时返回明确错误, 不尝试文本模型 fallback
- `ContextOverflowError`: LM Studio 400 错误中检测上下文溢出关键词, 直接抛出提示

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
- `GET /api/chat/runtime-status` — LLM运行时可用性与当前选择
- `GET /api/settings/` — 获取运行时设置
- `PUT /api/settings/` — 更新运行时设置 (持久化到 data/user_settings.json)
- `POST /api/settings/reset` — 重置为默认设置

### SSE 事件类型
前端通过 fetch + ReadableStream 接收以下事件:
- `thought` — Agent 思考步骤
- `action` — 工具调用
- `observation` — 工具结果
- `phase_start / phase_complete / phase_resume` — 阶段生命周期
- `todo_update` — TODO列表更新
- `cancelled / error / warning` — 状态事件
- `done` — 完成

### 前端 (ChatView.vue)
- SSE 流式消费 (fetch + ReadableStream)
- 图片上传: 多文件选择 → Canvas 压缩 (max 1024px, JPEG 0.8) → base64 发送
- 图片预览: 输入框上方缩略图行, 可删除, 发送后自动清空
- 图片灯箱: 点击消息中的图片弹出全屏遮罩查看 (90vw/90vh)
- Markdown 渲染: 使用 `marked` 库, 完整的标题/代码块/引用/链接样式
- TODO 卡片: 任务计划可视化展示
- 步骤展示: ReAct Thought/Action/Observation 折叠面板
- 上下文清除按钮

### 前端设置 (SettingsView.vue)
- LLM 提供商选择: DeepSeek API / LM Studio
- 图片描述后端选择: 4 种预设方案
  - 百炼 Qwen-VL (推荐)
  - 百炼 → PixAI标签 → LM Studio
  - PixAI标签 (本地优先)
  - 仅本地模型 (PixAI + LM Studio)
- 百炼 API 密钥配置 (密码输入框, 带显隐切换)
- 设置持久化: 前端 localStorage + 后端 `data/user_settings.json`

## 可用工具列表

Agent 可调用的工具 (共19个):
rag_search, list_skills, view_skill,
yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image,
ocr_recognize, describe_image,
get_runtime_status, focus_bh3_window, click_coordinates,
tts_qwen3, tts_voxcpm, play_audio,
todo_write, web_search, fetch_page
