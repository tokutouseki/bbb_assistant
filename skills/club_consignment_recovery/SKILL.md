---
name: club_consignment_recovery
description: 舰团回收委托循环技能 - 自动循环提交舰团回收委托，直到剩余次数≤6为止。


# 舰团回收委托循环技能

## When to Use

当用户请求以下操作时使用此技能：
- "舰团委托回收"
- "舰团回收委托"
- "帮我做舰团委托"
- "舰团委托循环提交"
- "club回收委托"

## 概述

此技能用于完成舰团回收委托的循环提交操作。从舰桥导航到舰团界面，进入回收委托，通过循环提交或申请新委托，直到剩余提交次数≤6时结束。不可以虚构内容

## 技能流程

### 1. ⚠️ 聚焦游戏窗口（必须执行）
**重要：此步骤必须首先执行，不能跳过！**
使用 `focus_bh3_window` 工具确保游戏窗口处于活动状态

### 2. 前往舰桥（主界面）
**确保当前在舰桥界面**，如果不在，需要先回到舰桥：
- 使用场景分类模型 `yolo11n_scene_cls` 确认当前场景
- 如果不是 bridge，使用找到方向技能或按 ESC 逐级返回
- 确保最终到达 bridge 界面

### 3. 查看并加载舰桥检测模型
查看可用模型 `yolo_list_models`，检查 `yolo11n_bridge_ui_det` 是否已加载：
- 如果未加载，使用 `yolo_load_model yolo11n_bridge_ui_det` 加载

### 4. 识别舰桥界面元素
使用 `yolo_detect_image yolo11n_bridge_ui_det` 识别当前界面的UI元素：
- 查找 `button_club`（舰团按钮）
- 查找 `button_interaction`（看板娘交互按钮）

### 5. ⚠️ 调戏看板娘（必要步骤）
**重要：此步骤用于排除页面聚焦问题的干扰！**
从识别结果中找到 `button_interaction`：
- 提取 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮调戏看板娘
- 等待1-2秒让界面响应

### 6. 重新识别舰桥界面元素
**再次识别以确保界面状态正确：**
使用 `yolo_detect_image yolo11n_bridge_ui_det` 重新识别当前界面的UI元素：
- 查找 `button_club`（舰团按钮）

### 7. 点击舰团按钮
从识别结果中找到 `button_club`：
- 提取 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮
- 等待1-2秒让界面切换

### 8. 使用 club 识别模型识别当前界面
使用 `yolo_list_models` 检查 `yolo11n_club_ui_det` 是否已加载
- 如果未加载，使用 `yolo_load_model yolo11n_club_ui_det` 加载
- 使用 `yolo_detect_image yolo11n_club_ui_det` 识别当前界面的UI元素
- 查找 `button_consignment_recovery`（前往委托回收按钮）
- 查找 `button_consignment_interface_active` 或 `button_consignment_interface_inactive`

### 9. 点击委托回收按钮
从识别结果中找到 `button_consignment_recovery`：
- 提取 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮
- 等待1-2秒让界面切换到回收委托界面

### 10. 使用 club 识别模型识别回收委托界面
使用 `yolo_detect_image yolo11n_club_ui_det` 识别回收委托界面的UI元素：
- 查找 `button_consignment_active`（委托项目活跃中）
- 查找 `button_consignment_inactive`（委托项目未活跃）
- 查找 `button_new_consignment_able`（申请新委托可用按钮）
- 查找 `button_submit`（提交按钮）
- 查找 `button_accept`（接受回收委托按钮）
- 查找 `zone_rest_submit_times`（剩余提交次数区域）

### 11. OCR 识别剩余提交次数，决定是否继续
对 `zone_rest_submit_times` 区域进行OCR识别：
- 提取 `zone_rest_submit_times` 的 bbox 坐标 [x1, y1, x2, y2]
- 使用 `ocr_recognize` 对该区域进行文字识别
- **判断剩余次数的值**：
  - **如果 > 6**：继续执行第12步及后续循环
  - **如果 ≤ 6**：跳转到第16步，准备返回 bridge

### 12. 判断界面状态并操作
**依据第10步的检测结果**：

**情况A：存在 button_consignment_active（委托项目活跃中）**
- 说明当前有活跃的委托可以提交
- 找到 `button_submit`（提交按钮）
- 提取 button_submit 的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击 button_submit
- 等待1-2秒

**情况B：不存在 button_consignment_active**
- 说明需要申请一个新的委托
- 找到 `button_new_consignment_able`（申请新委托可用按钮）
- 提取 button_new_consignment_able 的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮
- 等待1-2秒

### 13. 使用 club 识别模型识别当前界面
使用 `yolo_detect_image yolo11n_club_ui_det` 重新识别界面：
- 确认界面状态变化
- 查找 `button_submit`对应情况A 或 `button_accept`对应情况B

### 14. 点击提交或接受按钮
**重要：此步骤的按钮位置与第12步不同！如果位置相同说明第12步点击失败！**

- 查找 `button_submit` 或 `button_accept` 的新位置
- 提取新的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- **对比确认新位置与第12步位置不同**
- 使用 `click_coordinates` 点击新位置的按钮
- 等待1-2秒

### 15. 重复循环（步骤10-14）
回到步骤10，继续执行循环：
- 重新识别界面
- OCR 识别 zone_rest_submit_times
- 判断是否 > 6
- 执行提交/申请操作
- **直到 zone_rest_submit_times 显示 ≤ 6，则停止循环**

### 16. 返回舰桥界面
完成委托提交后，返回到舰桥界面：
- 查找 `button_bridge`（前往舰桥按钮）并点击，或
- 使用 `press_key` 按 ESC 逐级返回，或
- 使用找到方向技能返回舰桥界面
- 确认返回 bridge

---

## 关键UI元素说明

| 元素标签 | 中文含义 | 用途 |
|----------|----------|------|
| button_interaction | 看板娘交互按钮 | 调戏看板娘，排除页面聚焦问题干扰 |
| button_club | 舰团按钮 | 在舰桥界面点击进入舰团 |
| button_consignment_recovery | 前往委托回收按钮 | 在舰团界面点击进入回收委托 |
| button_consignment_active | 委托项目活跃中 | 说明当前有活跃委托可提交 |
| button_consignment_inactive | 委托项目未活跃 | 需要先点击激活委托项目 |
| button_new_consignment_able | 申请新委托可用按钮 | 点击申请一个新委托 |
| button_submit | 提交按钮 | 提交当前委托 |
| button_accept | 接受回收委托按钮 | 接受回收委托 |
| zone_rest_submit_times | 剩余提交次数区域 | OCR识别具体次数，判断是否继续 |
| button_bridge | 前往舰桥按钮 | 返回主界面 |

---

## 完整流程图

```
开始
  ↓
[1] ⚠️ 聚焦游戏窗口
  ↓
[2] 确认/前往舰桥界面
  ↓
[3] 加载舰桥检测模型
  ↓
[4] 识别舰桥界面元素
  ↓
[5] ⚠️ 调戏看板娘（排除聚焦问题）
  ↓
[6] 重新识别舰桥界面元素
  ↓
[7] 点击 button_club
  ↓
[8] 加载 club 检测模型并识别界面
  ↓
[9] 点击 button_consignment_recovery
  ↓
┌──────────────────────────────────┐
│  [10] 识别回收委托界面            │
│       ↓                          │
│  [11] OCR 识别剩余提交次数        │
│       ↓                          │
│  {zone_rest_submit_times ≤ 6?}   │
│    ├─ 是 → [16] 返回 bridge ✅   │
│    │                             │
│    └─ 否 → [12] 判断界面状态     │
│              ├─ 有 active →       │
│              │  点击 button_submit│
│              └─ 无 active →       │
│                 点击 new_able     │
│              ↓                   │
│        [13] 重新识别界面          │
│              ↓                   │
│   [14] 点击 button_submit/accept │
│       （位置与步骤12不同）         │
│              ↓                   │
│      [15] 回到步骤 [10] 循环 ─────┘
│
└── → [16] 返回舰桥界面
           ↓
         结束 ✅
```

---

## 使用示例

### 示例：完整的舰团回收委托循环流程

```
1. 聚焦窗口: focus_bh3_window
2. 确认在舰桥: yolo_classify_image yolo11n_scene_cls
   → bridge (舰桥界面) ✓
3. 加载舰桥模型: yolo_load_model yolo11n_bridge_ui_det
4. 识别舰桥: yolo_detect_image yolo11n_bridge_ui_det
   → 找到: button_club at [150, 900, 300, 950]
   → 找到: button_interaction at [400, 400, 500, 500]
5. 调戏看板娘: click_coordinates 450, 450
6. 重新识别舰桥: yolo_detect_image yolo11n_bridge_ui_det
   → 找到: button_club at [150, 900, 300, 950]
7. 点击舰团: click_coordinates 225, 925
8. 加载模型: yolo_load_model yolo11n_club_ui_det
   → 识别: button_consignment_recovery at [400, 500, 500, 550]
9. 点击回收: click_coordinates 450, 525
10. 识别回收界面: yolo_detect_image yolo11n_club_ui_det
    → 找到: button_consignment_active
    → 找到: button_submit at [600, 400, 700, 450]
    → 找到: zone_rest_submit_times at [800, 100, 900, 130]
11. OCR识别次数: ocr_recognize 区域 zone_rest_submit_times
    → 当前剩余: 8 次 ( > 6，继续 )
12. 点击提交: click_coordinates 650, 425
13. 重新识别: yolo_detect_image yolo11n_club_ui_det
    → 找到: button_submit at [650, 450, 750, 500] (位置改变)
14. 点击提交: click_coordinates 700, 475
15. 循环: 回到步骤10
    → 识别回收界面
    → OCR识别次数: 5 次 ( ≤ 6，停止循环 )
16. 返回舰桥: 点击 button_bridge 或 press_key ESC
17. 完成 ✅
```

---

## 注意事项

### 关键提醒
1. **循环条件**：zone_rest_submit_times > 6 才执行循环，≤ 6 就结束
2. **每次操作必须重新识别**：按钮位置在每次操作后可能会改变
3. **调戏看板娘**：第5步调戏看板娘是必要步骤，用于排除页面聚焦问题干扰
4. **第12步和第14步的按钮位置不同**：
   - 如果两次位置相同，说明第12步的点击失败了
   - 需要重新执行第12步
5. **button_consignment_active 判断**：
   - 有活跃委托 → 直接点击 button_submit
   - 无活跃委托 → 点击 button_new_consignment_able 申请新委托
6. **等待时间**：
   - 每次点击后等待1-2秒，让界面完全切换
   - 不要连续快速点击
7. **OCR 识别**：
   - zone_rest_submit_times 区域的文字需要通过OCR识别具体数值
   - 确保OCR能正确识别数字

### 异常处理
- 如果在舰团界面找不到 button_consignment_recovery：
  - 检查是否真的在舰团界面
  - 可能需要点击 button_consignment_interface_inactive 激活接口
- 如果 button_new_consignment_able 不可用：
  - 可能已达到每日上限
  - 结束流程返回 bridge

---

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `focus_bh3_window` | 聚焦游戏窗口 |
| `yolo_list_models` | 列出可用模型 |
| `yolo_load_model` | 加载YOLO模型 |
| `yolo_classify_image` | 场景分类识别 |
| `yolo_detect_image` | UI元素检测 |
| `ocr_recognize` | OCR识别剩余次数 |
| `click_coordinates` | 点击指定坐标 |
| `press_key` | 模拟按键（ESC返回） |

---

## 技能输出示例

### 成功完成
```
✅ 舰团回收委托循环完成！

- 步骤1: 聚焦游戏窗口 ✓
- 步骤2: 确认在舰桥界面 ✓
- 步骤3: 加载舰桥检测模型 ✓
- 步骤4: 识别舰桥界面元素 ✓
- 步骤5: 调戏看板娘（排除聚焦问题） ✓
- 步骤6: 重新识别舰桥界面元素 ✓
- 步骤7: 点击舰团按钮 ✓
- 步骤8: 加载club检测模型并识别 ✓
- 步骤9: 点击委托回收按钮 ✓
- 步骤10-11: OCR识别剩余次数=8，继续循环 ✓
- 步骤12: 检测到委托活跃，点击提交 ✓
- 步骤13-14: 确认提交 ✓
- 步骤10-11: OCR识别剩余次数=7，继续循环 ✓
- 步骤12: 委托活跃，点击提交 ✓
- 步骤13-14: 确认提交 ✓
- 步骤10-11: OCR识别剩余次数=5，≤6停止 ✓
- 步骤16: 返回舰桥界面 ✓

📊 本次提交了 2 次委托，剩余 5 次。
```
