---
name: simulation_combat_room
description: 模拟作战室减负 — 自动进入舰团的模拟作战室并执行一键减负。
---

# 模拟作战室减负技能

## When to Use

当用户请求以下操作时使用此技能：
- "模拟作战室"、"模拟作战室减负"
- "simulation combat room"

## 概述

此技能调用 hongkai_done 的 `simulation_combat_room.py` 脚本，自动完成模拟作战室减负：
1. 点击"舰团"
2. 进入模拟作战室
3. 执行一键减负
4. 确认并返回主界面

## 技能流程

**步骤 1** — 调用 `run_hongkai_task task="simulation_combat_room"`

**步骤 2** — 报告结果

## 注意事项

1. **需要管理员权限**
2. **执行时间**：约 1-2 分钟
3. 周二和周日由 full_operation 自动执行

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `run_hongkai_task` | 执行模拟作战室减负 |
