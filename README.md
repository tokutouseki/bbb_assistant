# 崩坏3专属AI陪伴助手 (bbb-assistant)

<div align="center">

![Vue3](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vue.js)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi)
![YOLO](https://img.shields.io/badge/YOLO-11n-00BFFF?logo=yolo)
![Live2D](https://img.shields.io/badge/Live2D-Cubism_SDK_3-FF69B4)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

崩坏3游戏AI陪伴助手，提供**角色扮演对话**、**游戏辅助自动化**、**知识问答**等功能。支持 Live2D 桌宠、TTS 语音克隆、RAG 知识库、YOLO 视觉识别。

---

## 核心特性

| 模块 | 能力 |
|------|------|
| 🎮 **游戏自动化** | YOLO11n 场景识别 + OCR 文字提取 + 键鼠模拟，支持乐土/战场/减负/舰团等一键完成 |
| 🎭 **角色扮演** | 30 位崩坏3角色人格，Live2D 桌宠展示，Qwen3-TTS ICL 语音克隆 (39 种音色) |
| 🧠 **双 Agent 架构** | MainGameAgent (任务执行) + SubCompanionAgent (角色扮演)，ReAct 范式 |
| 📚 **知识记忆** | RAG 向量知识库 (ChromaDB + SentenceTransformers) + 对话记忆 |
| 🖼️ **图片理解** | 多后端自动降级 (Bailian Qwen-VL → PixAI Tagger → LM Studio) |
| 🖥️ **Live2D 桌宠** | PySide6 QOpenGLWidget 透明窗口，鼠标穿透，表情/动作/口型同步 |
| 🔍 **联网搜索** | 百度搜索主引擎 + Playwright 兜底 |

---

## 项目架构

```
bbb_assistant/
├── frontend/src/                 # Vue 3 + Vite 前端
│   ├── views/ChatView.vue        # 聊天主界面 (SSE流式、图片上传、Markdown)
│   ├── views/SettingsView.vue    # 设置界面 (LLM/图片描述/Live2D/角色选择)
│   └── stores/                   # Pinia 状态管理 (chat/settings)
├── backend/src/                  # Python FastAPI 后端
│   ├── api/                      # RESTful API (chat/settings)
│   ├── modules/
│   │   ├── agent/react_agent.py  # 双Agent架构 (MainGameAgent + SubCompanionAgent)
│   │   ├── character/            # 角色人格管理 (30个SKILL.md加载/缓存)
│   │   ├── vision/               # 视觉 (YOLO/OCR/屏幕截图/图片描述)
│   │   ├── audio/                # TTS (Qwen3-TTS / VoxCPM) + ASR (FunASR)
│   │   ├── live2d_control/       # Live2D桌宠 (Qt OpenGL + TCP服务)
│   │   ├── hongkai/              # 崩坏3自动化 (YOLO/OCR/模板匹配/脚本)
│   │   ├── rag/                  # RAG检索引擎 (ChromaDB)
│   │   ├── llm/                  # LLM路由 (多模型切换/vision能力过滤)
│   │   ├── web_search/           # 联网搜索 (百度 + Playwright)
│   │   └── skill/                # 技能系统 (SKILL.md解析/阶段提取)
│   ├── services/                 # 聊天服务
│   └── config/                   # 配置管理 (Pydantic Settings + JSON持久化)
├── skills/characters/            # 30个角色人格文件 (SKILL.md)
├── skills/                       # 15个游戏自动化技能
├── data/                         # 运行时数据 (chroma_db/user_settings.json/模型)
└── outputs/                      # TTS输出/ASR转录/任务检查点
```

---

## 快速开始

### 环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Node.js | ≥ 18.0 | 前端 |
| Python | 3.10+ | 后端 |
| Git | 最新版 | 版本控制 |
| GPU (建议) | NVIDIA CUDA | 本地 LLM / TTS / YOLO 推理加速 |

### 安装

```bash
git clone https://github.com/tokutouseki/bbb_assistant.git
cd bbb_assistant

# 后端
cd backend
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 配置

编辑 `backend/data/user_settings.json`，或通过前端设置页 (设置 → LLM设置) 配置 API 密钥。

```json
{
  "llm_provider": "deepseek",
  "llm_api_key": "sk-xxxxxxxx",
  "llm_model": "deepseek-chat",
  "companion_character": "爱莉希雅"
}
```

### 启动

```bash
# 后端 (Uvicorn :8000)
cd backend
uvicorn src.main:app --reload

# 前端 (Vite :5173)
cd frontend
npm run dev
```

---

## 功能模块

### 1. 双 Agent 架构

**MainGameAgent** (DeepSeek Pro): 游戏任务执行器，20 个工具，输出 JSON 报告，后端日志可见。

**SubCompanionAgent** (DeepSeek Flash): 角色扮演陪伴，9 个工具，唯一对用户可见的 Agent，支持 TTS + Live2D。

```
用户消息 → MainGameAgent (任务执行) → SubCompanionAgent (角色化回复) → 用户(SSE流式)
```

### 2. 角色人格系统

30 位崩坏3角色，每位独立 SKILL.md 人格文件。通过前端设置页角色 Tab 一键切换，下一轮对话自动生效。

支持角色: 爱莉希雅、琪亚娜、芽衣、布洛妮娅、符华、德丽莎、白希儿、黑希儿、魔法少女西琳、空之律者、识之律者、朔夜观星、月下初拥、月下誓约、萝莎莉娅、莉莉娅、德尔塔、姬子、丽塔、幽兰黛尔、八重樱、樱、伊甸、梅比乌斯、维尔薇、阿波尼亚、帕朵菲莉丝、格蕾修、渡鸦、苏莎娜、李素裳、时雨绮罗、薇塔、瑟莉姆、科拉莉、赫丽娅、灯、松雀、羽兔、普罗米修斯、爱衣、卡萝尔、希娜狄雅

### 3. TTS 语音克隆

- **Qwen3-TTS** (1.7B): ICL 声音克隆，3 秒参考音频即可克隆声音
- **VoxCPM** (0.5B): 零样本语音克隆
- 39 位角色参考音频，默认使用爱莉希雅声音

### 4. Live2D 桌宠

PySide6 QOpenGLWidget 桌面窗口，鼠标穿透，支持表情/动作/口型同步。通过前端设置页管理模型导入和窗口参数。

### 5. 游戏自动化 (hongkai)

进程内直接调用，YOLO 场景识别 + OCR + 模板匹配 + 键鼠模拟 (Win32 SendInput)：

| 技能 | 功能 |
|------|------|
| full_operation | 全量日常调度 (按星期自动执行) |
| letu | 往世乐土全流程 |
| meizhou_jianfu | 每周减负 |
| zhanchang | 记忆战场 BOSS 减负 |
| simulation_combat_room | 模拟作战室 |
| jiantuangongxian | 舰团每日贡献 |
| everyweek_gift | 商城免费礼包 |
| find_direction | 场景迷失自救援 |
| navigate_to | 任意场景导航到目标 |

### 6. 视觉感知

- YOLO11n: 24 类游戏 UI 元素检测 + 场景分类
- PaddleOCR: 屏幕文字识别
- PixAI Tagger: 13,461 个 Danbooru 动漫标签
- Bailian Qwen-VL: 阿里百炼云端多模态模型

### 7. 图片描述系统

多后端自动降级: `bailian → pixai_tagger → lmstudio` (顺序可配置)。用户上传图片后由主 Agent 转为文本描述注入子 Agent 上下文。

---

## API 概览

所有 API 挂载在 `/api/` 前缀下，启动后访问 `http://localhost:8000/docs`。

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/chat/stream` | POST | SSE 流式对话 (主要接口) |
| `/api/chat/cancel` | POST | 取消运行中的请求 |
| `/api/chat/clear` | POST | 清除对话上下文 |
| `/api/chat/runtime-status` | GET | LLM 运行时状态 |
| `/api/settings/` | GET/PUT | 运行时设置读写 |
| `/api/settings/reset` | POST | 重置为默认设置 |
| `/api/settings/characters` | GET | 列出可用角色人格 |
| `/api/live2d/models` | GET | 列出已安装 Live2D 模型 |
| `/api/live2d/models/import` | POST | 导入模型 |
| `/api/live2d/models/{name}` | DELETE | 删除模型 |
| `/api/live2d/apply` | PUT | 即时应用窗口设置 |

### SSE 事件类型

`thought` / `action` / `observation` / `phase_start` / `phase_complete` / `todo_update` / `cancelled` / `error` / `done`

---

## 技术栈

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API) |
| 构建 | Vite 5 |
| 状态管理 | Pinia 2 |
| 样式 | Scoped CSS |
| Markdown | marked |

### 后端

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| AI 模型 | YOLO11n / PaddleOCR / FunASR / PixAI Tagger |
| TTS | Qwen3-TTS (1.7B) / VoxCPM (0.5B) |
| LLM | DeepSeek API / LM Studio (Qwen) / Ollama |
| Agent | LangChain ReAct Agent |
| RAG | ChromaDB + SentenceTransformers |
| OCR | RapidOCR (PP-OCRv4 ONNX) |
| Live2D | live2d-py v0.7.0 (Cubism Native SDK v3) + PySide6 |
| 自动化 | Win32 API (SendInput / SetWindowLong) |
| 爬虫 | Playwright + BeautifulSoup4 |

---

## 贡献指南

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feat/amazing-feature`
3. 使用 Conventional Commits 格式提交
4. 推送到分支并创建 Pull Request

---

## 许可证

MIT 开源许可证。

---

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain) — AI Agent 框架
- [Ultralytics YOLO11](https://github.com/ultralytics/ultralytics) — 目标检测
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR 识别
- [FunASR](https://github.com/modelscope/FunASR) — 语音识别
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — 语音合成
- [VoxCPM](https://github.com/thuhcsi/VoxCPM) — TTS 语音克隆
- [ChromaDB](https://github.com/chroma-core/chroma) — 向量数据库
- [live2d-py](https://github.com/Arkueid/live2d-py) — Live2D Python 封装
- [崩坏3](https://bh3.mihoyo.com/) — 米哈游出品动作游戏

---

*最后更新: 2026-05-26*
