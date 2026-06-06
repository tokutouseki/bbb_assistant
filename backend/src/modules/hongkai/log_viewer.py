#!/usr/bin/env python3
"""Log viewer window for hongkai automation scripts.

Mouse behavior:
    - Window is fully mouse-transparent (WS_EX_TRANSPARENT + WA_TransparentForMouseEvents)
    - All clicks, scrolls, and mouse events pass through to the game
    - Auto-scrolls to follow new content (no manual scrolling needed)

Usage:
    python log_viewer.py --log-file <path> --title "任务名称"
"""

import sys
import os
import argparse
import time

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QTextCursor

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _GWL_EXSTYLE = -20
    _WS_EX_TRANSPARENT = 0x00000020
    _WS_EX_LAYERED = 0x00080000

    _SetWindowLongW = ctypes.windll.user32.SetWindowLongW
    _SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    _SetWindowLongW.restype = wintypes.LONG
    _GetWindowLongW = ctypes.windll.user32.GetWindowLongW
    _GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _GetWindowLongW.restype = wintypes.LONG


class LogViewer(QWidget):
    MIN_DISPLAY_SECONDS = 5
    IDLE_CLOSE_SECONDS = 120
    MIN_DISPLAY_BEFORE_CLOSE = 15

    def __init__(self, log_file: str, title: str = ""):
        super().__init__()
        self.log_file = log_file
        self._last_size = 0
        self._last_update = time.time()
        self._file_ready = os.path.exists(log_file)
        self._wait_start = time.time()
        self._display_start = None
        self._show_time = time.time()
        self._closing = False

        self._setup_ui(title)
        self._setup_timer()

    # ---- Win32 mouse transparency ----
    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                ex_style = _GetWindowLongW(hwnd, _GWL_EXSTYLE)
                _SetWindowLongW(
                    hwnd, _GWL_EXSTYLE,
                    ex_style | _WS_EX_TRANSPARENT | _WS_EX_LAYERED,
                )
            except Exception:
                pass

    # ---- UI setup ----
    def _setup_ui(self, title: str):
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        # Full mouse transparency — all events pass through to game
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.resize(620, 420)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(0, screen.bottom() - 420)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.WindowText, QColor(200, 200, 220))
        palette.setColor(QPalette.Base, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.Text, QColor(200, 200, 220))
        self.setPalette(palette)
        self.setAutoFillBackground(False)

        # Outer layout — zero margin so the container sits tight against window edges
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Unified container — one continuous block
        container = QWidget()
        container.setStyleSheet(
            "QWidget {"
            "  background-color: rgba(20, 20, 32, 220);"
            "  border-radius: 10px;"
            "}"
        )
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: #ffffff; font-size: 13px; font-weight: bold;"
            "padding: 6px 10px 4px 10px;"
            "background: transparent;"
        )
        title_font = QFont("Microsoft YaHei", 12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        container_layout.addWidget(title_label)

        # File hint
        path_label = QLabel(os.path.basename(self.log_file))
        path_label.setStyleSheet(
            "color: #ffffff; font-size: 11px;"
            "padding: 0px 10px 6px 10px;"
            "background: transparent;"
        )
        container_layout.addWidget(path_label)

        # Log text area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet(
            "QTextEdit {"
            "  background-color: transparent;"
            "  color: #ffffff;"
            "  border: none;"
            "  border-radius: 0px;"
            "  padding: 8px 10px;"
            "  font-family: 'Consolas', 'Microsoft YaHei', monospace;"
            "  font-size: 12px;"
            "}"
        )
        container_layout.addWidget(self.text_edit)

        layout.addWidget(container)


    # ---- Timer & polling ----
    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(200)

    def _schedule_close(self, reason: str, delay: float = 1.5):
        if self._closing:
            return
        self._closing = True
        self.timer.stop()
        elapsed = time.time() - self._show_time
        effective_delay = max(delay, self.MIN_DISPLAY_SECONDS - elapsed)
        QTimer.singleShot(int(effective_delay * 1000), self.close)

    def _poll(self):
        now = time.time()

        if not self._file_ready:
            if os.path.exists(self.log_file):
                self._file_ready = True
                self._last_update = now
            else:
                elapsed = now - self._wait_start
                if elapsed > 10:
                    self._schedule_close("", delay=1.0)
                return

        try:
            current_size = os.path.getsize(self.log_file)
            if current_size < self._last_size:
                self._last_size = 0

            if current_size > self._last_size:
                with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self._last_size)
                    new_text = f.read()
                    self._last_size = current_size
                    self._last_update = now

                    if self._display_start is None:
                        self._display_start = now

                    if "TASK_COMPLETE" in new_text:
                        self._schedule_close("", delay=1.5)

                    # Always auto-scroll to bottom (mouse-transparent window)
                    self.text_edit.moveCursor(QTextCursor.End)
                    self.text_edit.insertPlainText(new_text)
                    self.text_edit.moveCursor(QTextCursor.End)
                    self.text_edit.ensureCursorVisible()

                    # Limit memory
                    doc = self.text_edit.document()
                    if doc.blockCount() > 2000:
                        cursor = QTextCursor(doc.findBlockByNumber(0))
                        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 500)
                        cursor.removeSelectedText()

            else:
                min_displayed = (
                    self._display_start is not None
                    and (now - self._display_start) >= self.MIN_DISPLAY_BEFORE_CLOSE
                )
                idle = now - self._last_update
                if idle > self.IDLE_CLOSE_SECONDS and self._last_size > 0 and min_displayed:
                    self._schedule_close(f"{idle:.0f}s", delay=1.0)
        except (IOError, PermissionError):
            pass


def main():
    parser = argparse.ArgumentParser(description="Hongkai Log Viewer")
    parser.add_argument("--log-file", required=True, help="Path to log file")
    parser.add_argument("--title", default="", help="Window title")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    viewer = LogViewer(log_file=args.log_file, title=args.title)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
