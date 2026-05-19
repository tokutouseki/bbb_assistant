import ctypes
import time
import sys
from ctypes import wintypes

# 定义缺少的类型
LRESULT = ctypes.c_long

# 定义Windows API常量
GW_HWNDNEXT = 2
WM_SETFOCUS = 0x0007
SW_RESTORE = 9
SW_SHOW = 5
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040

# 定义结构体
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

# 加载Windows API函数
user32 = ctypes.windll.user32
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL

user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = LRESULT

user32.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
user32.GetWindow.restype = wintypes.HWND

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

def is_admin():
    """
    检查当前进程是否以管理员身份运行
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """
    以管理员身份重新启动当前程序
    """
    try:
        # 获取当前程序的路径
        script = sys.argv[0]
        
        # 使用ShellExecuteEx以管理员身份重新启动
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, script, None, 1
        )
        return True
    except Exception as e:
        print(f"提权失败: {e}")
        return False

def find_window_by_title(title):
    """
    根据窗口标题查找窗口句柄
    :param title: 窗口标题
    :return: 窗口句柄，如果没找到返回0
    """
    return user32.FindWindowW(None, title)

def set_focus_to_window(hwnd):
    """
    将焦点设置到指定窗口（增强版：强制置顶）
    :param hwnd: 窗口句柄
    :return: 如果成功返回True，否则返回False
    """
    if not hwnd:
        return False
    
    try:
        # 检查窗口是否可见，如果不可见则显示它
        if not user32.IsWindowVisible(hwnd):
            # 尝试恢复窗口
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.1)
        
        # 先将窗口置顶（使用SetWindowPos）
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
        time.sleep(0.05)
        
        # 再取消置顶，让窗口回到正常层级
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW)
        time.sleep(0.05)
        
        # 将窗口显示到最前面
        user32.ShowWindow(hwnd, SW_SHOW)
        time.sleep(0.1)
        
        # 设置焦点到窗口
        result = user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        
        # 发送WM_SETFOCUS消息确保窗口获得焦点
        user32.SendMessageW(hwnd, WM_SETFOCUS, 0, 0)
        
        return result != 0
    except Exception as e:
        print(f"设置窗口焦点时出错: {e}")
        return False

def focus_bh3_window():
    """
    将焦点转到名字叫做"崩坏3"的窗口中
    :return: 如果成功返回True，否则返回False
    """
    window_title = "崩坏3"
    hwnd = find_window_by_title(window_title)
    
    if not hwnd:
        print(f"未找到名为'{window_title}'的窗口")
        sys.exit(1)
    
    print(f"找到窗口: {window_title} (句柄: {hwnd})")
    
    if set_focus_to_window(hwnd):
        print(f"成功将焦点设置到'{window_title}'窗口")
        return True
    else:
        print(f"无法将焦点设置到'{window_title}'窗口")
        sys.exit(1)

if __name__ == "__main__":
    # 检查是否以管理员身份运行
    if not is_admin():
        print("程序需要以管理员身份运行才能正常工作！")
        print("正在尝试自动提权...")
        
        if run_as_admin():
            print("请在弹出的UAC提示中选择'是'以继续...")
            sys.exit(0)  # 退出当前进程，等待管理员权限进程启动
        else:
            print("自动提权失败，请手动右键点击程序并选择'以管理员身份运行'")
            input("按回车键退出...")
            sys.exit(1)
    
    # 尝试将焦点转到"崩坏3"窗口
    focus_bh3_window()