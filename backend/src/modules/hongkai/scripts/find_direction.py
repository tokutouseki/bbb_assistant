"""
find_direction.py — 游戏场景自救定位

当 Agent 无法识别当前界面时，通过以下策略重新定位：
1. 尝试在任意界面找到舰桥按钮（button_bridge），一键返回舰桥
2. 找不到则按 ESC 返回上级界面，通过场景分类确认位置
3. 最多循环 5 次 ESC，超过则返回失败

此模块由 agent 工具直接调用，运行在 agent 进程内，共享 YOLOModelManager 单例。
"""
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 场景名 → 对应检测模型（已知场景 = 已找到方向）
SCENE_TO_DET_MODEL = {
    "bridge": "yolo11n_bridge_ui_det",
    "home": "yolo11n_home_ui_det",
    "mission": "yolo11n_mission_ui_det",
    "club": "yolo11n_club_ui_det",
    "attack": "yolo11n_attack_ui_det",
}

# 阶段一：寻找舰桥按钮的检测模型优先级
DET_MODEL_PRIORITY = [
    "yolo11n_bridge_ui_det",
    "yolo11n_home_ui_det",
    "yolo11n_attack_ui_det",
    "yolo11n_mission_ui_det",
    "yolo11n_club_ui_det",
]

MAX_ESC_RETRIES = 5


def _get_manager():
    from src.modules.vision.yolo_model_manager import YOLOModelManager
    return YOLOModelManager.get_instance()


def _capture():
    from src.modules.vision.screen_capture import ScreenCapture
    sc = ScreenCapture()
    img = sc.capture()
    if img is None or img.size == 0:
        raise RuntimeError("屏幕捕获失败")
    return img


def _focus():
    from src.modules.vision.window_focus import focus_bh3_window, is_admin
    if not is_admin():
        return "warning: not admin"
    success, message = focus_bh3_window()
    return "ok" if success else f"fail: {message}"


def _available(manager) -> set:
    return {m["name"] for m in manager.list_available_models()}


def _loaded(manager) -> set:
    return {m["name"] for m in manager.list_loaded_models()}


def _ensure_model(manager, model_name: str) -> bool:
    if model_name in _loaded(manager):
        return True
    if model_name not in _available(manager):
        logger.warning("模型 %s 不可用", model_name)
        return False
    result = manager.load_model(model_name=model_name, device="cpu")
    return result.get("success", False)


def _click_bbox(bbox) -> None:
    import win32api
    import win32con
    x1, y1, x2, y2 = bbox
    cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
    win32api.SetCursorPos((cx, cy))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
    time.sleep(0.03)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
    time.sleep(0.05)


def _press_esc():
    import pyautogui
    pyautogui.press('esc')


def _classify(manager) -> Optional[str]:
    if not _ensure_model(manager, "yolo11n_scene_cls"):
        return None
    try:
        image = _capture()
        result = manager.classify(image=image, model_name="yolo11n_scene_cls")
        if result and result.get("predictions"):
            return result["predictions"][0].get("top1", {}).get("label", "")
    except Exception:
        logger.exception("场景分类失败")
    return None


def _detect_button(manager, model_name: str, button_name: str, threshold: float = 0.5):
    """在当前屏幕中检测指定按钮，返回 (bbox, confidence) 或 (None, 0)"""
    if not _ensure_model(manager, model_name):
        return None, 0
    try:
        image = _capture()
        result = manager.detect(image=image, model_name=model_name, confidence_threshold=threshold)
        if result and result.get("detections"):
            for det in result["detections"]:
                if det.get("label") == button_name:
                    return det.get("bbox"), det.get("confidence", 0)
    except Exception:
        logger.exception("检测 %s 失败", button_name)
    return None, 0


def find_direction() -> Dict[str, Any]:
    """
    游戏场景自救定位。

    Returns:
        {"success": bool, "scene": str|None, "message": str, "esc_used": int}
    """
    manager = _get_manager()
    available_models = _available(manager)

    # --- 阶段一：寻找舰桥按钮 ---
    focus_status = _focus()

    # 选择第一个可用的检测模型
    det_model = None
    for name in DET_MODEL_PRIORITY:
        if name in available_models:
            det_model = name
            break

    if det_model is None:
        return {"success": False, "scene": None,
                "message": "无可用的UI检测模型，请检查YOLO模型文件是否完整", "esc_used": 0}

    if not _ensure_model(manager, det_model):
        return {"success": False, "scene": None,
                "message": f"无法加载检测模型 {det_model}", "esc_used": 0}

    bbox, conf = _detect_button(manager, det_model, "button_bridge")

    if bbox and conf >= 0.5:
        _click_bbox(bbox)
        time.sleep(1.5)
        return {"success": True, "scene": "bridge",
                "message": f"找到舰桥按钮（置信度{conf:.2f}）并点击，已返回舰桥", "esc_used": 0}

    # --- 阶段二：ESC返回 + 场景识别 ---
    _press_esc()
    time.sleep(1.5)

    scene = _classify(manager)
    if scene and scene in SCENE_TO_DET_MODEL:
        return {"success": True, "scene": scene,
                "message": f"按ESC后定位到已知场景: {scene}", "esc_used": 1}

    # --- 阶段三：循环ESC ---
    for i in range(MAX_ESC_RETRIES):
        _press_esc()
        time.sleep(1.5)
        scene = _classify(manager)

        if scene and scene in SCENE_TO_DET_MODEL:
            return {"success": True, "scene": scene,
                    "message": f"经过{i+2}次ESC后定位到已知场景: {scene}", "esc_used": i + 2}

    return {"success": False, "scene": scene,
            "message": f"已按{MAX_ESC_RETRIES + 1}次ESC仍无法定位"
                       f"（最后识别: {scene or '未知'}），请手动引导",
            "esc_used": MAX_ESC_RETRIES + 1}
