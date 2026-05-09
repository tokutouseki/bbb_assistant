# 崩坏3专属AI陪伴助手（桌面端）

<div align="center">

![Vue3](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vue.js)
![Electron](https://img.shields.io/badge/Electron-28.2-47848F?logo=electron)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi)
![YOLO](https://img.shields.io/badge/YOLO-11n-00BFFF?logo=yolo)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

专为**崩坏3**玩家打造的沉浸式多模态 AI 陪伴助手桌面应用。实时感知游戏场景，支持语音/文字双模交互，以崩坏3角色原声进行智能应答，集成 RAG 知识库提供精准攻略，自动留存专属对话记忆。

---

## ✨ 核心特性

| 模块 | 能力 |
|------|------|
| 🎮 **视觉感知** | 基于 YOLO11n 实时识别崩坏3游戏场景（主界面/战斗/关卡/抽卡/任务/角色装备等），PaddleOCR 提取屏幕文字信息 |
| 🗣️ **双模交互** | 文字输入 + SenseVoiceSmall ASR 语音识别，支持全双工实时对话 |
| 🔊 **角色原声** | 双引擎 TTS（Qwen3-TTS / VoxCPM-0.5B），7位崩坏3角色原声语音合成 |
| 🧠 **智能决策** | 集成 DeepSeek / Kimi API + LM Studio 本地推理 + Ollama，融合场景感知+RAG知识库+用户记忆进行智能应答 |
| 📚 **知识记忆** | RAG 向量知识库（ChromaDB + Sentence Transformers）+ 用户专属对话记忆 |
| 🖥️ **桌面载体** | Electron + Vue3 桌面应用，支持悬浮窗、系统托盘、游戏覆盖层 |

---

## 🏗️ 项目架构

```
bbb_assistant/
├── frontend/                    # Electron + Vue3 前端
│   ├── electron/                # Electron 主进程、IPC 通信
│   ├── src/                     # Vue3 源码（路由、状态管理、视图）
│   └── vite.config.js           # Vite 构建配置
├── backend/                     # Python FastAPI 后端
│   └── src/
│       ├── api/                 # RESTful API 路由（chat/vision/audio/rag/memory）
│       ├── modules/             # 核心模块（vision/audio/llm/rag/agent/crawler）
│       ├── services/            # 业务服务（chat/game_monitor）
│       └── config/              # 配置管理（Pydantic Settings）
├── shared/                      # 前后端共享类型与协议
├── voice_resources/             # 7位角色参考音频
├── SenseVoiceSmall/             # ASR 语音识别模型
├── VoxCPM-0.5B/                 # TTS 语音克隆模型
├── Qwen3-TTS/                   # TTS 多语言语音合成模型
└── data/                        # 运行时数据（模型、知识库、日志）
```

---

## 🚀 快速开始

### 环境要求

| 工具 | 版本要求 | 说明 |
|------|----------|------|
| Node.js | ≥ 18.0 | 推荐使用 nvm / fnm 管理 |
| pnpm | ≥ 8.0 | 前端包管理器 |
| Python | 3.10+ | 推荐使用 conda / pyenv / uv 管理 |
| Git | 最新版 | 版本控制 |
| GPU（建议） | NVIDIA CUDA | 本地 LLM / TTS 推理加速 |

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/your-username/bbb-assistant.git
cd bbb-assistant

# 2. 一键安装所有依赖（前端 + 后端）
pnpm install:all
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，按需配置以下核心项：
#   - DEEPSEEK_API_KEY      DeepSeek API 密钥
#   - KIMI_API_KEY          Kimi API 密钥（可选）
#   - LM_STUDIO_BASE_URL    LM Studio 本地推理地址（默认 http://localhost:1234）
#   - TTS_DEFAULT_CHARACTER 默认角色语音（默认 elysia）
```

完整配置项说明请参考 [.env.example](./.env.example)。

### 启动开发环境

```bash
# 同时启动前端（Vite :5173）和后端（Uvicorn :8000）
pnpm dev

# 或分别启动
pnpm dev:frontend   # 仅启动前端
pnpm dev:backend    # 仅启动后端
```

### 模型准备

项目依赖以下 AI 模型（需单独下载放置到对应目录）：

| 模型 | 目录 | 用途 |
|------|------|------|
| YOLO11n | `data/models/` | 游戏场景目标检测 |
| PaddleOCR | `data/models/ocr/` | 屏幕文字识别 |
| SenseVoiceSmall | `SenseVoiceSmall/` | ASR 语音识别 |
| VoxCPM-0.5B | `VoxCPM-0.5B/` | TTS 零样本语音克隆 |
| Qwen3-TTS | `Qwen3-TTS/` | TTS 多语言音色合成 |

---

## 🎮 功能模块详解

### 1. 视觉感知
- YOLO11n 实时检测崩坏3游戏场景，覆盖 **主界面 / 战斗 / 关卡选择 / 抽卡 / 任务活动 / 角色装备** 等场景
- PaddleOCR 提取游戏内文字信息（任务名称、关卡进度、道具说明等）
- 支持多模型并行检测与动态加载/卸载

### 2. 交互输入
- 双模式输入：键盘文字 | 语音识别（SenseVoiceSmall，支持50+语言与情感检测）
- FunASR 框架支持离线/流式/全双工三种 ASR 模式

### 3. 智能应答
- 双引擎 TTS：**Qwen3-TTS**（多语言音色设计）+ **VoxCPM-0.5B**（零样本语音克隆）
- 7位崩坏3角色原声：爱莉希雅 / 琪亚娜 / 雷电芽衣 / 布洛妮娅 / 希儿 / 德丽莎 / 符华
- 情感化应答，文字与语音同步输出

### 4. 智能决策
- 多源 LLM 集成：**DeepSeek V3** / **Kimi** 云端 API + **LM Studio** (Qwen3.5-4B) 本地推理 + Ollama
- ReAct Agent 框架：感知→推理→行动→观察循环
- 融合场景上下文 + RAG 知识检索 + 对话记忆 + 联网搜索（DuckDuckGo / 米游社）

### 5. 知识记忆
- RAG 向量知识库：ChromaDB 存储 + Sentence Transformers 嵌入
- 三种检索模式：**快速匹配** / **精确搜索** / **混合检索**
- 用户专属对话记忆，个性化偏好学习

### 6. 桌面载体
- 系统托盘驻留，快捷键呼出
- 悬浮窗对话界面 + 游戏透明覆盖层
- 支持 Windows / macOS / Linux 三平台打包

---

## 📡 API 概览

所有 API 挂载在 `/api/` 前缀下，完整文档启动后访问 `http://localhost:8000/docs`。

| 模块 | 路径 | 主要端点 |
|------|------|----------|
| 聊天 | `/api/chat/` | POST 聊天补全（ReAct Agent）、GET 运行时状态 |
| 视觉 | `/api/vision/` | POST 目标检测、OCR、场景分析 |
| 音频 | `/api/audio/` | POST ASR语音转文字、TTS文字转语音、语音克隆 |
| RAG | `/api/rag/` | POST/GET 知识搜索、文档索引、分类管理 |
| 记忆 | `/api/memory/` | POST 存储/查询记忆、用户画像 |
| 健康 | `/api/health/` | GET 服务健康检查、系统资源、详细诊断 |

---

## 🛠️ 技术栈

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API) |
| 桌面端 | Electron 28 |
| 构建 | Vite 5 |
| 语言 | TypeScript 5.3 |
| 状态管理 | Pinia 2 |
| 路由 | Vue Router 4 |
| 样式 | Tailwind CSS 3 |
| 通信 | Axios + WebSocket |
| 打包 | electron-builder 24 |

### 后端

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn + WebSocket |
| AI 模型 | YOLO11n / PaddleOCR / SenseVoiceSmall |
| TTS | Qwen3-TTS (1.7B) / VoxCPM-0.5B |
| LLM | DeepSeek API / Kimi API / LM Studio (Qwen3.5-4B) / Ollama |
| RAG | LangChain + ChromaDB + Sentence Transformers |
| 数据库 | SQLite + ChromaDB (向量) |
| 日志 | Loguru |
| 爬虫 | Playwright + BeautifulSoup4 |

---

## 🔧 开发命令

```bash
# 代码质量
pnpm lint           # 全项目代码检查（ESLint + flake8）
pnpm format         # 全项目代码格式化（Prettier + Black）

# 测试
pnpm test           # 运行所有测试（Vitest + pytest）
pnpm test:frontend  # 仅前端测试
pnpm test:backend   # 仅后端测试

# 构建
pnpm build          # 构建所有项目
pnpm package        # 打包桌面应用（Windows NSIS/macOS DMG/Linux AppImage）
```

---

## 📦 部署打包

```bash
# 构建前端生产版本
pnpm build:frontend

# 打包桌面安装程序
pnpm package
```

输出目录：`frontend/release/`

---

## 🤝 贡献指南

我们欢迎任何形式的贡献！请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解详细的参与方式。

### 贡献流程
1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/amazing-feature`
3. 遵循代码规范（ESLint + Prettier / Black + isort + flake8）
4. 使用 Conventional Commits 格式提交
5. 推送到分支并创建 Pull Request

---

## 📄 许可证

本项目采用 **MIT** 开源许可证。

---

## 🙏 致谢

- [Ultralytics YOLO11](https://github.com/ultralytics/ultralytics) — 目标检测模型
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR 文字识别
- [FunASR](https://github.com/modelscope/FunASR) / [SenseVoiceSmall](https://github.com/FunAudioLLM/SenseVoice) — 语音识别
- [VoxCPM](https://github.com/thuhcsi/VoxCPM) — TTS 零样本语音克隆
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — 多语言音色合成 TTS
- [LangChain](https://github.com/langchain-ai/langchain) — AI 应用框架
- [ChromaDB](https://github.com/chroma-core/chroma) — 向量数据库
- [崩坏3](https://bh3.mihoyo.com/) — 米哈游出品动作游戏

---

*最后更新: 2026-05-09*
