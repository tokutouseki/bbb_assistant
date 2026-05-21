---
name: game_navigation
description: 游戏场景导航技能 - 从任意界面导航到目标界面。
---

# 游戏场景导航技能

## When to Use

当用户请求以下操作时使用此技能：
- "进入任务界面"、"导航到mission"、"打开任务"
- "进入出击界面"、"导航到attack"、"打开出击"
- "进入舰团界面"、"导航到club"、"打开舰团"
- "进入家园界面"、"导航到home"、"打开家园"
- 需要在游戏内不同界面之间切换

## 执行方式

**直接调用 `navigate_to` 工具**，传入目标场景英文名，无需分步操作。该工具会自动完成：

1. 识别当前位置
2. 如果不在舰桥 → 找到 button_bridge → 点击返回舰桥（找不到则调用 find_direction 自救）
3. 从舰桥加载 bridge_ui_det → 找到目标导航按钮 → 点击
4. 验证是否到达目标场景
5. 未到达则重试（最多3次）

目标场景可选值: `attack`, `club`, `bridge`, `mission`, `home`

## 导航路径表

所有导航经过舰桥（bridge）中转：

| 目标场景 | 导航路径 | 目标按钮 |
|----------|----------|----------|
| attack | 当前界面 → bridge → attack | button_attack |
| club | 当前界面 → bridge → club | button_club |
| bridge | 当前界面 → bridge | button_bridge |
| mission | 当前界面 → bridge → mission | button_mission |
| home | 当前界面 → bridge → home | button_home |

## 内部流程（参考）

<details>
<summary>阶段一：确认当前位置</summary>

- 聚焦窗口 → 加载 scene_cls → 分类
- 已在目标场景 → 结束 ✅
- 不在 → 继续

</details>

<details>
<summary>阶段二：导航到舰桥</summary>

- 根据当前场景加载对应检测模型（attack→attack_ui_det, club→club_ui_det 等）
- 检测 button_bridge → 点击 → 等待 → 验证是否到达 bridge
- 找不到检测模型或 button_bridge → 调用 find_direction 自救

</details>

<details>
<summary>阶段三：从舰桥导航到目标</summary>

- 加载 bridge_ui_det → 检测目标按钮 → 点击 → 等待
- 找不到目标按钮 → 重新验证场景或 find_direction

</details>

<details>
<summary>阶段四~五：验证 + 重试（最多3次）</summary>

- 分类验证是否到达目标
- 未到达 → 重新识别 → 从正确阶段重试
- 超过3次 → 结束 ⚠️，告知用户手动操作

</details>

## 场景—检测模型对照表

| 场景英文 | 场景中文 | 对应检测模型 |
|----------|----------|--------------|
| attack | 出击界面 | yolo11n_attack_ui_det |
| bridge | 舰桥界面 | yolo11n_bridge_ui_det |
| club | 舰团界面 | yolo11n_club_ui_det |
| home | 家园界面 | yolo11n_home_ui_det |
| mission | 任务界面 | yolo11n_mission_ui_det |
