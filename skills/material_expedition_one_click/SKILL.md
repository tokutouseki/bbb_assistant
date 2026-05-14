---
name: material_expedition_one_click
description: 材料远征一键减负技能 - 自动导航到材料活动界面并完成两次一键减负点击。
phases: 阶段一：定位到舰桥, 阶段二：导航到出击界面, 阶段三：激活出击界面（如需要）, 阶段四：进入材料活动界面, 阶段五：执行两次一键减负, 阶段六：返回舰桥
---

# 材料远征一键减负技能

## When to Use

当用户请求以下操作时使用此技能：
- "材料远征一键减负"
- "一键完成材料远征"
- "帮我做一下材料活动减负"
- "材料远征减负"
- "材料活动一键减负"

## 概述

此技能用于自动化完成材料远征的一键减负操作。从舰桥导航到出击界面，点击材料活动进入，执行两次一键减负点击（第一次开始减负，第二次确认完成），最后返回舰桥。

每个步骤只包含单一不可拆分的操作（一次工具调用或一次判断），不嵌套子步骤。

## 技能流程

### 阶段零：断点恢复检查

> **目的**：如果上次执行中断，从检查点恢复而不需要从头开始。检查点文件路径为 `outputs/task_checkpoint.json`。

**步骤 0a** — 检查是否存在任务检查点

读取 `outputs/task_checkpoint.json` 文件：
- 文件不存在 → 执行步骤 0b，从头开始
- 文件存在且 `skill` 字段为 `material_expedition_one_click` → 跳到步骤 0c，从断点恢复
- 文件存在但 `skill` 字段为其他技能 → 这是其他任务的检查点，执行步骤 0b

**步骤 0b** — 初始化新任务

创建初始检查点（后续各阶段会更新）：

调用 Write 工具写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 0,
  "phase_name": "初始化",
  "scene": "unknown",
  "context_summary": "任务刚开始，准备定位到舰桥",
  "completed_phases": [],
  "updated_at": "<当前ISO时间>"
}
```
然后跳到阶段一（步骤 1）。

**步骤 0c** — 从断点恢复

读取检查点文件内容，根据 `current_phase` 值跳转到对应阶段：

| current_phase | 跳转位置 | 说明 |
|---------------|----------|------|
| 1 | 阶段一末尾（步骤 6 之后） | 舰桥已确认，重新验证后继续 |
| 2 | 阶段二末尾（步骤 12 之后） | 出击界面已到达，重新验证后继续 |
| 3 | 阶段三末尾（步骤 17 之后） | 出击界面已激活，重新验证后继续 |
| 4 | 阶段四末尾（步骤 20 之后） | 已进入材料活动，重新检测后继续 |
| 5 | 阶段五（步骤 22 处判断） | 根据检查点中的 click_count 决定第几次点击 |
| 6 | 阶段六末尾（步骤 35） | 任务已完成，验证后汇报 |

**恢复流程**：
1. 先执行步骤 1（focus_bh3_window）、步骤 2（yolo_list_models）
2. 加载 `yolo11n_scene_cls`，调用 `yolo_classify_image` 验证当前场景是否与检查点中的 `scene` 字段一致
3. 一致则根据上表跳转；不一致则从阶段一重新开始

> **上下文刷新**：从断点恢复后，无需回顾此前各步骤的详细执行历史。检查点文件中的 `context_summary` 和 `scene` 字段已包含继续执行所需的全部上下文。

---

### 阶段一：定位到舰桥

**步骤 1** — 聚焦游戏窗口

调用 `focus_bh3_window` 工具，确保崩坏3游戏窗口处于活动状态并可以接收操作。这是必须执行的第一步。

**步骤 2** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具，查看所有可用的 YOLO 模型以及哪些模型已经加载到显存中。

**步骤 3** — 加载场景分类模型（如未加载）

从步骤 2 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 4
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 加载场景分类模型

**步骤 4** — 识别当前游戏场景

调用 `yolo_classify_image yolo11n_scene_cls` 对当前游戏窗口截图进行场景分类，获取当前所在的场景英文名称和中文名称。

**步骤 5** — 判断：当前场景是否为 bridge（舰桥界面）？

根据步骤 4 返回的场景英文名称判断：
- 是 bridge → 跳到步骤 7，开始导航到出击界面
- 不是 bridge → 执行步骤 6

**步骤 6** — 前往舰桥界面

参考 find_direction 技能，了解如何返回舰桥界面。find_direction 技能描述了通过寻找 button_bridge 或按 ESC 逐级返回的方式来回到舰桥的方法。按其中的方法回到舰桥后，回到步骤 4 重新验证当前场景。

**阶段一完成检查点** — 写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 1,
  "phase_name": "舰桥已确认",
  "scene": "bridge",
  "context_summary": "已在舰桥界面(bridge)，舰桥检测模型已加载，下一步从舰桥导航到出击界面",
  "completed_phases": ["定位到舰桥"],
  "updated_at": "<当前ISO时间>"
}
```

> 🔄 **上下文刷新点**：阶段一已结束。阶段二只需要知道：① 当前在舰桥(bridge)；② `yolo11n_bridge_ui_det` 已加载。不再需要阶段一步骤 1-6 的详细执行历史。从阶段二的步骤 7 开始执行。

---

### 阶段二：导航到出击界面

**步骤 7** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。

**步骤 8** — 加载舰桥检测模型（如未加载）

从步骤 7 的返回结果中检查 `yolo11n_bridge_ui_det` 是否已加载：
- 如果已加载 → 跳到步骤 9
- 如果未加载 → 调用 `yolo_load_model yolo11n_bridge_ui_det` 加载舰桥界面 UI 元素检测模型

**步骤 9** — 识别舰桥界面中的出击按钮

调用 `yolo_detect_image yolo11n_bridge_ui_det` 对当前游戏窗口截图进行 UI 元素检测。从检测结果中查找 `button_attack`（出击按钮），记录其 bbox 坐标 [x1, y1, x2, y2]。

**步骤 10** — 点击出击按钮

从步骤 9 的检测结果中找到 `button_attack`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标：center_x = (x1 + x2) / 2，center_y = (y1 + y2) / 2
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 11** — 等待界面切换

等待 1-2 秒，让游戏从舰桥界面切换到出击界面。

**步骤 12** — 验证已到达出击界面

调用 `yolo_classify_image yolo11n_scene_cls`（确保场景分类模型仍加载）识别当前场景。判断返回的场景英文名称是否为 attack：
- 是 attack → 执行步骤 13，进入出击界面操作
- 不是 attack → 回到步骤 9 重试（如果已重试 3 次仍失败，告知用户手动操作）

**阶段二完成检查点** — 写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 2,
  "phase_name": "出击界面已到达",
  "scene": "attack",
  "context_summary": "已在出击界面(attack)，准备检测出击界面激活状态并激活",
  "completed_phases": ["定位到舰桥", "导航到出击界面"],
  "updated_at": "<当前ISO时间>"
}
```

> 🔄 **上下文刷新点**：阶段二已结束。阶段三只需要知道：① 当前在出击界面(attack)；② 需要加载 `yolo11n_attack_ui_det`。不再需要阶段一和阶段二的详细执行历史。从阶段三的步骤 13 开始执行。

---

### 阶段三：激活出击界面（如需要）

**步骤 13** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。

**步骤 14** — 加载出击检测模型（如未加载）

从步骤 13 的返回结果中检查 `yolo11n_attack_ui_det` 是否已加载：
- 如果已加载 → 跳到步骤 15
- 如果未加载 → 调用 `yolo_load_model yolo11n_attack_ui_det` 加载出击界面 UI 元素检测模型

**步骤 15** — 识别出击界面元素

调用 `yolo_detect_image yolo11n_attack_ui_det` 对当前游戏窗口截图进行 UI 元素检测。重点查找以下元素：
- `button_strike_active`（出击界面已激活，说明无需额外操作）
- `button_strike_inactive`（出击界面未激活，需要点击激活）
- `button_material_event`（材料活动按钮，后续步骤需要）

**步骤 16** — 判断：出击界面是否已激活？

从步骤 15 的检测结果中查找 `button_strike_active`：
- 存在 `button_strike_active` → 界面已激活，跳到步骤 18（直接进入材料活动）
- 不存在 → 执行步骤 17（需要先点击激活出击界面）

**步骤 17** — 点击激活出击界面

从步骤 15 的检测结果中找到 `button_strike_inactive`（出击界面未激活按钮）：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

然后等待 1-2 秒让界面激活，重新调用 `yolo_detect_image yolo11n_attack_ui_det` 验证 `button_strike_active` 已出现后再继续。

**阶段三完成检查点** — 写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 3,
  "phase_name": "出击界面已激活",
  "scene": "attack",
  "context_summary": "出击界面已激活(button_strike_active可见)，attack_ui_det已加载，下一步点击材料活动按钮",
  "completed_phases": ["定位到舰桥", "导航到出击界面", "激活出击界面"],
  "key_data": {
    "attack_activated": true
  },
  "updated_at": "<当前ISO时间>"
}
```

> 🔄 **上下文刷新点**：阶段三已结束。阶段四只需要知道：① 当前在出击界面(attack)；② 界面已激活；③ `yolo11n_attack_ui_det` 已加载。不再需要之前的详细执行历史。从阶段四的步骤 18 开始执行。

---

### 阶段四：进入材料活动界面

**步骤 18** — 从检测结果中定位材料活动按钮

从最近一次 `yolo_detect_image yolo11n_attack_ui_det` 的检测结果中查找 `button_material_event`（材料活动按钮），记录其 bbox 坐标。如果在当前检测结果中找不到此按钮，回到步骤 15 重新检测。

**步骤 19** — 点击材料活动按钮

从检测结果中找到 `button_material_event`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 20** — 等待界面切换

等待 1-2 秒，让游戏从出击界面切换到材料活动子界面。材料活动界面使用的是出击检测模型。

**阶段四完成检查点** — 写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 4,
  "phase_name": "已进入材料活动",
  "scene": "attack",
  "context_summary": "已在材料活动子界面，attack_ui_det已加载，下一步检测button_one_click并执行第一次减负点击",
  "completed_phases": ["定位到舰桥", "导航到出击界面", "激活出击界面", "进入材料活动"],
  "key_data": {
    "in_material_event": true
  },
  "updated_at": "<当前ISO时间>"
}
```

> 🔄 **上下文刷新点**：阶段四已结束。阶段五只需要知道：① 当前在材料活动子界面；② `yolo11n_attack_ui_det` 已加载；③ 需要执行两次 button_one_click 点击。从阶段五的步骤 21 开始执行。

---

### 阶段五：执行两次一键减负

> **关键**：一键减负需要点击两次 button_one_click，两次的按钮位置不同。第一次点击开始减负流程，第二次点击确认完成。每次点击前都需要重新识别界面。

**步骤 21** — 识别材料活动界面

调用 `yolo_detect_image yolo11n_attack_ui_det` 对当前游戏窗口截图进行 UI 元素检测。从检测结果中查找 `button_one_click`（一键减负按钮），记录其 bbox 坐标。

**步骤 22** — 判断：是否检测到 button_one_click？

根据步骤 21 的检测结果判断：
- 检测到 `button_one_click` → 执行步骤 23
- 未检测到 → 可能不在材料活动界面，回到步骤 15 重新识别出击界面并确认是否成功进入材料活动

**步骤 23** — 第一次点击一键减负按钮

从步骤 21 的检测结果中找到 `button_one_click`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]，保存为旧位置
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 24** — 等待界面响应

等待 1-2 秒，让一键减负流程开始，界面发生变化。

**阶段五中途检查点（第一次点击完成）** — 写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 5,
  "phase_name": "第一次减负点击已完成",
  "scene": "attack",
  "click_count": 1,
  "context_summary": "第一次一键减负已点击，旧bbox已保存，下一步重新识别界面验证按钮位置变化",
  "completed_phases": ["定位到舰桥", "导航到出击界面", "激活出击界面", "进入材料活动"],
  "key_data": {
    "first_click_done": true,
    "old_bbox": "<步骤23保存的旧bbox>"
  },
  "updated_at": "<当前ISO时间>"
}
```

**步骤 25** — 重新识别当前界面

调用 `yolo_detect_image yolo11n_attack_ui_det` 重新识别界面。第一次点击后 button_one_click 的位置会发生移动（界面弹出了确认对话框或按钮位移），需要获取最新的位置。从检测结果中查找 `button_one_click` 的新位置，记录新的 bbox 坐标。

**步骤 26** — 验证按钮位置已变化

对比步骤 25 中 button_one_click 的新 bbox 坐标与步骤 23 保存的旧 bbox 坐标：
- 新位置与旧位置不同 → 第一次点击生效，界面已变化，执行步骤 27
- 新位置与旧位置相同 → 第一次点击可能未生效，回到步骤 23 重新点击

**步骤 27** — 第二次点击一键减负按钮

从步骤 25 的检测结果中找到 `button_one_click` 的新位置：
- 提取该按钮的新 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 28** — 等待界面响应

等待 1-2 秒，让第二次一键减负确认操作完成，材料远征减负处理完毕。

**阶段五完成检查点** — 写入 `outputs/task_checkpoint.json`：
```json
{
  "skill": "material_expedition_one_click",
  "current_phase": 5,
  "phase_name": "两次减负均已完成",
  "scene": "attack",
  "click_count": 2,
  "context_summary": "材料远征一键减负已处理完毕，下一步返回舰桥",
  "completed_phases": ["定位到舰桥", "导航到出击界面", "激活出击界面", "进入材料活动", "完成减负点击"],
  "key_data": {
    "both_clicks_done": true
  },
  "updated_at": "<当前ISO时间>"
}
```

> 🔄 **上下文刷新点**：阶段五已结束。阶段六只需要知道：① 减负已完成；② 当前在材料活动/出击界面；③ `yolo11n_attack_ui_det` 已加载；④ 需要查找 button_bridge 返回舰桥。从阶段六的步骤 29 开始执行。

---

### 阶段六：返回舰桥

**步骤 29** — 识别当前界面元素

调用 `yolo_detect_image yolo11n_attack_ui_det` 识别当前界面。从检测结果中查找 `button_bridge`（前往舰桥按钮），记录其 bbox 坐标。

**步骤 30** — 判断：是否检测到 button_bridge？

根据步骤 29 的检测结果判断：
- 检测到 `button_bridge` → 执行步骤 31（点击返回舰桥）
- 未检测到 → 调用 `press_key key='escape'` 按 ESC 键返回上级界面，等待 1-2 秒后重新执行步骤 29

**步骤 31** — 点击返回舰桥按钮

从步骤 29 的检测结果中找到 `button_bridge`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 32** — 等待界面切换

等待 1-2 秒，让游戏切换回舰桥界面。

**步骤 33** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。

**步骤 34** — 加载场景分类模型（如未加载）

从步骤 33 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 35
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 加载

**步骤 35** — 验证已返回舰桥

调用 `yolo_classify_image yolo11n_scene_cls` 识别当前场景。判断返回的场景英文名称是否为 bridge：
- 是 bridge → 流程结束 ✅，汇报用户"材料远征一键减负已完成"
- 不是 bridge → 调用 `press_key key='escape'` 按 ESC 键，等待 1 秒后回到步骤 35 重新验证

**任务完成清理** — 汇报用户"材料远征一键减负已完成"，然后删除检查点文件 `outputs/task_checkpoint.json`（任务已完成，无需保留断点）。

---

## 断点恢复说明

如果执行过程中被中断（上下文窗口耗尽、用户取消等），下次调用本技能时：

1. 阶段零会自动检测 `outputs/task_checkpoint.json`
2. 读取 `current_phase` 和 `context_summary` 确定恢复位置
3. 验证当前游戏场景与检查点记录一致
4. 从对应阶段继续执行，无需重复已完成的步骤

关键设计原则：
- **每个阶段只依赖检查点中的信息**，不依赖对话历史中的步骤细节
- **检查点在阶段边界写入**，确保中断后能恢复到最近的稳定状态
- **阶段五中途额外检查点**，防止两次减负点击之间丢失进度

---

## 完整流程图

```
开始
  ↓
[0a] 读取 outputs/task_checkpoint.json
  ├─ 不存在 → [0b] 初始化检查点
  ├─ 同技能 → [0c] 从检查点恢复 → 跳到对应阶段
  └─ 不同技能 → [0b] 初始化检查点
  ↓
[1] focus_bh3_window
  ↓
[2] yolo_list_models
  ↓
[3] 加载 scene_cls（未加载时）
  ↓
[4] yolo_classify_image → 识别场景
  ↓
[5] {是 bridge?}
  ├─ 否 → [6] find_direction → 回到 [4]
  └─ 是 ↓
★★★ 阶段一完成 → 写入检查点(phase=1) ★★★
  ↓
[7] yolo_list_models
  ↓
[8] 加载 bridge_ui_det（未加载时）
  ↓
[9] yolo_detect_image → 查找 button_attack
  ↓
[10] 提取 button_attack bbox → 计算中心点 → click_coordinates
  ↓
[11] 等待 1-2s
  ↓
[12] yolo_classify_image → 验证 attack
  ├─ 否 → 回到 [9]（最多 3 次）
  └─ 是 ↓
★★★ 阶段二完成 → 写入检查点(phase=2) ★★★
  ↓
[13] yolo_list_models
  ↓
[14] 加载 attack_ui_det（未加载时）
  ↓
[15] yolo_detect_image → 查找 strike_active/inactive, material_event
  ↓
[16] {存在 button_strike_active?}
  ├─ 是 → 跳到 [18]
  └─ 否 ↓
[17] 提取 strike_inactive → click_coordinates → 等待 1-2s → 重新检测验证
  ↓
★★★ 阶段三完成 → 写入检查点(phase=3) ★★★
  ↓
[18] 查找 button_material_event，提取 bbox
  ↓
[19] 计算中心点 → click_coordinates
  ↓
[20] 等待 1-2s
  ↓
★★★ 阶段四完成 → 写入检查点(phase=4) ★★★
  ↓
[21] yolo_detect_image → 查找 button_one_click
  ↓
[22] {找到 button_one_click?}
  ├─ 否 → 回到 [15]
  └─ 是 ↓
[23] 提取 bbox（保存为旧位置）→ 计算中心点 → click_coordinates
  ↓
[24] 等待 1-2s
  ↓
★★★ 中途检查点 → 写入检查点(phase=5, click_count=1) ★★★
  ↓
[25] yolo_detect_image → 查找 button_one_click 新位置
  ↓
[26] {新旧位置不同?}
  ├─ 否 → 回到 [23]
  └─ 是 ↓
[27] 提取新 bbox → 计算中心点 → click_coordinates
  ↓
[28] 等待 1-2s
  ↓
★★★ 阶段五完成 → 写入检查点(phase=5, click_count=2) ★★★
  ↓
[29] yolo_detect_image → 查找 button_bridge
  ↓
[30] {找到 button_bridge?}
  ├─ 否 → press_key ESC → 回到 [29]
  └─ 是 ↓
[31] 提取 bbox → 计算中心点 → click_coordinates
  ↓
[32] 等待 1-2s
  ↓
[33] yolo_list_models
  ↓
[34] 加载 scene_cls（未加载时）
  ↓
[35] yolo_classify_image → 验证 bridge
  ├─ 否 → press_key ESC → 回到 [35]
  └─ 是 ↓
★★★ 任务完成 → 删除检查点，汇报用户 ★★★
```

---

## 关键UI元素说明

| 元素标签 | 中文含义 | 首次出现步骤 |
|----------|----------|-------------|
| button_attack | 出击按钮（舰桥界面） | 步骤 9 |
| button_strike_active | 出击界面已激活 | 步骤 15 |
| button_strike_inactive | 出击界面未激活 | 步骤 15 |
| button_material_event | 材料活动按钮 | 步骤 15 |
| button_one_click | 一键减负按钮 | 步骤 21 |
| button_bridge | 前往舰桥按钮 | 步骤 29 |

---

## 使用示例

```
 1. focus_bh3_window
 2. yolo_list_models → 已加载: scene_cls, bridge_ui_det
 3. scene_cls 已加载 → 跳过
 4. yolo_classify_image yolo11n_scene_cls → "bridge (舰桥界面)"
 5. 判断: 是 bridge → 继续

--- 导航到出击 ---
 7. yolo_list_models → bridge_ui_det 已加载
 8. 跳过加载
 9. yolo_detect_image yolo11n_bridge_ui_det
    → button_attack 在 [500, 300, 600, 400]，置信度 0.91
10. button_attack bbox=[500,300,600,400] → 中心点 (550, 350) → click_coordinates 550, 350
11. 等待 1.5s
12. yolo_classify_image yolo11n_scene_cls → "attack (出击界面)" → 匹配 ✓

--- 激活出击界面 ---
13. yolo_list_models → attack_ui_det 未加载
14. yolo_load_model yolo11n_attack_ui_det
15. yolo_detect_image yolo11n_attack_ui_det
    → button_strike_inactive 在 [200, 200, 300, 300]，置信度 0.89
    → button_material_event 在 [400, 400, 500, 500]，置信度 0.92
16. 判断: 不存在 button_strike_active → 需要激活
17. button_strike_inactive bbox=[200,200,300,300] → 中心点 (250, 250) → click_coordinates 250, 250
    等待 1.5s

--- 进入材料活动 ---
25. yolo_detect_image yolo11n_attack_ui_det
    → button_strike_active 已出现 ✓
    → button_material_event 在 [400, 400, 500, 500]，置信度 0.90
18. 定位 button_material_event: bbox=[400,400,500,500]
19. 中心点 (450, 450) → click_coordinates 450, 450
20. 等待 1.5s

--- 第一次一键减负 ---
21. yolo_detect_image yolo11n_attack_ui_det
    → button_one_click 在 [600, 500, 700, 600]，置信度 0.93
22. 判断: 检测到 button_one_click
23. 保存旧位置 bbox=[600,500,700,600] → 中心点 (650, 550) → click_coordinates 650, 550
24. 等待 1.5s

--- 第二次一键减负 ---
25. yolo_detect_image yolo11n_attack_ui_det
    → button_one_click 在 [650, 550, 750, 650]，置信度 0.91
26. 新bbox [650,550,750,650] ≠ 旧bbox [600,500,700,600] → 位置不同 ✓
27. 新中心点 (700, 600) → click_coordinates 700, 600
28. 等待 1.5s

--- 返回舰桥 ---
29. yolo_detect_image yolo11n_attack_ui_det
    → button_bridge 在 [100, 50, 200, 80]，置信度 0.90
30. 判断: 检测到 button_bridge
31. button_bridge bbox=[100,50,200,80] → 中心点 (150, 65) → click_coordinates 150, 65
32. 等待 1.5s
33. yolo_list_models → scene_cls 已加载
34. 跳过加载
35. yolo_classify_image yolo11n_scene_cls → "bridge (舰桥界面)" → 完成 ✅
```

---

## 注意事项

1. **两次 button_one_click 点击都是必须的**：第一次点击开始减负流程，第二次点击确认完成。不可只点一次
2. **两次点击位置不同**：第一次点击后按钮位置会移动，必须通过步骤 25 重新检测获取新位置，步骤 26 验证位置变化后再点击
3. **步骤 26 位置验证**：如果新旧位置相同说明第一次点击失败，需要回到步骤 23 重试
4. **出击界面激活判断**：步骤 16 检查 button_strike_active 是否存在，存在则跳过激活步骤
5. **每次调用场景分类前检查模型**：步骤 4、步骤 12 和步骤 35 调用 `yolo_classify_image` 前需确认模型已加载
6. **等待时间**：每次点击后必须等待 1-2 秒，不要连续快速点击
7. **找不到 button_material_event 时**：可能需要先切换到"推荐"等子标签，检查是否有 button_recommend_inactive 等按钮并点击

### 异常处理

- **步骤 9 找不到 button_attack**：确认是否真的在舰桥界面，必要时重新识别场景
- **步骤 12 验证不是 attack**：重试点击 button_attack 最多 3 次，超过后建议用户手动操作
- **步骤 17 找不到 button_strike_inactive**：如果也没有 button_strike_active，可能不在正确的出击界面子标签，尝试查找 button_recommend_inactive 并点击切换
- **步骤 22 找不到 button_one_click**：可能未进入材料活动界面，回到步骤 15 重新检测确认
- **步骤 30 找不到 button_bridge**：调用 `press_key key='escape'` 逐级返回上级界面

---

## 工具依赖

| 工具名称 | 用途 | 使用步骤 |
|----------|------|----------|
| `focus_bh3_window` | 聚焦游戏窗口 | 1 |
| `yolo_list_models` | 列出可用模型及加载状态 | 2, 7, 13, 33 |
| `yolo_load_model` | 加载 YOLO 模型 | 3, 8, 14, 34 |
| `yolo_unload_model` | 卸载 YOLO 模型释放显存 | 按需使用 |
| `yolo_classify_image` | 场景分类识别 | 4, 12, 35 |
| `yolo_detect_image` | UI 元素检测 | 9, 15, 21, 25, 29 |
| `click_coordinates` | 点击坐标 | 10, 17, 19, 23, 27, 31 |
| `press_key` | 模拟按键 | 30(异常), 35(异常) |
| `Read` | 读取检查点文件恢复断点 | 0a, 0c |
| `Write` | 写入阶段检查点 | 0b, 各阶段完成后 |
