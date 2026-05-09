# 崩坏3专属AI陪伴助手 - 项目结构分析报告

> 生成日期: 2026-03-24
> 分析基准: `project_structure.md`
> 最后更新: 2026-03-24 (整改后)

---

## 目录

1. [执行摘要](#执行摘要)
2. [根目录结构分析](#根目录结构分析)
3. [前端模块分析 (frontend/)](#前端模块分析-frontend)
4. [后端模块分析 (backend/)](#后端模块分析-backend)
5. [模型文件分析](#模型文件分析)
6. [资源目录分析](#资源目录分析)
7. [共享代码分析 (shared/)](#共享代码分析-shared)
8. [构建脚本分析 (scripts/)](#构建脚本分析-scripts)
9. [结构偏差汇总](#结构偏差汇总)
10. [整改建议](#整改建议)

---

## 执行摘要

### 项目状态概览

| 类别 | 预期数量 | 实际数量 | 符合度 |
|------|----------|----------|--------|
| 核心目录 | 15 | 17 | 88% |
| 前端文件 | 18 | 18 | 100% |
| 后端模块 | 8 | 9 | 89% |
| API接口 | 5 | 6 | 100% |
| 服务层 | 3 | 3 | 100% |
| 配置文件 | 3 | 3 | 100% |

### 关键发现

1. **已实现功能**: 大部分核心功能已实现，包括ASR/TTS、LLM集成、联网搜索、百科爬虫
2. **已整改项目**: 
   - ✅ `YueXiaShiYue/` 已整合到 `to_clone_test/YueXiaShiYue/`
   - ✅ `backend/data/` 已移动到根目录 `data/`
   - ✅ RAG向量数据库已从Qdrant切换为ChromaDB
3. **缺失目录**: `docs/`、`.github/` 目录未创建
4. **配置文件**: `pyproject.toml` 未创建，使用 `requirements.txt` 替代

---

## 根目录结构分析

### 预期结构 vs 实际结构 (整改后)

```
预期目录                    实际状态        说明
─────────────────────────────────────────────────────────
README.md                   ✅ 存在        项目说明文档
package.json                ✅ 存在        Monorepo根配置
pnpm-workspace.yaml         ✅ 存在        Workspace配置
.env.example                ✅ 存在        环境变量示例
.gitignore                  ✅ 存在        Git忽略配置
LICENSE                     ✅ 存在        许可证文件
project_structure.md        ✅ 存在        结构规划文档
─────────────────────────────────────────────────────────
SenseVoiceSmall/            ✅ 存在        ASR模型目录
FunASR/                     ✅ 存在        FunASR框架源码
VoxCPM-0.5B/                ✅ 存在        TTS模型目录
Qwen3-TTS/                  ❌ 缺失        Qwen3-TTS模型目录
─────────────────────────────────────────────────────────
frontend/                   ✅ 存在        前端应用
backend/                    ✅ 存在        后端服务
voice_resources/            ✅ 存在        语音资源
outputs/                    ✅ 存在        输出文件
shared/                     ✅ 存在        共享代码
scripts/                    ✅ 存在        构建脚本
data/                       ✅ 存在        数据存储目录 (已整改)
─────────────────────────────────────────────────────────
docs/                       ❌ 缺失        文档目录
.github/                    ❌ 缺失        GitHub工作流
─────────────────────────────────────────────────────────
to_clone_test/              ✅ 存在        语音克隆测试音频 (已整合YueXiaShiYue)
ASR_TTS_test.txt            ⚠️ 额外        测试记录文件
FunASR2.0.txt               ⚠️ 额外        FunASR说明文件
```

### 根目录文件详情

#### package.json
- **路径**: `d:\TokusCode\bbb_assistant\package.json`
- **功能**: Monorepo根配置文件，定义工作区和脚本
- **依赖**:
  - `concurrently: ^8.2.2` - 并行执行脚本
  - `archiver: ^6.0.1` - 文件归档
- **工作区**: `frontend`, `shared`
- **脚本命令**:
  - `dev`: 并行启动前后端开发服务器
  - `build`: 构建前后端
  - `package`: 打包Electron应用
  - `lint/format`: 代码检查和格式化
  - `test`: 运行测试

#### pnpm-workspace.yaml
- **路径**: `d:\TokusCode\bbb_assistant\pnpm-workspace.yaml`
- **功能**: pnpm工作区配置
- **工作区包**: `frontend`, `shared`
- **特殊配置**: 忽略electron相关依赖的构建

#### .env.example
- **路径**: `d:\TokusCode\bbb_assistant\.env.example`
- **功能**: 环境变量示例文件
- **状态**: 存在

---

## 前端模块分析 (frontend/)

### 目录结构

```
frontend/
├── electron/                    # Electron主进程
│   ├── main.js                  # 主进程入口
│   ├── preload.js               # 预加载脚本
│   └── ipc/
│       └── handlers.js          # IPC处理器
├── src/                         # Vue渲染进程
│   ├── main.js                  # Vue应用入口
│   ├── App.vue                  # 根组件
│   ├── assets/
│   │   └── styles/
│   │       ├── main.css         # 主样式
│   │       └── tailwind.css     # Tailwind样式
│   ├── router/
│   │   └── index.js             # 路由配置
│   └── stores/
│       ├── index.js             # Pinia入口
│       └── app.js               # 应用状态
├── public/                      # 公共资源 (预期)
├── index.html                   # HTML入口
├── package.json                 # 前端依赖配置
├── vite.config.js               # Vite配置
├── tailwind.config.js           # Tailwind配置
├── tsconfig.json                # TypeScript配置
├── postcss.config.js            # PostCSS配置
├── .eslintrc.js                 # ESLint配置
├── .prettierrc                  # Prettier配置
└── env.d.ts                     # 环境类型声明
```

### 文件详情

#### electron/main.js
- **路径**: `frontend/electron/main.js`
- **功能**: Electron主进程入口，负责窗口管理、系统托盘、游戏监控
- **外部依赖**:
  - `electron` - 桌面应用框架
  - `electron-updater` - 自动更新
  - `electron-log` - 日志记录
- **内部依赖**: `preload.js`, `handlers.js`
- **主要功能**:
  - 创建主窗口和游戏覆盖层窗口
  - 系统托盘管理
  - 游戏进程监控
  - IPC通信设置

#### electron/preload.js
- **路径**: `frontend/electron/preload.js`
- **功能**: 预加载脚本，暴露安全API给渲染进程
- **状态**: 存在

#### electron/ipc/handlers.js
- **路径**: `frontend/electron/ipc/handlers.js`
- **功能**: IPC通信处理器
- **状态**: 存在

#### src/main.js
- **路径**: `frontend/src/main.js`
- **功能**: Vue应用入口
- **外部依赖**:
  - `vue: ^3.4.21` - Vue框架
  - `pinia: ^2.1.7` - 状态管理
  - `vue-router: ^4.2.5` - 路由
- **内部依赖**: `App.vue`, `router/index.js`, `stores/index.js`
- **配置**:
  - 全局错误处理
  - 应用版本管理
  - Electron环境检测

#### src/App.vue
- **路径**: `frontend/src/App.vue`
- **功能**: Vue根组件
- **状态**: 存在

#### src/router/index.js
- **路径**: `frontend/src/router/index.js`
- **功能**: 路由配置
- **状态**: 存在

#### src/stores/app.js
- **路径**: `frontend/src/stores/app.js`
- **功能**: 应用状态管理
- **状态**: 存在

#### package.json (前端)
- **路径**: `frontend/package.json`
- **功能**: 前端依赖配置
- **生产依赖**:
  | 包名 | 版本 | 用途 |
  |------|------|------|
  | vue | ^3.4.21 | Vue框架 |
  | pinia | ^2.1.7 | 状态管理 |
  | vue-router | ^4.2.5 | 路由管理 |
  | axios | ^1.6.8 | HTTP客户端 |
  | @vueuse/core | ^10.7.2 | Vue组合式工具 |
  | @iconify/vue | ^4.1.2 | 图标库 |
  | dayjs | ^1.11.10 | 日期处理 |
  | wavesurfer.js | ^7.7.10 | 音频波形 |
  | websocket | ^1.0.34 | WebSocket客户端 |
  | electron-updater | ^6.1.7 | 自动更新 |

- **开发依赖**:
  | 包名 | 版本 | 用途 |
  |------|------|------|
  | electron | ^28.2.0 | 桌面应用框架 |
  | electron-builder | ^24.9.1 | 打包工具 |
  | vite | ^5.1.0 | 构建工具 |
  | typescript | ~5.3.3 | TypeScript |
  | tailwindcss | ^3.4.1 | CSS框架 |
  | eslint | ^8.56.0 | 代码检查 |
  | prettier | ^3.2.5 | 代码格式化 |
  | vitest | ^1.2.2 | 测试框架 |

#### vite.config.js
- **路径**: `frontend/vite.config.js`
- **功能**: Vite构建配置
- **状态**: 存在

#### tsconfig.json
- **路径**: `frontend/tsconfig.json`
- **功能**: TypeScript编译配置
- **状态**: 存在

### 前端结构偏差

| 预期文件/目录 | 实际状态 | 说明 |
|---------------|----------|------|
| src/types/ | ❌ 缺失 | TypeScript类型定义目录未创建 |
| public/ | ⚠️ 未确认 | 公共资源目录状态待确认 |

---

## 后端模块分析 (backend/)

### 目录结构

```
backend/
├── src/
│   ├── main.py                  # 服务入口点
│   ├── api/                     # FastAPI路由
│   │   ├── __init__.py
│   │   ├── chat.py              # 聊天接口
│   │   ├── vision.py            # 视觉接口
│   │   ├── audio.py             # 音频接口
│   │   ├── memory.py            # 记忆接口
│   │   ├── health.py            # 健康检查
│   │   └── rag.py               # RAG检索接口 (额外)
│   ├── modules/                 # 核心功能模块
│   │   ├── audio/               # 音频处理
│   │   │   ├── asr_processor.py
│   │   │   ├── full_duplex_asr_processor.py
│   │   │   ├── tts_generator.py
│   │   │   ├── qwen3_tts_generator.py
│   │   │   ├── voice_clone.py
│   │   │   └── voice_resource_manager.py
│   │   ├── vision/              # 视觉感知
│   │   │   ├── screen_capture.py
│   │   │   ├── yolo_detector.py
│   │   │   ├── ocr_processor.py
│   │   │   └── scene_analyzer.py
│   │   ├── llm/                 # 大模型集成
│   │   │   ├── lm_studio_client.py
│   │   │   ├── deepseek_client.py
│   │   │   ├── local_model_client.py
│   │   │   ├── llm_router.py
│   │   │   └── model_registry.py
│   │   ├── crawler/             # 百科爬虫
│   │   │   └── honkai_wiki_crawler.py
│   │   ├── web_search/          # 联网搜索
│   │   │   └── web_searcher.py
│   │   ├── rag/                 # RAG知识库
│   │   │   ├── rag_engine.py
│   │   │   ├── embedding.py
│   │   │   ├── vector_store.py  # ChromaDB实现
│   │   │   ├── retriever.py
│   │   │   ├── index_manager.py
│   │   │   └── data_processor.py
│   │   └── tool_integration.py  # 工具集成
│   ├── services/                # 后台服务
│   │   ├── game_monitor.py
│   │   ├── chat_service.py
│   │   └── background_tasks.py
│   ├── config/                  # 配置文件
│   │   ├── settings.py
│   │   ├── game_scenes.py
│   │   └── honkai_voices.json
│   └── utils/                   # 工具模块 (额外)
│       └── model_manager.py
├── scripts/                     # 后端脚本
│   ├── audio_processor.py
│   ├── single_audio_tester.py
│   ├── performance_benchmark.py
│   └── [更多分类脚本...]
├── annotations/                 # 标注文件
│   ├── annotation_results.json
│   ├── statistics_report.json
│   └── asr_training_tasks.md
├── requirements.txt             # Python依赖
├── .env.example                 # 环境变量示例
└── pyproject.toml               # ❌ 缺失
```

### 核心文件详情

#### src/main.py
- **路径**: `backend/src/main.py`
- **功能**: FastAPI应用入口，服务生命周期管理
- **外部依赖**:
  - `fastapi` - Web框架
  - `uvicorn` - ASGI服务器
  - `loguru` - 日志库
- **内部依赖**:
  - `src.config.settings` - 配置管理
  - `src.api.*` - API路由模块
  - `src.services.*` - 后台服务
  - `src.modules.utils.logger` - 日志设置
- **主要功能**:
  - FastAPI应用创建和配置
  - CORS和GZip中间件
  - 生命周期管理（启动/关闭）
  - AI模型按需加载
  - 后台服务启动

#### src/config/settings.py
- **路径**: `backend/src/config/settings.py`
- **功能**: 应用配置管理，基于Pydantic Settings
- **外部依赖**:
  - `pydantic>=2.5.0`
  - `pydantic-settings`
- **配置类别**:
  - 应用基础配置（名称、版本、环境）
  - 服务器配置（主机、端口、工作进程）
  - 数据库配置（SQLite/PostgreSQL）
  - Redis配置
  - AI模型配置（YOLO、OCR、ASR、TTS、LLM）
  - RAG配置（ChromaDB、嵌入模型）
  - 游戏监控配置
  - 搜索配置

#### src/services/chat_service.py
- **路径**: `backend/src/services/chat_service.py`
- **功能**: 聊天服务，集成LLM、RAG、工具调用
- **外部依赖**: `logging`, `asyncio`
- **内部依赖**:
  - `modules.llm.llm_router` - LLM路由器
  - `modules.tool_integration` - 工具集成
  - `modules.rag` - RAG引擎
  - `config.settings` - 配置
- **主要功能**:
  - 聊天补全（同步/流式）
  - RAG知识检索
  - 工具增强响应
  - 任务类型判断
  - 对话情感分析

#### src/modules/tool_integration.py
- **路径**: `backend/src/modules/tool_integration.py`
- **功能**: LLM工具集成，统一管理搜索、爬虫、知识库工具
- **内部依赖**:
  - `modules.web_search.web_searcher` - 联网搜索
  - `modules.crawler.honkai_wiki_crawler` - 百科爬虫
- **注册工具**:
  - `web_search` - 联网搜索
  - `crawl_wiki` - 百科爬虫
  - `query_knowledge` - 知识库查询
- **主要功能**:
  - 工具注册和执行
  - 智能工具建议
  - 响应增强

#### src/modules/llm/lm_studio_client.py
- **路径**: `backend/src/modules/llm/lm_studio_client.py`
- **功能**: LM Studio本地模型客户端（OpenAI兼容API）
- **外部依赖**: `requests`
- **默认配置**:
  - 基础URL: `http://localhost:1234`
  - 超时: 120秒
  - 最大重试: 3次
- **主要功能**:
  - 聊天补全（同步/流式）
  - 模型列表获取
  - 模型加载/卸载
  - 连接测试

#### src/modules/audio/asr_processor.py
- **路径**: `backend/src/modules/audio/asr_processor.py`
- **功能**: 语音识别处理器，使用SenseVoiceSmall模型
- **外部依赖**:
  - `numpy` - 数值计算
  - `funasr` - ASR框架
  - `soundfile` - 音频文件处理
- **内部依赖**: 无
- **主要功能**:
  - 音频转录（实时/文件）
  - 语言检测
  - 流式转录
  - 结果保存

#### src/modules/rag/vector_store.py (已更新)
- **路径**: `backend/src/modules/rag/vector_store.py`
- **功能**: ChromaDB向量存储服务
- **外部依赖**:
  - `chromadb>=0.4.0` - 向量数据库
- **主要功能**:
  - 向量索引和存储
  - 相似度搜索
  - 元数据过滤
  - 本地持久化

#### requirements.txt
- **路径**: `backend/requirements.txt`
- **功能**: Python依赖管理
- **主要依赖**:
  | 包名 | 版本要求 | 用途 |
  |------|----------|------|
  | fastapi | >=0.104.0 | Web框架 |
  | uvicorn[standard] | >=0.24.0 | ASGI服务器 |
  | websockets | >=12.0 | WebSocket支持 |
  | pydantic | >=2.5.0 | 数据验证 |
  | sqlalchemy | >=2.0.0 | ORM |
  | loguru | >=0.7.0 | 日志 |
  | requests | >=2.31.0 | HTTP客户端 |
  | aiohttp | >=3.9.0 | 异步HTTP |
  | beautifulsoup4 | >=4.12.0 | HTML解析 |
  | playwright | >=1.40.0 | 浏览器自动化 |
  | pillow | >=10.0.0 | 图像处理 |
  | numpy | >=1.24.0 | 数值计算 |
  | opencv-python | >=4.8.0 | 计算机视觉 |
  | ultralytics | >=8.0.0 | YOLO模型 |
  | paddleocr | >=2.7.0 | OCR识别 |
  | langchain | >=0.0.300 | AI框架 |
  | chromadb | >=0.4.0 | 向量数据库 |
  | sentence-transformers | >=2.2.0 | 嵌入模型 |
  | mss | >=9.0.0 | 屏幕捕获 |
  | pyautogui | >=0.9.0 | 自动化 |
  | sounddevice | >=0.4.0 | 音频录制 |
  | soundfile | >=0.12.0 | 音频文件 |

### 后端结构偏差

| 预期文件/目录 | 实际状态 | 说明 |
|---------------|----------|------|
| pyproject.toml | ❌ 缺失 | Poetry配置文件未创建 |
| src/modules/memory/ | ❌ 缺失 | 对话记忆模块未实现 |
| src/models/ | ❌ 缺失 | 数据模型目录未创建 |
| src/tests/ | ⚠️ 待完善 | 单元测试目录待完善 |
| src/utils/ | ⚠️ 额外 | 工具模块已创建（规划中标记待实现） |
| src/api/rag.py | ⚠️ 额外 | RAG接口已添加 |
| data/ | ✅ 已整改 | 数据目录已移动到根目录 |

---

## 模型文件分析

### SenseVoiceSmall/
- **路径**: `d:\TokusCode\bbb_assistant\SenseVoiceSmall\`
- **功能**: ASR语音识别模型
- **文件**:
  - `model.pt` - 模型权重
  - `config.yaml` - 模型配置
  - `am.mvn` - 声学模型
  - `tokens.json` - 词表
  - `README.md` - 说明文档
- **状态**: ✅ 完整

### FunASR/
- **路径**: `d:\TokusCode\bbb_assistant\FunASR\`
- **功能**: FunASR框架源码仓库
- **子目录**:
  - `funasr/` - 核心库
  - `runtime/` - 部署运行时
  - `examples/` - 示例代码
  - `tests/` - 测试文件
  - `docs/` - 文档
- **状态**: ✅ 存在

### VoxCPM-0.5B/
- **路径**: `d:\TokusCode\bbb_assistant\VoxCPM-0.5B\`
- **功能**: TTS语音合成模型
- **文件**:
  - `pytorch_model.bin` (预期) / `audiovae.pth` (实际)
  - `config.json` - 模型配置
  - `tokenizer.json` - 分词器
  - `README.md` - 说明文档
- **状态**: ✅ 存在

### Qwen3-TTS/
- **路径**: `d:\TokusCode\bbb_assistant\Qwen3-TTS\`
- **功能**: Qwen3-TTS语音合成模型
- **状态**: ❌ 缺失

---

## 资源目录分析

### voice_resources/
- **路径**: `d:\TokusCode\bbb_assistant\voice_resources\`
- **功能**: 统一声音资源管理系统
- **角色目录**:
  | 角色 | 状态 | 文件 |
  |------|------|------|
  | elysia (爱莉希雅) | ✅ 完整 | reference.wav, reference.txt, metadata.json |
  | kiana (琪亚娜) | ⚠️ 待收集 | metadata.json |
  | mei (雷电芽衣) | ⚠️ 待收集 | metadata.json |
  | bronya (布洛妮娅) | ⚠️ 待收集 | metadata.json |
  | seele (希儿) | ⚠️ 待收集 | metadata.json |
  | theresa (德丽莎) | ⚠️ 待收集 | metadata.json |
  | fu_hua (符华) | ⚠️ 待收集 | metadata.json |

### outputs/
- **路径**: `d:\TokusCode\bbb_assistant\outputs\`
- **功能**: 程序输出文件目录
- **子目录**:
  - `asr_transcriptions/` - ASR转录结果
  - `asr_results/` - ASR结果（额外）
  - `asr_validation/` - ASR验证（额外）
  - `tts_audio/` - TTS生成音频
  - `single_test/` - 单次测试输出
  - `test_results/` - 批量测试结果
- **状态**: ✅ 存在且结构完整

### to_clone_test/
- **路径**: `d:\TokusCode\bbb_assistant\to_clone_test\`
- **功能**: 语音克隆测试音频
- **内容**: 
  - 原有25个WAV音频文件
  - **YueXiaShiYue/** 子目录（已整合，48个WAV文件）
- **角色**: 德丽莎、月下誓约、朔夜观星、渡尘之羽、识之律者、迷城骇兔、琪亚娜
- **状态**: ✅ 已整合完成

### data/
- **路径**: `d:\TokusCode\bbb_assistant\data\`
- **功能**: 数据存储目录（已从backend/data/移动）
- **子目录**:
  - `图鉴/` - 游戏图鉴数据
    - `人偶/`、`协同者/`、`圣痕/`、`女武神/`、`敌人/`、`材料/`、`武器/`
  - `chroma_db/` - ChromaDB向量数据库（预期）
  - `rag_index/` - RAG索引存储
- **状态**: ✅ 已整改完成

---

## 共享代码分析 (shared/)

### 目录结构
```
shared/
├── types/
│   └── index.ts         # TypeScript类型定义
└── protocol/
    └── api.ts           # API接口类型
```

### 文件详情

#### types/index.ts
- **路径**: `shared/types/index.ts`
- **功能**: 共享TypeScript类型定义
- **状态**: ✅ 存在

#### protocol/api.ts
- **路径**: `shared/protocol/api.ts`
- **功能**: API接口类型定义
- **状态**: ✅ 存在

---

## 构建脚本分析 (scripts/)

### 目录结构
```
scripts/
├── build.js             # 构建脚本
├── dev.js               # 开发脚本
└── package.js           # 打包脚本
```

### 文件详情

#### build.js
- **路径**: `scripts/build.js`
- **功能**: 项目构建脚本
- **状态**: ✅ 存在

#### dev.js
- **路径**: `scripts/dev.js`
- **功能**: 开发环境启动脚本
- **状态**: ✅ 存在

#### package.js
- **路径**: `scripts/package.js`
- **功能**: 应用打包脚本
- **状态**: ✅ 存在

---

## 结构偏差汇总

### 缺失项目

| 项目 | 类型 | 优先级 | 说明 |
|------|------|--------|------|
| Qwen3-TTS/ | 目录 | 中 | TTS模型目录 |
| docs/ | 目录 | 低 | 项目文档目录 |
| .github/ | 目录 | 低 | GitHub工作流 |
| pyproject.toml | 文件 | 低 | Poetry配置 |
| src/modules/memory/ | 目录 | 高 | 对话记忆模块 |
| src/models/ | 目录 | 中 | 数据模型 |
| src/types/ (前端) | 目录 | 低 | TypeScript类型 |

### 已整改项目

| 项目 | 原状态 | 整改后状态 | 整改说明 |
|------|--------|------------|----------|
| YueXiaShiYue/ | 额外目录 | ✅ 已整合 | 移动到 `to_clone_test/YueXiaShiYue/` |
| backend/data/ | 位置偏差 | ✅ 已整改 | 移动到根目录 `data/` |
| Qdrant | 向量数据库 | ✅ 已替换 | 切换为ChromaDB |

### 额外项目

| 项目 | 类型 | 建议 |
|------|------|------|
| ASR_TTS_test.txt | 文件 | 移动到 `docs/` 或删除 |
| FunASR2.0.txt | 文件 | 移动到 `docs/` 或删除 |
| backend/src/utils/ | 目录 | 保留（已实现） |
| backend/src/api/rag.py | 文件 | 保留（已实现） |

---

## 整改建议

### 高优先级

1. **实现对话记忆模块**
   - 创建 `backend/src/modules/memory/` 目录
   - 实现记忆存储、检索、管理功能
   - 集成到 `chat_service.py`

2. **创建数据模型目录**
   - 创建 `backend/src/models/` 目录
   - 定义SQLAlchemy模型
   - 实现数据库迁移

### 中优先级

3. **创建Qwen3-TTS模型目录**
   - 下载或创建 `Qwen3-TTS/` 目录结构
   - 配置模型权重和配置文件

4. **完善前端类型定义**
   - 创建 `frontend/src/types/` 目录
   - 定义组件Props和API响应类型

5. **整理测试文件**
   - 删除或移动根目录的测试文本文件

### 低优先级

6. **创建文档目录**
   - 创建 `docs/` 目录
   - 迁移API文档和开发指南

7. **创建GitHub工作流**
   - 创建 `.github/workflows/` 目录
   - 配置CI/CD流程

8. **添加Poetry配置**
   - 创建 `pyproject.toml`
   - 配置Python项目元数据

---

## 附录：依赖关系图

### 前端依赖关系
```
frontend/
├── Vue 3.4.21
├── Pinia 2.1.7 (状态管理)
├── Vue Router 4.2.5
├── Axios 1.6.8 (HTTP)
├── Tailwind CSS 3.4.1
├── Electron 28.2.0
├── Vite 5.1.0 (构建)
└── TypeScript 5.3.3
```

### 后端依赖关系
```
backend/
├── FastAPI 0.104.0+ (Web框架)
├── Uvicorn 0.24.0+ (ASGI)
├── Pydantic 2.5.0+ (验证)
├── SQLAlchemy 2.0.0+ (ORM)
├── Loguru 0.7.0+ (日志)
├── FunASR (ASR)
├── Ultralytics 8.0.0+ (YOLO)
├── PaddleOCR 2.7.0+ (OCR)
├── LangChain 0.0.300+ (AI框架)
├── ChromaDB 0.4.0+ (向量DB)
├── Playwright 1.40.0+ (爬虫)
└── MSS 9.0.0+ (屏幕捕获)
```

---

## 变更历史

| 日期 | 变更内容 |
|------|----------|
| 2026-03-24 | 初始分析报告生成 |
| 2026-03-24 | 整合 YueXiaShiYue/ 到 to_clone_test/ |
| 2026-03-24 | 移动 backend/data/ 到根目录 data/ |
| 2026-03-24 | RAG向量数据库从Qdrant切换为ChromaDB |

---

*报告更新完毕*
