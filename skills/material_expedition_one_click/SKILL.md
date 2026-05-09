---
name: material_expedition_one_click
description: 材料远征一键减负技能 - 自动导航到材料活动界面并完成两次一键减负点击。


# 材料远征一键减负技能

## When to Use

当用户请求以下操作时使用此技能：
- "材料远征一键减负"
- "一键完成材料远征"
- "帮我做一下材料活动减负"
- "材料远征减负"
- "材料活动一键减负"

## 概述

此技能用于自动化完成材料远征的一键减负操作。通过导航到材料活动界面，执行两次一键减负点击，快速完成材料远征任务。

## 技能流程

### 1. ⚠️ 聚焦游戏窗口（必须执行）
**重要：此步骤必须首先执行，不能跳过！**
使用 `focus_bh3_window` 工具确保游戏窗口处于活动状态

### 2. 前往舰桥（主界面）
**确保当前在舰桥界面**，如果不在，可能需要使用找到方向技能或手动导航
- 使用场景分类模型 `yolo11n_scene_cls` 确认当前场景
- 如果不是 bridge，使用找到方向技能或手动回到舰桥

### 3. 前往出击界面
使用场景导航技能导航到 attack（出击界面），或：
- 查看可用模型 `yolo_list_models`
- 加载舰桥检测模型（如果未加载）`yolo_load_model yolo11n_bridge_ui_det`
- 识别舰桥界面元素 `yolo_detect_image yolo11n_bridge_ui_det`
- 找到并点击 button_attack
- 等待1-2秒
- 确认到达 attack 界面

### 4. 加载 attack 识别模型
使用 `yolo_list_models` 检查 `yolo11n_attack_ui_det` 是否已加载
- 如果未加载，使用 `yolo_load_model yolo11n_attack_ui_det` 加载

### 5. 使用 attack 识别模型识别当前界面
使用 `yolo_detect_image yolo11n_attack_ui_det` 识别当前界面的UI元素
- 查找 button_strike_inactive 或 button_strike_active
- 查找 button_material_event
- 查找 button_one_click

### 6. 检查并点击出击按钮
**判断当前状态**：
- **如果存在 button_strike_active**：出击界面已激活，跳过此步骤
- **如果存在 button_strike_inactive**：需要点击激活出击界面
  - 提取 button_strike_inactive 的 bbox 坐标 [x1, y1, x2, y2]
  - 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
  - 使用 `click_coordinates` 点击该按钮
  - 等待1-2秒让界面激活

### 7. 再次识别界面（如果第6步执行了）
**仅当第6步点击了 button_strike_inactive 时执行**：
- 使用 `yolo_detect_image yolo11n_attack_ui_det` 重新识别
- 确认 button_strike_active 是否出现
- 查找 button_material_event

### 8. 点击材料活动按钮
从识别结果中找到 button_material_event：
- 提取 button_material_event 的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮
- 等待1-2秒让界面切换到材料活动

### 9. 再次使用 attack 识别模型
使用 `yolo_detect_image yolo11n_attack_ui_det` 识别材料活动界面的UI元素
- 确认已进入材料活动界面
- 查找 button_one_click

### 10. 第一次点击一键减负按钮
从识别结果中找到 button_one_click：
- 提取 button_one_click 的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮
- 等待1-2秒

### 11. 再次使用 attack 识别模型
使用 `yolo_detect_image yolo11n_attack_ui_det` 识别当前界面
- 观察界面变化
- 查找新位置的 button_one_click

### 12. 第二次点击一键减负按钮
**重要**：button_one_click 的位置和第一次点击时不同，需要再次点击，没有位置变化说明第一次点击失败了需要重复9-12步
- 从最新识别结果中找到 button_one_click的坐标
- 提取新的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击该按钮
- 等待1-2秒

### 13. 尝试返回舰桥界面
完成一键减负后，返回到舰桥界面：
- 使用 `press_key` 按 ESC 返回上级，或
- 查找 button_bridge 并点击，或
- 使用找到方向技能返回舰桥界面
- 确认返回舰桥

---

## 关键元素说明

| 元素标签 | 中文含义 | 用途 |
|----------|----------|------|
| button_strike_inactive | 出击界面未激活按钮 | 需要点击激活出击界面 |
| button_strike_active | 出击界面活跃中 | 说明出击界面已激活，无需操作 |
| button_material_event | 前往材料活动按钮 | 点击进入材料活动界面 |
| button_one_click | 一键减负按钮 | 第一次点击开始减负，第二次确认完成 |
| button_bridge | 前往舰桥按钮 | 返回主界面 |

---

## 完整流程图

```
开始
  ↓
[1] 聚焦游戏窗口
  ↓
[2] 确认/前往舰桥界面
  ↓
[3] 导航到出击界面 (attack)
  ↓
[4] 加载 attack 检测模型
  ↓
[5] 识别出击界面元素
  ↓
{有 button_strike_active?}
  ├─ 是 → 跳过 [6]
  │
  └─ 否 → [6] 点击 button_strike_inactive
              ↓
          [7] 重新识别界面
  ↓
[8] 点击 button_material_event
  ↓
[9] 识别材料活动界面
  ↓
[10] 第一次点击 button_one_click
  ↓
[11] 重新识别界面 (button_one_click 位置改变)
  ↓
[12] 第二次点击 button_one_click (必要步骤)
  ↓
[13] 可选：返回舰桥
  ↓
结束 ✅
```

---

## 使用示例

### 示例：完整的材料远征一键减负流程

1. **聚焦窗口**: `focus_bh3_window`
2. **确认在舰桥**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: bridge (舰桥界面) ✓
3. **前往出击**: `yolo_load_model yolo11n_bridge_ui_det`
4. **识别舰桥**: `yolo_detect_image yolo11n_bridge_ui_det`
   - 找到: button_attack at [500, 300, 600, 400]
5. **点击出击**: `click_coordinates 550, 350`
6. **等待**: (1-2秒)
7. **加载attack模型**: `yolo_load_model yolo11n_attack_ui_det`
8. **识别出击界面**: `yolo_detect_image yolo11n_attack_ui_det`
   - 找到: button_strike_inactive at [200, 200, 300, 300]
   - 找到: button_material_event at [400, 400, 500, 500]
9. **激活出击**: `click_coordinates 250, 250`
10. **等待**: (1-2秒)
11. **重新识别**: `yolo_detect_image yolo11n_attack_ui_det`
    - 找到: button_strike_active ✓
    - 找到: button_material_event
12. **点击材料活动**: `click_coordinates 450, 450`
13. **等待**: (1-2秒)
14. **识别材料界面**: `yolo_detect_image yolo11n_attack_ui_det`
    - 找到: button_one_click at [600, 500, 700, 600]
15. **第一次一键减负**: `click_coordinates 650, 550`
16. **等待**: (1-2秒)
17. **重新识别**: `yolo_detect_image yolo11n_attack_ui_det`
    - 找到: button_one_click at [650, 550, 750, 650] (位置改变)
18. **第二次一键减负**: `click_coordinates 700, 600` (必要步骤)
19. **等待**: (1-2秒)
20. **返回舰桥**: `press_key key='escape', duration=0.1`
21. **完成** ✅

---

## 注意事项

### 关键提醒
1. **两次 button_one_click 点击是必须的**：
   - 第一次点击：开始减负
   - 第二次点击：确认完成
   - 两次点击位置可能不同，每次都要重新识别

2. **button_strike_active/inactive 判断**：
   - 如果已经有 button_strike_active，不需要点击
   - 如果只有 button_strike_inactive，需要先点击激活

3. **等待时间**：
   - 每次点击后建议等待1-2秒，让界面完全切换
   - 不要连续快速点击

4. **模型加载**：
   - 确保 yolo11n_attack_ui_det 已正确加载
   - 每次识别都使用 attack 模型

5. **如果找不到 button_material_event**：
   - 可能需要先切换到推荐/挑战等标签
   - 查找 button_recommend_inactive / button_challenge_inactive 并点击

### 异常处理
- 如果在材料活动界面找不到 button_one_click：
  - 检查是否真的进入了材料活动界面
  - 重新识别确认场景
- 如果两次点击后任务未完成：
  - 可能需要额外操作，根据实际界面判断

---

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `focus_bh3_window` | 聚焦游戏窗口 |
| `yolo_list_models` | 列出可用模型 |
| `yolo_load_model` | 加载YOLO模型 |
| `yolo_classify_image` | 场景分类识别 |
| `yolo_detect_image` | UI元素检测 |
| `click_coordinates` | 点击指定坐标 |
| `press_key` | 模拟按键（ESC返回） |

---

## 技能输出示例

### 成功完成
```
✅ 材料远征一键减负完成！
- 步骤1: 聚焦游戏窗口
- 步骤2: 确认在舰桥界面
- 步骤3: 导航到出击界面
- 步骤4: 激活出击界面
- 步骤5: 进入材料活动
- 步骤6: 第一次一键减负点击
- 步骤7: 第二次一键减负点击 (必要)
- 结果：材料远征减负已完成！
```
