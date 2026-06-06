"""
运行时设置管理 —— 带 JSON 文件持久化
重启后自动加载上次保存的配置
"""
import json
import os
import logging
from typing import Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..", "data"
)
_CONFIG_DIR = os.path.abspath(_CONFIG_DIR)
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "user_settings.json")

DEFAULT_SETTINGS = {
    "llm_provider": "deepseek",
    "llm_model": "deepseek-chat",
    "llm_api_key": "",
    "llm_api_base_url": "https://api.deepseek.com/v1",
    "llm_temperature": 0.7,
    "llm_max_tokens": 4096,
    "image_describer_backend": "bailian",
    "bailian_api_key": "",
    "live2d_enabled": True,
    "live2d_model_name": "",
    "live2d_auto_emotion": True,
    "live2d_window_alpha": 1.0,
    "live2d_window_width": 400,
    "live2d_window_height": 500,
    "live2d_window_x": 100,
    "live2d_window_y": 100,
    "companion_character": "爱莉希雅",
    "companion_tts_voice": "爱莉希雅",
    "companion_personality": "",
    "auto_tts_enabled": False,
}

_lock = Lock()


def _load_from_file() -> Dict[str, Any]:
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        if os.path.isfile(_CONFIG_FILE):
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            for k in DEFAULT_SETTINGS:
                if k in saved and saved[k] is not None:
                    merged[k] = saved[k]
            return merged
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def _save_to_file(settings: Dict[str, Any]) -> None:
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存设置文件失败 ({_CONFIG_FILE}): {e}")


_runtime_settings = _load_from_file()


def get_runtime_settings() -> Dict[str, Any]:
    with _lock:
        return dict(_runtime_settings)


def get_config_file_path() -> str:
    return _CONFIG_FILE


def get_config_file_content() -> str:
    try:
        if os.path.isfile(_CONFIG_FILE):
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""


def update_runtime_settings(overrides: Dict[str, Any]) -> None:
    global _runtime_settings
    with _lock:
        changed = False
        for key in DEFAULT_SETTINGS:
            if key in overrides and overrides[key] is not None:
                new_val = overrides[key]
                old_val = _runtime_settings.get(key)
                if old_val != new_val:
                    _runtime_settings[key] = new_val
                    changed = True
                    if key == "companion_character":
                        logger.info(f"运行时设置变更: companion_character = '{old_val}' → '{new_val}'")
        if changed:
            _save_to_file(_runtime_settings)
            if "companion_character" in overrides:
                logger.info(f"设置已保存到文件: companion_character = '{_runtime_settings.get('companion_character')}'")


def reset_to_defaults() -> None:
    global _runtime_settings
    with _lock:
        _runtime_settings = dict(DEFAULT_SETTINGS)
        _save_to_file(_runtime_settings)
