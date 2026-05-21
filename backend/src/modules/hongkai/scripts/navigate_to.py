"""
navigate_to.py — 游戏场景导航

从任意界面导航到目标界面，所有导航经过舰桥（bridge）中转。
重试上限 3 次，超过则返回失败。

此模块由 agent 工具直接调用，运行在 agent 进程内，共享 YOLOModelManager 单例。
"""
import logging
import time
from typing import Any, Dict, Optional

from .find_direction import (
    _get_manager, _capture, _focus, _available, _loaded,
    _ensure_model, _click_bbox, _classify, _detect_button,
    SCENE_TO_DET_MODEL,
)

logger = logging.getLogger(__name__)

# 目标场景 → 舰桥界面上对应的导航按钮
TARGET_TO_BUTTON = {
    "attack": "button_attack",
    "club": "button_club",
    "mission": "button_mission",
    "home": "button_home",
}

# 场景 → 检测模型（用于查找 button_bridge）
SCENE_TO_DET_MODEL_FOR_BRIDGE = {
    "attack": "yolo11n_attack_ui_det",
    "club": "yolo11n_club_ui_det",
    "home": "yolo11n_home_ui_det",
    "mission": "yolo11n_mission_ui_det",
}

VALID_TARGETS = {"attack", "club", "bridge", "mission", "home"}
MAX_RETRIES = 3


def _find_direction():
    """调用 find_direction 作为兜底方案"""
    from .find_direction import find_direction
    return find_direction()


def navigate_to(target: str) -> Dict[str, Any]:
    """
    从任意界面导航到目标场景。

    Args:
        target: 目标场景英文名，可选: attack, club, bridge, mission, home

    Returns:
        {"success": bool, "scene": str|None, "message": str, "retries": int}
    """
    target = target.strip().lower()

    if target not in VALID_TARGETS:
        return {"success": False, "scene": None,
                "message": f"无效的目标场景 '{target}'，可选: {', '.join(sorted(VALID_TARGETS))}",
                "retries": 0}

    manager = _get_manager()

    # --- 阶段一：确认当前位置 ---
    _focus()

    scene = _classify(manager)
    if scene is None:
        return {"success": False, "scene": None,
                "message": "无法识别当前场景，请尝试 find_direction 先定位",
                "retries": 0}

    # 已在目标场景
    if scene == target:
        return {"success": True, "scene": scene,
                "message": f"已在目标界面 {target}，无需导航",
                "retries": 0}

    # --- 主循环（含重试） ---
    retries = 0

    while retries <= MAX_RETRIES:
        # --- 阶段二：导航到舰桥 ---
        if scene != "bridge":
            # 查找当前场景的 button_bridge
            det_model = SCENE_TO_DET_MODEL_FOR_BRIDGE.get(scene)

            if det_model is None:
                # 当前场景无对应检测模型，用 find_direction 自救
                fd_result = _find_direction()
                if fd_result.get("success"):
                    scene = fd_result.get("scene", "bridge")
                else:
                    return {"success": False, "scene": scene,
                            "message": f"当前场景 {scene} 无检测模型，且 find_direction 失败: "
                                       f"{fd_result.get('message')}",
                            "retries": retries}
                continue

            bbox, conf = _detect_button(manager, det_model, "button_bridge")

            if not bbox:
                # 找不到 button_bridge，用 find_direction 自救
                fd_result = _find_direction()
                if fd_result.get("success"):
                    scene = fd_result.get("scene", "bridge")
                else:
                    return {"success": False, "scene": scene,
                            "message": f"当前场景 {scene} 找不到舰桥按钮，且 find_direction 失败",
                            "retries": retries}
                continue

            # 点击舰桥按钮
            _click_bbox(bbox)
            time.sleep(1.5)

            # 验证是否到达舰桥
            scene = _classify(manager)
            if scene != "bridge":
                # 可能没点中或还在过渡动画中，继续尝试
                continue

        # --- 阶段三：从舰桥导航到目标 ---
        if target == "bridge":
            # 目标就是舰桥，已经到了
            return {"success": True, "scene": "bridge",
                    "message": "已到达舰桥界面", "retries": retries}

        button_name = TARGET_TO_BUTTON.get(target)
        if button_name is None:
            return {"success": False, "scene": scene,
                    "message": f"目标 {target} 没有对应的导航按钮映射", "retries": retries}

        if not _ensure_model(manager, "yolo11n_bridge_ui_det"):
            return {"success": False, "scene": scene,
                    "message": "无法加载舰桥检测模型 yolo11n_bridge_ui_det", "retries": retries}

        bbox, conf = _detect_button(manager, "yolo11n_bridge_ui_det", button_name)

        if not bbox or conf < 0.5:
            # 可能在舰桥但找不到按钮，重新验证场景
            scene = _classify(manager)
            if scene != "bridge":
                # 根本不在舰桥，重试
                retries += 1
                continue
            # 在舰桥但找不到按钮，用 find_direction
            fd_result = _find_direction()
            if fd_result.get("success"):
                scene = fd_result.get("scene", "bridge")
            else:
                return {"success": False, "scene": "bridge",
                        "message": f"在舰桥但找不到 {button_name} 按钮", "retries": retries}
            continue

        # 点击目标按钮
        _click_bbox(bbox)
        time.sleep(1.5)

        # --- 阶段四：验证导航结果 ---
        scene = _classify(manager)
        if scene == target:
            return {"success": True, "scene": scene,
                    "message": f"已到达目标界面 {target}", "retries": retries}

        # 导航失败，准备重试
        retries += 1

    # 超过重试上限
    return {"success": False, "scene": scene,
            "message": f"重试 {MAX_RETRIES} 次后仍未到达 {target}（当前: {scene}），请手动操作",
            "retries": retries}
