import pyautogui
import cv2
import numpy as np
import time
import os
import ctypes
from ctypes import wintypes, c_bool, c_int
import sys
from datetime import datetime
try:
    from ..on_window import focus_bh3_window
except ImportError:
    from on_window import focus_bh3_window

# 获取程序所在目录
if getattr(sys, 'frozen', False):
    # 如果是打包后的程序
    script_dir = sys._MEIPASS
else:
    # 如果是普通 Python 脚本
    script_dir = os.path.dirname(os.path.abspath(__file__))

# 定义Windows API常量和结构体
INPUT_MOUSE = 0
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_VIRTUALDESK = 0x4000  # 使用虚拟桌面坐标
MOUSEEVENTF_WHEEL = 0x0800  # 鼠标垂直滚轮
MOUSEEVENTF_HWHEEL = 0x1000  # 鼠标水平滚轮

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("mi", MOUSEINPUT)
    ]

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

def get_screen_scale():
    """
    获取屏幕缩放比例
    :return: 屏幕缩放比例（例如1.0表示100%缩放）
    """
    try:
        # 使用ctypes获取屏幕缩放比例
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        
        # 获取设备上下文
        hdc = user32.GetDC(0)
        
        # 获取逻辑DPI
        logical_dpi = gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        
        # 释放设备上下文
        user32.ReleaseDC(0, hdc)
        
        # 计算缩放比例（默认96 DPI为100%）
        scale = logical_dpi / 96.0
        return scale
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取屏幕缩放比例失败: {e}")
        return 1.0  # 默认返回1.0

def click_template(image_name, description=None, template_path=None, confidence=0.8, time_sleep=1, save_screenshot=False):
    """
    在屏幕上查找并点击指定的模板图片，只点击一次
    :param image_name: 模板图片名称（不包含路径）
    :param description: 图片描述（用于日志）
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :param time_sleep: 操作前等待时间
    :param save_screenshot: 是否保存识别结果截图，默认False
    :return: 如果找到并点击则返回True，否则返回False
    """
    found, center_x, center_y, match_region = is_template(image_name, description, template_path, confidence, time_sleep, save_screenshot)
    
    if found:
        try:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.05
            
            click_at_position(center_x, center_y)
            
            image_desc = f"{description} " if description else ""
            print(f"[{time.strftime('%H:%M:%S')}] 成功点击{image_desc}{image_name}图片，坐标: ({center_x}, {center_y})")
            
            if save_screenshot:
                try:
                    save_dir = os.path.join(script_dir, "rec")
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir)
                    
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    file_name = f"click_template_{image_name}_{current_time}.png"
                    file_path = os.path.join(save_dir, file_name)
                    
                    cv2.imwrite(file_path, cv2.cvtColor(match_region, cv2.COLOR_RGB2BGR))
                    
                    print(f"[{time.strftime('%H:%M:%S')}] 点击识别结果已保存至: {file_path}")
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] 保存点击识别结果失败: {e}")
            
            return True
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 执行错误: {e}")
            return False
    else:
        return False

def click_current_position():
    """
    使用Windows API在当前鼠标位置点击鼠标
    :return: 如果成功返回True，否则返回False
    """
    try:
        # 获取当前鼠标坐标
        current_x, current_y = pyautogui.position()
        
        # 调用现有的click_at_position函数执行点击操作
        return click_at_position(current_x, current_y)
    except Exception as e:
        # 捕获并显示任何异常
        print(f"[{time.strftime('%H:%M:%S')}] 执行错误: {e}")
        return False

def is_template(image_name, description=None, template_path=None, confidence=0.8, time_sleep=1, save_screenshot=False):
    """
    在屏幕上查找指定的模板图片，不执行点击操作
    :param image_name: 模板图片名称（不包含路径）
    :param description: 图片描述（用于日志）
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :param time_sleep: 操作前等待时间（秒），默认0秒
    :param save_screenshot: 是否保存识别结果截图，默认False
    :return: 如果找到图片则返回 (True, center_x, center_y, match_region)，否则返回 (False, None, None, None)
    """
    if time_sleep > 0:
        time.sleep(time_sleep)
    if not template_path:
        template_path = os.path.join(script_dir, image_name)
    
    if not os.path.exists(template_path):
        print(f"[{time.strftime('%H:%M:%S')}] 图片不存在: {template_path}")
        return False, None, None, None
    
    try:
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        template_height, template_width = template_gray.shape[:2]
        print(f"[{time.strftime('%H:%M:%S')}] 模板图片加载成功: {template_path}")
        
        from src.modules.vision.screen_capture import ScreenCapture
        sc = ScreenCapture()
        client_rect = sc.get_game_client_rect()
        if client_rect is not None:
            screenshot_np = sc.capture_game_client_area()
            offset_x, offset_y = client_rect[0], client_rect[1]
        else:
            screenshot_np = sc.capture()
            offset_x, offset_y = 0, 0
        screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)
        locations = list(zip(*locations[::-1]))

        if locations:
            x, y = locations[0]
            center_x = x + template_width // 2 + offset_x
            center_y = y + template_height // 2 + offset_y

            screen_width, screen_height = pyautogui.size()
            if 0 <= center_x < screen_width and 0 <= center_y < screen_height:
                match_region = screenshot_np[y:y+template_height, x:x+template_width]
                
                image_desc = f"{description} " if description else ""
                print(f"[{time.strftime('%H:%M:%S')}] 成功识别到{image_desc}{image_name}图片，坐标: ({center_x}, {center_y})")
                
                if save_screenshot:
                    try:
                        save_dir = os.path.join(script_dir, "rec")
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir)
                        
                        current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                        file_name = f"is_template_{image_name}_{current_time}.png"
                        file_path = os.path.join(save_dir, file_name)
                        
                        cv2.imwrite(file_path, cv2.cvtColor(match_region, cv2.COLOR_RGB2BGR))
                        
                        print(f"[{time.strftime('%H:%M:%S')}] 识别区域坐标范围: ({x}, {y}) - ({x+template_width}, {y+template_height})")
                        print(f"[{time.strftime('%H:%M:%S')}] 识别结果已保存至: {file_path}")
                    except Exception as e:
                        print(f"[{time.strftime('%H:%M:%S')}] 保存识别结果失败: {e}")
                
                return True, center_x, center_y, match_region
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 图片位置超出屏幕范围，坐标: ({center_x}, {center_y})")
                return False, None, None, None
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 未在屏幕上找到{image_name}图片")
            return False, None, None, None
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 执行错误: {e}")
        return False, None, None, None

def is_complex_temp(image_name, description=None, template_path=None, confidence=0.8, time_sleep=0, region=None, save_screenshot=False, debug=False):
    """
    在屏幕上查找指定的模板图片，使用复杂的识别方法（边缘检测、轮廓匹配、亮度检查等）
    
    识别方法（按优先级依次尝试）：
    1. 边缘检测匹配：使用Canny边缘检测提取图片边缘，然后进行模板匹配
       - Canny阈值：50, 200
       - 适用于：边缘清晰、背景变化较大的场景
       
    2. 轮廓匹配：提取模板和屏幕截图的轮廓，通过轮廓相似度进行匹配
       - 使用自适应阈值二值化（ADAPTIVE_THRESH_GAUSSIAN_C）
       - 高斯模糊核大小：(5, 5)
       - 轮廓相似度阈值：< 0.03
       - 面积匹配范围：模板面积的 0.7~1.3 倍
       - 圆形度阈值：> 0.6
       - 适用于：形状特征明显的目标（如圆形图标）
       
    3. 模板匹配：使用三种OpenCV模板匹配方法
       - TM_CCOEFF_NORMED：归一化相关系数匹配
       - TM_CCORR_NORMED：归一化互相关匹配
       - TM_SQDIFF_NORMED：归一化平方差匹配
       - 适用于：标准模板匹配场景
    
    验证条件（所有匹配方法都需要通过以下验证）：
    1. 亮度检查：使用HSV颜色空间检测高亮区域
       - HSV范围：H[0,180], S[0,50], V[120,255]
       - 平均亮度阈值：> 180
       - 高亮区域占比：> 5%
       
    2. 圆形度检查：验证高亮区域是否为圆形
       - 圆形度计算：4π*area/perimeter²
       - 圆形度阈值：> 0.6
       - 圆形面积比例：> 0.7（轮廓面积与最小外接圆面积之比）
    
    识别结果保存：
    - 保存路径：script_dir/rec/
    - 文件命名格式：{function_name}_{method_name}_{timestamp}.png
    - 时间戳格式：YYYYMMDD_HHMMSS_mmm（毫秒级）
    - 日志输出：识别区域坐标范围、保存路径
    
    :param image_name: 模板图片名称（不包含路径）
    :param description: 图片描述（用于日志输出，如"停止按钮"）
    :param template_path: 图片路径，如果不提供则使用默认路径（script_dir + image_name）
    :param confidence: 匹配置信度阈值，默认0.8，可根据场景调整
    :param time_sleep: 操作前等待时间（秒），默认0秒，可用于等待界面加载
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，表示左上角和右下角坐标，默认为None（全屏）
    :param save_screenshot: 是否保存识别结果截图，默认False
    :param debug: 是否输出详细调试信息，默认False
    :return: 如果找到图片且通过亮度和形状验证则返回 (True, center_x, center_y, match_region)，否则返回 (False, None, None, None)
    
    使用示例：
        is_complex_temp("stop_button.png", description="停止按钮", confidence=0.8)
        is_complex_temp("stop_button.png", description="停止按钮", confidence=0.8, region=(100, 100, 500, 500))
    """
    if time_sleep > 0:
        time.sleep(time_sleep)
    if not template_path:
        template_path = os.path.join(script_dir, image_name)
    
    if not os.path.exists(template_path):
        print(f"[{time.strftime('%H:%M:%S')}] 图片不存在: {template_path}")
        return False, None, None, None
    
    try:
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        from src.modules.vision.screen_capture import ScreenCapture
        sc = ScreenCapture()
        client_rect = sc.get_game_client_rect()
        if client_rect is not None:
            screenshot_np = sc.capture_game_client_area()
            offset_x, offset_y = client_rect[0], client_rect[1]
        else:
            screenshot_np = sc.capture()
            offset_x, offset_y = 0, 0
        
        if region is not None:
            x1, y1, x2, y2 = region
            screenshot_np = screenshot_np[y1:y2, x1:x2]
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 使用指定识别区域: ({x1}, {y1}) - ({x2}, {y2})")
        
        match_methods = {
            'TM_CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'TM_CCORR_NORMED': cv2.TM_CCORR_NORMED,
            'TM_SQDIFF_NORMED': cv2.TM_SQDIFF_NORMED
        }
        
        def match_with_edge_detection():
            template_edges = cv2.Canny(template, 50, 200)
            screenshot_edges = cv2.Canny(screenshot_np, 50, 200)
            result = cv2.matchTemplate(screenshot_edges, template_edges, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            return max_val >= confidence
        
        def match_with_contours():
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            template_blur = cv2.GaussianBlur(template_gray, (5, 5), 0)
            template_thresh = cv2.adaptiveThreshold(template_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            template_contours, _ = cv2.findContours(template_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not template_contours:
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 模板图片无法提取轮廓")
                return False
            
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
            screenshot_blur = cv2.GaussianBlur(screenshot_gray, (5, 5), 0)
            screenshot_thresh = cv2.adaptiveThreshold(screenshot_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            screenshot_contours, _ = cv2.findContours(screenshot_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            template_contour = max(template_contours, key=cv2.contourArea)
            template_area = cv2.contourArea(template_contour)
            template_perimeter = cv2.arcLength(template_contour, True)
            template_circularity = 4 * np.pi * template_area / (template_perimeter ** 2) if template_perimeter > 0 else 0
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 模板轮廓面积: {template_area:.2f}, 圆形度: {template_circularity:.2f}")
            
            for contour in screenshot_contours:
                contour_area = cv2.contourArea(contour)
                if not (0.7 * template_area <= contour_area <= 1.3 * template_area):
                    continue
                contour_perimeter = cv2.arcLength(contour, True)
                if contour_perimeter == 0:
                    continue
                contour_circularity = 4 * np.pi * contour_area / (contour_perimeter ** 2)
                if contour_circularity < 0.6:
                    continue
                similarity = cv2.matchShapes(template_contour, contour, cv2.CONTOURS_MATCH_I2, 0.0)
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 轮廓相似度: {similarity:.4f}, 模板面积: {template_area:.2f}, 匹配面积: {contour_area:.2f}, 匹配圆形度: {contour_circularity:.2f}")
                if similarity < 0.03:
                    return True
            return False
        
        def ensure_save_directory():
            save_dir = os.path.join(script_dir, "rec")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            return save_dir
        
        def save_recognition_result(function_name, method_name, image_name, location, region, save_screenshot):
            if not save_screenshot:
                return
            try:
                save_dir = ensure_save_directory()
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                file_name = f"{function_name}_{method_name}_{current_time}.png"
                file_path = os.path.join(save_dir, file_name)
                cv2.imwrite(file_path, cv2.cvtColor(region, cv2.COLOR_RGB2BGR))
                h, w = region.shape[:2]
                x, y = location
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 识别区域坐标范围: ({x}, {y}) - ({x+w}, {y+h})")
                    print(f"[{time.strftime('%H:%M:%S')}] 识别结果已保存至: {file_path}")
            except Exception as e:
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 保存识别结果失败: {e}")
        
        def check_brightness(region):
            hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            lower_white = np.array([0, 0, 120])
            upper_white = np.array([180, 50, 255])
            mask = cv2.inRange(hsv, lower_white, upper_white)
            if cv2.countNonZero(mask) == 0:
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 检测区域没有高亮白色部分")
                return False, None
            white_pixels = hsv[:,:,2][mask > 0]
            brightness = white_pixels.mean()
            white_area_ratio = cv2.countNonZero(mask) / (region.shape[0] * region.shape[1])
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 高亮区域平均亮度: {brightness:.2f}, 占比: {white_area_ratio:.2f}")
            is_bright = brightness > 180 and white_area_ratio > 0.05
            return is_bright, mask if is_bright else None
        
        def check_circle_shape(region, mask):
            if mask is None:
                return False
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 高亮区域无法提取轮廓")
                return False
            max_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(max_contour)
            perimeter = cv2.arcLength(max_contour, True)
            if perimeter == 0:
                return False
            circularity = 4 * np.pi * area / (perimeter ** 2)
            (x, y), radius = cv2.minEnclosingCircle(max_contour)
            circle_area = np.pi * (radius ** 2)
            circle_ratio = area / circle_area if circle_area > 0 else 0
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 高亮区域圆形度: {circularity:.2f}, 圆形面积比例: {circle_ratio:.2f}")
            return circularity > 0.6 and circle_ratio > 0.7
        
        if debug:
            print(f"[{time.strftime('%H:%M:%S')}] 开始使用边缘检测匹配{image_name}图片...")
        if match_with_edge_detection():
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(cv2.Canny(screenshot_np, 50, 200), cv2.Canny(template, 50, 200), cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 边缘检测匹配度: {max_val:.4f}, 匹配位置: {max_loc}")
            if max_val >= confidence:
                h, w = template.shape[:2]
                match_region = screenshot_np[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
                is_bright, mask = check_brightness(match_region)
                is_circle = check_circle_shape(match_region, mask) if is_bright else False
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 边缘检测 - 亮度检查: {is_bright}, 圆形检查: {is_circle}")
                if is_bright and is_circle:
                    image_desc = f"{description} " if description else ""
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] 使用边缘检测成功识别到{image_desc}{image_name}图片（亮度和形状符合要求）")
                    actual_loc = (max_loc[0] + region[0], max_loc[1] + region[1]) if region is not None else max_loc
                    center_x = actual_loc[0] + w // 2 + offset_x
                    center_y = actual_loc[1] + h // 2 + offset_y
                    save_recognition_result("is_complex_temp", "edge_detection", image_name, actual_loc, match_region, save_screenshot)
                    return True, center_x, center_y, match_region
            else:
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 边缘检测匹配度不足，阈值: {confidence:.2f}")
        else:
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 边缘检测未找到匹配")
        
        if debug:
            print(f"[{time.strftime('%H:%M:%S')}] 开始使用轮廓匹配{image_name}图片...")
        if match_with_contours():
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= confidence)
            match_count = len(list(zip(*locations[::-1])))
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 轮廓匹配找到 {match_count} 个可能的匹配位置")
            for pt in zip(*locations[::-1]):
                h, w = template.shape[:2]
                match_region = screenshot_np[pt[1]:pt[1]+h, pt[0]:pt[0]+w]
                is_bright, mask = check_brightness(match_region)
                is_circle = check_circle_shape(match_region, mask) if is_bright else False
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] 轮廓匹配 - 位置 {pt} - 亮度检查: {is_bright}, 圆形检查: {is_circle}")
                if is_bright and is_circle:
                    image_desc = f"{description} " if description else ""
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] 使用轮廓匹配成功识别到{image_desc}{image_name}图片（亮度和形状符合要求）")
                    center_x = pt[0] + w // 2 + offset_x
                    center_y = pt[1] + h // 2 + offset_y
                    save_recognition_result("is_complex_temp", "contour_matching", image_name, pt, match_region, save_screenshot)
                    return True, center_x, center_y, match_region
        else:
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 轮廓匹配未找到匹配")
        
        if debug:
            print(f"[{time.strftime('%H:%M:%S')}] 开始使用模板匹配方法查找{image_name}图片...")
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
        for method_name, method in match_methods.items():
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 尝试 {method_name} 方法...")
            result = cv2.matchTemplate(screenshot_gray, template_gray, method)
            if method == cv2.TM_SQDIFF_NORMED:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] {method_name} - 最小匹配度: {min_val:.4f}, 匹配位置: {min_loc}")
                if min_val <= (1 - confidence):
                    h, w = template.shape[:2]
                    match_region = screenshot_np[min_loc[1]:min_loc[1]+h, min_loc[0]:min_loc[0]+w]
                    is_bright, mask = check_brightness(match_region)
                    is_circle = check_circle_shape(match_region, mask) if is_bright else False
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] {method_name} - 亮度检查: {is_bright}, 圆形检查: {is_circle}")
                    if is_bright and is_circle:
                        image_desc = f"{description} " if description else ""
                        if debug:
                            print(f"[{time.strftime('%H:%M:%S')}] 使用{method_name}方法成功识别到{image_desc}{image_name}图片（亮度和形状符合要求）")
                        center_x = min_loc[0] + w // 2 + offset_x
                        center_y = min_loc[1] + h // 2 + offset_y
                        save_recognition_result("is_complex_temp", f"template_match_{method_name}", image_name, min_loc, match_region, save_screenshot)
                        return True, center_x, center_y, match_region
                else:
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] {method_name} 匹配度不足，阈值: {(1 - confidence):.2f}")
            else:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if debug:
                    print(f"[{time.strftime('%H:%M:%S')}] {method_name} - 最大匹配度: {max_val:.4f}, 匹配位置: {max_loc}")
                if max_val >= confidence:
                    h, w = template.shape[:2]
                    match_region = screenshot_np[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
                    is_bright, mask = check_brightness(match_region)
                    is_circle = check_circle_shape(match_region, mask) if is_bright else False
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] {method_name} - 亮度检查: {is_bright}, 圆形检查: {is_circle}")
                    if is_bright and is_circle:
                        image_desc = f"{description} " if description else ""
                        if debug:
                            print(f"[{time.strftime('%H:%M:%S')}] 使用{method_name}方法成功识别到{image_desc}{image_name}图片（亮度和形状符合要求）")
                        actual_max_loc = (max_loc[0] + region[0], max_loc[1] + region[1]) if region is not None else max_loc
                        center_x = actual_max_loc[0] + w // 2 + offset_x
                        center_y = actual_max_loc[1] + h // 2 + offset_y
                        save_recognition_result("is_complex_temp", f"template_match_{method_name}", image_name, actual_max_loc, match_region, save_screenshot)
                        return True, center_x, center_y, match_region
                else:
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] {method_name} 匹配度不足，阈值: {confidence:.2f}")
        
        if debug:
            print(f"[{time.strftime('%H:%M:%S')}] 所有检测方法均未找到{image_name}图片（亮度和形状均符合要求的匹配）")
        return False, None, None, None
    except Exception as e:
        if debug:
            print(f"[{time.strftime('%H:%M:%S')}] 执行错误: {e}")
        return False, None, None, None

def click_complex_temp(image_name, description=None, template_path=None, confidence=0.8, time_sleep=0, region=None, save_screenshot=False, debug=False):
    """
    在屏幕上查找并点击指定的模板图片，使用复杂的识别方法（边缘检测、轮廓匹配、亮度检查等）
    :param image_name: 模板图片名称（不包含路径）
    :param description: 图片描述（用于日志输出，如"停止按钮"）
    :param template_path: 图片路径，如果不提供则使用默认路径（script_dir + image_name）
    :param confidence: 匹配置信度阈值，默认0.8，可根据场景调整
    :param time_sleep: 操作前等待时间（秒），默认0秒，可用于等待界面加载
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，表示左上角和右下角坐标，默认为None（全屏）
    :param save_screenshot: 是否保存识别结果截图，默认False
    :param debug: 是否输出详细调试信息，默认False
    :return: 如果找到并点击则返回True，否则返回False
    """
    found, center_x, center_y, match_region = is_complex_temp(image_name, description, template_path, confidence, time_sleep, region, save_screenshot, debug)
    
    if found:
        try:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.05
            
            click_at_position(center_x, center_y)
            
            image_desc = f"{description} " if description else ""
            print(f"[{time.strftime('%H:%M:%S')}] 成功点击{image_desc}{image_name}图片，坐标: ({center_x}, {center_y})")
            
            if save_screenshot:
                try:
                    save_dir = os.path.join(script_dir, "rec")
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir)
                    
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    file_name = f"click_complex_temp_{image_name}_{current_time}.png"
                    file_path = os.path.join(save_dir, file_name)
                    
                    cv2.imwrite(file_path, cv2.cvtColor(match_region, cv2.COLOR_RGB2BGR))
                    
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] 点击识别结果已保存至: {file_path}")
                except Exception as e:
                    if debug:
                        print(f"[{time.strftime('%H:%M:%S')}] 保存点击识别结果失败: {e}")
            
            return True
        except Exception as e:
            if debug:
                print(f"[{time.strftime('%H:%M:%S')}] 执行错误: {e}")
            return False
    else:
        return False

def move_mouse_to_position(x, y):
    """
    使用Windows API将鼠标移动到屏幕指定位置
    :param x: 目标X坐标
    :param y: 目标Y坐标
    :return: 如果成功返回True，否则返回False
    """
    try:
        # 获取Windows API函数并设置参数类型
        user32 = ctypes.windll.user32
        
        # 初始化dwExtraInfo
        extra_info = ctypes.c_ulong(0)
        extra_info_ptr = ctypes.pointer(extra_info)
        
        # 计算绝对坐标（SendInput需要0-65535范围内的坐标）
        screen_width, screen_height = pyautogui.size()
        absolute_x = int(x * 65535 / screen_width)
        absolute_y = int(y * 65535 / screen_height)
        
        # 定义鼠标移动事件
        mouse_event = INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(
                dx=absolute_x,
                dy=absolute_y,
                mouseData=0,
                dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                time=0,
                dwExtraInfo=extra_info_ptr
            )
        )
        
        # 发送鼠标移动事件
        input_array = (INPUT * 1)(mouse_event)
        result = user32.SendInput(1, ctypes.byref(input_array), ctypes.sizeof(INPUT))
        
        if result > 0:
            print(f"[{time.strftime('%H:%M:%S')}] 已将鼠标移动到位置: ({x}, {y})")
            return True
        else:
            # 尝试使用SetCursorPos作为备选方案
            user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            user32.SetCursorPos.restype = ctypes.c_bool
            
            if user32.SetCursorPos(x, y):
                print(f"[{time.strftime('%H:%M:%S')}] 已将鼠标移动到位置 (备选方案): ({x}, {y})")
                return True
            else:
                return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 鼠标移动失败: {e}")
        return False


def move_mouse_to_center():
    """
    将鼠标移动到屏幕中间位置
    :return: 如果成功返回True，否则返回False
    """
    time.sleep(1)  # 操作前等待1秒
    try:
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 计算屏幕中心坐标
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # 调用move_mouse_to_position函数移动到中心位置
        return move_mouse_to_position(center_x, center_y)
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 鼠标移动到屏幕中心失败: {e}")
        return False

def click_center():
    move_mouse_to_center()
    click_current_position()

def click_at_position(x, y):
    """
    使用Windows API在指定位置点击鼠标
    :param x: 点击的X坐标
    :param y: 点击的Y坐标
    :return: 如果成功返回True，否则返回False
    """
    try:
        # 获取Windows API函数并设置参数类型
        user32 = ctypes.windll.user32
        
        # 初始化dwExtraInfo
        extra_info = ctypes.c_ulong(0)
        extra_info_ptr = ctypes.pointer(extra_info)
        
        # 计算绝对坐标（SendInput需要0-65535范围内的坐标）
        screen_width, screen_height = pyautogui.size()
        absolute_x = int(x * 65535 / screen_width)
        absolute_y = int(y * 65535 / screen_height)
        
        # 定义鼠标输入事件数组
        # 包含：移动到位置 -> 左键按下 -> 左键释放
        mouse_events = [
            # 移动到目标位置
            INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(
                    dx=absolute_x,
                    dy=absolute_y,
                    mouseData=0,
                    dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                    time=0,
                    dwExtraInfo=extra_info_ptr
                )
            ),
            # 左键按下
            INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=MOUSEEVENTF_LEFTDOWN,
                    time=0,
                    dwExtraInfo=extra_info_ptr
                )
            ),
            # 左键释放
            INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=MOUSEEVENTF_LEFTUP,
                    time=0,
                    dwExtraInfo=extra_info_ptr
                )
            )
        ]
        
        # 发送鼠标事件
        input_array = (INPUT * len(mouse_events))(*mouse_events)
        result = user32.SendInput(len(input_array), ctypes.byref(input_array), ctypes.sizeof(INPUT))
        
        if result > 0:
            print(f"[{time.strftime('%H:%M:%S')}] 已执行点击操作: ({x}, {y})")
            return True
        else:
            # 尝试使用SetCursorPos作为备选方案
            user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            user32.SetCursorPos.restype = ctypes.c_bool
            
            if user32.SetCursorPos(x, y):
                # 发送点击事件
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                print(f"[{time.strftime('%H:%M:%S')}] 已执行点击操作 (备选方案): ({x}, {y})")
                return True
            else:
                return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 点击失败: {e}")
        return False


def mouse_scroll(scroll_amount):
    """
    使用Windows API执行鼠标滚轮滚动
    :param scroll_amount: 滚动量，正值表示向上滚动，负值表示向下滚动
    :return: 如果成功返回True，否则返回False
    """
    try:
        # 获取Windows API函数并设置参数类型
        user32 = ctypes.windll.user32
        
        # 初始化dwExtraInfo
        extra_info = ctypes.c_ulong(0)
        extra_info_ptr = ctypes.pointer(extra_info)
        
        # 定义鼠标滚轮输入事件
        wheel_event = INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=scroll_amount,  # 滚动量
                dwFlags=MOUSEEVENTF_WHEEL,  # 垂直滚轮
                time=0,
                dwExtraInfo=extra_info_ptr
            )
        )
        
        # 发送鼠标事件
        input_array = (INPUT * 1)(wheel_event)
        result = user32.SendInput(1, ctypes.byref(input_array), ctypes.sizeof(INPUT))
        
        if result > 0:
            if scroll_amount > 0:
                print(f"[{time.strftime('%H:%M:%S')}] 已向上滚动鼠标滚轮: {scroll_amount} 单位")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 已向下滚动鼠标滚轮: {abs(scroll_amount)} 单位")
            return True
        else:
            # 尝试使用mouse_event作为备选方案
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, scroll_amount, 0)
            if scroll_amount > 0:
                print(f"[{time.strftime('%H:%M:%S')}] 已向上滚动鼠标滚轮 (备选方案): {scroll_amount} 单位")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 已向下滚动鼠标滚轮 (备选方案): {abs(scroll_amount)} 单位")
            return True
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 鼠标滚动失败: {e}")
        return False


def mouse_scroll_up(scroll_amount=120):
    """
    鼠标向上滚动
    :param scroll_amount: 滚动量（默认120单位）
    :return: 如果成功返回True，否则返回False
    """
    time.sleep(0.3)  # 操作前等待0.3秒
    return mouse_scroll(scroll_amount)


def mouse_scroll_down(scroll_amount=120):
    """
    鼠标向下滚动
    :param scroll_amount: 滚动量（默认120单位）
    :return: 如果成功返回True，否则返回False
    """
    time.sleep(0.3)  # 操作前等待0.3秒
    return mouse_scroll(-scroll_amount)

def click_phone(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击phone.png图片，只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("phone.png", template_path=template_path, confidence=confidence)

def click_chuji(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuji.png图片，只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuji.png", template_path=template_path, confidence=confidence)

def keyboard_press_release_template(key, description=None, delay=0.1):
    """
    短按并松开指定按键（连贯的操作）
    :param key: 要按下的按键
    :param description: 按键描述（用于日志）
    :param delay: 按键按下后的延迟时间（秒）
    :return: 如果成功返回True，否则返回False
    """
    time.sleep(1)  # 操作前等待1秒
    try:
        # 禁用pyautogui的安全设置
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05
        
        # 按下并松开按键
        key_desc = f"{description} " if description else f"{key} "
        print(f"[{time.strftime('%H:%M:%S')}] 正在短按{key_desc}键...")
        pyautogui.press(key)
        print(f"[{time.strftime('%H:%M:%S')}] 已短按{key_desc}键")
        return True
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 短按{key}键失败: {e}")
        return False


def keyboard_hold_release_template(key, description=None, hold_time=1.0):
    """
    长按并松开指定按键
    :param key: 要长按的按键
    :param description: 按键描述（用于日志）
    :param hold_time: 按键长按的时间（秒）
    :return: 如果成功返回True，否则返回False
    """
    time.sleep(1)  # 操作前等待1秒
    try:
        # 禁用pyautogui的安全设置
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05
        
        # 长按并松开按键
        key_desc = f"{description} " if description else f"{key} "
        print(f"[{time.strftime('%H:%M:%S')}] 正在长按{key_desc}键{hold_time}秒...")
        pyautogui.keyDown(key)
        time.sleep(hold_time)
        pyautogui.keyUp(key)
        print(f"[{time.strftime('%H:%M:%S')}] 已长按{key_desc}键{hold_time}秒")
        return True
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 长按{key}键失败: {e}")
        return False


def keyboard_rapid_press_template(key, description=None, press_count=5, interval=0.1):
    """
    快速连按指定按键多次
    :param key: 要连按的按键
    :param description: 按键描述（用于日志）
    :param press_count: 连按的次数
    :param interval: 每次按键之间的间隔时间（秒）
    :return: 如果成功返回True，否则返回False
    """
    time.sleep(1)  # 操作前等待1秒
    try:
        # 禁用pyautogui的安全设置
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05
        
        # 快速连按按键
        key_desc = f"{description} " if description else f"{key} "
        print(f"[{time.strftime('%H:%M:%S')}] 正在快速连按{key_desc}键{press_count}次...")
        for _ in range(press_count):
            pyautogui.press(key)
            time.sleep(interval)
        print(f"[{time.strftime('%H:%M:%S')}] 已快速连按{key_desc}键{press_count}次")
        return True
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 快速连按{key}键失败: {e}")
        return False


# 短按松开函数
def keyboard_w_press_release():
    """短按并松开W键"""
    return keyboard_press_release_template('w', '前进')

def keyboard_a_press_release():
    """短按并松开A键"""
    return keyboard_press_release_template('a', '左移')

def keyboard_s_press_release():
    """短按并松开S键"""
    return keyboard_press_release_template('s', '后退')

def keyboard_d_press_release():
    """短按并松开D键"""
    return keyboard_press_release_template('d', '右移')

def keyboard_j_press_release():
    """短按并松开J键"""
    return keyboard_press_release_template('j','普攻')

def keyboard_k_press_release():
    """短按并松开K键"""
    return keyboard_press_release_template('k','闪避')

def keyboard_u_press_release():
    """短按并松开U键"""
    return keyboard_press_release_template('u','武器技/重置')

def keyboard_i_press_release():
    """短按并松开I键"""
    return keyboard_press_release_template('i','大招/选择')

def keyboard_1_press_release():
    """短按并松开1键"""
    return keyboard_press_release_template('1','角色1/选择1')

def keyboard_2_press_release():
    """短按并松开2键"""
    return keyboard_press_release_template('2','角色2/选择2')

def keyboard_3_press_release():
    """短按并松开3键"""
    return keyboard_press_release_template('3','选择3')

def keyboard_q_press_release():
    """短按并松开Q键"""
    return keyboard_press_release_template('q','视角左转')

def keyboard_e_press_release():
    """短按并松开E键"""
    return keyboard_press_release_template('e','视角右转')

def keyboard_space_press_release():
    """短按并松开空格键"""
    return keyboard_press_release_template('space', '空格')

def keyboard_r_press_release():
    """短按并松开R键"""
    return keyboard_press_release_template('r','交互')

def keyboard_f_press_release():
    """短按并松开F键"""
    return keyboard_press_release_template('f')


# 长按松开函数
def keyboard_w_hold_release(hold_time=1.0):
    """长按并松开W键"""
    return keyboard_hold_release_template('w', '前进', hold_time)

def keyboard_a_hold_release(hold_time=1.0):
    """长按并松开A键"""
    return keyboard_hold_release_template('a', '左移', hold_time)

def keyboard_s_hold_release(hold_time=1.0):
    """长按并松开S键"""
    return keyboard_hold_release_template('s', '后退', hold_time)

def keyboard_d_hold_release(hold_time=1.0):
    """长按并松开D键"""
    return keyboard_hold_release_template('d', '右移', hold_time)

def keyboard_j_hold_release(hold_time=1.0):
    """长按并松开J键"""
    return keyboard_hold_release_template('j', '长按普攻', hold_time)

def keyboard_k_hold_release(hold_time=1.0):
    """长按并松开K键"""
    return keyboard_hold_release_template('k', None, hold_time)

def keyboard_u_hold_release(hold_time=1.0):
    """长按并松开U键"""
    return keyboard_hold_release_template('u', None, hold_time)

def keyboard_i_hold_release(hold_time=1.0):
    """长按并松开I键"""
    return keyboard_hold_release_template('i', '长按大招', hold_time)

def keyboard_1_hold_release(hold_time=1.0):
    """长按并松开1键"""
    return keyboard_hold_release_template('1', None, hold_time)

def keyboard_2_hold_release(hold_time=1.0):
    """长按并松开2键"""
    return keyboard_hold_release_template('2', None, hold_time)

def keyboard_3_hold_release(hold_time=1.0):
    """长按并松开3键"""
    return keyboard_hold_release_template('3', None, hold_time)

def keyboard_q_hold_release(hold_time=1.0):
    """长按并松开Q键"""
    return keyboard_hold_release_template('q', '视角左转', hold_time)

def keyboard_e_hold_release(hold_time=1.0):
    """长按并松开E键"""
    return keyboard_hold_release_template('e', '视角右转', hold_time)

def keyboard_space_hold_release(hold_time=1.0):
    """长按并松开空格键"""
    return keyboard_hold_release_template('space', '空格', hold_time)

def keyboard_r_hold_release(hold_time=1.0):
    """长按并松开R键"""
    return keyboard_hold_release_template('r', None, hold_time)

def keyboard_f_hold_release(hold_time=1.0):
    """长按并松开F键"""
    return keyboard_hold_release_template('f', None, hold_time)


# 快速连按函数
def keyboard_w_rapid_press(press_count=5, interval=0.1):
    """快速连按W键"""
    return keyboard_rapid_press_template('w', '前进', press_count, interval)

def keyboard_a_rapid_press(press_count=5, interval=0.1):
    """快速连按A键"""
    return keyboard_rapid_press_template('a', '左移', press_count, interval)

def keyboard_s_rapid_press(press_count=5, interval=0.1):
    """快速连按S键"""
    return keyboard_rapid_press_template('s', '后退', press_count, interval)

def keyboard_d_rapid_press(press_count=5, interval=0.1):
    """快速连按D键"""
    return keyboard_rapid_press_template('d', '右移', press_count, interval)

def keyboard_j_rapid_press(press_count=5, interval=0.1):
    """快速连按J键"""
    return keyboard_rapid_press_template('j', '连续普攻', press_count, interval)

def keyboard_k_rapid_press(press_count=5, interval=0.1):
    """快速连按K键"""
    return keyboard_rapid_press_template('k', '连续闪避', press_count, interval)

def keyboard_u_rapid_press(press_count=5, interval=0.1):
    """快速连按U键"""
    return keyboard_rapid_press_template('u', '连续武器技', press_count, interval)

def keyboard_i_rapid_press(press_count=5, interval=0.1):
    """快速连按I键"""
    return keyboard_rapid_press_template('i', '连续大招', press_count, interval)

def keyboard_1_rapid_press(press_count=5, interval=0.1):
    """快速连按1键"""
    return keyboard_rapid_press_template('1', None, press_count, interval)

def keyboard_2_rapid_press(press_count=5, interval=0.1):
    """快速连按2键"""
    return keyboard_rapid_press_template('2', None, press_count, interval)

def keyboard_3_rapid_press(press_count=5, interval=0.1):
    """快速连按3键"""
    return keyboard_rapid_press_template('3', None, press_count, interval)

def keyboard_q_rapid_press(press_count=5, interval=0.1):
    """快速连按Q键"""
    return keyboard_rapid_press_template('q', None, press_count, interval)

def keyboard_e_rapid_press(press_count=5, interval=0.1):
    """快速连按E键"""
    return keyboard_rapid_press_template('e', None, press_count, interval)

def keyboard_space_rapid_press(press_count=5, interval=0.1):
    """快速连按空格键"""
    return keyboard_rapid_press_template('space', '空格', press_count, interval)

def keyboard_r_rapid_press(press_count=5, interval=0.1):
    """快速连按R键"""
    return keyboard_rapid_press_template('r', None, press_count, interval)

def keyboard_f_rapid_press(press_count=5, interval=0.1):
    """快速连按F键"""
    return keyboard_rapid_press_template('f', None, press_count, interval)


# 优化现有的keyboard_esc函数
def keyboard_esc_press_release():
    """
    模拟按下并松开ESC键
    :return: 如果成功返回True，否则返回False
    """
    return keyboard_press_release_template('esc', '退出')

def click_cailiaoyuanzheng(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击cailiaoyuanzheng.png图片，只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("cailiaoyuanzheng.png", template_path=template_path, confidence=confidence)

def click_chuji_chuji(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuji_chuji.png图片（出击），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuji_chuji.png", "出击", template_path=template_path, confidence=confidence)

def click_chuji_huodong(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuji_huodong.png图片（活动），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuji_huodong.png", "活动", template_path=template_path, confidence=confidence)

def click_chuji_tiaozhan(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuji_tiaozhan.png图片（挑战），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuji_tiaozhan.png", "挑战", template_path=template_path, confidence=confidence)

def click_chuji_tuijian(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuji_tuijian.png图片（推荐），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuji_tuijian.png", "推荐", template_path=template_path, confidence=confidence)

def is_tuijian(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_tuijian.png图片（推荐），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_tuijian.png", "推荐", template_path=template_path, confidence=confidence)

def click_jianfu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jianfu.png图片（一键减负），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jianfu.png", "一键减负", template_path=template_path, confidence=confidence)

def click_jianfu_jianfu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jianfu_jianfu.png图片（减负），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jianfu_jianfu.png", "减负", template_path=template_path, confidence=confidence)

def click_meiri(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击meiri.png图片（领取），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("meiri.png", "领取", template_path=template_path, confidence=confidence)

def click_jiantuan(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiantuan.png图片（舰团），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiantuan.png", "舰团", template_path=template_path, confidence=confidence)

def click_jiantuanjiangchi(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiantuanjiangchi.png图片（舰团奖池），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiantuanjiangchi.png", "舰团奖池", template_path=template_path, confidence=confidence)

def click_jiantuanjiangchi_lingqv(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiantuanjiangchi_lingqv.png图片（领取），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiantuanjiangchi_lingqv.png", "领取", template_path=template_path, confidence=confidence)

def click_weituohuishou(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击weituohuishou.png图片（委托回收），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("weituohuishou.png", "委托回收", template_path=template_path, confidence=confidence)

def click_xinweituo_jieshou(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击xinweituo_jieshou.png图片（接受），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("xinweituo_jieshou.png", "接受", template_path=template_path, confidence=confidence)

def click_dagong_lingqv(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击dagong_lingqv.png图片（领取奖励），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("dagong_lingqv.png", "领取奖励", template_path=template_path, confidence=confidence)

def click_dagong(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击dagong.png图片（打工），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("dagong.png", "打工", template_path=template_path, confidence=confidence)

def click_huishouweituo(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击huishouweituo.png图片（回收委托），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("huishouweituo.png", "回收委托", template_path=template_path, confidence=confidence)

def click_xinweituo_tijiao(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击xinweituo_tijiao.png图片（提交新委托），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("xinweituo_tijiao.png", "提交新委托", template_path=template_path, confidence=confidence)

def click_xinweituo_tijiaoweituo(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击xinweituo_tijiaoweituo.png图片（提交委托），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("xinweituo_tijiaoweituo.png", "提交委托", template_path=template_path, confidence=confidence)

def click_xinweituo(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击xinweituo.png图片（新委托），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("xinweituo.png", "新委托", template_path=template_path, confidence=confidence)

def click_yijiandagong(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yijiandagong.png图片（一键打工），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yijiandagong.png", "一键打工", template_path=template_path, confidence=confidence)

def click_yijiandagong_yijiandagong(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yijiandagong_yijiandagong.png图片（一键打工），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yijiandagong_yijiandagong.png", "一键打工", template_path=template_path, confidence=confidence)

def click_yuanzheng_paiqian(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yuanzheng_paiqian.png图片（远征派遣），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yuanzheng_paiqian.png", "远征派遣", template_path=template_path, confidence=confidence)

def click_yuanzheng(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yuanzheng.png图片（远征），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yuanzheng.png", "远征", template_path=template_path, confidence=confidence)

def click_yuanzheng_wancheng(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yuanzheng_wancheng.png图片（完成远征），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yuanzheng_wancheng.png", "完成远征", template_path=template_path, confidence=confidence)

def click_yuanzheng_yijian(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yuanzheng_yijian.png图片（一键远征），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yuanzheng_yijian.png", "一键远征", template_path=template_path, confidence=confidence)

def click_jiayuan(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiayuan.png图片（家园），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiayuan.png", "家园", template_path=template_path, confidence=confidence)

def click_qvchutili(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击qvchutili.png图片（取出体力），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("qvchutili.png", "取出体力", template_path=template_path, confidence=confidence)


def click_jiantuangongxian(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiantuangongxian.png图片（舰团贡献），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiantuangongxian.png", "舰团贡献", template_path=template_path, confidence=confidence)

def click_jiantuangongxian_5000(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiantuangongxian_5000.png图片（舰团贡献5000），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiantuangongxian_5000.png", "舰团贡献5000", template_path=template_path, confidence=confidence)

def click_renwu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击renwu.png图片（任务），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("renwu.png", "任务", template_path=template_path, confidence=confidence)

def click_yijianlingqv(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yijianlingqv.png图片（一键领取），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yijianlingqv.png", "一键领取", template_path=template_path, confidence=confidence)

def click_meirijiangli(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击meirijiangli.png图片（每日奖励），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("meirijiangli.png", "每日奖励", template_path=template_path, confidence=confidence)

def click_jiyizhanchang(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiyizhanchang.png图片（一键远征），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiyizhanchang.png", "记忆战场", template_path=template_path, confidence=confidence)

def click_chaoxiankongjian(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chaoxiankongjian.png图片（超弦空间），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chaoxiankongjian.png", "超弦空间", template_path=template_path, confidence=confidence)

def click_kongjian_zhandou(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击kongjian_zhandou.png图片（空间_战斗），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("kongjian_zhandou.png", "空间_战斗", template_path=template_path, confidence=confidence)

def click_zhandouzhunbei(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zhandouzhunbei.png图片（战斗_准备），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zhandouzhunbei.png", "战斗_准备", template_path=template_path, confidence=confidence)

def click_shenzhijian(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击shenzhijian.png图片（神之键），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("shenzhijian.png", "神之键", template_path=template_path, confidence=confidence)

def click_zuozhanrenwu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zuozhanrenwu.png图片（作战任务），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zuozhanrenwu.png", "作战任务", template_path=template_path, confidence=confidence)

def click_kaifangshijie(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击kaifangshijie.png图片（开放世界），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("kaifangshijie.png", "开放世界", template_path=template_path, confidence=confidence)

def click_renwu_jianfu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击renwu_jianfu.png图片（任务_减负），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("renwu_jianfu.png", "任务_减负", template_path=template_path, confidence=confidence)

def click_ditu_xuanze1(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击ditu_xuanze.png图片（地图_选择），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("ditu_xuanze1.png", "地图_选择", template_path=template_path, confidence=confidence)

def click_ditu_xuanze2(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击ditu_xuanze2.png图片（地图_选择），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("ditu_xuanze2.png", "地图_选择", template_path=template_path, confidence=confidence)

def click_letu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击letu.png图片（往世乐土），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("letu.png", "往世乐土", template_path=template_path, confidence=confidence)

def click_shencengxvlie(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击shencengxvlie.png图片（深层序列），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("shencengxvlie.png", "深层序列", template_path=template_path, confidence=confidence)

def click_chuzhanwei(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuzhanwei.png图片（出战位），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuzhanwei.png", "出战位", template_path=template_path, confidence=confidence)

def click_tianyanzhibei(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击tianyanzhibei.png图片（天衍之杯），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("tianyanzhibei.png", "天衍之杯", template_path=template_path, confidence=confidence)

def click_ailixiya(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击ailixiya.png图片（爱莉希雅），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("ailixiya.png", "爱莉希雅", template_path=template_path, confidence=confidence)

def click_shaixuan(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击shaixuan.png图片（筛选），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("shaixuan.png", "筛选", template_path=template_path, confidence=confidence)

def click_charactor_ensure(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击charactor_ensure.png图片（确认），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("charactor_ensure.png", "确认", template_path=template_path, confidence=confidence)

def click_zhiyuanwei(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zhiyuanwei.png图片（支援位），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zhiyuanwei.png", "支援位", template_path=template_path, confidence=confidence)

def click_zhanche(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zhanche.png图片（战车），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zhanche.png", "战车", template_path=template_path, confidence=confidence)

def click_yunmodanxin(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击yunmodanxin.png图片（云墨丹心），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("yunmodanxin.png", "云墨丹心", template_path=template_path, confidence=confidence)

def click_letuxuanze(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击letuxuanze.png图片（乐土选择），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("letuxuanze.png", "乐土选择", template_path=template_path, confidence=confidence)

def click_michenghaitu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击michenghaitu.png图片（迷城骇兔），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("michenghaitu.png", "迷城骇兔", template_path=template_path, confidence=confidence)

def click_letu_kaishizhandou(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击letu_kaishizhandou.png图片（乐土开始战斗），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("letu_kaishizhandou.png", "乐土开始战斗", template_path=template_path, confidence=confidence)

def click_elysia_star_jiaxin(template_path=None, confidence=0.9):
    """
    在屏幕上查找并点击elysia_star_jiaxin.png图片（爱莉希雅_星环_佳信），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("elysia_star_jiaxin.png", "爱莉希雅_星环_佳信", template_path=template_path, confidence=confidence)

def click_elysia_star_fangting(template_path=None, confidence=0.9):
    """
    在屏幕上查找并点击elysia_star_fangting.png图片（爱莉希雅_星环_芳庭），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("elysia_star_fangting.png", "爱莉希雅_星环_芳庭", template_path=template_path, confidence=confidence)

def click_zhenwo(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zhenwo.png图片（真我），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zhenwo.png", "真我", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_zhanchang_jianfu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zhanchang_jianfu.png图片（战场减负），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zhanchang_jianfu.png", "战场减负", template_path=template_path, confidence=confidence)

def click_chuzhanrenwu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击chuzhanrenwu.png图片（出战人物），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chuzhanrenwu.png", "出战人物", template_path=template_path, confidence=confidence)

def click_houbenghuaishu1(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击houbenghuaishu1.png图片（后崩坏书1），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("houbenghuaishu1.png", "后崩坏书1", template_path=template_path, confidence=confidence)

def click_ditu_jinru(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击ditu_jinru.png图片（地图_进入），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("ditu_jinru.png", "地图_进入", template_path=template_path, confidence=confidence)

def click_houbenghuai1_weituo(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击houbenghuai1_weituo.png图片（后崩坏书1_委托），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("houbenghuai1_weituo.png", "后崩坏书1_委托", template_path=template_path, confidence=confidence)

def click_weituo_kaiqi(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击weituo_kaiqi.png图片（委托开启），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("weituo_kaiqi.png", "委托开启", template_path=template_path, confidence=confidence)

def click_jinbi(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jinbi.png图片（金币），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jinbi.png", "金币", template_path=template_path, confidence=confidence)

def click_qvchujinbi(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击qvchujinbi.png图片（领取金币），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("qvchujinbi.png", "领取金币", template_path=template_path, confidence=confidence)

def click_lingqv(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击lingqv.png图片（领取），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("lingqv.png", "领取", template_path=template_path, confidence=confidence)

def click_monizuozhanshi(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击monizuozhanshi.png图片（模拟作战室），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("monizuozhanshi.png", "模拟作战室", template_path=template_path, confidence=confidence)

def click_letu_jianfuzhandou(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击letu_jianfuzhandou.png图片（乐土_减负战斗），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("letu_jianfuzhandou.png", "乐土_减负战斗", template_path=template_path, confidence=confidence)

def click_elysia_star_jinjian(template_path=None, confidence=0.4):
    """
    在屏幕上查找并点击elysia_star_jinjian.png图片（爱莉希雅_星_金箭），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("elysia_star_jinjian.png", "爱莉希雅_星_金箭", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_goumaikeyin(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击goumaikeyin.png图片（购买刻印），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("goumaikeyin.png", "购买刻印", template_path=template_path, confidence=confidence)

def click_jiushi(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击jiushi.png图片（救世），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiushi.png", "救世", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_huangjin(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击huangjin.png图片（黄金），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("huangjin.png", "黄金", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_aomie(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击aomie.png图片（鏖灭），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("aomie.png", "鏖灭", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_fanxing(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击fanxing.png图片（繁星），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("fanxing.png", "繁星", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_kongmeng(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击kongmeng.png图片（空梦），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("kongmeng.png", "空梦", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_fusheng(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击fusheng.png图片（浮生），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("fusheng.png", "浮生", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_chana(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击chana.png图片（刹那），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("chana.png", "刹那", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_luoxuan(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击luoxuan.png图片（螺旋），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("luoxuan.png", "螺旋", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_xvguang(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击xvguang.png图片（旭光），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("xvguang.png", "旭光", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_wuxian(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击wuxian.png图片（无限），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("wuxian.png", "无限", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_jielv(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击jielv.png图片（戒律），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jielv.png", "戒律", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_tianhui(template_path=None, confidence=0.7):
    """
    在屏幕上查找并点击tianhui.png图片（天慧），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("tianhui.png", "天慧", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_weituo_xuanze(template_path=None, confidence=0.8):    
    """
    在屏幕上查找并点击weituo_xuanze.png图片（委托选择），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("weituo_xuanze.png", "委托选择", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_weituo_jieqv(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击weituo_jieqv.png图片（委托接取），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("weituo_jieqv.png", "委托接取", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_weituo_jianfu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击weituo_jianfu.png图片（委托减负），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("weituo_jianfu.png", "委托减负", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_queding(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击queding.png图片（确定），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("queding.png", "确定", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_jiantuan_yijianjianfu(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击jiantuan_yijianjianfu.png图片（舰团一键减负），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("jiantuan_yijianjianfu.png", "舰团一键减负", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_letu_jixvtiaozhan(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击letu_jixvtiaozhan.png图片（乐土_继续挑战），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("letu_jixvtiaozhan.png", "乐土_继续挑战", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_shangcheng(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击shangcheng.png图片（商城），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("shangcheng.png", "商城", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_libao(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击libao.png图片（礼包），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("libao.png", "礼包", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_zhouqi(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击zhouqi.png图片（周期），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("zhouqi.png", "周期", template_path=template_path, confidence=confidence,time_sleep=0.5)

def click_mianfei(template_path=None, confidence=0.8):
    """
    在屏幕上查找并点击mianfei.png图片（免费），只点击一次
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到并点击则返回True，否则返回False
    """
    return click_template("mianfei.png", "免费", template_path=template_path, confidence=confidence,time_sleep=0.5)

def is_letu_elysia_star(template_path=None, confidence=0.8,time_sleep=0.1):
    """
    在屏幕上查找letu_elysia_star.png图片（乐土爱莉希雅星环），不执行点击操作
    支持两种图片：letu_elysia_star.png 和 letu_elysia_star_change.png
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    result = is_template("letu_elysia_star_change.png", "乐土爱莉希雅星环(嫦娥)", template_path=template_path, time_sleep=time_sleep, confidence=confidence)
    if result[0]:
        return True
    
    result = is_template("letu_elysia_star.png", "乐土爱莉希雅星环", template_path=template_path, time_sleep=time_sleep, confidence=confidence)
    return result[0]

def is_letu_zhiyuan_yunmo(template_path=None, confidence=0.8,time_sleep=0.1):
    """
    在屏幕上查找letu_zhiyuan_yunmo.png图片（乐土支援云墨），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("letu_zhiyuan_yunmo.png", "乐土支援云墨", template_path=template_path,time_sleep=time_sleep, confidence=confidence)

def is_letu_zhiyuan_haitu(template_path=None, confidence=0.8,time_sleep=0.1):
    """
    在屏幕上查找letu_zhiyuan_haitu.png图片（乐土支援骇兔），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("letu_zhiyuan_haitu.png", "乐土支援骇兔", template_path=template_path,time_sleep=time_sleep, confidence=confidence)

def is_letu_zhuiyizhizheng(template_path=None, confidence=0.8,time_sleep=0.1):
    """
    在屏幕上查找letu_zhuiyizhizheng.png图片（追忆之证），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("letu_zhuiyizhizheng.png", "追忆之证", template_path=template_path,time_sleep=time_sleep, confidence=confidence)

def is_huishouweituo(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_huishouweituo.png图片（回收委托），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_huishouweituo.png", "回收委托", template_path=template_path, confidence=confidence)

def is_jiantuanjiangchi(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_jiantuanjiangchi.png图片（舰团奖池），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_jiantuanjiangchi.png", "舰团奖池", template_path=template_path, confidence=confidence)

def is_chuji(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_chuji.png图片（出击），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_chuji.png", "出击", template_path=template_path, confidence=confidence)

def is_tiaozhan(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_tiaozhan.png图片（挑战），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_tiaozhan.png", "挑战", template_path=template_path, confidence=confidence)

def is_shenzhijian_done(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_shenzhijian_done.png图片（神之键），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_shenzhijian_done.png", "神之键", template_path=template_path, confidence=confidence)

def is_chongxin_tiaozhan(template_path=None, confidence=0.8):
    """
    在屏幕上查找is_chongxin_tiaozhan.png图片（重新挑战），不执行点击操作
    :param template_path: 图片路径，如果不提供则使用默认路径
    :param confidence: 匹配置信度阈值
    :return: 如果找到图片则返回True，否则返回False
    """
    return is_template("is_chongxin_tiaozhan.png", "重新挑战", template_path=template_path, confidence=confidence)

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
    
    # 按照指定顺序执行测试
    print("\n=== 开始测试流程 ===")
    
    # 0. 执行focus_bh3_window()
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")
    
    print("\n=== 测试流程结束 ===")
    input("按回车键退出...")