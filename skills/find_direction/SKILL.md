---
name: find_direction
description: 找到方向技能 - 当LLM/Agent无论如何都无法识别当前页面时使用。通过查找舰桥按钮或使用ESC返回，逐步找到明确的方向。
---

# 找到方向 (Find Direction) 技能

## When to Use

当出现以下情况时，Agent 使用此技能：
- Agent 多次尝试识别当前场景但无法确定
- Agent 无法识别当前界面，不确定下一步如何操作
- 场景分类结果置信度很低，Agent 对当前位置没有信心
- Agent 发现自己"迷路"了，需要重新定位

## 执行方式

**直接调用 `find_direction` 工具**，无需分步操作。该工具会自动完成：

1. 聚焦游戏窗口
2. 加载检测模型，寻找舰桥按钮（button_bridge）→ 找到就点击返回舰桥
3. 找不到则按 ESC 返回上级界面 → 场景分类确认位置
4. 仍不确定则循环 ESC（最多5次）直到找到已知场景

调用后根据返回结果决定下一步。

## 内部流程（参考）

<details>
<summary>阶段一：寻找舰桥按钮</summary>

- 聚焦窗口 → 列模型 → 选第一个可用检测模型（优先级: bridge > home > attack > mission > club）
- 检测 button_bridge
- 置信度 ≥ 0.5 → 计算中心点 → 点击 → 等待 → 结束

</details>

<details>
<summary>阶段二：ESC返回 + 场景识别</summary>

- 按 ESC → 等待 1.5s → 加载 scene_cls → 分类
- 场景在已知列表（bridge/home/mission/club/attack）→ 结束
- 不在 → 进入阶段三

</details>

<details>
<summary>阶段三：循环 ESC（最多5次）</summary>

- 按 ESC → 等待 → 分类 → 查表
- 找到已知场景 → 结束 ✅
- 超过5次 → 结束 ⚠️，告知用户手动引导

</details>

## 场景—检测模型对照表

| 场景英文 | 场景中文 | 对应检测模型 |
|----------|----------|--------------|
| attack | 出击界面 | yolo11n_attack_ui_det |
| bridge | 舰桥界面 | yolo11n_bridge_ui_det |
| club | 舰团界面 | yolo11n_club_ui_det |
| home | 家园界面 | yolo11n_home_ui_det |
| mission | 任务界面 | yolo11n_mission_ui_det |
