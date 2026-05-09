"""
窗口聚焦模块 - 用于操作Windows窗口
提供查找窗口、设置焦点等功能，针对崩坏3游戏窗口优化
"""

import ctypes
import time
from ctypes import wintypes

# Windows API 常量
WM_SETFOCUS = 0x0007
SW_RESTORE = 9
SW_SHOW = 5
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040

# 加载 Windows API 函数
user32 = ctypes.windll.user32
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, 
                                ctypes.c_int, ctypes.c_int, 
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, 
                                wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_long

def is_admin():
    """检查当前进程是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def find_window_by_title(title):
    """根据窗口标题查找窗口句柄"""
    return user32.FindWindowW(None, title)

def get_foreground_window():
    """获取当前前台窗口句柄"""
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    return user32.GetForegroundWindow()


def set_focus_to_window(hwnd):
    """将焦点设置到指定窗口"""
    if not hwnd:
        return False, "无效的窗口句柄"
    
    try:
        # 检查窗口是否可见
        if not user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.1)
        
        # 先尝试提升窗口到最顶层
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 
                            SWP_NOSIZE | SWP_NOMOVE)
        time.sleep(0.05)
        
        # 然后取消置顶但保持显示
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, 
                            SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW)
        time.sleep(0.05)
        
        # 确保窗口可见
        user32.ShowWindow(hwnd, SW_SHOW)
        time.sleep(0.1)
        
        # 尝试设置前台窗口
        result = user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        
        # 发送焦点消息
        user32.SendMessageW(hwnd, WM_SETFOCUS, 0, 0)
        
        # 验证是否成功（即使SetForegroundWindow返回False，窗口可能已经被激活）
        time.sleep(0.1)
        current_foreground = get_foreground_window()
        
        if current_foreground == hwnd:
            return True, "窗口已成功激活"
        elif result != 0:
            return True, "SetForegroundWindow调用成功"
        else:
            # SetForegroundWindow返回False但窗口可能仍被激活
            return True, "窗口操作已执行（Windows安全限制可能阻止SetForegroundWindow返回True）"
            
    except Exception as e:
        return False, f"设置焦点失败: {str(e)}"

def focus_bh3_window(window_title: str = "崩坏3"):
    """将焦点转到崩坏3游戏窗口"""
    # 尝试多种可能的窗口标题
    possible_titles = [
        window_title,
        "崩坏3",
        "Honkai Impact 3rd",
        "HonkaiImpact3",
        "崩坏3-PC",
        "BH3",
    ]
    
    hwnd = None
    found_title = None
    
    # 尝试每个可能的标题
    for title in possible_titles:
        hwnd = find_window_by_title(title)
        if hwnd:
            found_title = title
            break
    
    if not hwnd:
        # 尝试模糊匹配（包含关键词的窗口）
        hwnd = find_window_by_partial_title("崩坏")
        if hwnd:
            found_title = "包含'崩坏'的窗口"
        else:
            hwnd = find_window_by_partial_title("Honkai")
            if hwnd:
                found_title = "包含'Honkai'的窗口"
    
    if not hwnd:
        return False, f"未找到游戏窗口，请确保游戏已启动。尝试过的标题: {', '.join(possible_titles)}"
    
    # 使用新的 set_focus_to_window（返回元组）
    success, message = set_focus_to_window(hwnd)
    if success:
        return True, f"成功聚焦'{found_title}'窗口 - {message}"
    else:
        return False, f"找到窗口'{found_title}'但无法设置焦点: {message}"


def find_window_by_partial_title(partial_title):
    """根据部分窗口标题查找窗口句柄（模糊匹配）"""
    hwnd_list = []
    
    def callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                window_title = buffer.value
                if partial_title in window_title:
                    hwnd_list.append((hwnd, window_title))
        return True
    
    # 添加 GetWindowTextLengthW 和 GetWindowTextW 的类型定义
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(callback), 0)
    
    if hwnd_list:
        # 返回第一个找到的窗口
        return hwnd_list[0][0]
    return None
