---
name: jiantuangongxian
description: 舰团贡献 — 自动完成舰团每日5000贡献。
---

# 舰团贡献技能

## When to Use

当用户请求以下操作时使用此技能：
- "舰团贡献"、"armada contribution"
- "舰队贡献"、"团贡献"

## 概述

此技能调用 hongkai_done 的 `jiantuangongxian.py` 脚本，自动完成舰团每日贡献：
1. 确保在主界面
2. 点击"舰团"按钮
3. 点击"舰团贡献"
4. 点击 5000 贡献按钮
5. 按 ESC 三次返回主界面

## 技能流程

**步骤 1** — 调用 `run_hongkai_task task="jiantuangongxian"`

**步骤 2** — 报告结果

## 注意事项

1. **需要管理员权限**
2. **执行时间**：约 30 秒
3. 周日由 full_operation 自动执行

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `run_hongkai_task` | 执行舰团贡献 |
