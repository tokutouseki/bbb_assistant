---
name: shenzhijian
description: 神之键配置 — 自动配置乐土中的神之键，通过键盘宏回放完成操作。
---

# 神之键配置技能

## When to Use

当用户请求以下操作时使用此技能：
- "神之键"、"配置神之键"
- "divine key"、"shenzhijian"

## 概述

此技能调用 hongkai_done 的 `shenzhijian.py` 脚本，自动配置神之键：
1. 点击神之键按钮
2. 回放键盘宏 (`reproduce/shenzhijian.json`)
3. 按 ESC 退出
4. 标记配置完成

> 注意：此技能通常是往世乐土流程的一部分，由 letu 技能在内部调用。仅在需要单独重新配置神之键时使用。

## 技能流程

**步骤 1** — 调用 `run_hongkai_task task="shenzhijian"`

**步骤 2** — 报告结果

## 前置条件

- 需要 `reproduce/shenzhijian.json` 键盘宏录制文件
- 使用 `config.json` 中的 `shenzhijian_done` 标记避免重复执行

## 注意事项

1. **需要管理员权限**
2. **执行时间**：约 30 秒

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `run_hongkai_task` | 执行神之键配置 |
