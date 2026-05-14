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

## 概述

此技能用于从任意界面导航到指定目标界面，支持自动循环重试。核心能力：
1. 自动识别当前游戏场景
2. 根据当前场景选择合适的导航路径
3. 自动点击界面元素完成导航
4. 验证导航结果并支持循环重试

每个步骤只包含单一不可拆分的操作（一次工具调用或一次判断），不嵌套子步骤。所有场景间导航都经过舰桥（bridge）中转。

## 导航路径表

| 目标场景 | 导航路径 | 目标按钮 |
|----------|----------|----------|
| attack | 当前界面 → bridge → attack | button_attack |
| club | 当前界面 → bridge → club | button_club |
| bridge | 当前界面 → bridge | button_bridge |
| mission | 当前界面 → bridge → mission | button_mission |
| home | 当前界面 → bridge → home | button_home |

> **关键规则**：所有导航都需要经过舰桥（bridge）中转。如果当前已在舰桥，直接点击目标按钮。如果不在舰桥，先返回舰桥再导航到目标。

## 技能流程

### 阶段一：确认当前位置

**步骤 1** — 聚焦游戏窗口

调用 `focus_bh3_window` 工具，确保崩坏3游戏窗口处于活动状态并可以接收操作。这是必须执行的第一步。

**步骤 2** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具，查看所有可用的 YOLO 模型以及哪些模型已经加载到显存中。后续步骤需要根据模型加载情况决定是否调用 `yolo_load_model`。

**步骤 3** — 加载场景分类模型（如未加载）

从步骤 2 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 4
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 加载场景分类模型

**步骤 4** — 识别当前游戏场景

调用 `yolo_classify_image yolo11n_scene_cls` 对当前游戏窗口截图进行场景分类，获取当前所在的场景英文名称和中文名称。场景分类模型可识别 34 个游戏场景。

**步骤 5** — 判断：当前场景是否已是目标场景？

将步骤 4 返回的场景英文名称与用户请求的目标场景进行对比：
- 当前场景 = 目标场景 → 技能结束 ✅，告诉用户"已在目标界面，无需导航"
- 当前场景 ≠ 目标场景 → 执行步骤 6，开始导航

### 阶段二：导航到舰桥（如需要）

> 如果步骤 5 判断当前已在舰桥（bridge），直接跳到步骤 12。

**步骤 6** — 判断：当前是否已在舰桥？

从步骤 4 的结果判断当前场景英文名称是否为 bridge：
- 是 bridge → 跳到步骤 12（直接在舰桥找目标按钮）
- 不是 bridge → 执行步骤 7（需要先返回舰桥）

**步骤 7** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。由于可能经过了其他操作，需要重新确认。

**步骤 8** — 加载当前场景的检测模型（如未加载）

根据步骤 4 识别的当前场景，在场景—检测模型对照表中找到对应的检测模型：

| 当前场景 | 检测模型 |
|----------|----------|
| attack | yolo11n_attack_ui_det |
| club | yolo11n_club_ui_det |
| home | yolo11n_home_ui_det |
| mission | yolo11n_mission_ui_det |

从步骤 7 的返回结果中检查该检测模型是否已加载：
- 如果已加载 → 跳到步骤 9
- 如果未加载 → 调用 `yolo_load_model` 加载对应检测模型

如果当前场景不在上述四个场景中（无对应检测模型），则参考 find_direction 技能了解如何返回舰桥。

**步骤 9** — 识别当前界面中的舰桥按钮

调用 `yolo_detect_image`（使用步骤 8 确认已加载的检测模型）对当前游戏窗口截图进行 UI 元素检测。从检测结果中查找 `button_bridge`（前往舰桥按钮），记录其 bbox 坐标。

**步骤 10** — 判断：是否检测到 button_bridge？

根据步骤 9 的检测结果判断：
- 检测到 `button_bridge` → 执行步骤 11（点击返回舰桥）
- 未检测到 `button_bridge` → 参考 find_direction 技能了解如何通过按 ESC 逐级返回或寻找舰桥按钮回到舰桥，完成后回到步骤 3 重新验证场景

**步骤 11** — 点击舰桥按钮返回舰桥

从步骤 9 的检测结果中找到 `button_bridge`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标：center_x = (x1 + x2) / 2，center_y = (y1 + y2) / 2
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 12** — 等待界面切换

等待 1-2 秒，让游戏切换到舰桥界面。然后回到步骤 3，重新验证是否已到达舰桥。

### 阶段三：从舰桥导航到目标场景

**步骤 13** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。

**步骤 14** — 加载舰桥检测模型（如未加载）

从步骤 13 的返回结果中检查 `yolo11n_bridge_ui_det` 是否已加载：
- 如果已加载 → 跳到步骤 15
- 如果未加载 → 调用 `yolo_load_model yolo11n_bridge_ui_det` 加载舰桥界面 UI 元素检测模型

**步骤 15** — 识别舰桥界面中的目标导航按钮

调用 `yolo_detect_image yolo11n_bridge_ui_det` 对当前游戏窗口截图进行 UI 元素检测。从检测结果中查找前往目标场景对应的导航按钮：

| 目标场景 | 要查找的按钮 |
|----------|-------------|
| attack | button_attack |
| club | button_club |
| mission | button_mission |
| home | button_home |

记录该按钮的 bbox 坐标 [x1, y1, x2, y2]。

**步骤 16** — 判断：是否检测到目标导航按钮？

根据步骤 15 的检测结果判断：
- 检测到目标按钮且置信度 ≥ 0.5 → 执行步骤 17
- 未检测到或置信度 < 0.5 → 步骤 15 的检测可能不准确，先确认是否真的在舰桥：回到步骤 3 重新验证场景。如果确实在舰桥但仍找不到按钮，参考 find_direction 技能了解返回舰桥的方法重新定位

**步骤 17** — 点击目标导航按钮

从步骤 15 的检测结果中找到目标按钮：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 18** — 等待界面切换

等待 1-2 秒，让游戏从舰桥界面切换到目标场景。

### 阶段四：验证导航结果

**步骤 19** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认场景分类模型是否仍在显存中。

**步骤 20** — 加载场景分类模型（如已卸载）

从步骤 19 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 21
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 重新加载

**步骤 21** — 验证是否到达目标场景

调用 `yolo_classify_image yolo11n_scene_cls` 识别当前场景。将返回的场景英文名称与目标场景对比：
- 场景名称匹配 → 技能结束 ✅，导航成功，告知用户已到达目标界面
- 场景名称不匹配 → 执行步骤 22，进行重试

### 阶段五：循环重试

> 重试上限为 3 次，超过则告知用户手动操作。

**步骤 22** — 判断：重试次数是否已达上限？

统计从步骤 21 失败后已进行的重试次数：
- 已重试 < 3 次 → 执行步骤 23
- 已重试 ≥ 3 次 → 技能结束 ⚠️，告知用户导航失败，建议手动点击或检查游戏状态

**步骤 23** — 重新识别当前场景

调用 `yolo_classify_image yolo11n_scene_cls` 识别当前所在场景，确定当前实际位置作为重试的起点。

**步骤 24** — 返回阶段二重新导航

根据步骤 23 识别到的实际场景，回到对应的阶段重新执行：
- 如果在 bridge → 回到步骤 13（阶段三：从舰桥导航）
- 如果在其他场景 → 回到步骤 6（阶段二：先返回舰桥）

---

## 完整流程图

```
开始
  ↓
[1] focus_bh3_window
  ↓
[2] yolo_list_models
  ↓
[3] 加载 scene_cls（未加载时）
  ↓
[4] yolo_classify_image → 识别场景
  ↓
[5] {已是目标场景?}
  ├─ 是 → 结束 ✅
  └─ 否 ↓
[6] {当前是 bridge?}
  ├─ 是 → 跳到 [13]
  └─ 否 ↓
[7] yolo_list_models
  ↓
[8] 加载当前场景检测模型（未加载时）
  ↓
[9] yolo_detect_image → 查找 button_bridge
  ↓
[10] {找到 button_bridge?}
  ├─ 否 → find_direction → 回到 [3]
  └─ 是 ↓
[11] 提取 bbox → 计算中心点 → click_coordinates
  ↓
[12] 等待 1-2s → 回到 [3]
  ↓
[13] yolo_list_models
  ↓
[14] 加载 bridge_ui_det（未加载时）
  ↓
[15] yolo_detect_image → 查找目标导航按钮
  ↓
[16] {找到目标按钮?}
  ├─ 否 → 回到 [3] 验证是否在 bridge
  └─ 是 ↓
[17] 提取 bbox → 计算中心点 → click_coordinates
  ↓
[18] 等待 1-2s
  ↓
[19] yolo_list_models
  ↓
[20] 加载 scene_cls（未加载时）
  ↓
[21] yolo_classify_image → 验证场景
  ↓
{是目标场景?}
  ├─ 是 → 结束 ✅
  └─ 否 → ┌──────────────────────────┐
           │ [22] {重试 < 3 次?}      │
           │  ├─ 否 → 结束 ⚠️         │
           │  └─ 是 ↓                │
           │ [23] yolo_classify_image │
           │ [24] 回到 [6] ──────────┘
           └──────────────────────────
```

---

## 使用示例

### 示例：从舰团界面导航到任务界面

```
目标: mission

--- 阶段一 ---
 1. focus_bh3_window
 2. yolo_list_models → 当前已加载: scene_cls, club_ui_det
 3. scene_cls 已加载 → 跳过
 4. yolo_classify_image yolo11n_scene_cls → "club (舰团界面)"
 5. 判断: club ≠ mission → 继续导航

--- 阶段二：返回舰桥 ---
 6. 判断: club 不是 bridge → 需要返回舰桥
 7. yolo_list_models → club_ui_det 已加载
 8. club 场景对应 yolo11n_club_ui_det → 已加载，跳过
 9. yolo_detect_image yolo11n_club_ui_det
    → button_bridge 在 [50, 50, 100, 100]，置信度 0.91
10. 判断: 检测到 button_bridge
11. button_bridge bbox=[50,50,100,100] → 中心点 (75, 75) → click_coordinates 75, 75
12. 等待 1.5s → 回到步骤 3

--- 验证已在舰桥 ---
 3. scene_cls 已加载 → 跳过
 4. yolo_classify_image yolo11n_scene_cls → "bridge (舰桥界面)"
 5. 判断: bridge ≠ mission → 继续
 6. 判断: 当前是 bridge → 跳到步骤 13

--- 阶段三：导航到 mission ---
13. yolo_list_models → bridge_ui_det 未加载
14. yolo_load_model yolo11n_bridge_ui_det
15. yolo_detect_image yolo11n_bridge_ui_det
    → button_mission 在 [100, 200, 150, 250]，置信度 0.93
    → button_attack 在 [300, 500, 400, 580]
    → button_club 在 [400, 600, 550, 680]
16. 判断: button_mission 存在且置信度 0.93 ≥ 0.5
17. button_mission bbox=[100,200,150,250] → 中心点 (125, 225) → click_coordinates 125, 225
18. 等待 1.5s

--- 阶段四：验证 ---
19. yolo_list_models → scene_cls 已加载
20. 跳过加载
21. yolo_classify_image yolo11n_scene_cls → "mission (任务界面)" → 匹配 ✓
→ 结束 ✅
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

> 完整的 34 个场景列表请参考 `scene_mapping.json`。以上 5 个为当前支持 UI 元素检测的场景，场景分类模型 `yolo11n_scene_cls` 可以识别全部 34 个场景。

---

## 注意事项

1. **所有导航经过舰桥**：当前不在舰桥时，必须先找到 button_bridge 返回舰桥，再从舰桥点击目标按钮，不存在跨场景直达路径
2. **每次调用场景分类前检查模型**：步骤 4、步骤 21 和步骤 23 调用 `yolo_classify_image` 前，都需要先通过 `yolo_list_models` 确认 `yolo11n_scene_cls` 已加载
3. **找不到 button_bridge 时参考 find_direction**：步骤 10 中如果当前场景没有舰桥按钮，参考 find_direction 技能了解通过 ESC 逐级返回的方法
4. **重试次数限制**：最多重试 3 次，每次重试前重新识别当前场景作为新的起点，超过后告知用户手动操作
5. **等待时间**：每次点击后必须等待 1-2 秒，让游戏界面完成切换动画
6. **置信度判断**：步骤 16 中目标按钮置信度低于 0.5 时视为检测不可靠，需要重新确认

### 异常处理

- **步骤 8 当前场景无对应检测模型**：参考 find_direction 技能了解如何返回舰桥，而不是尝试在当前场景检测
- **步骤 10 找不到 button_bridge**：参考 find_direction 技能了解通过 ESC 逐级返回的方法
- **步骤 15 在桥找不到目标按钮**：回到步骤 3 确认是否真的在舰桥，可能场景分类识别有误
- **步骤 21 导航验证失败**：进入重试流程，重新识别当前场景后从正确的阶段重新开始

---

## 工具依赖

| 工具名称 | 用途 | 使用步骤 |
|----------|------|----------|
| `focus_bh3_window` | 聚焦游戏窗口 | 1 |
| `yolo_list_models` | 列出可用模型及加载状态 | 2, 7, 13, 19 |
| `yolo_load_model` | 加载 YOLO 模型 | 3, 8, 14, 20 |
| `yolo_unload_model` | 卸载 YOLO 模型释放显存 | 按需使用 |
| `yolo_classify_image` | 场景分类识别 | 4, 21, 23 |
| `yolo_detect_image` | UI 元素检测 | 9, 15 |
| `click_coordinates` | 点击坐标 | 11, 17 |
