# 贡献指南

感谢你对**崩坏3专属AI陪伴助手**的关注！我们欢迎任何形式的贡献。

## 行为准则

- 保持友善和尊重
- 建设性地提出意见
- 专注于项目改进

## 如何贡献

### 报告 Bug

1. 使用 GitHub Issues 提交 Bug 报告
2. 描述清晰的复现步骤
3. 附上相关的日志和截图
4. 注明运行环境（操作系统、Python 版本、Node.js 版本）

### 提出新功能

1. 先在 Issues 中讨论，确保功能与项目方向一致
2. 清晰描述功能的使用场景和预期效果
3. 如涉及 AI 模型，说明模型选型理由

### 提交代码

#### 开发流程

```bash
# 1. Fork 仓库并克隆
git clone https://github.com/YOUR_USERNAME/bbb-assistant.git
cd bbb-assistant

# 2. 安装依赖
pnpm install:all

# 3. 创建特性分支
git checkout -b feat/your-feature-name
# 或 fix/your-bugfix-name
```

#### 分支命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feat/<描述>` | `feat/voice-clone-enhancement` |
| Bug 修复 | `fix/<描述>` | `fix/tts-memory-leak` |
| 文档 | `docs/<描述>` | `docs/api-reference` |
| 重构 | `refactor/<描述>` | `refactor/rag-module` |
| 性能优化 | `perf/<描述>` | `perf/yolo-inference` |

#### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```bash
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**类型 (type)**：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响运行） |
| `refactor` | 代码重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具变动 |
| `ci` | CI 配置 |

**范围 (scope)**：

| 范围 | 说明 |
|------|------|
| `frontend` | 前端相关 |
| `backend` | 后端相关 |
| `vision` | 视觉感知模块 |
| `audio` | 音频处理模块 |
| `llm` | 大模型模块 |
| `rag` | 知识库模块 |
| `agent` | ReAct Agent模块 |
| `electron` | Electron主进程 |
| `shared` | 共享类型/协议 |

示例：

```bash
feat(audio): add Qwen3-TTS emotion control parameter
fix(rag): resolve ChromaDB collection conflict on concurrent writes
docs(readme): update TTS model comparison table
refactor(agent): extract tool execution to separate module
```

### 代码规范

#### 前端（Vue3 + TypeScript）

- 遵循 ESLint 配置
- 使用 Prettier 格式化
- Vue 组件使用 Composition API + `<script setup>`
- TypeScript 严格模式

```bash
pnpm lint          # 代码检查
pnpm format        # 代码格式化
pnpm test:frontend # 运行测试
```

#### 后端（Python）

- 遵循 PEP 8
- 使用 Black 格式化（行宽 100）
- isort 排序导入
- 类型注解鼓励使用

```bash
cd backend
black src/ tests/   # 格式化
isort src/ tests/   # 导入排序
flake8 src/         # 代码检查
pytest              # 运行测试
```

### Pull Request 流程

1. 确保代码通过所有 lint 和测试检查
2. 更新相关文档（如有必要）
3. 提供清晰的 PR 描述：
   - 改了什么
   - 为什么这样改
   - 如何测试
4. PR 标题遵循 Conventional Commits 格式

## 项目结构速览

```
bbb_assistant/
├── frontend/          # Electron + Vue3 前端
│   ├── electron/      # 主进程、IPC
│   └── src/           # Vue3 源码
├── backend/           # Python FastAPI 后端
│   └── src/
│       ├── api/       # API 路由
│       ├── modules/   # 核心模块
│       ├── services/  # 业务服务
│       └── config/    # 配置
├── shared/            # 共享类型与协议
└── voice_resources/   # 角色语音资源
```

## 问题反馈

如有任何问题，欢迎通过 GitHub Issues 联系。
