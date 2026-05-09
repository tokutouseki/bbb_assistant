import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ScreenCapture:
    """屏幕捕获工具，支持全屏和区域捕获"""
    
    def __init__(self):
        self.capture_method = self._detect_capture_method()
        logger.info(f"使用屏幕捕获方法: {self.capture_method}")
    
    def _detect_capture_method(self):
        """检测可用的屏幕捕获方法"""
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
        """
        捕获屏幕截图
        
        Args:
            region: 可选区域 (x1, y1, x2, y2)
            
        Returns:
            numpy数组格式的截图 (RGB)
        """
        if self.capture_method == "mss":
            return self._capture_mss(region)
        elif self.capture_method == "pyautogui":
            return self._capture_pyautogui(region)
        else:
            return self._capture_pil(region)
    
    def _capture_mss(self, region=None):
        """使用mss库捕获"""
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                if region:
                    monitor = {"left": region[0], "top": region[1], 
                              "width": region[2]-region[0], "height": region[3]-region[1]}
                else:
                    monitor = sct.monitors[1]  # 主显示器
                screenshot = sct.grab(monitor)
                return np.array(screenshot)
        except Exception as e:
            logger.error(f"mss捕获失败: {e}")
            return self._capture_fallback(region)
    
    def _capture_pyautogui(self, region=None):
        """使用pyautogui捕获"""
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
        """使用PIL捕获（备用）"""
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
        """备用捕获方法"""
        logger.warning("使用备用捕获方法")
        # 返回黑色图像
        if region:
            height = region[3] - region[1]
            width = region[2] - region[0]
        else:
            width, height = 1920, 1080
        return np.zeros((height, width, 3), dtype=np.uint8)
    
    def capture_game_window(self, window_title: str = "崩坏3") -> Optional[np.ndarray]:
        """
        捕获特定游戏窗口
        
        Args:
            window_title: 窗口标题
            
        Returns:
            游戏窗口截图或None
        """
        # TODO: 实现游戏窗口捕获
        logger.info(f"尝试捕获游戏窗口: {window_title}")
        return self.capture()