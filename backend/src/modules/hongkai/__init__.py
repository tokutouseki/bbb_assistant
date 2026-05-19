"""
hongkai 自动化模块 — 从 hongkai_done 提取的核心游戏自动化功能。

提供：
- 模板匹配 + 键鼠模拟 (clicks_keyboard.py + 112 张 PNG 模板)
- YOLO 目标检测 (call_YOLO.py + yolo_server)
- OCR 文字识别 (ocr_functions.py + ocr_server)
- 窗口管理 (on_window.py)
- 键鼠录制回放 (replay_keyboard.py)
- 配置管理 (config.py)
"""
import os as _os
import sys as _sys

# 确保本包及其子模块在 sys.path 中
_pkg_root = _os.path.dirname(_os.path.abspath(__file__))
if _pkg_root not in _sys.path:
    _sys.path.insert(0, _pkg_root)
