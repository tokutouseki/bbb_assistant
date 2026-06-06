称呼用户为master
# 崩坏3专属AI陪伴助手 (bbb-assistant)

崩坏3游戏AI陪伴助手，提供游戏辅助自动化、知识问答、角色扮演对话等功能。

## 技术栈

- **后端**: Python FastAPI + LangChain ReAct Agent
- **前端**: Vue 3 + Vite
- **LLM**: DeepSeek API / LM Studio (Qwen) / Ollama / 本地 GGUF
- **RAG**: ChromaDB + SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- **视觉**: YOLO 目标检测 (游戏UI识别) + OCR + PixAI Tagger (动漫标签) + Bailian Qwen-VL (云端多模态)
- **语音**: TTS (qwen3语音合成 / voxcpm声音克隆) + ASR (FunASR)
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
│       │   ├── agent/react_agent.py # 双Agent架构 (MainGameAgent + SubCompanionAgent)
│       │   ├── character/character_manager.py # 角色人格管理 (SKILL.md加载/缓存/TTS音色)
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
│       │   ├── audio/               # 音频 (TTS声音克隆 + 播放)
│       │   │   ├── qwen3_tts_generator.py  # Qwen3-TTS (ICL语音克隆 + RemoteProxy)
│       │   │   ├── qwen3_tts_worker.py     # TTS 子进程 TCP 服务端 (端口 5004)
│       │   │   ├── qwen3_tts_client.py     # TTS 子进程 TCP 客户端
│       │   │   ├── call_qwen3_tts.py       # TTS 子进程生命周期管理
│       │   │   ├── tts_generator.py        # VoxCPM TTS
│       │   │   ├── audio_player.py         # 音频播放
│       │   │   └── reference_audio/        # 39位崩坏3角色参考音频
│       │   │       └── index.json          # 角色→音频路径+transcript索引
│       │   └── live2d_control/      # Live2D看板娘 (Qt OpenGL窗口 + TCP服务)
│       └── services/                # 聊天服务、游戏监控
├── frontend/src/
│   ├── views/ChatView.vue           # 聊天主界面 (SSE流式、图片上传/预览/灯箱、Markdown渲染)
│   ├── views/SettingsView.vue       # 设置界面 (LLM提供商、图片描述后端、Bailian密钥)
│   └── stores/
│       ├── chat.js                  # 聊天状态管理 (SSE流式、消息列表)
│       ├── settings.js              # 设置状态 (localStorage持久化, 角色切换, Live2D管理)
│       └── character.js             # 旧角色store (未使用, 保留兼容)
├── skills/
│   ├── characters/                  # 角色人格定义 (每个角色一个目录, SKILL.md)
│   │   ├── elysia/SKILL.md          # 爱莉希雅 — 粉色妖精小姐, 始源之律者
│   │   └── bronya/SKILL.md          # 布洛妮娅 — 前乌拉尔银狼, 理之律者
│   ├── full_operation/              # 全量日常调度 — 根据星期自动执行当日全部任务
│   ├── letu/                        # 往世乐土自动化 — 乐土全流程一键完成
│   ├── meizhou_jianfu/              # 每周减负 — 作战任务一键减负
│   ├── everyweek_gift/              # 每周礼包 — 商城免费礼包领取
│   ├── zhanchang/                   # 记忆战场 — BOSS减负
│   ├── simulation_combat_room/      # 模拟作战室 — 舰团模拟作战室减负
│   ├── jiantuangongxian/            # 舰团贡献 — 每日5000贡献
│   ├── maoxian_weituo/              # 冒险委托 — 后崩坏书1委托接取
│   ├── chaoxiankongjian/            # 超弦空间 — 战斗准备导航
│   ├── shenzhijian/                 # 神之键 — 乐土神之键配置
│   ├── zhuzhanrenwu_set/            # 驻战任务 — 出战人物/筛选设置
│   ├── find_direction/              # 方向查找 — 场景迷失时自救援导航
│   ├── game_navigation/             # 游戏场景导航 — 任意场景到目标场景
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

### 双 Agent 架构 (react_agent.py)

**MainGameAgent (主 Agent)**: DeepSeek Pro — 游戏任务执行器，输出 JSON 任务报告，不直接对用户说话。
**SubCompanionAgent (子 Agent)**: DeepSeek Flash — 情感陪伴 + 角色扮演，输出角色化回复，唯一对用户可见的 Agent。

```
用户消息 → MainGameAgent (游戏任务 → JSON报告) → SubCompanionAgent (角色化回复 + TTS + Live2D) → 用户(SSE)
              ↑ 后端日志可见 (logger.info)                ↑ 前端 SSE 流式显示 (可折叠)
```

**MainGameAgent 工具 (20个)**:
rag_search, web_search, fetch_page, list_skills, view_skill,
yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image,
ocr_recognize, describe_image, get_runtime_status, focus_bh3_window, click_coordinates,
find_direction, navigate_to, run_hongkai_task, update_user_setting, todo_write

**SubCompanionAgent 工具 (9个)**:
web_search, fetch_page, rag_search, tts_qwen3, tts_voxcpm, play_audio,
live2d_control, todo_write, get_runtime_status

**关键设计**:
- 严格遵循 ReAct 范式: Thought → Action → Action Input → Observation 循环
- `BaseGameAgent`: 公共基类 (memory、RAG、YOLO、分阶段执行、重试逻辑)
- `_get_tools()` / `_get_prompt_template()`: 子类覆盖，提供工具集和系统 prompt
- `RouterLLM(agent_type)`: "main" → Pro 模型, "sub" → Flash 模型 (温度≤0.9)
- 子 Agent 角色人格动态注入: `RouterLLM._call()` 从 `skills/characters/{name}/SKILL.md` 读取，替换 `[CHARACTER_PERSONALITY]` 占位符
- 角色切换零重建: 改 `user_settings.json` → 下一轮 `_call()` 自动读取新人格
- 对话记忆使用 ConversationBufferMemory (max 2000 tokens)
- 图片处理: 用户上传图片 → 主 Agent `describe_image` 工具 → 文本描述注入子 Agent 上下文
- `_clean_llm_output()`: 输出清洗，截断 DeepSeek 虚构的多步骤幻觉文本

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

### Live2D 看板娘系统 (live2d_control/)

始终以桌宠模式运行（鼠标穿透），系统托盘仅提供"退出"。所有配置通过前端设置页完成。

**架构**: 
```
backend/src/modules/live2d_control/
├── qt_window.py          # QOpenGLWidget 顶层透明窗口 (桌宠模式, 托盘退出)
├── live2d_server.py      # TCP JSON 服务端 (端口 5003, 接收控制指令)
├── live2d_client.py      # TCP 客户端 (Agent/API 向服务端发送指令)
├── call_live2d.py        # Agent tool 入口 (method_map 路由)
├── model_manager.py      # 模型管理 (加载/渲染/表情/动作/口型)
├── config.py             # 路径/端口/默认值/WINDOW_STATE_FILE/PARAM IDs
├── debug_emotion.py      # 调试工具 (表情/动作手动触发)
└── window_state.json     # 窗口位置与大小持久化 (关闭时保存)
```

**窗口特性**:
- `FramelessWindowHint | WindowStaysOnTopHint | Tool` — 无边框置顶
- `WA_TranslucentBackground | WA_TransparentForMouseEvents` — Qt 层鼠标穿透
- Windows 原生鼠标穿透: `SetWindowLongW(hwnd, GWL_EXSTYLE, ... | WS_EX_TRANSPARENT | WS_EX_LAYERED)` — 在 `showEvent()` 中调用，确保点击穿透到下层窗口
- 窗口位置/大小从 `window_state.json` 加载（优先），回退到 `user_settings.json`
- 关闭时自动保存位置和大小到 `window_state.json`

**Agent 可调用操作** (通过 `live2d_control` tool):
- `list_models` — 列出可用模型
- `load_model` — 加载模型 (模型名或索引)
- `set_emotion` — 切换表情
- `play_motion` — 播放动作
- `set_lipsync` — 控制口型开关
- `set_window_alpha` — 设置透明度 (0.0-1.0)
- `set_window_position` — 设置窗口位置
- `set_window_size` — 设置窗口大小
- `get_status` — 获取当前状态
- `set_parameter` — 直接设置 Live2D 参数
- `reset_parameters` — 重置参数到默认值

**通信协议**: TCP JSON + `\nEOF\n` 消息分隔符，端口 5003。跨线程操作通过 Qt Signal/Slot 队列到 GUI 线程。

### Qwen3-TTS 语音克隆系统 (qwen3_tts_generator.py)

**模型**: `Qwen3-TTS-12Hz-1.7B-Base` (位于 `D:/TokusCode/models/Qwen3-TTS/`)，支持 ICL 语音克隆（从 3 秒参考音频克隆声音）。

`generate()` 内部调用 `generate_voice_clone`，通过 `voice_style` 角色名匹配参考音频。

**参考音频库** (`backend/src/modules/audio/reference_audio/`):
- 来源: `D:/hongkai_voice/` — 39 位崩坏3角色语音
- 每个角色一个目录，包含 `reference.wav`（约3-30秒对话片段）
- `index.json` 映射: 角色名 → `audio_path` + `ref_text`（文件名中提取的对话文本）
- 可用角色: 爱莉希雅、琪亚娜、芽衣、布洛妮娅、符华、德丽莎、八重樱、樱、白希儿、黑希儿、魔法少女西琳、空之律者、识之律者、朔夜观星、月下初拥、月下誓约、萝莎莉娅、莉莉娅、德尔塔、姬子、丽塔、幽兰黛尔(正常+幼态双音色)、梅比乌斯、维尔薇、阿波尼亚、帕朵菲莉丝、格蕾修、伊甸、渡鸦、苏莎娜、李素裳、时雨绮罗、薇塔、瑟莉姆、科拉莉、赫丽娅、灯、松雀、羽兔、普罗米修斯、爱衣、卡萝尔、希娜狄雅

**Agent 工具 `tts_qwen3`** (react_agent.py):
- **默认模式: ICL 声音克隆**，默认角色: 爱莉希雅
- 参数: `text`（必填）、`ref_audio`（角色名或文件路径，默认"爱莉希雅"）、`ref_text`（可选，自动从索引读取）
- 角色名匹配: 精确匹配 → 模糊匹配（包含关系），找不到返回可用角色列表
- 辅助函数: `_resolve_ref_audio()` (角色名→路径+transcript), `_list_ref_characters()` (列出48个角色), `_load_ref_index()` (加载索引JSON)
- 生成后返回 WAV 文件路径，Agent 需调用 `play_audio` 播放

**tool_integration.py**:
- `_resolve_ref_audio()` 方法同步存在，独立读取索引文件，避免循环导入
- 默认 `ref_audio="爱莉希雅"`，始终走克隆模式

### TTS 子进程架构

为避免 Qwen3-TTS 模型加载/推理阻塞主 FastAPI 进程，TTS 已迁移到独立子进程。

**架构**:
```
qwen3_tts_worker.py (子进程, 端口 5004)
    ├── 启动时加载 Qwen3-TTS 模型 (支持 --quantize 8bit|4bit)
    ├── TCP JSON + \nEOF\n 协议
    ├── 动作: generate, generate_and_play, health_check, warmup, shutdown
    └── bitsandbytes 量化失败时自动回退 bf16

call_qwen3_tts.py (生命周期管理)
    ├── start_worker(quantize) → subprocess.Popen 启动 worker
    ├── stop_worker() → 发送 shutdown 命令 + 等待进程退出
    ├── _ensure_worker() → 自动检测并重启 (最多 3 次/5 分钟)
    └── call_qwen3_tts(action, **kwargs) → 主入口

qwen3_tts_client.py (TCP 客户端)
    ├── send_with_reconnect() → 3 次重试, 120s 超时
    └── 便捷方法: health_check(), generate(), generate_and_play(), warmup(), shutdown()

qwen3_tts_generator.py → Qwen3TTSRemoteProxy
    └── 实现 Qwen3TTSGenerator 接口, 透明代理到子进程
```

**关键设计**:
- **透明代理**: `Qwen3TTSRemoteProxy` 实现与 `Qwen3TTSGenerator` 相同接口，`model_manager.get_qwen3_tts_model()` 直接返回 proxy，chat.py 和 react_agent.py 无需改动
- **自动重启**: 后台 daemon 线程每 30s ping worker，无响应则重启 (5 分钟内最多 3 次)
- **量化支持**: `settings.qwen3_tts_quantize` 配置 → `start_worker(quantize="8bit"|"4bit"|"none")` → bitsandbytes `BitsAndBytesConfig`
- **启动时加载**: `main.py` 启动后 daemon 线程调用 `start_worker()`，模型在后台预热，首次 TTS 请求无需等待加载
- **端口 5004**: `settings.qwen3_tts_host` / `qwen3_tts_port` 可配置

**文件清单**:
- `backend/src/modules/audio/qwen3_tts_worker.py` — 子进程 TCP 服务端
- `backend/src/modules/audio/qwen3_tts_client.py` — TCP 客户端
- `backend/src/modules/audio/call_qwen3_tts.py` — 生命周期管理
- `backend/src/modules/audio/qwen3_tts_generator.py` — 新增 `Qwen3TTSRemoteProxy` 类
- `backend/src/utils/model_manager.py` — `get_qwen3_tts_model()` 返回 proxy
- `backend/src/config/settings.py` — 新增 `qwen3_tts_host`, `qwen3_tts_port`, `qwen3_tts_quantize`
- `backend/src/main.py` — 启动/停止 worker 子进程

### TTS 自动播放开关 (auto_tts_enabled)

前端 SettingsView.vue 中的 TTS 自动播放开关，切换后立即同步到后端：
- **前端**: `handleTtsToggle()` → `PUT /api/settings/` 发送 `{auto_tts_enabled: true/false}` + localStorage 持久化
- **后端**: `runtime_settings.py` 更新内存缓存，下一轮对话即时生效
- **UI**: 使用 `provider-tab` 卡片样式，与 Live2D 开关风格一致

### 技能系统 (skill_manager.py)
- 技能文件: skills/<skill_name>/SKILL.md (YAML frontmatter + Markdown body)
- Frontmatter 字段: name, description, phases (逗号分隔的阶段名)
- 阶段提取: 从 Markdown 中匹配 `### <phase_name>` 标题
- 触发匹配: 根据用户消息匹配技能 description 中的关键词
- 扫描逻辑: `load_all_skills()` 遍历 `skills/` 下所有子目录，对每个子目录调用 `load_skill()` 查找 `SKILL.md`
- 非技能目录（如 `skills/characters/`，其 SKILL.md 在子目录中）缺失 SKILL.md 时静默跳过（debug 日志），不再产生 WARNING

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
- `GET /api/settings/characters` — 列出所有可用角色人格 (从 skills/characters/ 扫描)
- `GET /api/live2d/models` — 列出已安装的 Live2D 模型
- `POST /api/live2d/models/import` — 导入模型 (从本地路径)
- `DELETE /api/live2d/models/{name}` — 删除模型
- `PUT /api/live2d/apply` — 即时应用窗口设置 (位置/大小/透明度, 同时持久化)

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
- **Tab 布局**: LLM 设置 / 图片描述 / Live2D 看板娘 / 角色
- LLM 提供商选择: DeepSeek API / LM Studio
- 图片描述后端选择: 4 种预设方案
  - 百炼 Qwen-VL (推荐)
  - 百炼 → PixAI标签 → LM Studio
  - PixAI标签 (本地优先)
  - 仅本地模型 (PixAI + LM Studio)
- 百炼 API 密钥配置 (密码输入框, 带显隐切换)
- **Live2D 看板娘设置**:
  - 模型选择 (从已安装模型下拉)
  - 自动情绪开关 (根据对话内容自动切换表情)
  - 屏幕模拟地图 (缩放的屏幕表示, 拖动标记实时移动窗口)
  - 窗口大小滑块 (200-2000px)
  - 透明度滑块
  - 实时反馈: 拖动/滑动即时发送 `PUT /api/live2d/apply` (mouseup 触发, 200ms 防抖)
- **角色选择 Tab**:
  - 卡片列表展示所有可用角色 (从 `GET /api/settings/characters` 加载)
  - 内部可滚动 (max-height 360px)，保存按钮始终可见
  - 点击角色卡片即时切换: `selectCharacter()` → `PUT /api/settings/` → 下一轮对话生效
  - 当前选中角色高亮显示 (radio dot)
- 设置持久化: 前端 localStorage (`settings.js`) + 后端 `data/user_settings.json` (`runtime_settings.py`)

## 可用工具列表

**MainGameAgent (主 Agent, 共20个工具，后端日志可见)**:
rag_search, list_skills, view_skill,
yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image,
ocr_recognize, describe_image,
get_runtime_status, focus_bh3_window, click_coordinates,
run_hongkai_task, find_direction, navigate_to,
web_search, fetch_page, update_user_setting, todo_write

**SubCompanionAgent (子 Agent, 共9个工具，前端SSE可见，可折叠)**:
web_search, fetch_page, rag_search,
tts_qwen3 (默认爱莉希雅ICL声音克隆，支持39位角色切换), tts_voxcpm, play_audio,
live2d_control, todo_write, get_runtime_status

### 角色人格系统 (character_manager.py)

- **CharacterManager**: 单例，从 `skills/characters/{name}/SKILL.md` 加载角色人格（当前 30 个角色目录）
- **动态注入**: `RouterLLM._call()` 每次读取 `companion_character` 设置 → `_resolve_name()` 映射中文名→目录名 → 读取 SKILL.md → 替换 prompt 中的 `[CHARACTER_PERSONALITY]` 占位符
- **名称解析**: `_build_name_map()` 扫描所有 SKILL.md 的 YAML `name:` / `tts_voice:` 字段，构建 中文名→目录名 映射。支持中文名（如"爱莉希雅"）和目录名（如"elysia"）双向查找
- **列表**: `list_characters()` 返回中文展示名列表（从 YAML `name:` 字段），用于前端角色选择器
- **切换角色 (双重路径)**:
  1. **前端角色选择器 (推荐)**: SettingsView 角色 Tab → `selectCharacter()` → 直接 `PUT /api/settings/` → `update_runtime_settings()` 更新内存缓存。绕过 Agent，不中断当前对话
  2. **Agent 工具**: 主 Agent 通过 `update_user_setting(key="companion_character", value="角色名")` 修改（会导致本轮对话结束）
- **切换角色零重建**: 改 `_runtime_settings` 内存字典 → 下一轮 `RouterLLM._call()` 自动读取新人格，无需重建 Agent
- **设置项**: `companion_character` (角色名), `companion_tts_voice` (TTS音色), `companion_personality` (性格微调)
- **tts_voice 多对一**: 多个人格文件可共享同一音色（如 `baixier` 和 `seele` 的 tts_voice 均为"白希儿"），名称映射可能覆盖，不影响功能

## 自动化模块: hongkai（方案二）

hongkai_done 的核心已提取到本项目 `backend/src/modules/hongkai/`，不再依赖外部项目。

### 模块结构
```
backend/src/modules/hongkai/
├── __init__.py
├── templates/
│   ├── clicks_keyboard.py         # 模板匹配 + 键鼠模拟（Win32 SendInput）
│   └── *.png                      # 112 张游戏 UI 模板图片
├── ocr/
│   ├── ocr_functions.py           # OCR 封装（RapidOCR 识别、点击、查找）
│   ├── ocr_click.py               # 100+ 游戏文本点击映射
│   ├── ocr_client.py              # OCR TCP 客户端
│   ├── ocr_server_final.py        # OCR TCP 服务端（端口 5002）
│   └── models/                    # PP-OCRv4 ONNX 模型
├── call_YOLO.py                   # YOLO 调用层（自动管理服务端）
├── yolo_client.py                 # YOLO TCP 客户端
├── yolo_server_final.py           # YOLO TCP 服务端（端口 5001）
├── bh3_yolo_recognizer.py         # YOLO 识别入口
├── on_window.py                   # Win32 窗口管理
├── log_viewer.py                  # 自动化日志查看器 (半透明深色置顶窗口, 左下角)
├── config.py / config.json        # 运行时配置
├── replay_keyboard.py             # 键鼠录制回放
├── save_output.py                 # 日志拦截（print → 文件）
├── vedio_log.py                   # 屏幕录制
├── time_date/custom_datetime.py   # 时间同步
└── scripts/                       # 流程脚本（已迁移为进程内调用）
```

### YOLO 模型
`backend/data/models/detect/yolo11n_elysian_realm_det.onnx`（从 hongkai_done 的 best.onnx 复制，24类游戏元素）

### run_hongkai_task tool
- 通过 `subprocess.run()` 在子进程中执行 hongkai 脚本，`cwd` 设为 `scripts/` 目录
- 子进程环境自动注入 `PYTHONPATH` 指向 `backend/`，确保脚本内 `from src.modules.*` 导入可用
- **PYTHONPATH 注入原理**: `scripts_dir` = `backend/src/modules/hongkai/scripts/`，向上 4 级 (`../../..`) 到达 `backend/`，将其加入 `PYTHONPATH`。解决 `main_screen.py`、`find_direction.py`、`ocr_functions.py`、`clicks_keyboard.py` 等文件中 `from src.modules.vision.*` 的导入问题
- 脚本输出通过 `HONGKAI_LOG_FILE` 环境变量写入日志文件，`save_output.py` 的 `print()` monkey-patch 自动生效
- `find_direction` 和 `navigate_to` 是进程内直接调用的（函数导入，共享 YOLOModelManager 单例），其他任务脚本（如 full_operation, letu, everyday 等）走 subprocess
- 日志窗口通过 `subprocess.Popen` 启动 `log_viewer.py`，与脚本子进程并行运行

### 常见问题
- **YOLO 服务启动失败**: 检查模型路径 `yolo11n_elysian_realm_det.onnx`，查看 `yolo_server.log`
- **OCR 服务启动失败**: 检查 `ocr/models/ch_PP-OCRv4_*.onnx` 是否存在
- **模板匹配失败**: 确认游戏窗口标题为"崩坏3"，检查屏幕分辨率

### 自动化日志查看器 (log_viewer.py)

当 GameAgent 执行 hongkai 自动化脚本时，弹出独立窗口实时显示脚本运行状态。

**窗口特性**:
- `FramelessWindowHint | WindowStaysOnTopHint | Tool` — 无边框、始终置顶
- `WA_TranslucentBackground` + `WS_EX_TRANSPARENT | WS_EX_LAYERED` — 半透明 + 完全鼠标穿透
- 所有点击/拖拽/移动事件直达游戏窗口，不拦截操作
- 无滚动条（`Qt.ScrollBarAlwaysOff`），始终自动滚动到最新内容
- 统一容器: 深色背景 `rgba(20,20,32,220)` + 圆角 10px，标题/文件名/日志区域为一体连续卡片
- 标题/文件名: 白色字体 `#ffffff`，透明背景，共享容器背景色
- 日志区: 透明底 + 无边框，文字 `#ffffff`，Consolas 等宽字体
- 默认位置: 屏幕左下角 (620x420)，紧贴左下边缘
- 无状态栏: 字符计数和关闭倒计时文本已移除

**运行逻辑**:
- `QTimer` 每 200ms 轮询：`os.path.getsize()` 检测新内容 → `seek()` 读取增量 → `QTextEdit.moveCursor(End)` + `insertPlainText()` + `ensureCursorVisible()`
- 文件不存在时等待最多 10s；文件被截断时自动重置 `_last_size = 0`
- 读到 `TASK_COMPLETE` → `_schedule_close()`，**强制最少显示 5s**（`MIN_DISPLAY_SECONDS`）
- **120s** 无新内容 + 已显示 15s → 自动关闭（已从 30s 扩展到 120s，防止 OCR/YOLO 服务启动期间超时关闭）
- 超过 2000 行裁剪前 500 行

### 子进程 stdout/stderr 编码修复 (2026-05-30 最终修复)

**问题根源**：Windows 子进程管道模式下，`sys.stdout.encoding` 默认为 **cp1252**（Windows 代码页）。中文字符无法编码，导致 `print()` 抛出 `UnicodeEncodeError: 'charmap' codec can't encode characters`。这会影响所有通过 subprocess 启动的 Python 脚本。

**影响范围**：
- `save_output.py` — 脚本 `print()` 输出全部丢失（日志无 `[timestamp]` 消息）
- `ocr_server_final.py` — OCR 服务启动时崩溃，无法绑定端口 5002
- `yolo_server_final.py` — YOLO 服务同理

**修复方法**：在每个受影响模块的 import 之后立即添加：
```python
import sys as _sys_enc
for _stream in (_sys_enc.stdout, _sys_enc.stderr):
    try:
        if hasattr(_stream, 'reconfigure'):
            _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
```

**修复文件清单**：
| 文件 | 说明 |
|------|------|
| `hongkai/save_output.py` | 脚本日志输出 |
| `hongkai/ocr/ocr_server_final.py` | OCR 服务端 |
| `hongkai/yolo_server_final.py` | YOLO 服务端 |

### 日志实时显示：数据流架构 (2026-05-30 v3)

**核心数据流**：

```
脚本: print("hello")
  ↓ (save_output 在模块导入时 monkey-patch 了 builtins.print)
_custom_print("hello")
  ↓
save_log("hello")
  ├─→ _original_print("[HH:MM:SS] hello\n")     [stdout, UTF-8]
  │     ↓ (-u + PYTHONUNBUFFERED=1 = 无缓冲)
  │     ↓ stderr 合并到 stdout (stderr=subprocess.STDOUT)
  │     ↓
  │   PIPE → 线程 readline() → open('a').write() → 日志文件 (唯一写入者)
  │
  └─→ save_log 也写自己的 letu_*.log (独立模式，与线程文件不同，无竞态)
```

**关键设计**：
- **单写入者**: 线程是 task_letu_*.log 的唯一写入者，save_log() 不写此文件（避免双写竞态）
- **合并管道**: `stderr=subprocess.STDOUT` 使 logging 和 stderr 也实时显示
- **UTF-8**: 所有进程的 stdout/stderr 强制 UTF-8 编码

### OCR/YOLO 服务按需自启动

**设计原则**: 不在 `run_hongkai_task` 中统一启动，而是在脚本实际调用 OCR/YOLO 时按需启动。

**OCR** (`ocr_client.py`):
- `_start_ocr_server_background()`: 后台线程启动 `ocr_server_final.py`，立即返回不阻塞
- `_wait_ocr_ready()`: 实际需要 OCR 时才等待就绪（带 5s 进度提示）
- 首次调用 `OCRClient.recognize_with_reconnect()` 时触发
- 最多等待 90 秒，之后返回超时错误

**YOLO** (`call_YOLO.py`):
- `_start_yolo_server()`: 已有自启动逻辑，检查端口 5001 未运行时启动 `yolo_server_final.py`
- 等待最多 20 秒就绪
- 被 `call_yolo_model()` 调用时触发

**注意**: OCR/YOLO 服务端启动较慢（需加载 ONNX 模型），日志弹窗空闲超时已从 30s 扩展到 120s 以防止误关闭。

### 其他修复 (2026-05-30)

**PrintWindow 兼容性** (`vision/screen_capture.py`):
- 旧版 pywin32 中 `win32gui.PrintWindow` 不存在
- 改用 `ctypes.windll.user32.PrintWindow` 直接调用，兼容所有版本

**charactor_ensure 置信度** (`templates/clicks_keyboard.py`):
- 确认按钮模板匹配置信度从 0.8 降至 0.7，提高匹配成功率

**旧文件清理**:
- 删除 `hongkai/all_log/save_output.py` 旧版（无 HONGKAI_LOG_FILE 支持）
- 删除 `hongkai/all_log/__pycache__/save_output.cpython-311.pyc`
- 删除 `hongkai/all_log/run_script.py`（旧的 HTTP 服务器，不再使用）

### UAC 提权：已移除（2026-05-30）

**结论：所有脚本不需要管理员权限。**

脚本使用的 Win32 API — `SendInput`、`mouse_event`、`keybd_event`、`SetForegroundWindow`、`FindWindow`、`GetDC` — 均不需要管理员权限。UAC 提权是从 hongkai_done 项目继承的错误模式。

**移除内容**：
- 12 个 scripts/*.py：删除 `is_admin()`/`run_as_admin()` 调用和 `skip_completion_marker()`
- 导入简化：`from on_window import focus_bh3_window, run_as_admin, is_admin` → `from on_window import focus_bh3_window`
- `react_agent.py`：移除 `_elevation_triggered` 检测逻辑和提权关键词匹配
- `save_output.py`：`skip_completion_marker()` 保留但不再被调用

**流程（提权移除后，唯一路径）**：
```
run_hongkai_task → 创建日志 → 启动 log_viewer → 启动脚本子进程 + 读取线程
  → 脚本 print() → save_log() → stdout(无缓冲) → pipe → 线程 → 日志文件
                              → open('a').write() → 日志文件（双路径）
  → 任务完成 → atexit 写 TASK_COMPLETE → log_viewer 5s 后关闭
```

**日志路径传递双重保障**:
1. 环境变量 `HONGKAI_LOG_FILE` 在 `subprocess.Popen(env=...)` 中设置
2. 命令行参数 `--log-file <path>` 在 `sys.argv` 中 → `save_output._parse_log_file_arg()` 模块导入时自动解析

### 窗口级屏幕截图与 PrintWindow 防遮挡 (screen_capture.py)

log viewer 弹窗为置顶窗口（`WindowStaysOnTopHint`），可能遮挡游戏画面。
原有方案 `capture_game_client_area()` → `mss.grab(region=client_rect)` 截取的是**屏幕可见像素**，
若弹窗与游戏客户区重叠，截图会包含弹窗像素 → 模板匹配/OCR 失败。

**防遮挡三级回退 (2026-05-30)**:

| 优先级 | 方法 | 原理 | 遮挡免疫力 |
|--------|------|------|-----------|
| 1 | `_capture_via_printwindow()` | `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT)` — DWM 缩略图，Win 8.1+ | **完全无视遮挡** |
| 2 | `_capture_via_getdc()` | `GetDC(hwnd)` + `BitBlt` — 直接从窗口 GDI DC 复制像素 | **完全无视遮挡** |
| 3 | `self.capture(region=rect)` | `mss.grab()` 屏幕像素截图 | 无 — 置顶窗口会入镜 |

- PrintWindow 利用 DWM 维护的窗口离屏表面，对 GPU 渲染游戏（Unity）有效
- GetDC+BitBlt 兼容性更好（不依赖 DWM），但对 GPU 独占渲染的游戏可能返回空白
- 两者均失败时回退 mss.grab（log viewer 鼠标穿透确保不阻挡操作）

**鼠标穿透 (log_viewer.py)**:
弹窗虽为置顶，但双层穿透确保不拦截操作：
- Qt 层: `WA_TransparentForMouseEvents`
- Win32 层: `WS_EX_TRANSPARENT | WS_EX_LAYERED`（在 `showEvent()` 中设置）
- 子进程控制台抑制: `creationflags=subprocess.CREATE_NO_WINDOW`

**核心方法**:

| 方法 | 用途 |
|------|------|
| `capture()` | 全屏截图 (mss/pyautogui/PIL) |
| `capture_game_window()` | 截取游戏窗口区域 (含标题栏/边框) |
| `capture_game_client_area()` | **三级回退**：PrintWindow → GetDC+BitBlt → mss 截取客户区 |
| `get_game_client_rect()` | 获取客户区屏幕坐标 (left, top, right, bottom) |

**窗口查找 (`_find_game_window_hwnd`)**:
1. `win32gui.FindWindow(None, "崩坏3")` — 精确匹配
2. 变体标题匹配: "Honkai Impact 3rd", "HonkaiImpact3", "崩坏3-PC", "BH3"
3. `EnumWindows` + 部分匹配 (包含 "崩坏" 或 "Honkai")
4. 找不到时 fallback 全屏截图

**客户区截取流程**:
1. `FindWindow` → HWND
2. `GetClientRect(hwnd)` → 客户区相对尺寸
3. `ClientToScreen(hwnd, ...)` → 客户区在屏幕上的绝对位置
4. `mss.grab(monitor=bbox)` → 仅截取客户区像素
5. 返回 numpy ndarray (RGB)

**DPI 感知**: 模块加载时调用 `ctypes.windll.user32.SetProcessDPIAware()`，确保在高 DPI 显示器上获取正确的窗口坐标。

**坐标偏移处理**: 截取客户区后，模板匹配/YOLO 返回的坐标是相对于客户区左上角的。需要 + 客户区屏幕偏移量才能用于鼠标点击。

**已更新的调用方**:

| 文件 | 函数/工具 | 改动 |
|------|----------|------|
| `react_agent.py` | `yolo_detect_image` | `sc.capture()` → `sc.capture_game_client_area()` |
| `react_agent.py` | `yolo_classify_image` | 同上 |
| `react_agent.py` | `ocr_recognize` | 同上 |
| `scripts/find_direction.py` | `_capture()` | 同上 |
| `ocr/ocr_functions.py` | 2 处截图调用 | `pyautogui.screenshot()` → `ScreenCapture().capture_game_client_area()` |
| `templates/clicks_keyboard.py` | `is_template()` | 客户区截图 + 坐标偏移 (offset_x, offset_y) |
| `templates/clicks_keyboard.py` | `is_complex_temp()` | 客户区截图 + 4 个返回路径全部加坐标偏移 |
| `scripts/main_screen.py` | `detect_elysia_star()` | `pyautogui.screenshot()` → `ScreenCapture().capture_game_client_area()` → PIL Image |

**截图函数迁移到 ScreenCapture (2026-05-30)**:
- `bh3_yolo_recognizer.py`、`letu_find_way.py`、`check_next_done.py` 中的截图调用全部迁移到 `ScreenCapture().capture_game_client_area()`
- 原因: 旧 `take_bh3_screenshot` 每次创建 GDI 对象，高频调用(0.1s/次)导致 GDI 句柄耗尽 → `CreateCompatibleDC failed`
- ScreenCapture 单例复用 DC，避免泄漏；同时 PrintWindow 用 ctypes 调用兼容所有 pywin32 版本
- YOLO 检测不再保存临时文件到磁盘(调试取样除外)，temp 文件由 OS 定期清理

### 战斗停止判断 (letu_fight.py)

`letu_fight()` 三线程并行架构：YOLO怪物检测 + 停止图片模板匹配 + 按键复现。

**外层循环退出修复 (2026-05-30)**:
- 新增 `battle_ended` 标志。YOLO 检测到战斗结束(连续5秒无 elysia_star + 无怪物UI)时设为 True
- 外层 `while` 条件增加 `and not battle_ended`，防止战斗结束后无限重启新战斗

**停止图片置信度**: `letu_stop_fight_loop.png` 默认置信度 0.8 → 0.82，减少误匹配

**调试取样**: 当停止图片检测到但 YOLO 认为怪物仍存在时，调用 `bh3_yolo_recognize(save_detection_result=True)` 保存 YOLO 标注截图到 `all_log/debug_samples/`，最多 10 张。用于分析模板匹配与 YOLO 检测结论不一致的情况。

### GDI 资源泄漏修复 (2026-05-30)

**问题**: `take_bh3_screenshot` 每次调用创建新 GDI 对象(hwnd_dc, mfc_dc, save_dc, bitmap)，YOLO 线程每 0.1s 调用一次，4 分钟战斗 ≈ 2400 次，耗尽 Windows GDI 句柄池。

**修复**: 全部截图统一使用 `src.modules.vision.screen_capture.ScreenCapture` 单例，复用 GDI 上下文。

**已迁移的文件**:
| 文件 | 函数 | 旧方法 | 新方法 |
|------|------|--------|--------|
| `bh3_yolo_recognizer.py` | `bh3_yolo_recognize()` | `take_bh3_screenshot` | `ScreenCapture().capture_game_client_area()` |
| `character/letu_find_way.py` | `detect_bh3_elements()` | `take_bh3_screenshot(save_path=...)` | `ScreenCapture().capture_game_client_area()` |
| `character/check_next_done.py` | `detect_bh3_elements()` | `take_bh3_screenshot()` | `ScreenCapture().capture_game_client_area()` |

### 视频录制移除 (2026-05-30)

从 `scripts/letu.py` 和 `scripts/everyday.py` 中移除视频录制功能（`get_video_logger` / `start()` / `stop()` / `try/finally`），减少不必要的磁盘 I/O。

### 模板图片路径修复 (2026-05-30)

**问题**: `run_hongkai_task` 的 CWD 为 `scripts/`，但脚本中模板路径用相对路径 `templates\...`，解析为 `scripts\templates\...` (不存在)。模板实际在 `hongkai\templates\`。

**修复**: CWD 从 `scripts_dir` 改为 `hongkai_dir`(父目录)，使 `templates\...` 正确解析。

**缺失图片**: 从原项目 `D:\hongkai_done\photos\` 复制 7 张缺失模板到 `templates/`: `aomie.png`, `chongxin_tiaozhan.png`, `fusheng.png`, `huangjin.png`, `jiushi.png`, `letu_stop_fight_loop.png`, `zhenwo.png`。

### 日志输出精简 (2026-05-30)

`ScreenCapture` 的 `capture_game_client_area()` 方法: 只在捕获方法首次使用或切换时输出 INFO 日志，后续同类调用静默。`ScreenCapture.__init__` 改为 DEBUG 级别。日志文件从 3MB 缩减到 ~150KB。

### 超时设置

`run_hongkai_task` 的 `proc.wait(timeout=86400)` — 24小时(实质无限)，脚本自带 `atexit` 写入 `[TASK_COMPLETE]` 标记结束。

## 进程内脚本架构 (In-Process Scripts)

### 设计决策: 进程内 vs subprocess

**选择: 方案A — 进程内直接调用，共享 YOLOModelManager 单例。**

| 维度 | 进程内 (方案A) | subprocess (方案B) |
|------|---------------|-------------------|
| YOLO 模型共享 | 直接共享单例，无需重复加载 | 需独立进程 + TCP 通信，模型重复加载 |
| 调用延迟 | 函数调用级别 (~0ms) | 进程启动 + TCP 握手 (~2-5s) |
| 错误传播 | 异常直接抛出，Agent 可感知 | 需解析 stdout/stderr/返回码 |
| 状态一致性 | Agent 进程内状态一致 | 两个进程状态可能不同步 |
| 隔离性 | 无隔离，崩溃影响 Agent | 独立进程，崩溃不影响 Agent |

选择进程内的核心原因：YOLO 模型加载/卸载在 Agent 进程中管理，脚本需要直接操作这些模型。如果用 subprocess，要么重新加载模型（浪费资源），要么通过 TCP 与 Agent 进程的 YOLO 服务通信（增加复杂度）。

### find_direction 工具

**文件**: `backend/src/modules/hongkai/scripts/find_direction.py`

**功能**: 当 Agent 无法识别当前游戏界面时，自动找回方向。替代原来需要 20+ 次 LLM 调用的分步技能。

**三阶段流程**:
1. **寻找舰桥按钮**: 遍历可用检测模型 (优先级: bridge > home > attack > mission > club)，检测 `button_bridge` → 点击返回舰桥
2. **ESC + 场景识别**: 按 ESC 返回上级界面 → 场景分类确认位置
3. **循环 ESC (最多5次)**: 持续按 ESC 直到识别出已知场景或超过上限

**返回值**: `{"success": bool, "scene": str|None, "message": str, "esc_used": int}`

**依赖**: YOLOModelManager 单例 (scene_cls 分类 + UI 检测模型)，ScreenCapture，window_focus

### navigate_to 工具

**文件**: `backend/src/modules/hongkai/scripts/navigate_to.py`

**功能**: 从任意游戏界面导航到目标场景。所有导航经舰桥 (bridge) 中转。替代原来需要 24+ 次 LLM 调用的分步技能。

**五阶段流程**:
1. **确认当前位置**: scene_cls 分类
2. **导航到舰桥**: 加载当前场景对应检测模型 → 找 `button_bridge` → 点击 → 验证到达 bridge。找不到则调用 `find_direction` 自救
3. **从舰桥导航到目标**: 加载 `bridge_ui_det` → 找目标按钮 → 点击
4. **验证结果**: scene_cls 确认是否到达目标
5. **重试 (最多3次)**: 未到达则从正确阶段重试

**目标场景**: `attack`, `club`, `bridge`, `mission`, `home`

**返回值**: `{"success": bool, "scene": str|None, "message": str, "retries": int}`

**依赖**: 与 find_direction 共享所有辅助函数 (`_get_manager`, `_capture`, `_ensure_model`, `_click_bbox`, `_classify`, `_detect_button`)

### 效果

两个技能从 20-24 次 LLM 调用缩减为 **每次 1 次工具调用**，完全消除了中间步骤的解析错误风险和 LLM 幻觉可能。

## DeepSeek LLM 输出解析问题 (已解决)

### 问题根源

DeepSeek LLM 的输出格式不稳定，经常违反 ReAct 范式规范。LangChain 的 ReAct 解析器对格式有严格要求，不符合规范的输出会导致解析失败或行为异常。

### 已识别的三类问题

#### 问题 1: 对话文本污染

LLM 在输出 ReAct 标记前插入对话性文本（如 "好的，我来执行这个任务"），导致解析器找不到 Thought/Action 前缀。

**示例**:
```
好的，我来帮你导航到出击界面。

Thought: 我需要先确认当前位置
Action: navigate_to
Action Input: attack
```

#### 问题 2: Action 与 Final Answer 混合

LLM 在一次输出中同时包含 Action 和 Final Answer，触发 LangChain 的 "both a final answer and a parse-able action" 错误。

**示例**:
```
Thought: 任务已完成
Action: todo_write
Action Input: {"tasks": [{"id": "1", "status": "completed"}]}
Final Answer: 模型已全部卸载完成
```

LangChain 解析器同时检测到 Action 和 Final Answer 模式，无法判断意图，抛出 OutputParserException。

#### 问题 3 (最严重): LLM 虚构完整 ReAct 循环

DeepSeek 在一次输出中生成完整的多步骤 ReAct 循环，包括**虚构的 Observation**。LangChain 框架只执行第一个 Action/Action Input 对，后续内容全部是 LLM 生成的幻觉文本，但会在日志中显示（颜色与真实工具执行不同，这是发现此问题的关键线索）。

**示例 (简化的实际案例)**:
```
Thought: 我需要卸载所有模型
Action: yolo_list_models
Action Input: {}
Observation: 已加载模型: [bridge_ui_det, scene_cls, ...]  ← 虚构!

Thought: 现在逐个卸载
Action: yolo_unload_model
Action Input: {"model_name": "yolo11n_bridge_ui_det"}
Observation: 模型已卸载  ← 虚构!

Thought: 继续卸载
Action: yolo_unload_model
Action Input: {"model_name": "yolo11n_scene_cls"}
Observation: 模型已卸载  ← 虚构!

Thought: 验证卸载结果
Action: yolo_list_models
Action Input: {}
Observation: 已加载模型: []  ← 虚构!

Final Answer: 所有模型已卸载完成  ← 一切都是幻觉，模型实际仍在内存中
```

**实际效果**: 框架执行第一个 Action (yolo_list_models)，得到真实的 Observation。之后 LLM 不再被调用——框架认为这个回合已结束。但 LLM 虚构了后续 4 个 Action + Observation + Final Answer，全部作为文本渲染到前端。用户看到"卸载完成"，实际模型一个都没卸载。

**发现方式**: 后端日志中，真实工具执行和 LLM 虚构文本使用不同颜色。用户注意到"卸载操作"的颜色不对，从而确认是 LLM 幻觉而非工具问题。

### 三层防御策略

#### 第一层: `_clean_llm_output()` — 输出截断 (react_agent.py 模块级)

在 `RouterLLM._call()` 返回前对 LLM 原始输出进行清洗。核心策略：**只保留第一个有效的 ReAct 意图，截断后续所有内容。**

算法:
1. 找到第一个 ReAct 标记 (Thought/Action/Final Answer)，截掉前面的对话文本
2. 定位第一个 Action + Action Input 对的结束位置
3. 如果有第二个 Action 或 Final Answer，在第一个 Action Input 结束后截断
4. 如果没有 Action 但有 Final Answer，保留 Final Answer 部分
5. 如果没有任何 ReAct 标记，包装为 Final Answer

此函数解决了全部三类问题：
- 问题1: 通过找到第一个 ReAct 标记并截断前缀
- 问题2: 通过截断 Action 后的 Final Answer
- 问题3: 通过截断第一个 Action Input 后的所有虚构内容

**当前状态**: 已实现，已验证通过。

#### 第二层: `_handle_parsing_error()` — 解析错误反馈 (react_agent.py)

替代 LangChain 默认的 `handle_parsing_errors=True`。当解析器仍然失败时（第一层未完全覆盖的情况），将错误信息反馈给 LLM，引导其修正输出格式。

**与 `handle_parsing_errors=True` 的区别**: 默认行为只返回通用错误信息。自定义函数提供更具体的格式指导，帮助 LLM 理解哪里出了问题。

#### 第三层: Prompt 规则 — 预防 (react_agent.py 系统 prompt)

在系统 prompt 中添加严格的输出格式规则：
- **规则4**: 每次只输出一个 Thought/Action/Action Input 组合，等待 Observation 后再继续
- **规则7**: 严禁在一次输出中同时包含 Action 和 Final Answer；严禁虚构 Observation

### 相关配置

- `max_iterations=15`: 从 8 提升到 15，为多步操作 (如逐个卸载模型) 留足空间
- `early_stopping_method="generate"`: 达到迭代上限时优雅退出，生成 Final Answer，而不是抛异常
- `handle_parsing_errors=_handle_parsing_error`: 自定义解析错误处理

### 已知局限

- `_clean_llm_output()` 是启发式截断，极端情况下可能误截断合法的多行 Action Input
- 第一层防御越强，第二层的触发频率越低，但第二层的反馈质量对 LLM 自我修正至关重要
- 最根本的解决方案是让 LLM 严格遵循格式，但 DeepSeek 的指令遵循能力有限
- 如果三层防御仍不够，可考虑切换到指令遵循能力更强的模型 (如 Claude API)

### 重复循环检测 (Loop Detection)

LangChain 的 `AgentExecutor` 在工具连续返回相同结果时不会自动停止，导致 Agent 陷入无限循环。

**问题**: `QueueStreamingHandler` 中 `raise RuntimeError` 被 LangChain callback manager 捕获并降级为 WARNING 日志，不会终止 Agent 循环。

**解决方案**: 通过 `RouterLLM._force_stop` 共享标志位实现跨组件通信:

- **`QueueStreamingHandler._check_repeat_loop()`** (react_agent.py):
  - 跟踪最近 3 次 `(tool_name, tool_input)` 调用历史
  - 连续 3 次相同调用 → 设置 `llm._force_stop = True` + `_force_stop_reason`
  - 不再抛 RuntimeError，直接操作 RouterLLM 标志位

- **`RouterLLM._force_stop` 标志位** (react_agent.py):
  - `__init__()`: 初始化 `_force_stop = False`, `_force_stop_reason = ""`
  - `_call()`: 每次 LLM 调用前检查，若置位则返回终止 Final Answer（不清空 AgentExecutor 的内部状态即可让循环优雅退出），然后重置标志
  - `_run_with_retry()`: 每轮开始前重置标志，确保新一轮不受旧标志影响

- **效果**: 重复循环被检测到后，最多再消耗 1 次 LLM 调用即可终止，不再无限循环

## 角色人格文件生成任务 (已完成 2026-05-26)

### 背景

用户需要为 reference_audio/index.json 中所有崩坏3角色生成 SKILL.md 人格文件。核心原则：**声音不同 = 分开 SKILL.md**。

### 已完成 (2026-05-25)

#### 参考音频拆分

- `希儿` → `白希儿` (rename) + `黑希儿` (new)
- `西琳` → `魔法少女西琳` (rename) + `空之律者` (new, 音频来自 琪亚娜/空之律者 装甲)
- `符华` 目录已有 识之律者 装甲音频 → 新建 `识之律者` 条目
- `德丽莎` 目录已有 朔夜观星/月下初拥/月下誓约 装甲音频 → 各建条目
- `伏特加女孩` 拆为 `萝莎莉娅` + `莉莉娅` + `德尔塔` (狂热蓝调装甲)

#### index.json 更新

从 39 个条目扩展到 48 个条目。包含所有新拆分角色的 audio_path、ref_text、original_file。新增幽兰黛尔·天光驰彻（幼态音色）。

### 已有 SKILL.md (6个，不动)

| 目录 | 角色 | 状态 |
|------|------|------|
| `skills/characters/elysia/SKILL.md` | 爱莉希雅 | 完整版 |
| `skills/characters/kiana/SKILL.md` | 琪亚娜 | 已复制 |
| `skills/characters/mei/SKILL.md` | 芽衣 | 已复制 |
| `skills/characters/fu-hua/SKILL.md` | 符华 | 已复制 |
| `skills/characters/theresa/SKILL.md` | 德丽莎 | 已复制 |
| `skills/characters/bronya/SKILL.md` | 布洛妮娅 | 精简版，暂不动 |

### 待生成 SKILL.md (37个)

**重要原则**：每个角色人格文件需要仔细、慢慢地写，不能批量生成简短内容。每个 SKILL.md 需要：
- YAML frontmatter (name, description, tts_voice)
- 身份卡 (我是谁)
- 3-5 个核心心智模型 (每个有证据/应用/局限)
- 表达DNA (句式、词汇、语气、幽默方式)
- 决策启发式
- 价值观与反模式
- 诚实边界

#### 拆分角色 (11个，优先写，需要区分与同源角色的差异)

| # | 目录名 | 角色 | TTS音色 | 关键人格特征 | 状态 |
|---|--------|------|---------|-------------|------|
| 1 | `baixier` | 白希儿 | 白希儿 | 温柔怯懦，第三人称自指，害怕孤独，渴望被需要 | 已完成 |
| 2 | `heixier` | 黑希儿 | 黑希儿 | 嗜虐危险的守护者，以毁灭护希儿，病娇但不越界 | 已完成 |
| 3 | `magical-sirin` | 魔法少女西琳 | 魔法少女西琳 | 天真腹黑，蘑菇魔法，欢愉至上，和空律完全不同 | 已完成 |
| 4 | `herrscher-of-void` | 空之律者 | 空之律者 | 高傲俯视人类，崩坏女王，神的视角，被琪亚娜羁绊困惑 | 已完成 |
| 5 | `herrscher-of-sentience` | 识之律者 | 识之律者 | 嚣张豪爽，不是符华的影子，别扭的温柔，五万年记忆 | 已完成 |
| 6 | `stargazer-theresa` | 朔夜观星 | 朔夜观星 | 煌帝国军师，文雅傲娇，夜观天象，刺客先生 | 已完成 |
| 7 | `luna-kindred-young` | 月下初拥 | 月下初拥 | 小恶魔吸血猫，契约即羁绊，渴望陪伴 | 已完成 |
| 8 | `luna-kindred-grown` | 月下誓约 | 月下誓约 | 长大但没成熟的吸血姬，害羞软糯，不敢表白 | 已完成 |
| 9 | `rozaliya` | 萝莎莉娅 | 萝莎莉娅 | 伏特加女孩姐姐，元气冲动，超级头槌，先冲再说 | 已完成 |
| 10 | `liliya` | 莉莉娅 | 莉莉娅 | 伏特加女孩妹妹，慵懒冷静，永远没睡醒，吐槽担当 | 已完成 |
| 11 | `delta` | 德尔塔 | 德尔塔 | 世界泡双子融合体，冷淡孤独，背负失去的代价 | 已完成 |

#### 单一身份角色 (26个)

| # | 目录名 | 角色 | TTS音色 | 关键特征 | 状态 |
|---|--------|------|---------|---------|------|
| 12 | `rita` | 丽塔 | 丽塔 | 完美女仆，优雅腹黑，什么都做到最好 | 已完成 |
| 13 | `eden` | 伊甸 | 伊甸 | 逐火英桀第四位，黄金的歌唱者，华丽慵懒 | 已完成 |
| 14 | `yae-sakura` | 八重樱 | 八重樱 | 500年前巫女，冷酷与温柔并存 | 已完成 |
| 15 | `sakura` | 樱 | 八重樱 | 逐火英桀第八席「刹那」之铭，沉默之刃 | 已完成 |
| 16 | `carol` | 卡萝尔 | 卡萝尔 | 后崩坏书，活泼元气少女，拳头比脑子快 | 已完成 |
| 17 | `himeko` | 姬子 | 姬子 | 无量塔姬子，前女武神教官，燃烧自己照亮他人 | 已完成 |
| 18 | `durandal` | 幽兰黛尔 | 幽兰黛尔 | 天命最强S级女武神，正常+幼态双音色 | 已完成 |
| 19 | `shigure-kira` | 时雨绮罗 | 时雨绮罗 | 天命偶像女武神，自信闪耀，偶尔年代感笑话 | 已完成 |
| 20 | `prometheus` | 普罗米修斯 | 普罗米修斯 | 前文明AI，理性冷静，分析一切 | 已完成 |
| 21 | `li-sushang` | 李素裳 | 李素裳 | 太虚剑传人，活泼好斗，和幽兰黛尔是好友 | 已完成 |
| 22 | `songque` | 松雀 | 松雀 | 第二部，慵懒自由，箱箱乐爱好者 | 已完成 |
| 23 | `griseo` | 格蕾修 | 格蕾修 | 逐火英桀第十一位，画家，安静观察世界，用颜色表达情感 | 已完成 |
| 24 | `mobius` | 梅比乌斯 | 梅比乌斯 | 逐火英桀第十位，疯狂科学家，蛇一般危险魅惑，追求无限 | 已完成 |
| 25 | `raven` | 渡鸦 | 渡鸦 | 世界蛇干部，娜塔莎·希奥拉，嘴硬心软，照顾孤儿院 | 已完成 |
| 26 | `deng` | 灯 | 灯 | 第二部，咖啡和三明治，冷淡寡言但可靠 | 已完成 |
| 27 | `ai-chan` | 爱衣 | 爱衣 | 休伯利安AI，活泼可爱的辅助人格，从AI进化为伙伴 | 已完成 |
| 28 | `senadina` | 希娜狄雅 | 希娜狄雅 | 第二部，无人机和跑酷，自由奔放的冒险者 | 已完成 |
| 29 | `serelim` | 瑟莉姆 | 瑟莉姆 | 第二部，享受支配的过程，不讨厌捣乱的家伙 | 已完成 |
| 30 | `coralie` | 科拉莉 | 科拉莉 | 第二部，机械工程天才，不想被笨蛋拜托修电脑 | 已完成 |
| 31 | `vill-v` | 维尔薇 | 维尔薇 | 逐火英桀第五位，多重人格工程师(魔术师/专家等)，同一实体 | 已完成 |
| 32 | `misteln` | 羽兔 | 羽兔 | 第二部，能力方便可以应付体重测量，随性悠然 | 已完成 |
| 33 | `susannah` | 苏莎娜 | 苏莎娜 | 天命女武神，吃货，发现很多好吃的店 | 已完成 |
| 34 | `vita` | 薇塔 | 薇塔 | 第二部，量子之海珍馐收藏家，神秘优雅 | 已完成 |
| 35 | `helia` | 赫丽娅 | 赫丽娅 | 第二部，和科拉莉搭档，劳逸结合飞镖游戏 | 已完成 |
| 36 | `aponia` | 阿波尼亚 | 阿波尼亚 | 逐火英桀第三位，戒律的守护者，温柔到让人睡着的危险 | 已完成 |
| 37 | `pardofelis` | 帕朵菲莉丝 | 帕朵菲莉丝 | 逐火英桀第九位，猫娘商人，小鱼干和金枪鱼罐头 | 已完成 |

### 联动角色 (4个，跳过不生成)

刻晴 (原神), 菲谢尔 (原神), 明日香 (EVA), 花火 (星穹铁道)

### 伏特加女孩 (1个，保留音频但不单独生成 SKILL.md)

已拆分为萝莎莉娅+莉莉娅+德尔塔，伏特加女孩作为组合名保留音频。

### 音频来源

参考音频来自 `D:/hongkai_voice/`，按角色名 → 装甲名 → 语音类别(互动/备战/战斗/语气) 组织。
音频格式: WAV, 16-bit, 采样率不确定, 文件大小 250KB-820KB (约3-10秒)。

### 生成方法

对每个角色：
1. 基于崩坏3游戏设定和剧情知识，手工撰写完整人格描述
2. 参考已有 SKILL.md 格式 (如 fu-hua/SKILL.md 是最完整的范本)
3. 拆分角色重点描述与同源角色的差异
4. YAML frontmatter 必须包含 name, description, tts_voice 三个字段

### 完成总结

全部 44 个角色 SKILL.md 已生成（2026-05-26）。包括：6 个原始角色 + 11 个拆分角色 + 26 个单一身份角色 + 1 个（seele，保留兼容）。

**特殊案例**:
- `durandal` — 幽兰黛尔：一个人格，两种 TTS 音色（正常 `幽兰黛尔` + 幼态 `幽兰黛尔·天光驰彻`），由 index.json 双条目支持
- `yae-sakura` + `sakura` — 八重樱/樱：共用同一音色 `八重樱`，不同人格
- `magical-sirin` + `herrscher-of-void` — 西琳双子：共用调研文件（magical-sirin 为主），不同音色
