---
name: chaoxiankongjian
description: 超弦空间 — 自动进入超弦空间战斗准备界面。
---

# 超弦空间技能

## When to Use

当用户请求以下操作时使用此技能：
- "超弦空间"、"超限空间"
- "superstring dimension"

## 概述

此技能调用 hongkai_done 的 `chaoxiankongjian.py` 脚本，自动导航到超弦空间战斗准备界面：
1. 点击"出击" → "挑战"
2. 点击"超弦空间"
3. 点击"空间_战斗"
4. 点击"战斗_准备"

## 技能流程

**步骤 1** — 调用 `run_hongkai_task task="chaoxiankongjian"`

**步骤 2** — 报告结果

## 注意事项

1. **需要管理员权限**
2. **执行时间**：约 30 秒
3. 此脚本仅完成导航，实际战斗需手动操作

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `run_hongkai_task` | 执行超弦空间导航 |
