---
name: club_consignment_recovery
description: 舰团回收委托循环技能 - 自动循环提交舰团回收委托，直到剩余次数≤6为止。
---

# 舰团回收委托循环技能

## When to Use

当用户请求以下操作时使用此技能：
- "舰团委托回收"
- "舰团回收委托"
- "帮我做舰团委托"
- "舰团委托循环提交"
- "club回收委托"

## 概述

此技能用于完成舰团回收委托的循环提交操作。从舰桥导航到舰团界面，进入回收委托，通过循环提交或申请新委托，直到剩余提交次数≤6时结束。不可虚构内容。

每个步骤只包含单一不可拆分的操作（一次工具调用或一次判断），不嵌套子步骤。

## 技能流程

### 阶段一：定位到舰桥

**步骤 1** — 聚焦游戏窗口

调用 `focus_bh3_window` 工具，确保崩坏3游戏窗口处于活动状态并可以接收操作。这是必须执行的第一步，否则后续所有截图和点击操作都将失败。

**步骤 2** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具，查看所有可用的 YOLO 模型以及哪些模型已经加载到显存中。这个步骤可以帮你确认模型状态，后续步骤根据模型加载情况决定是否需要调用 `yolo_load_model`。

**步骤 3** — 加载场景分类模型（如未加载）

从步骤 2 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 4
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 加载场景分类模型

**步骤 4** — 识别当前游戏场景

调用 `yolo_classify_image yolo11n_scene_cls` 对当前游戏窗口截图进行场景分类，获取当前所在的场景英文名称和中文名称。

**步骤 5** — 判断：当前场景是否为 bridge（舰桥界面）？

根据步骤 4 返回的场景英文名称判断：
- 是 bridge → 跳到步骤 7，开始舰桥界面操作
- 不是 bridge → 执行步骤 6

**步骤 6** — 前往舰桥界面

调用 find_direction 技能，知道如何导航到舰桥界面。find_direction 技能会通过寻找舰桥按钮或按 ESC 逐级返回的方式来定位回舰桥。完成后回到步骤 4 重新验证当前场景。

### 阶段二：舰桥界面操作

**步骤 7** — 查看当前已加载的模型列表

再次调用 `yolo_list_models` 工具确认模型状态（因为如果经过了步骤 6 的 find_direction，模型列表可能已经发生了变化）。

**步骤 8** — 加载舰桥检测模型（如未加载）

从步骤 7 的返回结果中检查 `yolo11n_bridge_ui_det` 是否已加载：
- 如果已加载 → 跳到步骤 9
- 如果未加载 → 调用 `yolo_load_model yolo11n_bridge_ui_det` 加载舰桥界面 UI 元素检测模型

**步骤 9** — 识别舰桥界面元素

调用 `yolo_detect_image yolo11n_bridge_ui_det` 对当前游戏窗口截图进行 UI 元素检测。这一步的核心目标是从检测结果中寻找 `button_interaction`（看板娘交互按钮），记录它的 bbox 边界框坐标 [x1, y1, x2, y2]。

**步骤 10** — 调戏看板娘

从步骤 9 的检测结果中找到 `button_interaction`（看板娘交互按钮）：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标：center_x = (x1 + x2) / 2，center_y = (y1 + y2) / 2
- 调用 `click_coordinates` 点击该中心点坐标

此步骤用于排除页面聚焦问题的干扰，是必要步骤不可跳过。

**步骤 11** — 等待界面响应

等待 1-2 秒，让看板娘交互动画播放完毕，界面恢复稳定状态。

**步骤 12** — 重新识别舰桥界面元素

再次调用 `yolo_detect_image yolo11n_bridge_ui_det` 识别当前界面。调戏看板娘后界面可能发生变化，需要重新检测以获取最新的 UI 元素位置。从检测结果中查找 `button_club`（舰团按钮），记录其 bbox 坐标。

**步骤 13** — 点击舰团按钮进入舰团界面

从步骤 12 的检测结果中找到 `button_club`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 14** — 等待界面切换

等待 1-2 秒，让游戏从舰桥界面切换到舰团界面。

### 阶段三：进入委托回收界面

**步骤 15** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。

**步骤 16** — 加载舰团检测模型（如未加载）

从步骤 15 的返回结果中检查 `yolo11n_club_ui_det` 是否已加载：
- 如果已加载 → 跳到步骤 17
- 如果未加载 → 调用 `yolo_load_model yolo11n_club_ui_det` 加载舰团界面 UI 元素检测模型

**步骤 17** — 识别舰团界面元素

调用 `yolo_detect_image yolo11n_club_ui_det` 对当前游戏窗口截图进行 UI 元素检测。从检测结果中查找 `button_consignment_recovery`（前往委托回收按钮），记录其 bbox 坐标。

**步骤 18** — 点击进入委托回收界面

从步骤 17 的检测结果中找到 `button_consignment_recovery`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 19** — 等待界面切换

等待 1-2 秒，让游戏从舰团界面切换到委托回收界面，委托回收界面是舰团界面的子界面，模型是通用的。

### 阶段四：循环提交委托

> **循环说明**：步骤 20 ~ 35 为一次完整提交循环。每轮循环结束后回到步骤 20 重新开始。当步骤 23 判断剩余次数 ≤ 6 时跳出循环，进入阶段五。

**步骤 20** — 识别回收委托界面元素

调用 `yolo_detect_image yolo11n_club_ui_det` 对当前游戏窗口截图进行 UI 元素检测。重点查找以下元素：
- `button_consignment_active`（委托项目活跃中，说明当前有活跃委托可提交）
- `button_consignment_inactive`（委托项目未活跃，说明需要先激活委托项目）
- `button_new_consignment_able`（申请新委托可用按钮）
- `button_submit`（提交按钮）
- `button_accept`（接受回收委托按钮）
- `zone_rest_submit_times`（剩余提交次数显示区域）

**步骤 21** — 定位剩余提交次数区域

从步骤 20 的检测结果中找到 `zone_rest_submit_times`（剩余提交次数显示区域）：
- 提取该区域的 bbox 坐标 [x1, y1, x2, y2]
- 计算该区域的中心点坐标（OCR 需要定位参考点）

**步骤 22** — OCR 识别剩余提交次数

调用 `ocr_recognize` 工具，对步骤 21 确定的 `zone_rest_submit_times` 区域进行光学字符识别（OCR），读取该区域显示的剩余提交次数数值。务必确认识别结果是一个有效的数字。

**步骤 23** — 判断：剩余提交次数是否大于 6？

根据步骤 22 OCR 识别的数值结果判断：
- 剩余次数 ≤ 6 → 跳到步骤 36（退出循环，进入阶段五返回舰桥）
- 剩余次数 > 6 → 执行步骤 24（继续本轮提交操作）

**步骤 24** — 判断当前界面状态：是否存在活跃委托？

从步骤 20 的检测结果中查找 `button_consignment_active`（委托项目活跃中）：
- 存在 → 执行步骤 25（情况 A：有活跃委托，走提交流程）
- 不存在 → 执行步骤 26（情况 B：无活跃委托，走申请新委托流程）

**步骤 25** — 【情况 A】点击提交按钮

从步骤 20 的检测结果中找到 `button_submit`（提交按钮）：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

执行完毕后跳到步骤 27。

**步骤 26** — 【情况 B】点击申请新委托按钮

从步骤 20 的检测结果中找到 `button_new_consignment_able`（申请新委托可用按钮）：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

如果找不到 `button_new_consignment_able`，说明可能已达每日上限，直接跳到步骤 36 返回舰桥。

**步骤 27** — 等待界面响应

等待 1-2 秒，让点击操作的界面变化生效。不要连续快速点击，否则可能导致界面错乱。

**步骤 28** — 重新识别当前界面

调用 `yolo_detect_image yolo11n_club_ui_det` 重新识别界面。点击提交或申请按钮后界面状态已变化（例如弹出了确认对话框或按钮位置发生了位移），需要重新检测获取最新状态。查找确认按钮：
- 情况 A（提交流程）→ 查找 `button_submit`（提交确认按钮）
- 情况 B（申请流程）→ 查找 `button_accept`（接受回收委托按钮）

**步骤 29** — 验证确认按钮位置已变化

对比步骤 28 中确认按钮的新 bbox 坐标与步骤 25/26 中旧 bbox 坐标：
- 新位置与旧位置不同 → 说明上一步点击生效，界面已变化，执行步骤 30
- 新位置与旧位置相同 → 说明上一步点击可能未生效，回到步骤 25/26 重试点击

**步骤 30** — 点击确认按钮

从步骤 28 的检测结果中找到确认按钮的新位置（情况 A 为 button_submit，情况 B 为 button_accept）：
- 提取该按钮的新 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

**步骤 31** — 等待界面响应

等待 1-2 秒，让提交或接受操作完成，界面回到回收委托列表状态。

**步骤 32** — 回到循环起点

回到步骤 20，开始下一轮循环（重新识别界面 → OCR 剩余次数 → 判断是否继续）。

### 阶段五：返回舰桥

**步骤 33** — 识别当前界面元素

调用 `yolo_detect_image yolo11n_club_ui_det` 识别当前界面。从检测结果中查找 `button_bridge`（前往舰桥按钮），记录其 bbox 坐标。

**步骤 34** — 点击返回舰桥按钮

从步骤 33 的检测结果中找到 `button_bridge`：
- 提取该按钮的 bbox 坐标 [x1, y1, x2, y2]
- 计算该按钮的中心点坐标
- 调用 `click_coordinates` 点击该中心点坐标

如果在当前界面找不到 `button_bridge`，调用 `press_key key='escape'` 按 ESC 键回到上级界面，然后重新执行步骤 33。

**步骤 35** — 等待界面切换

等待 1-2 秒，让游戏切换回舰桥界面。

**步骤 36** — 查看当前已加载的模型列表

调用 `yolo_list_models` 工具确认模型状态。

**步骤 37** — 加载场景分类模型（如未加载）

从步骤 36 的返回结果中检查 `yolo11n_scene_cls` 是否已加载：
- 如果已加载 → 跳到步骤 38
- 如果未加载 → 调用 `yolo_load_model yolo11n_scene_cls` 加载场景分类模型

**步骤 38** — 验证已返回舰桥

调用 `yolo_classify_image yolo11n_scene_cls` 识别当前场景。判断返回的英文名称是否为 bridge：
- 是 bridge → 流程结束 ✅，汇报用户"舰团回收委托循环已完成"
- 不是 bridge → 调用 `press_key key='escape'` 按 ESC 键，等待 1 秒后回到步骤 38 重新验证

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
[5] {是 bridge?}
  ├─ 否 → [6] find_direction → 回到 [4]
  └─ 是 ↓
[7] yolo_list_models
  ↓
[8] 加载 bridge_ui_det（未加载时）
  ↓
[9] yolo_detect_image → 查找 button_club, button_interaction
  ↓
[10] 提取 button_interaction bbox → 计算中心点 → click_coordinates
  ↓
[11] 等待 1-2s
  ↓
[12] yolo_detect_image → 查找 button_club
  ↓
[13] 提取 button_club bbox → 计算中心点 → click_coordinates
  ↓
[14] 等待 1-2s
  ↓
[15] yolo_list_models
  ↓
[16] 加载 club_ui_det（未加载时）
  ↓
[17] yolo_detect_image → 查找 button_consignment_recovery
  ↓
[18] 提取 bbox → 计算中心点 → click_coordinates
  ↓
[19] 等待 1-2s
  ↓
┌──────────────────────────────────────────────┐
│ [20] yolo_detect_image → 查找全部回收界面元素  │
│        ↓                                     │
│ [21] 定位 zone_rest_submit_times bbox         │
│        ↓                                     │
│ [22] ocr_recognize → 识别剩余次数             │
│        ↓                                     │
│ [23] {剩余次数 > 6?}                          │
│  ├─ 否 → 跳到 [33] 退出循环                   │
│  └─ 是 ↓                                     │
│ [24] {存在 button_consignment_active?}        │
│  ├─ 是 → [25] 提取 button_submit → click     │
│  └─ 否 → [26] 提取 new_consignment_able → click│
│        ↓                                     │
│ [27] 等待 1-2s                                │
│        ↓                                     │
│ [28] yolo_detect_image → 查找确认按钮 新位置   │
│        ↓                                     │
│ [29] {新旧位置不同?}                           │
│  ├─ 否 → 回到 [25/26] 重试                    │
│  └─ 是 ↓                                     │
│ [30] 提取确认按钮 新bbox → click_coordinates   │
│        ↓                                     │
│ [31] 等待 1-2s                                │
│        ↓                                     │
│ [32] 回到 [20] ──────────────────────────────┘
│
└── → [33] yolo_detect_image → 查找 button_bridge
         ↓
     [34] 提取 bbox → click_coordinates
         (若找不到则 press_key ESC → 回到 [33])
         ↓
     [35] 等待 1-2s
         ↓
     [36] yolo_list_models
         ↓
     [37] 加载 scene_cls（未加载时）
         ↓
     [38] yolo_classify_image → 验证 bridge
       ├─ 否 → press_key ESC → 回到 [38]
       └─ 是 → 完成 ✅
```

---

## 关键UI元素说明

| 元素标签 | 中文含义 | 首次出现步骤 |
|----------|----------|-------------|
| button_interaction | 看板娘交互按钮 | 步骤 9 |
| button_club | 舰团按钮 | 步骤 9 |
| button_consignment_recovery | 前往委托回收按钮 | 步骤 17 |
| button_consignment_active | 委托项目活跃中 | 步骤 20 |
| button_consignment_inactive | 委托项目未活跃 | 步骤 20 |
| button_new_consignment_able | 申请新委托可用按钮 | 步骤 20 |
| button_submit | 提交按钮 | 步骤 20 |
| button_accept | 接受回收委托按钮 | 步骤 20 |
| zone_rest_submit_times | 剩余提交次数区域 | 步骤 20 |
| button_bridge | 前往舰桥按钮 | 步骤 33 |

---

## 使用示例

```
 1. focus_bh3_window
 2. yolo_list_models → 当前已加载: yolo11n_bridge_ui_det, yolo11n_club_ui_det
 3. scene_cls 未加载 → yolo_load_model yolo11n_scene_cls
 4. yolo_classify_image yolo11n_scene_cls → "bridge (舰桥界面)"
 5. 判断: 是 bridge → 继续
 7. yolo_list_models → bridge_ui_det 已加载
 8. 跳过加载
 9. yolo_detect_image yolo11n_bridge_ui_det
    → button_club 在 [150, 900, 300, 950]，置信度 0.89
    → button_interaction 在 [400, 400, 500, 500]，置信度 0.91
10. button_interaction bbox=[400,400,500,500] → 中心点 (450, 450) → click_coordinates 450, 450
11. 等待 1.5s
12. yolo_detect_image yolo11n_bridge_ui_det
    → button_club 在 [150, 900, 300, 950]，置信度 0.87
13. button_club bbox=[150,900,300,950] → 中心点 (225, 925) → click_coordinates 225, 925
14. 等待 1.5s
15. yolo_list_models → club_ui_det 已加载
16. 跳过加载
17. yolo_detect_image yolo11n_club_ui_det
    → button_consignment_recovery 在 [400, 500, 500, 550]，置信度 0.92
18. bbox=[400,500,500,550] → 中心点 (450, 525) → click_coordinates 450, 525
19. 等待 1.5s

--- 循环开始（第1轮）---

20. yolo_detect_image yolo11n_club_ui_det
    → button_consignment_active 在 [300, 200, 450, 260]，置信度 0.88
    → button_submit 在 [600, 400, 700, 450]，置信度 0.93
    → zone_rest_submit_times 在 [800, 100, 900, 130]，置信度 0.85
21. zone_rest_submit_times bbox=[800, 100, 900, 130]
22. ocr_recognize → "剩余 8 次" → 数值 = 8
23. 判断: 8 > 6 → 继续提交
24. 判断: 存在 button_consignment_active → 情况 A
25. button_submit bbox=[600,400,700,450] → 中心点 (650, 425) → click_coordinates 650, 425
27. 等待 1.5s
28. yolo_detect_image yolo11n_club_ui_det
    → button_submit 在 [650, 450, 750, 500]，置信度 0.91
29. 新bbox [650,450,750,500] ≠ 旧bbox [600,400,700,450] → 位置不同，继续
30. 新中心点 (700, 475) → click_coordinates 700, 475
31. 等待 1.5s
32. 回到步骤 20

--- 循环（第2轮）---

20. yolo_detect_image yolo11n_club_ui_det
    → button_consignment_active 在 [300, 200, 450, 260]
    → button_submit 在 [600, 400, 700, 450]
    → zone_rest_submit_times 在 [800, 100, 900, 130]
21. zone_rest_submit_times bbox=[800, 100, 900, 130]
22. ocr_recognize → "剩余 5 次" → 数值 = 5
23. 判断: 5 ≤ 6 → 退出循环

--- 返回舰桥 ---

33. yolo_detect_image yolo11n_club_ui_det
    → button_bridge 在 [100, 50, 200, 80]，置信度 0.90
34. button_bridge bbox=[100,50,200,80] → 中心点 (150, 65) → click_coordinates 150, 65
35. 等待 1.5s
36. yolo_list_models → scene_cls 已加载
37. 跳过加载
38. yolo_classify_image yolo11n_scene_cls → "bridge (舰桥界面)" → 完成 ✅
```

---

## 注意事项

1. **步骤 5 和步骤 38 的场景验证**：这两处都需要先用 `yolo_list_models` 检查模型状态，确认 `yolo11n_scene_cls` 已加载后再调用 `yolo_classify_image`
2. **循环结束条件**：剩余次数 ≤ 6 时停止循环，进入阶段五返回舰桥
3. **每次操作必须重新识别**：按钮位置在每次点击后可能改变，不要复用旧的检测结果
4. **步骤 29 的位置对比**：如果新旧 bbox 位置完全相同，说明步骤 25/26 的点击没有生效，需要重试
5. **步骤 24 的判断**：有 button_consignment_active 走步骤 25 的提交流程，没有则走步骤 26 申请新委托流程
6. **等待时间**：每次点击后必须等待 1-2 秒，给游戏界面足够的响应时间，不要连续快速点击
7. **步骤 26 异常**：如果找不到 button_new_consignment_able，说明可能已达每日委托上限，直接跳到步骤 33 返回舰桥

### 异常处理

- **步骤 4 场景识别不是 bridge**：参考 find_direction 技能了解如何返回舰桥，然后重新验证
- **步骤 17 找不到 button_consignment_recovery**：可能不在舰团界面，确认当前场景是否正确，必要时按 ESC 退回上级重新导航
- **步骤 22 OCR 无法识别数字**：检查 zone_rest_submit_times 区域的 bbox 是否正确，可能需要重新检测后再 OCR
- **步骤 33 找不到 button_bridge**：调用 `press_key key='escape'` 按 ESC 键逐级返回，然后重新检测
- **步骤 38 验证不是 bridge**：调用 `press_key key='escape'` 按 ESC 键，等待 1 秒后重新验证

---

## 工具依赖

| 工具名称 | 用途 | 使用步骤 |
|----------|------|----------|
| `focus_bh3_window` | 聚焦游戏窗口 | 1 |
| `yolo_list_models` | 列出可用模型及加载状态 | 2, 7, 15, 36 |
| `yolo_load_model` | 加载指定 YOLO 模型 | 3, 8, 16, 37 |
| `yolo_classify_image` | 场景分类识别 | 4, 38 |
| `yolo_detect_image` | UI 元素检测 | 9, 12, 17, 20, 28, 33 |
| `ocr_recognize` | OCR 识别剩余次数 | 22 |
| `click_coordinates` | 点击指定坐标 | 10, 13, 18, 25, 26, 30, 34 |
| `press_key` | 模拟按键（ESC 返回） | 34(异常), 38(异常) |
