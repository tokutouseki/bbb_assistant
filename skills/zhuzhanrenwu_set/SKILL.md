---
name: zhuzhanrenwu_set
description: 驻战任务设置 — 快速点击出战人物和筛选按钮。
---

# 驻战任务设置技能

## When to Use

当用户请求以下操作时使用此技能：
- "驻战任务设置"、"出战人物"
- "garrison setup"、"zhuzhanrenwu"

## 概述

此技能调用 hongkai_done 的 `zhuzhanrenwu_set.py` 脚本，执行驻战任务相关设置：
1. 点击"出战人物"按钮
2. 点击"筛选"按钮

> 注意：此脚本较简单，仅完成两步点击操作，可能为未完成的功能。

## 技能流程

**步骤 1** — 调用 `run_hongkai_task task="zhuzhanrenwu_set"`

**步骤 2** — 报告结果

## 注意事项

1. **需要管理员权限**
2. **执行时间**：约 10 秒
3. 此脚本功能不完整，仅执行两个点击操作

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `run_hongkai_task` | 执行驻战任务设置 |
