---
name: maoxian_weituo
description: 冒险委托 — 自动接取后崩坏书1的冒险委托任务。
---

# 冒险委托技能

## When to Use

当用户请求以下操作时使用此技能：
- "冒险委托"、"接委托"
- "adventure commission"、"maoxian"

## 概述

此技能调用 hongkai_done 的 `maoxian_weituo.py` 脚本，自动接取冒险委托：
1. 点击"出击" → "开放世界"
2. 选择地图
3. 选择"后崩坏书1"
4. 接取委托任务
5. 返回主界面

## 技能流程

**步骤 1** — 调用 `run_hongkai_task task="maoxian_weituo"`

**步骤 2** — 报告结果

## 注意事项

1. **需要管理员权限**
2. **执行时间**：约 1 分钟

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `run_hongkai_task` | 执行冒险委托 |
