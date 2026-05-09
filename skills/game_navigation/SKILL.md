---
name: game_navigation
description: 游戏场景导航技能 - 从任意界面导航到目标界面。


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

## 导航流程

### 1. ⚠️ 聚焦游戏窗口（必须执行）
**重要：此步骤必须首先执行，不能跳过！**
使用 `focus_bh3_window` 工具确保游戏窗口处于活动状态

### 2. 查看模型状态
使用 `yolo_list_models` 工具查看所有可用模型和已加载状态

### 3. 加载场景分类模型
- 检查 `yolo11n_scene_cls` 是否已加载
- 如果未加载，使用 `yolo_load_model yolo11n_scene_cls` 加载

### 4. 识别当前场景
使用 `yolo_classify_image yolo11n_scene_cls` 识别当前场景
- 支持识别34个游戏场景
- 返回格式：场景英文名称 (中文名称)
- 如果当前场景已是目标场景，导航完成

### 5. 加载当前场景的检测模型
根据当前场景选择对应的检测模型：
| 当前场景 | 检测模型 |
|----------|----------|
| attack | yolo11n_attack_ui_det |
| club | yolo11n_club_ui_det |
| home | yolo11n_home_ui_det |
| mission | yolo11n_mission_ui_det |

- 检查对应模型是否已加载
- 如果未加载，使用 `yolo_load_model` 工具加载

### 6. 识别导航按钮
使用 `yolo_detect_image` 识别当前界面的UI元素
- 返回元素标签、置信度和边界框坐标
- 查找前往目标界面的按钮（如 mission_button）

### 7. 点击导航按钮
使用 `click_coordinates` 工具点击目标按钮的中心坐标
- 从检测结果中提取元素的bbox坐标 [x1, y1, x2, y2]
- 计算中心点：(x1+x2)/2, (y1+y2)/2
- 点击后等待1-2秒

### 8. 验证导航结果
使用 `yolo_classify_image yolo11n_scene_cls` 确认是否成功进入目标场景
- 如果成功，导航完成
- 如果失败，进入循环重试

### 9. 循环重试（可选）
如果导航失败，可重复执行以下步骤：
1. 重新识别当前场景
2. 加载对应检测模型（如未加载）
3. 识别导航按钮
4. 点击导航按钮
5. 再次验证

## 导航路径映射

| 目标场景 | 导航路径 | 对应按钮 |
|----------|----------|----------|
| attack | bridge → attack | button_attack |
| club | bridge → club | button_club |
| bridge | 任意 → bridge | button_bridge |
| mission | bridge → mission | button_mission |

## 场景导航示例

### 示例1：从任意界面导航到任务界面 (mission)

1. **聚焦窗口**: `focus_bh3_window`
2. **查看模型状态**: `yolo_list_models`
3. **加载场景模型**: `yolo_load_model yolo11n_scene_cls`
4. **识别当前场景**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: club (舰团界面)
5. **加载club检测模型**: `yolo_load_model yolo11n_club_ui_det`
6. **识别导航按钮**: `yolo_detect_image yolo11n_club_ui_det`
   - 结果: button_bridge, bbox: [50, 50, 100, 100]
7. **点击bridge按钮**: `click_coordinates 75, 75`
8. **等待1秒并验证**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: bridge (舰桥界面)
9. **加载bridge检测模型**: `yolo_load_model yolo11n_bridge_ui_det`
10. **识别bridge按钮**: `yolo_detect_image yolo11n_bridge_ui_det`
    - 结果: button_mission, bbox: [100, 200, 150, 250]
11. **点击mission按钮**: `click_coordinates 125, 225`
12. **验证最终结果**: `yolo_classify_image yolo11n_scene_cls`
    - 结果: mission (任务界面) ✓

### 示例2：循环重试逻辑

如果点击后导航失败：
1. **验证失败**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: bridge (仍在舰桥界面，未进入mission)
2. **重新识别**: `yolo_detect_image yolo11n_bridge_ui_det`
   - 结果: button_mission, bbox: [100, 200, 150, 250]
3. **重新点击**: `click_coordinates 125, 225`
4. **再次验证**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: mission (任务界面) ✓

## 可用场景列表

> **说明**：场景名称和中文映射来自 `backend/data/models/classification/scene_mapping.json`，当前支持34个游戏场景。

| 英文名称 | 中文名称 | 对应检测模型 |
|----------|----------|--------------|
| attack | 出击界面 | yolo11n_attack_ui_det |
| bridge | 舰桥界面 | yolo11n_bridge_ui_det |
| club | 舰团界面 | yolo11n_club_ui_det |
| home | 家园界面 | yolo11n_home_ui_det |
| mission | 任务界面 | yolo11n_mission_ui_det |

> **提示**：完整的34个场景列表请参考 `scene_mapping.json` 文件，场景识别结果会自动附带中文名称。UI元素检测结果同样会通过 `backend/data/models/detect/detect_mapping.json` 显示中文含义。

## 注意事项

1. 确保游戏窗口已打开且可见
2. 模型加载可能需要几秒钟时间
3. 如果检测结果置信度低于0.5，建议重新检测
4. 点击坐标后建议等待1-2秒再验证结果
5. 如果导航失败，可循环执行步骤4-8，建议最多重试3次
6. 某些场景之间可能需要经过中间界面（如先回到home）

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `focus_bh3_window` | 聚焦游戏窗口 |
| `yolo_list_models` | 列出可用模型和已加载状态 |
| `yolo_load_model` | 加载YOLO模型 |
| `yolo_classify_image` | 场景分类识别 |
| `yolo_detect_image` | UI元素检测 |
| `click_coordinates` | 点击指定坐标 |