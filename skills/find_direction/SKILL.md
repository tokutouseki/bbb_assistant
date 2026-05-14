---
name: find_direction
description: 找到方向技能 - 当LLM/Agent无论如何都无法识别当前页面时使用。通过查找舰桥按钮或使用ESC返回，逐步找到明确的方向。
---

# 找到方向 (Find Direction) 技能

## When to Use

当出现以下情况时，Agent 自动使用此技能：
- Agent 多次尝试识别当前场景但无法确定
- Agent 无法识别当前界面，不确定下一步如何操作
- 用户请求执行某个操作，但 Agent 不知道当前在什么页面
- 场景分类结果置信度很低，Agent 对当前位置没有信心
- Agent 发现自己"迷路"了，需要重新定位

## 概述

此技能是 Agent 的**自我定位工具**，用于当 Agent 自己无法识别当前页面时，帮助重新找到方向。核心策略：
1. 首先尝试寻找舰桥按钮直接回到主界面（最清晰的定位）
2. 如果找不到舰桥按钮，使用 ESC 键逐级返回上级界面
3. 通过场景分类模型确认当前位置
4. 循环执行直到找到明确的、有对应检测模型的场景

这是 Agent 的**应急自救技能**，帮助 Agent 在"迷路"时重新建立对环境的认知。每个步骤只包含单一不可拆分的操作，不嵌套子步骤。

## 技能流程

### 阶段一：寻找舰桥按钮（快速返回舰桥）

> **目标**：优先尝试在任意界面直接找到舰桥按钮，一键返回舰桥，这是最快的定位方式。

**步骤 1** — 聚焦游戏窗口

调用 `focus_bh3_window` 工具，确保崩坏3游戏窗口处于活动状态并可以接收操作。这是必须执行的第一步，否则后续所有截图和点击操作都将失败。

**步骤 2** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具，查看所有可用的 YOLO 模型以及哪些模型已经加载到显存中。后续步骤需要根据模型加载情况决定是否调用 `yolo_load_model`。

**步骤 3** — 加载舰桥检测模型（如未加载）

从步骤 2 的返回结果中检查 `yolo11n_bridge_ui_det` 是否已加载：
- 如果已加载 → 跳到步骤 4
- 如果未加载 → 调用 `yolo_load_model yolo11n_bridge_ui_det` 加载舰桥界面 UI 元素检测模型

如果 `yolo11n_bridge_ui_det` 在可用模型列表中不存在，则按以下优先级选择替代检测模型：
1. `yolo11n_home_ui_det`（家园界面检测模型）
2. `yolo11n_attack_ui_det`（出击界面检测模型）
3. `yolo11n_mission_ui_det`（任务界面检测模型）
4. `yolo11n_club_ui_det`（舰团界面检测模型）

**步骤 4** — 识别当前界面 UI 元素

调用 `yolo_detect_image` 对当前游戏窗口截图进行 UI 元素检测（使用步骤 3 中确认已加载的检测模型）。从检测结果中重点查找 `button_bridge`（前往舰桥按钮），记录其 bbox 坐标 [x1, y1, x2, y2]。

**步骤 5** — 判断：是否检测到 button_bridge？

根据步骤 4 的检测结果判断 `button_bridge` 是否存在且置信度 ≥ 0.5：
- 检测到且置信度 ≥ 0.5 → 执行步骤 6（点击舰桥按钮，快速返回舰桥）
- 未检测到或置信度 < 0.5 → 跳到步骤 8（进入阶段二，使用 ESC 逐级返回）

**步骤 6** — 点击舰桥按钮

从步骤 4 的检测结果中找到 `button_bridge`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标：center_x = (x1 + x2) / 2，center_y = (y1 + y2) / 2
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 7** — 等待界面切换并结束技能

等待 1-2 秒，让游戏切换回舰桥界面。技能结束 ✅ — 已找到方向，当前位于舰桥界面，可继续执行用户请求的任务。

---

### 阶段二：ESC 返回 + 场景识别

> **目标**：当前界面无法直接找到舰桥按钮，使用 ESC 键返回上级界面，然后识别场景确定位置。

**步骤 8** — 按 ESC 键返回上级界面

调用 `press_key key='escape' duration=0.1` 模拟按下 ESC 键，让游戏从当前界面返回上级界面。ESC 键是崩坏3中通用的返回上级操作，等效于点击界面上的返回按钮。

**步骤 9** — 等待界面切换

等待 1-2 秒，让游戏完成界面切换动画，确保后续截图能够获取到稳定的界面画面。

**步骤 10** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态（后续步骤需要确认场景分类模型是否已加载）。

**步骤 11** — 加载场景分类模型（如未加载）

从步骤 10 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 12
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 加载场景分类模型

**步骤 12** — 识别当前场景

调用 `yolo_classify_image yolo11n_scene_cls` 对当前游戏窗口截图进行场景分类，获取当前所在场景的英文名称和中文名称。

**步骤 13** — 判断：当前场景是否有对应的 UI 检测模型？

根据步骤 12 返回的场景英文名称，对照下表判断该场景是否拥有对应的 UI 元素检测模型：

| 场景英文 | 场景中文 | 对应检测模型 |
|----------|----------|--------------|
| attack | 出击界面 | yolo11n_attack_ui_det |
| bridge | 舰桥界面 | yolo11n_bridge_ui_det |
| club | 舰团界面 | yolo11n_club_ui_det |
| home | 家园界面 | yolo11n_home_ui_det |
| mission | 任务界面 | yolo11n_mission_ui_det |

- 当前场景在表中 → 技能结束 ✅，已找到方向，当前场景明确，可继续执行用户请求的任务
- 当前场景不在表中 → 执行步骤 14（进入阶段三，继续按 ESC 返回）

---

### 阶段三：循环 ESC 返回（最多重试 5 次）

> **目标**：当前场景仍不明确，继续按 ESC 返回更上级界面，直到找到有对应检测模型的明确场景。

**步骤 14** — 按 ESC 键返回上级界面

调用 `press_key key='escape' duration=0.1` 模拟按下 ESC 键。

**步骤 15** — 等待界面切换

等待 1-2 秒，让界面完全切换到上级界面。

**步骤 16** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认场景分类模型是否仍加载在显存中。

**步骤 17** — 加载场景分类模型（如已卸载）

从步骤 16 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 18
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 重新加载

**步骤 18** — 识别当前场景

调用 `yolo_classify_image yolo11n_scene_cls` 对当前游戏窗口截图进行场景分类。

**步骤 19** — 判断：当前场景是否有对应的 UI 检测模型？

使用与步骤 13 相同的场景—模型对照表进行判断：
- 当前场景有对应检测模型 → 技能结束 ✅，已找到方向
- 当前场景无对应检测模型 → 执行步骤 20

**步骤 20** — 判断：ESC 重试次数是否已达上限？

统计从步骤 14 开始已执行的 ESC 返回次数：
- 已重试 < 5 次 → 回到步骤 14，继续按 ESC 返回
- 已重试 ≥ 5 次 → 技能结束 ⚠️，无法自动定位，建议告知用户当前情况并请求用户手动引导

---

## 完整流程图

```
开始
  ↓
[1] focus_bh3_window
  ↓
[2] yolo_list_models
  ↓
[3] 加载 bridge_ui_det（未加载时，优先选 bridge）
  ↓
[4] yolo_detect_image → 查找 button_bridge
  ↓
[5] {检测到 button_bridge 且置信度 ≥ 0.5?}
  ├─ 是 → [6] 提取 bbox → 计算中心点 → click_coordinates
  │         ↓
  │       [7] 等待 1-2s → 结束 ✅
  │
  └─ 否 → [8] press_key ESC
              ↓
          [9] 等待 1-2s
              ↓
          [10] yolo_list_models
              ↓
          [11] 加载 scene_cls（未加载时）
              ↓
          [12] yolo_classify_image → 识别场景
              ↓
          [13] {场景有对应检测模型?}
              ├─ 是 → 结束 ✅
              └─ 否 ↓
┌─────────────────────────────────┐
│ [14] press_key ESC              │
│        ↓                        │
│ [15] 等待 1-2s                  │
│        ↓                        │
│ [16] yolo_list_models           │
│        ↓                        │
│ [17] 加载 scene_cls（未加载时）  │
│        ↓                        │
│ [18] yolo_classify_image        │
│        ↓                        │
│ [19] {场景有对应检测模型?}       │
│  ├─ 是 → 结束 ✅                │
│  └─ 否 ↓                       │
│ [20] {重试 < 5 次?}             │
│  ├─ 是 → 回到 [14]              │
│  └─ 否 → 结束 ⚠️               │
└─────────────────────────────────┘
```

---

## 使用示例

### 示例 1：成功找到舰桥按钮（阶段一）

```
 1. focus_bh3_window
 2. yolo_list_models → 当前已加载: 无
 3. bridge_ui_det 未加载 → yolo_load_model yolo11n_bridge_ui_det
 4. yolo_detect_image yolo11n_bridge_ui_det
    → button_bridge 在 [100, 200, 200, 300]，置信度 0.92
    → button_club 在 [400, 600, 550, 680]，置信度 0.88
 5. 判断: button_bridge 存在且置信度 0.92 ≥ 0.5 → 点击
 6. button_bridge bbox=[100,200,200,300] → 中心点 (150, 250) → click_coordinates 150, 250
 7. 等待 1.5s → 回到舰桥 → 结束 ✅
```

### 示例 2：ESC 一次后找到方向（阶段二）

```
 1. focus_bh3_window
 2. yolo_list_models → 当前已加载: yolo11n_home_ui_det
 3. bridge_ui_det 未加载且在可用列表中 → yolo_load_model yolo11n_bridge_ui_det
    若 bridge_ui_det 也不在可用列表中 → 使用 home_ui_det 作为替代
 4. yolo_detect_image yolo11n_bridge_ui_det
    → 未找到 button_bridge，仅检测到 home 相关按钮
 5. 判断: 未检测到 button_bridge → 进入阶段二
 8. press_key key='escape', duration=0.1
 9. 等待 1.5s
10. yolo_list_models → scene_cls 未加载
11. yolo_load_model yolo11n_scene_cls
12. yolo_classify_image yolo11n_scene_cls → "mission (任务界面)"
13. 判断: mission 在场景—模型对照表中，有对应检测模型 yolo11n_mission_ui_det → 结束 ✅
```

### 示例 3：多次 ESC 后成功（阶段三）

```
 1. focus_bh3_window
 2. yolo_list_models → 当前已加载: yolo11n_club_ui_det
 3. bridge_ui_det 未加载 → yolo_load_model yolo11n_bridge_ui_det
 4. yolo_detect_image yolo11n_bridge_ui_det → 未找到 button_bridge
 5. 判断: 不存在 → 进入阶段二
 8. press_key ESC → 等待 1.5s
10-11. 加载 scene_cls
12. yolo_classify_image → "unknown_scene (未知场景)"
13. 判断: unknown_scene 不在对照表中 → 进入阶段三

--- 循环第 1 次 ---
14. press_key ESC → 等待 1.5s
16-17. scene_cls 仍加载，跳过
18. yolo_classify_image → "unknown_scene (未知场景)"
19. 判断: 仍不在对照表中
20. 重试 1 次 < 5 次 → 继续

--- 循环第 2 次 ---
14. press_key ESC → 等待 1.5s
16-17. scene_cls 仍加载，跳过
18. yolo_classify_image → "home (家园界面)"
19. 判断: home 在对照表中，有对应检测模型 yolo11n_home_ui_det → 结束 ✅
```

---

## 场景—检测模型对照表

| 场景英文 | 场景中文 | 对应检测模型 |
|----------|----------|--------------|
| attack | 出击界面 | yolo11n_attack_ui_det |
| bridge | 舰桥界面 | yolo11n_bridge_ui_det |
| club | 舰团界面 | yolo11n_club_ui_det |
| home | 家园界面 | yolo11n_home_ui_det |
| mission | 任务界面 | yolo11n_mission_ui_det |

> 完整的 34 个场景列表请参考 `scene_mapping.json`，以上 5 个为当前支持 UI 元素检测的场景。场景分类模型 `yolo11n_scene_cls` 可以识别全部 34 个场景，但只有以上 5 个场景拥有对应的 UI 检测模型。

---

## 检测模型优先顺序

在步骤 3 中寻找舰桥按钮时，按以下优先级选择检测模型：
1. `yolo11n_bridge_ui_det` — 专门检测舰桥界面 UI 元素，优先使用
2. `yolo11n_home_ui_det` — 家园界面也有导航按钮，可作为替代
3. `yolo11n_attack_ui_det` — 出击界面检测模型
4. `yolo11n_mission_ui_det` — 任务界面检测模型
5. `yolo11n_club_ui_det` — 舰团界面检测模型

选择逻辑：从优先级 1 开始，选择第一个在 `yolo_list_models` 的可用模型列表中存在的模型。如果该模型未加载，调用 `yolo_load_model` 加载。

---

## 注意事项

1. **ESC 键等待时间**：每次按 ESC 后必须等待 1-2 秒，让界面完全切换，不要连续快速按 ESC
2. **重试次数限制**：阶段三最多循环 5 次，超过后告知用户手动操作，防止无限循环
3. **置信度判断**：步骤 5 中即使检测到 button_bridge，如果置信度低于 0.5 也视为不可靠，走 ESC 路径
4. **模型加载顺序**：每次调用 `yolo_classify_image` 前都需通过 `yolo_list_models` 确认模型状态
5. **异常处理**：如果 5 次 ESC 后仍找不到方向，向用户说明当前状态并询问用户希望如何操作

---

## 工具依赖

| 工具名称 | 用途 | 使用步骤 |
|----------|------|----------|
| `focus_bh3_window` | 聚焦游戏窗口 | 1 |
| `yolo_list_models` | 列出可用模型及加载状态 | 2, 10, 16 |
| `yolo_load_model` | 加载 YOLO 模型 | 3, 11, 17 |
| `yolo_unload_model` | 卸载 YOLO 模型释放显存 | 按需使用 |
| `yolo_detect_image` | UI 元素检测 | 4 |
| `yolo_classify_image` | 场景分类识别 | 12, 18 |
| `click_coordinates` | 点击坐标 | 6 |
| `press_key` | 模拟按键（ESC） | 8, 14 |
