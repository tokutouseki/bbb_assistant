"""Live2D QOpenGLWidget with transparent frameless window.

Always in mascot mode (mouse passthrough). System tray provides quit only.
Window position and size persist between restarts.
"""

import json
import os
import sys
import ctypes
import logging

logger = logging.getLogger(__name__)

try:
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import (
        QSurfaceFormat, QKeyEvent, QGuiApplication,
        QIcon, QPixmap, QPainter, QColor, QAction,
    )
    from PySide6.QtWidgets import (
        QApplication, QSystemTrayIcon, QMenu,
    )
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False
    QOpenGLWidget = object


def _make_tray_icon() -> QIcon:
    """Create a simple colored square icon for the system tray (16x16)."""
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(100, 180, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 12, 12, 3, 3)
    painter.end()
    return QIcon(pixmap)


def _init_live2d_gl():
    """Initialize live2d OpenGL bindings. Called once after GL context is ready."""
    import live2d.v3 as live2d_v3
    live2d_v3.glInit()
    logger.info("Live2D OpenGL initialized")


def _load_window_state():
    """Load saved window position and size from disk.
    Checks window_state.json first, then falls back to user_settings.json.
    Returns (x, y, width, height) tuple.
    """
    try:
        from .config import WINDOW_STATE_FILE, DEFAULT_WINDOW_X, DEFAULT_WINDOW_Y, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
    except ImportError:
        from config import WINDOW_STATE_FILE, DEFAULT_WINDOW_X, DEFAULT_WINDOW_Y, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT  # type: ignore[no-redef]

    # 1. window_state.json (saved on close)
    if os.path.exists(WINDOW_STATE_FILE):
        try:
            with open(WINDOW_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            x = state.get("x", DEFAULT_WINDOW_X)
            y = state.get("y", DEFAULT_WINDOW_Y)
            w = state.get("width", DEFAULT_WINDOW_WIDTH)
            h = state.get("height", DEFAULT_WINDOW_HEIGHT)
            logger.info(f"Loaded window state from window_state.json: pos=({x}, {y}) size={w}x{h}")
            return x, y, w, h
        except Exception:
            pass

    # 2. Fallback: user_settings.json (saved by frontend settings)
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "data", "user_settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            x = settings.get("live2d_window_x", DEFAULT_WINDOW_X)
            y = settings.get("live2d_window_y", DEFAULT_WINDOW_Y)
            w = settings.get("live2d_window_width", DEFAULT_WINDOW_WIDTH)
            h = settings.get("live2d_window_height", DEFAULT_WINDOW_HEIGHT)
            logger.info(f"Loaded window state from user_settings.json: pos=({x}, {y}) size={w}x{h}")
            return x, y, w, h
        except Exception:
            pass

    return DEFAULT_WINDOW_X, DEFAULT_WINDOW_Y, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT


def _save_window_state(x: int, y: int, width: int = 400, height: int = 500):
    """Save window position and size to disk."""
    try:
        from .config import WINDOW_STATE_FILE
    except ImportError:
        from config import WINDOW_STATE_FILE  # type: ignore[no-redef]
    try:
        with open(WINDOW_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"x": x, "y": y, "width": width, "height": height}, f)
    except Exception:
        pass


class Live2DWidget(QOpenGLWidget):
    """Top-level transparent OpenGL window hosting a Live2D model.

    Always in mascot mode (mouse passthrough). The system tray icon
    provides only a quit option.
    """

    invoke_signal = Signal(object)
    hide_requested = Signal()
    show_requested = Signal()
    move_requested = Signal(int, int)
    alpha_requested = Signal(float)
    close_requested = Signal()

    def __init__(self, model_manager):
        super().__init__()
        self._manager = model_manager
        self._gl_ready = False
        self._dpr = 1.0

        # ---------- window setup ----------
        self.setWindowTitle("Live2D")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # ---------- OpenGL format ----------
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        fmt.setSamples(0)
        self.setFormat(fmt)

        # ---------- signals ----------
        self.invoke_signal.connect(self._on_invoke)
        self.hide_requested.connect(self._on_hide)
        self.show_requested.connect(self._on_show)
        self.move_requested.connect(self._on_move)
        self.alpha_requested.connect(self._on_set_alpha)
        self.close_requested.connect(self._on_close)

        # ---------- size & position ----------
        start_x, start_y, start_w, start_h = _load_window_state()
        self.resize(start_w, start_h)
        self.move(start_x, start_y)
        self._manager.window_x = start_x
        self._manager.window_y = start_y

        # ---------- system tray (quit only) ----------
        self._tray = QSystemTrayIcon(_make_tray_icon(), self)
        self._tray.setToolTip("Live2D 看板娘")
        tray_menu = QMenu()
        quit_action = QAction("退出", tray_menu)
        quit_action.triggered.connect(self.close_requested.emit)
        tray_menu.addAction(quit_action)
        self._tray.setContextMenu(tray_menu)
        self._tray.show()

        # ---------- animation timer ----------
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(16)

        logger.info(f"Live2D window created pos=({start_x},{start_y}) size={start_w}x{start_h}")

    # ==================================================================
    # OpenGL callbacks
    # ==================================================================

    def initializeGL(self):
        try:
            _init_live2d_gl()
            self._dpr = QGuiApplication.primaryScreen().devicePixelRatio()
            self._gl_ready = True
            logger.info("Live2D GL widget initialized (top-level window)")
        except Exception as e:
            logger.error(f"initializeGL failed: {e}")

    def resizeGL(self, w: int, h: int):
        if self._gl_ready:
            self._manager.resize(w, h)

    def paintGL(self):
        if not self._gl_ready:
            return
        self._manager.render_model()

    # ==================================================================
    # Input handling
    # ==================================================================

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close_requested.emit()
            event.accept()

    def _enable_os_mouse_passthrough(self):
        """Set Windows extended styles so clicks pass through to underlying windows."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
            logger.info("OS-level mouse passthrough enabled")
        except Exception as e:
            logger.warning(f"Failed to enable OS mouse passthrough: {e}")

    # ==================================================================
    # Signal slots
    # ==================================================================

    def _on_invoke(self, func):
        func()

    def _on_hide(self):
        self.hide()
        self._manager.window_visible = False

    def showEvent(self, event):
        super().showEvent(event)
        self._enable_os_mouse_passthrough()

    def _on_show(self):
        self.show()
        self._manager.window_visible = True

    def _on_move(self, x: int, y: int):
        self.move(x, y)
        self._manager.window_x = x
        self._manager.window_y = y

    def _on_set_alpha(self, alpha: float):
        self.setWindowOpacity(float(alpha))
        self._manager.window_alpha = alpha

    def _on_close(self):
        logger.info("Live2D window closing")
        pos = self.frameGeometry().topLeft()
        sz = self.frameGeometry().size()
        _save_window_state(pos.x(), pos.y(), sz.width(), sz.height())
        self._tray.hide()
        self.hide()
        QApplication.instance().quit()
