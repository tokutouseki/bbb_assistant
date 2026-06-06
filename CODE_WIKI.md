# 崩坏3专属AI陪伴助手 - Code Wiki

## 1. 项目概述

### 1.1 项目简介

**项目名称**：bbb_assistant（崩坏3专属AI陪伴助手）

**项目类型**：跨平台桌面端AI应用

**核心功能**：为崩坏3玩家提供沉浸式多模态AI陪伴助手，支持语音/文字双模交互、角色原声语音合成、RAG知识库检索、游戏场景感知等功能。

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Electron + TypeScript + Vite |
| 后端框架 | FastAPI + Python 3.10+ |
| AI模型 | YOLO11n、PaddleOCR、SenseVoiceSmall、Qwen3-TTS、VoxCPM |
| LLM集成 | DeepSeek API、Kimi API、LM Studio、Ollama |
| 知识库 | LangChain + ChromaDB + Sentence Transformers |
| 数据库 | SQLite + ChromaDB（向量数据库） |

## 2. 项目架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Electron + Vue3)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   聊天界面   │  │  实时语音   │  │  Live2D看板 │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/WebSocket
┌────────────────────────────┴────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  ┌──────────────────────────────────────────────────┐        │
│  │              API路由层 (api/)                     │        │
│  │  chat | vision | audio | memory | rag | live2d  │        │
│  └──────────────────────────────────────────────────┘        │
│  ┌──────────────────────────────────────────────────┐        │
│  │              核心模块层 (modules/)                 │        │
│  │  agent | audio | vision | llm | rag | crawler   │        │
│  │  keyboard | live2d_control | skill | web_search │        │
│  └──────────────────────────────────────────────────┘        │
│  ┌──────────────────────────────────────────────────┐        │
│  │              业务服务层 (services/)               │        │
│  │           chat_service | game_monitor            │        │
│  └──────────────────────────────────────────────────┘        │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ AI模型  │         │ 知识库  │         │ 游戏窗口 │
   │ YOLO    │         │ ChromaDB│         │ 自动化   │
   │ ASR/TTS │         │ RAG索引 │         │ 操作    │
   └─────────┘         └─────────┘         └─────────┘
```

### 2.2 模块职责划分

| 模块目录 | 职责 | 核心功能 |
|---------|------|---------|
| `api/` | RESTful API接口 | 提供聊天、视觉、音频、记忆、RAG等HTTP接口 |
| `modules/agent/` | AI Agent核心 | ReAct Agent执行框架，集成RAG+YOLO+工具 |
| `modules/audio/` | 音频处理 | ASR语音识别、TTS语音合成、语音克隆 |
| `modules/vision/` | 视觉感知 | YOLO目标检测、OCR文字识别、屏幕捕获 |
| `modules/llm/` | LLM路由 | 多模型智能路由选择（DeepSeek/LM Studio/Ollama） |
| `modules/rag/` | 知识检索 | 向量知识库管理、混合检索（RAG核心） |
| `modules/crawler/` | 网页爬虫 | 崩坏3Wiki数据爬取 |
| `modules/live2d_control/` | Live2D控制 | 看板娘模型管理、表情/动作控制 |
| `modules/skill/` | 技能管理 | 技能注册与执行 |
| `modules/web_search/` | 联网搜索 | DuckDuckGo/百度搜索 |
| `modules/hongkai/` | 游戏自动化 | 崩坏3游戏自动化操作脚本 |
| `modules/keyboard/` | 键盘控制 | 模拟键盘输入 |
| `services/` | 业务服务 | 聊天服务、游戏监控服务 |

## 3. 目录结构

```
bbb_assistant/
├── frontend/                          # Electron + Vue3 前端
│   ├── electron/                     # Electron 主进程
│   ├── src/                         # Vue3 源码
│   │   ├── components/              # Vue 组件
│   │   ├── views/                  # 页面视图
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── api/                    # API 调用封装
│   │   └── utils/                  # 工具函数
│   ├── package.json                 # 前端依赖
│   └── vite.config.js              # Vite 配置
│
├── backend/                          # Python FastAPI 后端
│   ├── src/
│   │   ├── main.py                 # 应用入口
│   │   ├── api/                    # API 路由
│   │   │   ├── chat.py             # 聊天接口
│   │   │   ├── vision.py           # 视觉接口
│   │   │   ├── audio.py            # 音频接口
│   │   │   ├── memory.py           # 记忆接口
│   │   │   ├── rag.py              # RAG接口
│   │   │   ├── health.py           # 健康检查
│   │   │   ├── settings.py         # 设置接口
│   │   │   └── live2d.py           # Live2D接口
│   │   ├── config/                 # 配置管理
│   │   │   ├── settings.py         # Pydantic Settings
│   │   │   ├── game_scenes.py      # 游戏场景配置
│   │   │   ├── runtime_settings.py # 运行时配置
│   │   │   ├── honkai_voices.json  # 角色语音配置
│   │   │   └── cancel_signal.py    # 取消信号
│   │   ├── modules/                # 核心模块
│   │   │   ├── agent/              # Agent模块
│   │   │   ├── audio/              # 音频模块
│   │   │   ├── vision/             # 视觉模块
│   │   │   ├── llm/                # LLM模块
│   │   │   ├── rag/                # RAG模块
│   │   │   ├── crawler/            # 爬虫模块
│   │   │   ├── live2d_control/     # Live2D模块
│   │   │   ├── skill/              # 技能模块
│   │   │   ├── web_search/         # 搜索模块
│   │   │   ├── hongkai/            # 游戏自动化
│   │   │   ├── keyboard/           # 键盘控制
│   │   │   └── tool_integration.py # 工具集成
│   │   ├── services/               # 业务服务
│   │   │   ├── chat_service.py     # 聊天服务
│   │   │   ├── game_monitor.py    # 游戏监控
│   │   │   └── background_tasks.py # 后台任务
│   │   └── utils/                  # 工具函数
│   ├── data/                       # 运行时数据
│   │   ├── models/                 # AI模型文件
│   │   │   ├── detect/             # YOLO检测模型
│   │   │   └── classification/     # YOLO分类模型
│   │   ├── rag_index/              # RAG索引
│   │   └── chroma_db/              # ChromaDB数据
│   ├── scripts/                    # 工具脚本
│   └── requirements.txt            # 后端依赖
│
├── data/                            # 游戏数据
│   ├── 图鉴/                       # 游戏图鉴数据
│   │   ├── 女武神/                 # 角色数据
│   │   ├── 武器/                   # 武器数据
│   │   ├── 圣痕/                   # 圣痕数据
│   │   ├── 人偶/                   # 人偶数据
│   │   ├── 协同者/                 # 协同者数据
│   │   ├── 材料/                   # 材料数据
│   │   └── 敌人/                   # 敌人数据
│
├── FunASR/                          # 音频识别模块
├── voice_resources/                 # 角色参考音频
├── SenseVoiceSmall/                # ASR模型
├── VoxCPM-0.5B/                    # TTS克隆模型
├── Qwen3-TTS/                      # TTS合成模型
├── package.json                     # 根目录npm配置
├── .env.example                     # 环境变量模板
└── README.md                        # 项目说明
```

## 4. 核心模块详解

### 4.1 API层

#### 4.1.1 聊天接口 (`api/chat.py`)

**主要功能**：
- 提供聊天补全接口，集成ReAct Agent执行框架
- 支持流式输出（SSE）
- 支持音频自动转写
- 支持多模态输入（文字+图片+音频）

**核心端点**：

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/` | 聊天补全（非流式） |
| POST | `/stream` | SSE流式聊天 |
| POST | `/cancel` | 取消请求 |
| POST | `/clear` | 清除对话上下文 |
| GET | `/runtime-status` | LLM运行时状态 |
| POST | `/react-agent` | 直接运行ReAct Agent |

**核心函数**：

```python
# 聊天补全主函数
async def chat_completion(request: ChatRequest) -> ChatResponse
    - 接收消息列表，返回AI回复
    - 支持RAG知识库检索
    - 返回处理时间和思考步骤

# 流式聊天
async def chat_stream(request: ChatRequest) -> StreamingResponse
    - 使用SSE协议流式推送中间结果
    - 实时推送Agent执行步骤

# 取消请求
async def cancel_chat(req: CancelRequest)
    - 根据request_id取消正在执行的请求
```

### 4.2 Agent模块 (`modules/agent/`)

#### 4.2.1 ReAct Agent (`react_agent.py`)

**核心类**：`ReActGameAgent`

**主要功能**：
- 集成LangChain ReAct Agent框架
- 接入RAG+YOLO+多种工具
- 支持多轮对话记忆
- 支持分阶段技能执行

**核心属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `rag_engine` | RAGEngine | RAG引擎实例 |
| `yolo_manager` | YOLOModelManager | YOLO模型管理器 |
| `_memory` | ConversationBufferMemory | 对话记忆 |
| `_agent` | AgentExecutor | LangChain Agent执行器 |

**核心方法**：

```python
class ReActGameAgent:
    def __init__(self)
        # 初始化Agent，配置RAG引擎、YOLO管理器、对话记忆

    def run(self, user_input: str, max_retries: int = 2, 
            request_id: str = "", images: Optional[List[str]] = None) -> Dict[str, Any]
        # 非流式执行Agent
        # 参数：
        #   - user_input: 用户输入
        #   - max_retries: 最大重试次数
        #   - request_id: 请求ID（用于取消）
        #   - images: 用户上传的图片列表
        # 返回：包含output、steps、errors的结果字典

    def run_streaming(self, user_input: str, request_id: str, 
                      event_queue: queue.Queue, ...) -> Dict[str, Any]
        # 流式执行Agent，实时推送中间步骤

    def run_phased(self, skill_name: str, user_input: str, ...) -> Dict[str, Any]
        # 分阶段执行技能（用于复杂任务）

    def clear_context(self) -> Dict[str, Any]
        # 清除对话上下文，重置记忆

    def _build_agent(self) -> AgentExecutor
        # 构建LangChain Agent，包含所有可用工具
```

**可用工具**（Tools）：

| 工具名称 | 功能描述 |
|---------|---------|
| `rag_search` | 检索本地RAG知识库 |
| `list_skills` | 列出所有可用技能 |
| `view_skill` | 查看技能详细说明 |
| `yolo_list_models` | 列出YOLO模型 |
| `yolo_load_model` | 加载YOLO模型 |
| `yolo_detect_image` | 屏幕目标检测 |
| `yolo_classify_image` | 场景分类 |
| `ocr_recognize` | OCR文字识别 |
| `focus_bh3_window` | 聚焦游戏窗口 |
| `click_coordinates` | 模拟鼠标点击 |
| `tts_qwen3` | Qwen3-TTS语音合成 |
| `tts_voxcpm` | VoxCPM语音克隆 |
| `play_audio` | 播放音频 |
| `web_search` | 联网搜索 |
| `fetch_page` | 获取网页内容 |
| `run_hongkai_task` | 执行游戏自动化任务 |
| `find_direction` | 游戏场景定位 |
| `navigate_to` | 导航到目标场景 |
| `live2d_control` | 控制Live2D模型 |
| `describe_image` | 描述上传图片 |
| `todo_write` | 任务计划管理 |

### 4.3 LLM模块 (`modules/llm/`)

#### 4.3.1 LLM路由器 (`llm_router.py`)

**核心类**：`LLMRouter`

**主要功能**：
- 多模型智能路由选择
- 支持DeepSeek API、Kimi API、LM Studio、Ollama、本地GGUF
- 根据任务类型、成本、延迟自动选择最优模型
- 支持模型fallback机制

**模型类型枚举**：

```python
class ModelType(Enum):
    DEEPSEEK_V3_API = "deepseek_v3_api"  # DeepSeek云端API
    LM_STUDIO = "lm_studio"               # LM Studio本地服务
    LOCAL_GGUF = "local_gguf"            # 本地GGUF模型
    OLLAMA = "ollama"                     # Ollama本地服务
```

**任务类型枚举**：

```python
class TaskType(Enum):
    CASUAL_CHAT = "casual_chat"           # 日常聊天
    GAME_GUIDE = "game_guide"              # 游戏攻略
    COMPLEX_REASONING = "complex_reasoning" # 复杂推理
    CODE_GENERATION = "code_generation"    # 代码生成
    TRANSLATION = "translation"            # 翻译
    SUMMARIZATION = "summarization"        # 摘要
    EMOTIONAL_SUPPORT = "emotional_support" # 情感支持
```

**核心方法**：

```python
class LLMRouter:
    def route_request(
        messages: List[Dict[str, str]],
        task_type: Union[TaskType, str],
        stream: bool = False,
        images: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]
        # 路由请求到合适的模型
        # 自动选择最优模型，支持fallback
        # 返回模型响应

    def select_model(
        task_context: TaskContext,
        available_models: Optional[List[str]] = None
    ) -> Optional[ModelInfo]
        # 根据任务上下文选择模型
        # 考虑优先级、成本、延迟、用户偏好

    def get_model_stats() -> Dict[str, Any]
        # 获取模型使用统计
```

### 4.4 RAG模块 (`modules/rag/`)

#### 4.4.1 RAG引擎 (`rag_engine.py`)

**核心类**：`RAGEngine`

**主要功能**：
- 统一RAG检索接口
- 支持快速检索、精确检索、混合检索三种模式
- 自动索引知识库数据
- 管理向量存储和索引

**检索模式**：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `FAST` | 向量相似度检索 | 语义搜索 |
| `PRECISE` | 关键词精确匹配 | 精确查询 |
| `HYBRID` | RRF混合检索 | 综合搜索（默认） |

**核心方法**：

```python
class RAGEngine:
    async def initialize() -> bool
        # 初始化RAG引擎组件
        # 包括：嵌入服务、向量存储、索引管理器

    async def search(
        query: str,
        mode: Optional[SearchMode] = None,
        category: Optional[str] = None,
        top_k: Optional[int] = None,
        score_threshold: float = 0.0
    ) -> List[UnifiedSearchResult]
        # 搜索知识库
        # 返回相关性排序的搜索结果

    async def retrieve(
        query: str,
        mode: Optional[SearchMode] = None,
        ...
    ) -> str
        # 检索并生成格式化上下文文本

    async def index_knowledge_base(
        category: Optional[str] = None,
        batch_size: int = 100,
        force_reindex: bool = False
    ) -> Dict[str, Any]
        # 索引知识库数据
        # 构建向量索引和关键词索引

    async def add_document(
        name: str,
        content: str,
        category: str,
        ...
    ) -> str
        # 添加单个文档到知识库
```

#### 4.4.2 统一检索器 (`retriever.py`)

**核心类**：`Retriever`

**主要功能**：
- 封装快速检索和精确检索
- 实现RRF（Reciprocal Rank Fusion）混合检索
- 名称匹配加权优化

**RRF混合检索算法**：

```
RRF_score = Σ(1 / (k + rank))
- k = 60（行业标准）
- rank = 结果在各自列表中的排名
- 名称精确匹配额外加权 +0.5
- 名称部分匹配额外加权 +0.15
```

### 4.5 音频模块 (`modules/audio/`)

#### 4.5.1 ASR语音识别 (`asr_processor.py`)

**核心类**：`ASRProcessor`

**主要功能**：
- 基于SenseVoiceSmall的语音识别
- 支持50+语言识别
- 支持情感检测

**核心方法**：

```python
class ASRProcessor:
    def transcribe_file(file_path: str, language: str = "zh") -> ASRResult
        # 转写音频文件
        # 返回：文本内容、置信度、处理时间

    def transcribe_audio(audio_data: np.ndarray, sample_rate: int) -> ASRResult
        # 转写音频数据
```

#### 4.5.2 TTS语音合成

**Qwen3-TTS** (`qwen3_tts_generator.py`)：
- 多语言音色设计
- 支持爱莉希雅、琪亚娜、芽衣等多种声音风格
- 基于自然语言描述自定义声音

**VoxCPM** (`tts_generator.py`)：
- 零样本语音克隆
- 基于参考音频生成相似语音
- 支持崩坏3角色原声

### 4.6 视觉模块 (`modules/vision/`)

#### 4.6.1 YOLO模型管理 (`yolo_model_manager.py`)

**核心类**：`YOLOModelManager`（单例模式）

**主要功能**：
- 动态加载/卸载YOLO模型
- 支持检测模型和分类模型
- 多模型并行检测
- 模型缓存管理

**模型类型**：

| 类型 | 示例 | 功能 |
|------|------|------|
| 检测模型 | `yolo11n_attack_ui_det.onnx` | 识别UI元素位置 |
| 分类模型 | `yolo11n_scene_cls.onnx` | 识别游戏场景 |

**核心方法**：

```python
class YOLOModelManager:
    @staticmethod
    def get_instance() -> YOLOModelManager
        # 获取单例实例

    def load_model(model_name: str, device: str = "cpu") -> Dict[str, Any]
        # 加载YOLO模型到内存
        # device: cpu/cuda:0

    def unload_model(model_name: str) -> Dict[str, Any]
        # 卸载模型释放内存

    def detect(
        image: np.ndarray,
        model_name: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45
    ) -> Dict[str, Any]
        # 目标检测
        # 返回检测结果列表

    def classify(
        image: np.ndarray,
        model_name: str
    ) -> Dict[str, Any]
        # 图像分类
        # 返回预测结果（Top1/Top5）

    def parallel_detect(
        image: np.ndarray,
        model_names: List[str],
        ...
    ) -> Dict[str, Any]
        # 多模型并行检测
```

#### 4.6.2 OCR文字识别 (`ocr_processor.py`)

**核心类**：`OCRProcessor`

**主要功能**：
- 基于RapidOCR的OCR识别
- 支持中英文混合识别
- 返回文字内容和位置

### 4.7 游戏自动化模块 (`modules/hongkai/`)

#### 4.7.1 功能概述

提供崩坏3游戏自动化操作能力，包括：
- 每日任务（登录领取、出击减负）
- 往世乐土周常
- 记忆战场减负
- 模拟作战室减负
- 舰团贡献
- 冒险委托

#### 4.7.2 核心组件

| 组件 | 功能 |
|------|------|
| `scripts/` | 自动化任务脚本 |
| `character/` | 角色操作脚本 |
| `ocr/` | 游戏内文字识别 |
| `templates/` | UI模板图片 |
| `bh3_yolo_recognizer.py` | YOLO识别封装 |

## 5. 配置管理

### 5.1 环境变量配置 (`.env.example`)

```bash
# 应用基础配置
APP_NAME="崩坏3专属AI陪伴助手"
APP_VERSION="0.1.0"
ENVIRONMENT="development"

# 服务器配置
HOST="0.0.0.0"
PORT=8000

# AI模型配置
ASR_MODEL_PATH="D:/TokusCode/models/SenseVoiceSmall"
VOXCPM_MODEL_PATH="D:/TokusCode/models/VoxCPM-0.5B"
QWEN3_TTS_MODEL_PATH="D:/TokusCode/models/Qwen3-TTS"

# LLM配置
LLM_PROVIDER="deepseek"
DEEPSEEK_API_KEY="your-api-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"

# LM Studio / Ollama
LM_STUDIO_BASE_URL="http://127.0.0.1:1234"
OLLAMA_BASE_URL="http://127.0.0.1:11434"

# RAG配置
RAG_ENABLED=true
KNOWLEDGE_BASE_PATH="./data"
VECTOR_STORE_PATH="./data/rag_index"
EMBEDDING_MODEL="paraphrase-multilingual-MiniLM-L12-v2"

# 游戏监控
ENABLE_GAME_MONITOR=true
GAME_WINDOW_TITLE="崩坏3"
```

### 5.2 配置管理类 (`config/settings.py`)

**核心类**：`Settings`（Pydantic BaseSettings）

**特性**：
- 环境变量自动注入
- 类型验证和转换
- 单例模式访问
- 动态重载支持

## 6. 依赖关系

### 6.1 Python后端依赖

```
# Web框架
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0

# 数据验证
pydantic>=2.5.0
pydantic-settings>=2.0.0

# 数据库
sqlalchemy>=2.0.0

# AI/ML
torch>=2.0.0
ultralytics>=8.0.0          # YOLO11n
rapidocr-onnxruntime>=1.3.0  # OCR
funasr>=1.0.0                # ASR
langchain-core>=0.2.0
sentence-transformers>=2.2.0
chromadb>=0.4.0

# 本地LLM
llama-cpp-python>=0.2.0

# 爬虫
beautifulsoup4>=4.12.0
playwright>=1.40.0
```

### 6.2 Node.js前端依赖

```
# 核心框架
vue@^3.4.21
vue-router@^4.2.5
pinia@^2.1.7

# Electron
electron@^28.2.0

# 构建工具
vite@^5.1.0
typescript@~5.3.3

# UI
tailwindcss@^3.4.1
@iconify/vue@^4.1.2
```

## 7. 运行方式

### 7.1 开发环境启动

```bash
# 1. 安装所有依赖
pnpm install:all

# 2. 配置环境变量
cp .env.example .env
# 编辑.env配置API密钥等

# 3. 启动开发服务器（前后端同时启动）
pnpm dev

# 单独启动前端
pnpm dev:frontend

# 单独启动后端
pnpm dev:backend
```

### 7.2 后端直接启动

```bash
cd backend
python src/main.py
```

启动参数检查：
- Python版本 ≥ 3.10
- 管理员权限（用于窗口聚焦）
- 依赖完整性检查

### 7.3 前端开发

```bash
cd frontend
pnpm dev
```

Vite开发服务器默认运行在 `http://localhost:5173`

### 7.4 生产构建

```bash
# 构建所有项目
pnpm build

# 构建前端
pnpm build:frontend

# 打包桌面应用
pnpm package
```

### 7.5 代码质量检查

```bash
# 代码检查
pnpm lint

# 代码格式化
pnpm format

# 运行测试
pnpm test
```

## 8. 数据流程

### 8.1 聊天请求处理流程

```
用户输入
    │
    ▼
┌─────────────────────┐
│   API路由 (chat.py)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ReAct Agent执行     │
│  (react_agent.py)   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │            │
     ▼            ▼
┌─────────┐  ┌──────────┐
│ RAG检索 │  │ 工具调用 │
└─────────┘  └──────────┘
     │            │
     └─────┬──────┘
           │
           ▼
┌─────────────────────┐
│   LLM路由选择       │
│  (llm_router.py)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   模型响应生成       │
│  DeepSeek/LM Studio │
└──────────┬──────────┘
           │
           ▼
返回响应给用户
```

### 8.2 RAG检索流程

```
用户查询
    │
    ▼
┌─────────────────────┐
│  查询向量化          │
│  (embedding.py)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  混合检索 (RRF)     │
│  (retriever.py)     │
│  ├─ 向量相似度      │
│  └─ 关键词匹配      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  结果排序和过滤     │
│  名称匹配加权       │
└──────────┬──────────┘
           │
           ▼
返回Top-K检索结果
```

## 9. API接口文档

### 9.1 聊天接口 `/api/chat/`

#### POST / - 聊天补全

**请求体**：

```json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "request_id": "optional-request-id",
  "game_scene": "home",
  "use_rag": true,
  "stream": false,
  "show_thinking": true,
  "images": ["data:image/png;base64,..."],
  "audios": ["data:audio/webm;base64,..."]
}
```

**响应**：

```json
{
  "message": {
    "role": "assistant",
    "content": "你好！有什么可以帮你？",
    "timestamp": 1234567890
  },
  "processing_time": 1.5,
  "tool_steps": [...],
  "thinking_steps": [...]
}
```

### 9.2 视觉接口 `/api/vision/`

#### POST /detect - 目标检测

**请求**：上传图片文件

**参数**：
- `confidence_threshold`: 置信度阈值（默认0.5）
- `model_name`: 模型名称（默认yolo11n）
- `iou_threshold`: IOU阈值（默认0.45）

**响应**：

```json
[
  {
    "label": "attack_button",
    "confidence": 0.95,
    "bbox": [100, 200, 150, 250],
    "class_id": 0
  }
]
```

### 9.3 音频接口 `/api/audio/`

#### POST /asr - 语音识别

**请求**：上传音频文件

**参数**：
- `language`: 语言代码（默认zh）
- `audio_format`: 音频格式（默认wav）

#### POST /tts - 语音合成

**请求体**：

```json
{
  "text": "你好",
  "voice_id": "爱莉希雅",
  "tts_engine": "qwen3",
  "language": "Chinese"
}
```

**响应**：

```json
{
  "audio_base64": "...",
  "format": "wav",
  "sample_rate": 24000,
  "tts_engine": "qwen3"
}
```

### 9.4 RAG接口 `/api/rag/`

#### POST /search - 知识检索

**请求体**：

```json
{
  "query": "炽翎怎么配装",
  "mode": "hybrid",
  "top_k": 5
}
```

#### GET /stats - 知识库统计

## 10. 数据库结构

### 10.1 SQLite数据库

**路径**：`./data/bbb_assistant.db`

**主要表**：
- `conversations`: 对话历史
- `memories`: 用户记忆
- `settings`: 用户设置

### 10.2 ChromaDB向量数据库

**路径**：`./data/chroma_db`

**集合**：
- `bbb_knowledge`: 游戏知识库向量

**文档结构**：

```json
{
  "id": "unique-document-id",
  "name": "文档名称",
  "content": "文档内容",
  "category": "女武神",
  "subcategory": "属性",
  "source_file": "原数据文件",
  "metadata": {...}
}
```

## 11. 常见问题

### 11.1 依赖安装失败

```bash
# 确保Python版本 ≥ 3.10
python --version

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 11.2 模型加载失败

- 检查模型路径配置是否正确
- 确保模型文件存在
- GPU版本需要CUDA环境

### 11.3 API连接失败

- 检查后端服务是否启动
- 确认端口配置一致
- 查看CORS配置

### 11.4 游戏窗口聚焦失败

- 需要以管理员权限运行程序
- 检查游戏窗口标题配置

## 12. 扩展开发指南

### 12.1 添加新工具

1. 在 `react_agent.py` 的 `_build_agent` 方法中定义新工具
2. 使用 `@tool` 装饰器
3. 添加工具说明和参数描述

```python
@tool
def my_new_tool(param: str = "") -> str:
    """工具说明"""
    # 工具实现
    return result
```

### 12.2 添加新技能

1. 在 `modules/skill/` 目录创建技能文件
2. 使用 `SkillManager` 注册技能
3. 定义技能触发词和执行内容

### 12.3 添加新模型

1. 在 `modules/llm/` 创建模型客户端
2. 在 `LLMRouter` 中注册模型
3. 配置模型类型和能力

---

**文档版本**：1.0  
**最后更新**：2026-05-24  
**维护者**：bbb_assistant开发团队
