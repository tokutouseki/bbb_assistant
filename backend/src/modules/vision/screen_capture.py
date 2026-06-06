import ctypes
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 避免日志刷屏：只在捕获方法变化时输出 INFO，重复使用同一方法时静默
_last_capture_method = [None]  # 'printwindow' | 'getdc' | 'mss'

# DPI awareness — set once at module load to get correct window coordinates
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Game window title variants to try (in priority order)
_GAME_TITLE_VARIANTS = ["崩坏3", "Honkai Impact 3rd", "HonkaiImpact3", "崩坏3-PC", "BH3"]


def _find_game_window_hwnd(title: str = "崩坏3"):
    """Find the game window handle. Tries exact match first, then variant titles."""
    import win32gui

    # Exact match
    hwnd = win32gui.FindWindow(None, title)
    if hwnd:
        return hwnd

    # Try all variant titles
    for variant in _GAME_TITLE_VARIANTS:
        hwnd = win32gui.FindWindow(None, variant)
        if hwnd:
            return hwnd

    # Partial title match via EnumWindows
    def _enum_callback(h, _result):
        try:
            wt = win32gui.GetWindowText(h)
            if "崩坏" in wt or "Honkai" in wt:
                _result.append(h)
                return False
        except Exception:
            pass
        return True

    result = []
    try:
        win32gui.EnumWindows(_enum_callback, result)
    except Exception:
        pass

    return result[0] if result else None


def _get_window_rect(hwnd):
    """Get window rect (left, top, right, bottom) via win32gui."""
    import win32gui
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def _get_client_rect_screen(hwnd):
    """Get client area in screen coordinates (excludes title bar/borders)."""
    import win32gui
    try:
        rect = win32gui.GetClientRect(hwnd)
        pt = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
        return (pt[0], pt[1], pt[0] + rect[2] - rect[0], pt[1] + rect[3] - rect[1])
    except Exception:
        return None


class ScreenCapture:
    """屏幕捕获工具，支持全屏、区域和窗口级捕获"""

    def __init__(self):
        self.capture_method = self._detect_capture_method()
        logger.debug(f"使用屏幕捕获方法: {self.capture_method}")

    def _detect_capture_method(self):
        try:
            import mss
            return "mss"
        except ImportError:
            try:
                import pyautogui
                return "pyautogui"
            except ImportError:
                return "pil"

    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """捕获屏幕截图。region: (x1, y1, x2, y2) 或 None=全屏。"""
        if self.capture_method == "mss":
            return self._capture_mss(region)
        elif self.capture_method == "pyautogui":
            return self._capture_pyautogui(region)
        else:
            return self._capture_pil(region)

    def _capture_mss(self, region=None):
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                if region:
                    monitor = {"left": region[0], "top": region[1],
                              "width": region[2] - region[0], "height": region[3] - region[1]}
                else:
                    monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                return np.array(screenshot)
        except Exception as e:
            logger.error(f"mss捕获失败: {e}")
            return self._capture_fallback(region)

    def _capture_pyautogui(self, region=None):
        try:
            import pyautogui
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            return np.array(screenshot)
        except Exception as e:
            logger.error(f"pyautogui捕获失败: {e}")
            return self._capture_fallback(region)

    def _capture_pil(self, region=None):
        try:
            from PIL import ImageGrab
            if region:
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()
            return np.array(screenshot)
        except Exception as e:
            logger.error(f"PIL捕获失败: {e}")
            return np.zeros((100, 100, 3), dtype=np.uint8)

    def _capture_fallback(self, region=None):
        logger.warning("使用备用捕获方法")
        if region:
            height = region[3] - region[1]
            width = region[2] - region[0]
        else:
            width, height = 1920, 1080
        return np.zeros((height, width, 3), dtype=np.uint8)

    def capture_game_window(self, window_title: str = "崩坏3") -> np.ndarray:
        """捕获游戏窗口区域（含标题栏/边框），仅截取窗口 bbox 不包含其他窗口。"""
        hwnd = _find_game_window_hwnd(window_title)
        if hwnd is None:
            logger.warning(f"未找到游戏窗口 '{window_title}'，回退全屏截图")
            return self.capture()

        rect = _get_window_rect(hwnd)
        if rect is None:
            logger.warning("获取窗口矩形失败，回退全屏截图")
            return self.capture()

        logger.info(f"捕获游戏窗口区域: {rect}")
        return self.capture(region=rect)

    def get_game_client_rect(self, window_title: str = "崩坏3") -> Optional[Tuple[int, int, int, int]]:
        """获取游戏客户区屏幕坐标 (left, top, right, bottom)，失败返回 None。"""
        hwnd = _find_game_window_hwnd(window_title)
        if hwnd is None:
            return None
        return _get_client_rect_screen(hwnd)

    def capture_game_client_area(self, window_title: str = "崩坏3") -> np.ndarray:
        """捕获游戏窗口客户区（不含标题栏/边框），用于 YOLO/OCR。

        优先使用 PrintWindow API 捕获窗口内容（无视遮挡），
        失败时回退到 mss 屏幕截图（可能被置顶窗口遮挡）。
        """
        hwnd = _find_game_window_hwnd(window_title)
        if hwnd is None:
            logger.warning(f"未找到游戏窗口 '{window_title}'，回退全屏截图")
            return self.capture()

        rect = _get_client_rect_screen(hwnd)
        if rect is None:
            logger.warning("获取客户区失败，回退窗口截图")
            return self.capture_game_window(window_title)

        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w < 100 or h < 100:
            logger.warning(f"客户区太小 ({w}x{h})，回退窗口截图")
            return self.capture_game_window(window_title)

        # 优先级 1: PrintWindow（DWM 缩略图，无视遮挡，Win 8.1+）
        result = self._capture_via_printwindow(hwnd, rect)
        if result is not None:
            if _last_capture_method[0] != 'printwindow':
                _last_capture_method[0] = 'printwindow'
                logger.info(f"PrintWindow 捕获成功 ({w}x{h})，无视遮挡 (后续同类捕获将静默)")
            return result

        # 优先级 2: GetDC + BitBlt（窗口 DC，无视遮挡，兼容性更好）
        result = self._capture_via_getdc(hwnd, rect)
        if result is not None:
            if _last_capture_method[0] != 'getdc':
                _last_capture_method[0] = 'getdc'
                logger.info(f"GetDC+BitBlt 捕获成功 ({w}x{h})，无视遮挡 (后续同类捕获将静默)")
            return result

        # 优先级 3: mss.grab 屏幕截图（可能被置顶窗口遮挡）
        if _last_capture_method[0] != 'mss':
            _last_capture_method[0] = 'mss'
            logger.warning(f"PrintWindow 和 GetDC 均失败，回退 mss.grab 屏幕截图（可能被置顶窗口遮挡）")
        return self.capture(region=rect)

    def _capture_via_printwindow(self, hwnd, rect) -> Optional[np.ndarray]:
        """使用 PrintWindow API 捕获窗口客户区内容。

        PrintWindow 直接从窗口 DC 获取内容，不受置顶窗口遮挡影响。
        需要 Windows 8.1+ (PW_RENDERFULLCONTENT)。

        Returns:
            numpy ndarray (RGB) on success, None on failure.
        """
        import win32gui
        import win32ui
        import ctypes
        from ctypes import wintypes

        # 通过 ctypes 调用 PrintWindow（兼容所有 pywin32 版本）
        _user32 = ctypes.windll.user32
        _user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.c_uint]
        _user32.PrintWindow.restype = wintypes.BOOL

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        hwnd_dc = None
        mfc_dc = None
        save_dc = None
        bitmap = None

        try:
            # PW_RENDERFULLCONTENT = 2: 捕获 DWM 缩略图（含 GPU 渲染内容）
            # PW_CLIENTONLY = 1: 仅客户区（XP+ 兼容）
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            # 尝试 PW_RENDERFULLCONTENT (Win 8.1+)
            result = _user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
            if result != 1:
                # 回退 PW_CLIENTONLY
                result = _user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 1)

            if result != 1:
                return None

            # 位图 → numpy array (BGRA → RGB)
            bitmap_bits = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bitmap_bits, dtype=np.uint8)
            img = img.reshape((height, width, 4))
            img = img[..., :3][..., ::-1].copy()  # BGRA → RGB

            return img

        except Exception as e:
            logger.warning(f"PrintWindow 捕获失败: {e}")
            return None
        finally:
            try:
                if save_dc:
                    save_dc.DeleteDC()
                if mfc_dc:
                    mfc_dc.DeleteDC()
                if hwnd_dc:
                    win32gui.ReleaseDC(hwnd, hwnd_dc)
                if bitmap:
                    win32gui.DeleteObject(bitmap.GetHandle())
            except Exception:
                pass

    def _capture_via_getdc(self, hwnd, rect) -> Optional[np.ndarray]:
        """使用 GetDC + BitBlt 从窗口 DC 直接捕获客户区内容。

        与 PrintWindow 不同，GetDC 返回窗口的 GDI 设备上下文，
        BitBlt 直接从该 DC 复制像素——完全不受置顶窗口遮挡影响。
        兼容性优于 PrintWindow（不依赖 DWM），但对 GPU 独占渲染的游戏可能无效。

        Returns:
            numpy ndarray (RGB) on success, None on failure.
        """
        import win32gui
        import win32ui
        import win32con

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        hwnd_dc = None
        mfc_dc = None
        save_dc = None
        bitmap = None

        try:
            hwnd_dc = win32gui.GetDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            # BitBlt 从窗口 DC 复制到内存 DC（无视遮挡）
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

            bitmap_bits = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bitmap_bits, dtype=np.uint8)
            img = img.reshape((height, width, 4))
            img = img[..., :3][..., ::-1].copy()  # BGRA → RGB

            return img

        except Exception as e:
            logger.warning(f"GetDC+BitBlt 捕获失败: {e}")
            return None
        finally:
            try:
                if save_dc:
                    save_dc.DeleteDC()
                if mfc_dc:
                    mfc_dc.DeleteDC()
                if hwnd_dc:
                    win32gui.ReleaseDC(hwnd, hwnd_dc)
                if bitmap:
                    win32gui.DeleteObject(bitmap.GetHandle())
            except Exception:
                pass
