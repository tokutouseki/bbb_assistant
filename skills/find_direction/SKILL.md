---
name: find_direction
description: 找到方向技能 - 当LLM/Agent无论如何都无法识别当前页面时使用。通过查找舰桥按钮或使用ESC返回，逐步找到明确的方向。


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
2. 如果找不到舰桥按钮，使用ESC键逐级返回上级界面
3. 通过场景分类模型确认当前位置
4. 循环执行直到找到明确的、有对应检测模型的场景

这是 Agent 的**应急自救技能**，帮助 Agent 在"迷路"时重新建立对环境的认知。

## 技能流程

### 阶段1：寻找舰桥按钮（快速返回）

#### 1. ⚠️ 聚焦游戏窗口（必须执行）
**重要：此步骤必须首先执行，不能跳过！**
使用 `focus_bh3_window` 工具确保游戏窗口处于活动状态

#### 2. 查看可用模型
使用 `yolo_list_models` 查看所有可用的检测模型

#### 3. 加载检测模型
选择任意一个检测模型（优先选择 yolo11n_bridge_ui_det）
- 检查模型是否已加载
- 如果未加载，使用 `yolo_load_model` 加载
- 如果 yolo11n_bridge_ui_det 不可用，选择其他任意检测模型

#### 4. 识别当前界面元素
使用 `yolo_detect_image` 识别当前窗口的UI元素
- 特别查找 `button_bridge` 元素
- 同时也可以查找其他可能的导航按钮

#### 5. 判断是否有舰桥按钮
**如果检测到 button_bridge**：
- 提取 button_bridge 的 bbox 坐标 [x1, y1, x2, y2]
- 计算中心点坐标：((x1+x2)/2, (y1+y2)/2)
- 使用 `click_coordinates` 点击舰桥按钮
- 等待1-2秒
- **技能结束** ✅ - 已找到方向（回到舰桥）

**如果没有检测到 button_bridge**：
- 进入阶段2，使用ESC返回

---

### 阶段2：ESC返回 + 场景识别

#### 6. 模拟按ESC键
使用 `press_key` 工具按下 ESC 键
- 参数：`key='escape', duration=0.1`
- 等待1-2秒让界面切换

#### 7. 加载场景分类模型
使用 `yolo_list_models` 检查 `yolo11n_scene_cls` 是否已加载
- 如果未加载，使用 `yolo_load_model yolo11n_scene_cls` 加载

#### 8. 识别当前场景
使用 `yolo_classify_image yolo11n_scene_cls` 识别当前场景
- 获取场景的英文和中文名称

#### 9. 判断是否有对应检测模型
查看场景是否对应有检测模型：

| 场景英文 | 场景中文 | 对应检测模型 |
|----------|----------|--------------|
| attack | 出击界面 | yolo11n_attack_ui_det |
| bridge | 舰桥界面 | yolo11n_bridge_ui_det |
| club | 舰团界面 | yolo11n_club_ui_det |
| home | 家园界面 | yolo11n_home_ui_det |
| mission | 任务界面 | yolo11n_mission_ui_det |

**如果当前场景有对应检测模型**：
- **技能结束** ✅ - 已找到方向（当前场景明确）

**如果当前场景没有对应检测模型**：
- 继续阶段3，循环执行

---

### 阶段3：循环返回（最多重试5次）

#### 10. 再次按ESC键
使用 `press_key` 工具按下 ESC 键
- 参数：`key='escape', duration=0.1`
- 等待1-2秒

#### 11. 再次识别场景
使用 `yolo_classify_image yolo11n_scene_cls` 识别当前场景

#### 12. 再次判断
**如果当前场景有对应检测模型**：
- **技能结束** ✅ - 已找到方向

**如果仍然没有对应检测模型**：
- 检查重试次数
- 如果未超过5次，回到步骤10继续
- 如果已超过5次，**技能结束** ⚠️ - 建议用户手动操作

---

## 完整流程图

```
开始
  ↓
[1] 聚焦游戏窗口
  ↓
[2] 查看可用模型
  ↓
[3] 加载检测模型 (优先 bridge)
  ↓
[4] 识别界面元素
  ↓
{有 button_bridge?}
  ├─ 是 → [5] 点击舰桥按钮 → 结束 ✅
  │
  └─ 否 → [6] 按ESC返回
              ↓
          [7] 加载场景分类模型
              ↓
          [8] 识别当前场景
              ↓
          {有对应检测模型?}
              ├─ 是 → 结束 ✅
              │
              └─ 否 → [9] 按ESC返回
                          ↓
                      [10] 识别场景
                          ↓
                      {有对应检测模型?}
                          ├─ 是 → 结束 ✅
                          └─ 否 → {重试<5次?}
                                        ├─ 是 → 回到[9]
                                        └─ 否 → 结束 ⚠️
```

## 使用示例

### 示例1：成功找到舰桥按钮

1. **聚焦窗口**: `focus_bh3_window`
2. **查看模型**: `yolo_list_models`
3. **加载bridge模型**: `yolo_load_model yolo11n_bridge_ui_det`
4. **识别界面**: `yolo_detect_image yolo11n_bridge_ui_det`
   - 结果: button_bridge detected at [100, 200, 200, 300]
5. **点击舰桥**: `click_coordinates 150, 250`
6. **结束** ✅ - 已回到舰桥界面

### 示例2：使用ESC返回后找到方向

1. **聚焦窗口**: `focus_bh3_window`
2. **查看模型**: `yolo_list_models`
3. **加载检测模型**: `yolo_load_model yolo11n_home_ui_det`
4. **识别界面**: `yolo_detect_image yolo11n_home_ui_det`
   - 结果: no button_bridge found
5. **按ESC**: `press_key key='escape', duration=0.1`
6. **加载场景模型**: `yolo_load_model yolo11n_scene_cls`
7. **识别场景**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: mission (任务界面)
8. **判断**：mission 有对应检测模型 ✓
9. **结束** ✅ - 已找到方向（在任务界面）

### 示例3：多次ESC返回后成功

1. **聚焦窗口**: `focus_bh3_window`
2. **查看模型**: `yolo_list_models`
3. **加载检测模型**: `yolo_load_model yolo11n_club_ui_det`
4. **识别界面**: `yolo_detect_image yolo11n_club_ui_det`
   - 结果: no button_bridge found
5. **按ESC (第1次)**: `press_key key='escape', duration=0.1`
6. **识别场景**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: unknown_scene (无对应模型)
7. **按ESC (第2次)**: `press_key key='escape', duration=0.1`
8. **识别场景**: `yolo_classify_image yolo11n_scene_cls`
   - 结果: home (家园界面)
9. **判断**：home 有对应检测模型 ✓
10. **结束** ✅ - 已找到方向（在家园界面）

## 检测模型优先顺序

寻找舰桥按钮时，按以下优先级选择检测模型：
1. **yolo11n_bridge_ui_det** - 专门检测舰桥界面
2. **yolo11n_home_ui_det** - 家园界面也有导航按钮
3. **yolo11n_attack_ui_det** - 出击界面
4. **yolo11n_mission_ui_det** - 任务界面
5. **yolo11n_club_ui_det** - 舰团界面

## 注意事项

1. **ESC键等待时间**：每次按ESC后建议等待1-2秒，让界面完全切换
2. **重试次数限制**：最多循环5次，避免无限循环
3. **置信度判断**：如果检测到button_bridge但置信度<0.5，建议谨慎点击或继续ESC
4. **场景映射参考**：场景与检测模型的映射关系参考 `scene_mapping.json`
5. **模型加载顺序**：优先尝试加载bridge模型，如果没有再选其他
6. **用户反馈**：如果5次ESC后仍找不到方向，建议礼貌告知用户并建议手动操作

## 工具依赖

| 工具名称 | 用途 |
|----------|------|
| `focus_bh3_window` | 聚焦游戏窗口 |
| `yolo_list_models` | 列出可用模型和已加载状态 |
| `yolo_load_model` | 加载YOLO模型 |
| `yolo_classify_image` | 场景分类识别 |
| `yolo_detect_image` | UI元素检测 |
| `click_coordinates` | 点击指定坐标 |
| `press_key` | 模拟按键（ESC） |

## 技能输出示例

### 成功场景1（找到舰桥）
```
🔍 Agent 自我定位中...
✅ 定位成功！
- 执行操作：点击了舰桥按钮
- 当前位置：舰桥界面 (bridge)
- 状态：已重新建立环境认知，可继续执行任务
```

### 成功场景2（ESC返回后识别场景）
```
🔍 Agent 自我定位中...
- 第一次识别：无法确定当前场景
- 执行操作：按ESC返回上级
- 重新识别：mission (任务界面)
✅ 定位成功！
- 当前位置：任务界面 (mission)
- 状态：场景明确，有对应检测模型，可继续执行任务
```

### 成功场景3（多次ESC后找到）
```
🔍 Agent 自我定位中...
- 第一次识别：unknown_scene (无对应模型)
- 执行操作：按ESC返回 (第1次)
- 第二次识别：unknown_scene (无对应模型)
- 执行操作：按ESC返回 (第2次)
- 第三次识别：home (家园界面)
✅ 定位成功！
- 当前位置：家园界面 (home)
- 状态：已找到明确方向
```

### 达到重试上限
```
🔍 Agent 自我定位中...
- 已尝试：5次ESC返回
- 结果：仍无法识别到有对应检测模型的场景
⚠️ 定位失败
- 建议：请告诉我您当前在哪个界面，或者您想执行什么操作
```
