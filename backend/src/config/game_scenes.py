"""
崩坏3专属AI陪伴助手 - 游戏场景配置
定义崩坏3游戏中的各种场景及其特征
"""

from typing import Dict, List, Tuple, Any

# 崩坏3游戏场景类型
GAME_SCENE_TYPES = {
    "MAIN_MENU": "main_menu",           # 主界面
    "BATTLE": "battle",                 # 战斗场景
    "LEVEL_SELECT": "level_select",     # 关卡选择
    "GACHA": "gacha",                   # 抽卡界面
    "QUEST": "quest",                   # 任务活动界面
    "CHARACTER_EQUIP": "character_equip",  # 角色装备面板
    "DORM": "dorm",                     # 宿舍
    "SHOP": "shop",                     # 商店
    "SETTINGS": "settings",             # 设置界面
    "LOADING": "loading",               # 加载界面
    "UNKNOWN": "unknown",               # 未知场景
}

# 游戏场景配置
GAME_SCENES: Dict[str, Dict[str, Any]] = {
    GAME_SCENE_TYPES["MAIN_MENU"]: {
        "name": "主界面",
        "description": "游戏主菜单界面，包含开始游戏、角色、装备、任务等入口",
        "features": {
            "ui_elements": ["开始游戏按钮", "角色按钮", "装备按钮", "任务按钮", "设置按钮"],
            "colors": [(100, 100, 200), (50, 50, 150)],  # 主色调
            "text_patterns": ["开始游戏", "角色", "装备", "任务", "设置"],
            "key_points": [(0.5, 0.2), (0.3, 0.5), (0.7, 0.5)],  # 关键点位置
        },
        "yolo_classes": ["button_start", "button_character", "button_equipment", "button_quest"],
        "ocr_keywords": ["开始游戏", "角色", "装备", "任务", "崩坏3"],
        "actions": ["开始游戏", "查看角色", "查看装备", "查看任务", "打开设置"],
    },
    GAME_SCENE_TYPES["BATTLE"]: {
        "name": "战斗场景",
        "description": "游戏战斗界面，包含角色、敌人、技能按钮、血量条等",
        "features": {
            "ui_elements": ["角色头像", "敌人模型", "技能按钮", "血量条", "能量条"],
            "colors": [(200, 50, 50), (50, 200, 50)],  # 红绿对比色
            "text_patterns": ["HP", "MP", "技能", "攻击", "防御"],
            "key_points": [(0.1, 0.9), (0.9, 0.5), (0.5, 0.1)],  # 技能栏位置
        },
        "yolo_classes": ["character", "enemy", "skill_button", "health_bar", "energy_bar"],
        "ocr_keywords": ["HP", "MP", "技能", "攻击", "胜利", "失败"],
        "actions": ["使用技能", "切换角色", "躲避攻击", "发动攻击", "结束战斗"],
    },
    GAME_SCENE_TYPES["LEVEL_SELECT"]: {
        "name": "关卡选择",
        "description": "关卡选择界面，显示不同关卡和难度",
        "features": {
            "ui_elements": ["关卡图标", "难度选择", "开始按钮", "关卡描述"],
            "colors": [(150, 150, 255), (100, 100, 200)],  # 蓝色调
            "text_patterns": ["关卡", "难度", "开始", "推荐等级", "奖励"],
            "key_points": [(0.3, 0.3), (0.5, 0.3), (0.7, 0.3)],  # 关卡位置
        },
        "yolo_classes": ["level_icon", "difficulty_indicator", "start_button"],
        "ocr_keywords": ["关卡", "难度", "开始", "等级", "奖励", "挑战"],
        "actions": ["选择关卡", "选择难度", "开始挑战", "查看奖励", "返回"],
    },
    GAME_SCENE_TYPES["GACHA"]: {
        "name": "抽卡界面",
        "description": "抽卡/召唤界面，包含抽卡按钮、保底计数、角色池信息",
        "features": {
            "ui_elements": ["抽卡按钮", "角色卡片", "保底计数器", "水晶数量"],
            "colors": [(255, 215, 0), (200, 150, 50)],  # 金色调
            "text_patterns": ["抽卡", "召唤", "保底", "水晶", "概率"],
            "key_points": [(0.5, 0.7), (0.3, 0.4), (0.7, 0.4)],  # 抽卡按钮位置
        },
        "yolo_classes": ["gacha_button", "character_card", "counter", "crystal_count"],
        "ocr_keywords": ["抽卡", "召唤", "保底", "水晶", "概率", "新角色"],
        "actions": ["单抽", "十连抽", "查看概率", "查看保底", "返回"],
    },
    GAME_SCENE_TYPES["QUEST"]: {
        "name": "任务活动界面",
        "description": "任务和活动界面，显示日常、周常、活动任务",
        "features": {
            "ui_elements": ["任务列表", "奖励图标", "完成状态", "领取按钮"],
            "colors": [(100, 200, 100), (50, 150, 50)],  # 绿色调
            "text_patterns": ["任务", "日常", "周常", "活动", "奖励", "领取"],
            "key_points": [(0.2, 0.3), (0.5, 0.5), (0.8, 0.7)],  # 任务列表位置
        },
        "yolo_classes": ["quest_item", "reward_icon", "complete_status", "claim_button"],
        "ocr_keywords": ["任务", "日常", "周常", "活动", "奖励", "完成", "领取"],
        "actions": ["查看任务", "领取奖励", "刷新任务", "参加活动", "返回"],
    },
    GAME_SCENE_TYPES["CHARACTER_EQUIP"]: {
        "name": "角色装备面板",
        "description": "角色装备和属性界面，显示角色属性、装备、技能",
        "features": {
            "ui_elements": ["角色模型", "属性面板", "装备槽", "技能图标"],
            "colors": [(200, 150, 200), (150, 100, 150)],  # 紫色调
            "text_patterns": ["攻击", "防御", "生命", "暴击", "装备", "技能"],
            "key_points": [(0.2, 0.5), (0.5, 0.3), (0.8, 0.5)],  # 属性面板位置
        },
        "yolo_classes": ["character_model", "attribute_panel", "equipment_slot", "skill_icon"],
        "ocr_keywords": ["攻击", "防御", "生命", "暴击", "装备", "技能", "升级"],
        "actions": ["更换装备", "升级角色", "学习技能", "查看属性", "返回"],
    },
    GAME_SCENE_TYPES["DORM"]: {
        "name": "宿舍",
        "description": "角色宿舍界面，角色互动和休息的场景",
        "features": {
            "ui_elements": ["房间背景", "角色模型", "互动按钮", "家具"],
            "colors": [(255, 240, 200), (200, 180, 150)],  # 暖色调
            "text_patterns": ["宿舍", "互动", "心情", "家具", "休息"],
            "key_points": [(0.3, 0.5), (0.5, 0.3), (0.7, 0.5)],  # 角色位置
        },
        "yolo_classes": ["room_background", "character_model", "interact_button", "furniture"],
        "ocr_keywords": ["宿舍", "互动", "心情", "家具", "休息", "好感度"],
        "actions": ["互动", "更换家具", "查看心情", "休息", "返回"],
    },
    GAME_SCENE_TYPES["SHOP"]: {
        "name": "商店",
        "description": "游戏商店界面，购买道具、装备、材料",
        "features": {
            "ui_elements": ["商品列表", "价格标签", "购买按钮", "货币数量"],
            "colors": [(255, 200, 100), (200, 150, 50)],  # 橙色调
            "text_patterns": ["商店", "购买", "价格", "货币", "道具", "装备"],
            "key_points": [(0.3, 0.4), (0.5, 0.4), (0.7, 0.4)],  # 商品位置
        },
        "yolo_classes": ["item_list", "price_tag", "buy_button", "currency_count"],
        "ocr_keywords": ["商店", "购买", "价格", "水晶", "道具", "装备", "材料"],
        "actions": ["购买物品", "刷新商店", "查看价格", "返回"],
    },
    GAME_SCENE_TYPES["SETTINGS"]: {
        "name": "设置界面",
        "description": "游戏设置界面，调整画面、声音、控制等设置",
        "features": {
            "ui_elements": ["设置选项", "滑动条", "复选框", "确认按钮"],
            "colors": [(150, 150, 150), (100, 100, 100)],  # 灰色调
            "text_patterns": ["设置", "画面", "声音", "控制", "语言", "确认"],
            "key_points": [(0.3, 0.3), (0.5, 0.5), (0.7, 0.7)],  # 设置选项位置
        },
        "yolo_classes": ["setting_option", "slider", "checkbox", "confirm_button"],
        "ocr_keywords": ["设置", "画面", "声音", "控制", "语言", "确认", "取消"],
        "actions": ["调整设置", "保存设置", "恢复默认", "返回"],
    },
    GAME_SCENE_TYPES["LOADING"]: {
        "name": "加载界面",
        "description": "游戏加载界面，显示加载进度和提示",
        "features": {
            "ui_elements": ["加载条", "提示文字", "背景图", "logo"],
            "colors": [(50, 50, 100), (30, 30, 70)],  # 深蓝色调
            "text_patterns": ["加载中", "请稍候", "提示", "进度"],
            "key_points": [(0.5, 0.7), (0.5, 0.3)],  # 加载条位置
        },
        "yolo_classes": ["loading_bar", "hint_text", "background"],
        "ocr_keywords": ["加载中", "请稍候", "提示", "进度", "崩坏3"],
        "actions": ["等待加载", "查看提示", "取消加载"],
    },
}

# 场景检测配置
SCENE_DETECTION_CONFIG = {
    "confidence_threshold": 0.6,  # 置信度阈值
    "iou_threshold": 0.5,  # IOU阈值
    "max_detections": 10,  # 最大检测数量
    "min_ui_elements": 2,  # 最少UI元素数量
    "scene_switch_delay": 2.0,  # 场景切换延迟(秒)
}

# 场景转换关系
SCENE_TRANSITIONS = {
    GAME_SCENE_TYPES["MAIN_MENU"]: [
        GAME_SCENE_TYPES["BATTLE"],
        GAME_SCENE_TYPES["LEVEL_SELECT"],
        GAME_SCENE_TYPES["CHARACTER_EQUIP"],
        GAME_SCENE_TYPES["QUEST"],
        GAME_SCENE_TYPES["GACHA"],
        GAME_SCENE_TYPES["DORM"],
        GAME_SCENE_TYPES["SHOP"],
        GAME_SCENE_TYPES["SETTINGS"],
    ],
    GAME_SCENE_TYPES["LEVEL_SELECT"]: [
        GAME_SCENE_TYPES["BATTLE"],
        GAME_SCENE_TYPES["MAIN_MENU"],
    ],
    GAME_SCENE_TYPES["BATTLE"]: [
        GAME_SCENE_TYPES["MAIN_MENU"],
        GAME_SCENE_TYPES["LEVEL_SELECT"],
    ],
}

# 场景优先级（数值越高优先级越高）
SCENE_PRIORITIES = {
    GAME_SCENE_TYPES["BATTLE"]: 100,
    GAME_SCENE_TYPES["GACHA"]: 90,
    GAME_SCENE_TYPES["QUEST"]: 80,
    GAME_SCENE_TYPES["CHARACTER_EQUIP"]: 70,
    GAME_SCENE_TYPES["LEVEL_SELECT"]: 60,
    GAME_SCENE_TYPES["MAIN_MENU"]: 50,
    GAME_SCENE_TYPES["DORM"]: 40,
    GAME_SCENE_TYPES["SHOP"]: 30,
    GAME_SCENE_TYPES["SETTINGS"]: 20,
    GAME_SCENE_TYPES["LOADING"]: 10,
    GAME_SCENE_TYPES["UNKNOWN"]: 0,
}

def get_scene_by_name(name: str) -> Dict[str, Any]:
    """根据名称获取场景配置"""
    for scene_id, scene_config in GAME_SCENES.items():
        if scene_config["name"] == name:
            return scene_config
    return GAME_SCENES[GAME_SCENE_TYPES["UNKNOWN"]]

def get_scene_by_id(scene_id: str) -> Dict[str, Any]:
    """根据ID获取场景配置"""
    return GAME_SCENES.get(scene_id, GAME_SCENES[GAME_SCENE_TYPES["UNKNOWN"]])

def get_all_scene_names() -> List[str]:
    """获取所有场景名称"""
    return [config["name"] for config in GAME_SCENES.values()]

def get_all_scene_ids() -> List[str]:
    """获取所有场景ID"""
    return list(GAME_SCENES.keys())

def is_valid_scene(scene_id: str) -> bool:
    """检查是否为有效场景"""
    return scene_id in GAME_SCENES

def get_scene_priority(scene_id: str) -> int:
    """获取场景优先级"""
    return SCENE_PRIORITIES.get(scene_id, 0)

def can_transition(from_scene: str, to_scene: str) -> bool:
    """检查是否可以场景转换"""
    if from_scene not in SCENE_TRANSITIONS:
        return True  # 如果没有定义转换关系，允许所有转换
    return to_scene in SCENE_TRANSITIONS[from_scene]