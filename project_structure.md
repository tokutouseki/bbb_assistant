# 崩坏3专属AI陪伴助手（桌面端）项目结构规划

## 项目概述
基于Vue3 + Electron与Python全栈技术栈，实现崩坏3游戏场景视觉感知、实时语音交互、角色原声应答、攻略智能查询、专属对话记忆留存一体化的沉浸式AI陪伴助手。

## 技术栈
- **前端**: Vue3 + Electron + Vite + TypeScript + Pinia + Tailwind CSS
- **后端**: Python + FastAPI + WebSocket + SQLite/ChromaDB
- **AI模型**: YOLO11n (目标检测) + PaddleOCR/EasyOCR (文字识别) + FunASR 1.3.x (语音识别框架，支持SenseVoiceSmall/Paraformer流式/全双工实时对话) + VoxCPM-0.5B (TTS合成，零样本语音克隆) + Qwen3-TTS (TTS合成，声音设计) + Qwen3.5-4B via LM Studio (本地大模型，支持vision/tool_use)
- **知识库**: RAG (检索增强生成) + ChromaDB (向量数据库) + Sentence Transformers (嵌入模型)
- **工具库**: MSS (屏幕捕获) + PyAutoGUI (自动化) + LangChain (AI应用框架) + 声音资源管理器 (统一语音资源管理)

## 已实现技能
### 🎤 音频处理
- **ASR语音识别**: FunASR 1.3.x框架，支持三种模式：
  - SenseVoiceSmall: 高精度多语言识别+情感检测 (50+语言)
  - Paraformer-streaming: 低延迟流式识别 (首包延迟<100ms)
  - 全双工实时对话: 2pass级联架构+VAD检测+随时打断
- **TTS语音合成**: VoxCPM-0.5B模型，零样本语音克隆，支持崩坏3角色音色
- **Qwen3-TTS语音合成**: 阿里Qwen3-TTS模型，支持10种语言、声音设计、3秒语音克隆
- **语音克隆**: 基于参考音频克隆角色音色
- **声音资源管理**: 统一管理7个崩坏3角色（爱莉希雅、琪亚娜、雷电芽衣、布洛妮娅、希儿、德丽莎、符华）的语音资源

### 👁️ 视觉感知
- **屏幕捕获**: 实时捕获游戏画面，支持多显示器
- **目标检测**: YOLO11n模型识别游戏内UI元素、角色、敌人
- **OCR文字识别**: 提取屏幕中的文字信息（任务提示、对话文本等）
- **场景分析**: 分析当前游戏场景（主界面、战斗、剧情等）
- **短期记忆**: 缓存视觉信息，支持上下文关联

### 🧠 大模型集成
- **LM Studio客户端**: 本地运行Qwen3.5-4B模型，OpenAI兼容API
- **LLM路由器**: 智能路由不同任务到合适的模型
- **模型注册表**: 管理可用模型及其配置
- **工具集成**: 将联网搜索和百科爬虫功能集成到LLM系统

### 🔍 联网搜索与爬虫
- **联网搜索**: 支持Google和DuckDuckGo搜索引擎，实时获取最新信息
- **答案提取**: 从搜索结果中智能提取相关答案
- **百科爬虫**: 崩坏3官方百科爬虫，支持requests和playwright模式，可获取JavaScript动态内容
- **智能工具调用**: 根据用户查询自动触发搜索或爬虫工具

### 💬 聊天服务
- **聊天补全**: 集成LLM、RAG（待实现）、记忆管理（待实现）
- **工具增强响应**: 自动使用联网搜索和百科爬虫增强LLM回复
- **游戏场景感知**: 根据当前游戏场景优化回复内容
- **流式输出**: 支持流式聊天响应

### 🛠️ 工具与集成
- **工具集成系统**: 统一管理web_search、crawl_wiki、query_knowledge工具
- **智能工具建议**: 基于关键词匹配自动推荐工具
- **错误处理与降级**: 工具失败时优雅降级，保证系统可用性

## 目录结构

```
崩坏3专属AI陪伴助手（桌面端）/
├── README.md                          # 项目总览文档
├── package.json                       # 根package.json (monorepo管理)
├── pnpm-workspace.yaml                # pnpm workspace配置
├── .env.example                       # 环境变量示例
├── .gitignore                         # Git忽略配置
├── LICENSE                            # 许可证文件
├── project_structure.md               # 项目结构文档（本文档）
├── SenseVoiceSmall/                   # ASR模型文件 (SenseVoiceSmall)
│   ├── example/                       # 示例音频文件
│   ├── fig/                           # 模型说明图片
│   ├── config.yaml                    # 模型配置
│   ├── model.pt                       # 模型权重
│   └── README.md                      # 模型说明文档
├── FunASR/                            # FunASR官方源码仓库 (新增)
│   ├── funasr/                        # FunASR核心库
│   ├── examples/                      # 示例代码
│   ├── runtime/                       # 部署运行时
│   └── README.md                      # 说明文档
├── VoxCPM-0.5B/                       # TTS模型文件 (VoxCPM-0.5B)
│   ├── assets/                        # 资源文件
│   ├── config.json                    # 模型配置
│   ├── pytorch_model.bin              # 模型权重
│   └── README.md                      # 模型说明文档
├── Qwen3-TTS/                         # TTS模型文件 (Qwen3-TTS) - 新增
│   ├── models/                        # 模型权重目录
│   │   └── Qwen3-TTS-12Hz-1.7B-VoiceDesign/
│   ├── examples/                      # 示例音频文件
│   ├── configs/                       # 配置文件
│   ├── README.md                      # 模型说明文档
│   └── requirements.txt               # 依赖文件
├── frontend/                          # Electron+Vue3前端应用
│   ├── package.json                   # 前端依赖配置
│   ├── electron/                      # Electron主进程代码
│   │   ├── main.js                    # 主进程入口
│   │   ├── preload.js                 # 预加载脚本
│   │   └── ipc/                       # IPC通信处理
│   │       └── handlers.js            # IPC处理器
│   ├── src/                           # Vue渲染进程源码
│   │   ├── main.js                    # Vue应用入口
│   │   ├── App.vue                    # 根组件
│   │   ├── assets/                    # 静态资源
│   │   │   └── styles/                # 样式文件
│   │   │       ├── main.css           # 主样式
│   │   │       └── tailwind.css       # Tailwind样式
│   │   ├── stores/                    # Pinia状态管理
│   │   │   ├── app.js                 # 应用状态
│   │   │   └── index.js               # 状态管理入口
│   │   ├── router/                    # 路由配置
│   │   │   └── index.js               # 路由入口
│   │   └── types/                     # TypeScript类型定义
│   ├── public/                        # 公共资源
│   ├── index.html                     # HTML入口
│   ├── vite.config.js                 # Vite配置
│   ├── tailwind.config.js             # Tailwind配置
│   ├── tsconfig.json                  # TypeScript配置
│   ├── postcss.config.js              # PostCSS配置
│   ├── .eslintrc.js                   # ESLint配置
│   └── .prettierrc                    # Prettier配置
├── backend/                           # Python AI后端服务
│   ├── pyproject.toml                 # Python项目配置 (Poetry)
│   ├── requirements.txt               # Python依赖 (传统方式)
│   ├── src/                           # 后端源码
│   │   ├── main.py                    # 服务入口点
│   │   ├── api/                       # FastAPI路由
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                # 聊天接口
│   │   │   ├── vision.py              # 视觉接口
│   │   │   ├── audio.py               # 音频接口 (ASR/TTS)
│   │   │   ├── memory.py              # 记忆接口
│   │   │   └── health.py              # 健康检查
│   │   ├── modules/                   # 核心功能模块
│   │   │   ├── vision/                # 视觉感知模块
│   │   │   │   ├── __init__.py
│   │   │   │   ├── screen_capture.py  # 屏幕捕获
│   │   │   │   ├── yolo_detector.py   # YOLO11n目标检测
│   │   │   │   ├── ocr_processor.py   # OCR文字识别
│   │   │   │   └── scene_analyzer.py  # 场景分析器
│   │   │   ├── audio/                 # 音频处理模块
│   │   │   │   ├── __init__.py
│   │   │   │   ├── asr_processor.py   # ASR语音识别 (SenseVoiceSmall)
│   │   │   │   ├── full_duplex_asr_processor.py  # 全双工实时ASR处理器 (新增)
│   │   │   │   ├── tts_generator.py   # TTS语音合成 (VoxCPM-0.5B)
│   │   │   │   ├── qwen3_tts_generator.py  # Qwen3-TTS语音合成 - 新增
│   │   │   │   ├── voice_clone.py     # 语音克隆
│   │   │   │   └── voice_resource_manager.py  # 声音资源管理器
│   │   │   ├── llm/                   # 大模型模块 (已实现: Qwen3.5-4B via LM Studio)
│   │   │   ├── crawler/               # 崩坏3百科爬虫模块 (已实现)
│   │   │   ├── web_search/            # 联网搜索模块 (已实现)
│   │   │   ├── rag/                   # RAG知识库模块 (待实现)
│   │   │   ├── memory/                # 对话记忆模块 (待实现)
│   │   │   ├── utils/                 # 工具模块 (待实现)
│   │   │   └── tool_integration.py    # 工具集成模块 (已实现)
│   │   ├── services/                  # 后台服务
│   │   │   ├── __init__.py
│   │   │   ├── game_monitor.py        # 游戏监控服务
│   │   │   ├── chat_service.py        # 聊天服务
│   │   │   └── background_tasks.py    # 后台任务
│   │   ├── config/                    # 配置文件
│   │   │   ├── __init__.py
│   │   │   ├── settings.py            # 应用设置
│   │   │   ├── game_scenes.py         # 游戏场景定义
│   │   │   └── honkai_voices.json     # 崩坏3角色语音配置 (7个角色)
│   │   ├── tests/                     # 单元测试 (待完善)
│   │   └── models/                    # 数据模型 (待实现)
│   ├── annotations/                   # 标注和记录文件
│   │   ├── annotation_results.json    # 标注结果
│   │   ├── statistics_report.json     # 统计报告
│   │   └── asr_training_tasks.md      # ASR训练任务记录
│   ├── scripts/                       # 后端脚本
│   │   ├── audio_processor.py         # 批量音频处理器 (ASR转录 + TTS合成)
│   │   ├── single_audio_tester.py     # 单文件音频处理器
│   │   ├── performance_benchmark.py   # 完整流程性能测速脚本
│   │   └── batch_asr_tts_test_legacy.py # 旧版批量测试脚本 (已迁移)
│   ├── test_asr_tts_integration.py    # ASR/TTS集成测试
│   ├── test_file_outputs.py           # 文件输出测试
│   └── test_voice_resource_system.py  # 声音资源系统测试
├── voice_resources/                   # 统一声音资源管理系统
│   ├── elysia/                        # 爱莉希雅角色
│   │   ├── reference.wav              # 参考音频
│   │   ├── reference.txt              # 参考文本
│   │   └── metadata.json              # 角色元数据
│   ├── kiana/                         # 琪亚娜角色 (待收集音频)
│   │   └── metadata.json              # 角色元数据
│   ├── mei/                           # 雷电芽衣角色 (待收集音频)
│   │   └── metadata.json              # 角色元数据
│   ├── bronya/                        # 布洛妮娅角色 (待收集音频)
│   │   └── metadata.json              # 角色元数据
│   ├── seele/                         # 希儿角色 (待收集音频)
│   │   └── metadata.json              # 角色元数据
│   ├── theresa/                       # 德丽莎角色 (待收集音频)
│   │   └── metadata.json              # 角色元数据
│   └── fu_hua/                        # 符华角色 (待收集音频)
│       └── metadata.json              # 角色元数据
├── outputs/                           # 程序输出文件目录
│   ├── asr_transcriptions/            # ASR转录结果
│   │   ├── asr_20260311_181530_test_audio_zh.txt  # 示例转录文件
│   │   └── ...
│   ├── tts_audio/                     # TTS生成音频
│   │   ├── tts_20260311_181552_elysia_bd4534.wav  # 示例音频文件
│   │   └── ...
│   ├── single_test/                   # 单次测试输出
│   │   ├── asr_result.txt             # 单次ASR结果
│   │   └── tts_result.wav             # 单次TTS结果
│   └── test_results/                  # 批量测试结果
│       ├── asr_transcriptions/        # 批量ASR转录
│       ├── tts_audio/                 # 批量TTS音频
│       └── reports/                   # 测试报告
├── to_clone_test/                     # 语音克隆测试音频
│   ├── 德丽莎-*.wav                   # 德丽莎角色语音片段
│   ├── 月下誓约-*.wav                 # 月下誓约语音片段
│   ├── 朔夜观星-*.wav                 # 朔夜观星语音片段
│   ├── 渡尘之羽-*.wav                 # 渡尘之羽语音片段
│   ├── 识之律者-*.wav                 # 识之律者语音片段
│   ├── 迷城骇兔-*.wav                 # 迷城骇兔语音片段
│   ├── KianaData_SVC_Raw_*.wav        # 琪亚娜原始语音
│   └── Da_Yue_Xia_*.wav               # 大月下语音
├── shared/                            # 前后端共享代码
│   ├── types/                         # 共享类型定义
│   │   └── index.ts                   # TypeScript类型定义
│   └── protocol/                      # 通信协议定义
│       └── api.ts                     # API接口类型
├── scripts/                           # 项目构建脚本
│   ├── build.js                       # 构建脚本
│   ├── dev.js                         # 开发脚本
│   └── package.js                     # 打包脚本
├── docs/                              # 项目文档 (待完善)
├── data/                              # 数据存储目录 (待实现)
└── .github/                           # GitHub工作流 (待实现)
```

注意：标有"(待实现)"的目录或模块表示尚未完全实现，标有"(待收集音频)"的角色表示需要收集游戏内语音片段作为参考音频。

## 模块详细说明

### 前端模块 (frontend/)
- **Electron主进程**: 负责窗口管理、系统托盘、原生API调用、进程间通信
- **Vue渲染进程**: 提供用户界面，包括聊天窗口、设置面板、游戏覆盖层
- **状态管理**: 使用Pinia管理应用状态，包括聊天历史、游戏状态、用户设置
- **通信层**: 通过IPC与Electron主进程通信，通过WebSocket/HTTP与后端服务通信

### 后端模块 (backend/)
- **API服务**: FastAPI提供RESTful API和WebSocket接口
- **视觉感知模块**: 集成YOLO11n进行游戏场景识别，OCR提取屏幕文字信息
- **音频处理模块**: 
  - FunASR 1.3.x框架：支持SenseVoiceSmall (高精度多语言+情感检测)、Paraformer-streaming (低延迟流式)、全双工实时对话 (2pass级联+VAD+中断)
  - VoxCPM-0.5B和Qwen3-TTS进行TTS文字转语音（零样本语音克隆+声音设计）
  - 支持崩坏3角色音色，内置统一声音资源管理系统
- **大模型集成**: 通过LM Studio本地运行Qwen3.5-4B模型，支持vision/tool_use能力，处理自然语言理解与生成，集成工具调用功能 (已实现)
- **联网搜索与爬虫模块**: 支持Google/DuckDuckGo实时搜索，崩坏3官方百科爬虫，智能答案提取 (已实现)
- **工具集成模块**: 统一管理web_search、crawl_wiki、query_knowledge工具，智能工具建议与执行 (已实现)
- **RAG知识库**: 构建崩坏3垂直领域知识库，支持攻略查询、角色培养建议 (待实现)
- **对话记忆**: 存储用户对话历史，实现个性化陪伴体验 (待实现)
- **游戏监控服务**: 持续监测游戏状态，实时感知玩家当前场景

### 数据存储 (data/)
- **知识库**: 存储崩坏3攻略、角色信息、活动说明等结构化知识 (待实现)
- **对话记忆**: 保存用户与AI的交互历史，形成个性化记忆 (待实现)
- **模型文件**: 存放本地AI模型权重文件，减少网络依赖
- **配置文件**: 应用运行时配置，支持热更新

## TTS模型对比

| 特性 | VoxCPM-0.5B | Qwen3-TTS |
|------|-------------|-----------|
| 模型大小 | 0.5B | 1.7B |
| 语音克隆 | ✅ 零样本克隆 | ✅ 3秒克隆 |
| 声音设计 | ❌ 不支持 | ✅ 自然语言描述 |
| 支持语言 | 中文 | 10种语言 |
| 音质 | 高质量 | 高质量 |
| 推理速度 | 快 | 中等 |
| 适用场景 | 角色配音克隆 | 多语言、多风格 |

## 通信架构
1. **前端内部通信**: Vue组件 ↔ Pinia状态 ↔ Electron主进程 (IPC)
2. **前后端通信**: Electron前端 ↔ Python后端 (HTTP/WebSocket)
3. **后端模块通信**: 模块间通过服务接口调用，松耦合设计

## 开发环境配置
- **Node.js**: v18+，使用pnpm作为包管理器
- **Python**: 3.10+，使用uv或poetry管理虚拟环境
- **IDE推荐**: VS Code + 相应插件
- **开发命令**:
  ```bash
  # 启动前端开发服务器
  cd frontend && pnpm dev
  
  # 启动后端开发服务器
  cd backend && python src/main.py
  
  # 构建生产版本
  pnpm build:all
  ```

## 部署方案
- **桌面端**: 使用electron-builder打包为Windows/macOS可执行文件
- **后端服务**: 可独立部署为系统服务，支持Docker容器化
- **数据同步**: 可选云同步功能，备份用户对话记忆与个性化设置

---
*最后更新: 2026-03-14*
