import sys
import os
import time

from PIL import Image

# 添加父目录到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入YOLO调用函数
from call_YOLO import call_yolo_model, reset_yolo_client, _last_success_time, filter_guaiwu_ui_upper_half

# 替换print函数为logging.info
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_next_done.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
print = logging.info

def take_bh3_screenshot(window_title="崩坏3", save_path=None):
    """
    对崩坏3窗口进行截图
    
    Args:
        window_title (str): 窗口标题，默认为"崩坏3"
        save_path (str, optional): 截图保存路径，如果为None则不保存
    
    Returns:
        str: 截图保存的临时文件路径，如果截图失败则返回None
    """
    import win32gui
    import win32ui
    import win32con
    from PIL import Image
    
    # 查找崩坏3窗口
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd == 0:
        print(f"未找到窗口: {window_title}")
        return None
    
    # 获取窗口坐标
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    
    # 确保窗口可见
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.1)  # 等待窗口激活
    
    # 获取窗口的DC
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    
    # 创建位图对象
    save_bit_map = win32ui.CreateBitmap()
    save_bit_map.CreateCompatibleBitmap(mfc_dc, width, height)
    
    # 将位图对象选入DC
    save_dc.SelectObject(save_bit_map)
    
    # 截图到DC
    save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
    
    # 保存截图
    if save_path is None:
        # 如果没有指定保存路径，保存到photos/bh3_screenshot目录
        photos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "photos", "bh3_screenshot")
        os.makedirs(photos_dir, exist_ok=True)
        save_path = os.path.join(photos_dir, f"bh3_screenshot_{int(time.time())}.jpg")
    
    try:
        # 获取位图数据
        bmpinfo = save_bit_map.GetInfo()
        bmpstr = save_bit_map.GetBitmapBits(True)
        
        # 使用PIL保存图片
        im = Image.frombuffer(
            'RGB', 
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
            bmpstr, 
            'raw', 
            'BGRX', 
            0, 
            1
        )
        im.save(save_path, 'JPEG')
        print(f"截图已保存到: {save_path}")
        return save_path
    except Exception as e:
        print(f"保存截图失败: {e}")
        return None
    finally:
        # 释放资源
        try:
            win32gui.DeleteObject(save_bit_map.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception as e:
            print(f"释放资源失败: {e}")

# filter_guaiwu_ui_upper_half 已移至 call_YOLO.py 公共模块


def detect_bh3_elements(save_screenshot=False, save_detection_result=False, yolo_timeout=10):
    """
    对崩坏3窗口进行截图并使用YOLO模型进行元素检测

    Args:
        save_screenshot (bool, optional): 是否保存源截图到photos/bh3_screenshot目录，默认为False
        save_detection_result (bool, optional): 是否保存检测后的截图到photos/bh3_YOLO_checked目录，默认为False
        yolo_timeout (int, optional): YOLO客户端超时时间（秒），默认为30秒
    
    Returns:
        dict: YOLO模型的检测结果
    """
    import datetime

    start_time = time.time()

    # 使用 ScreenCapture（复用 GDI 对象），替代 take_bh3_screenshot
    import cv2, tempfile as _tempfile
    _parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    from src.modules.vision.screen_capture import ScreenCapture
    _sc = ScreenCapture()
    img = _sc.capture_game_client_area("崩坏3")
    if img is None:
        return {"success": False, "message": "窗口截图失败"}
    temp_file = _tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    screenshot_path = temp_file.name
    temp_file.close()
    cv2.imwrite(screenshot_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    if screenshot_path is None:
        return {
            "success": False,
            "message": "窗口截图失败"
        }
    
    try:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"2. 正在使用YOLO模型进行元素检测... (开始时间: {current_time})")
        yolo_start = time.time()
        
        checked_photos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "photos", "bh3_YOLO_checked")
        
        # 客户端健康检查：如果距最后一次成功调用超过yolo_timeout秒，重置客户端
        if _last_success_time > 0 and (time.time() - _last_success_time) > yolo_timeout:
            print(f"调试信息：YOLO客户端已超时（{time.time() - _last_success_time:.1f}秒未成功调用），正在重置客户端...")
            reset_yolo_client()
        
        if save_detection_result:
            detection_result = call_yolo_model(
                image_path=screenshot_path,
                conf_threshold=0.5,
                output_dir=checked_photos_dir
            )
        else:
            detection_result = call_yolo_model(
                image_path=screenshot_path,
                conf_threshold=0.5,
                output_dir=None
            )
        
        yolo_end = time.time()
        print(f"2.1 YOLO检测完成，耗时: {yolo_end - yolo_start:.2f}秒")
        
        if detection_result.get("success", False):
            predictions = detection_result.get("predictions", [])
            predictions = filter_guaiwu_ui_upper_half(screenshot_path, predictions)
            detection_result["predictions"] = predictions
            total_objects = len(predictions)
            print(f"2.2 检测结果：成功识别到 {total_objects} 个目标")

            if "predictions" in detection_result:
                elements = [pred.get("class_name", "未知") for pred in detection_result["predictions"]]
                print(f"2.3 识别到的元素：{elements}")
        else:
            print(f"2.2 检测结果：失败，原因: {detection_result.get('message', '未知错误')}")

        end_time = time.time()
        print(f"3. 整个detect_bh3_elements函数完成，总耗时: {end_time - start_time:.2f}秒")

        return detection_result
    finally:
        # 如果不保存源截图，删除临时文件
        # 注意: 不删除 temp 文件 — YOLO 服务端是独立进程，可能异步读取
        pass

def check_elysia_star_exists(max_attempts=20, interval=0.2):
    """
    持续检查是否存在elysia_star元素，直到检测到或达到最大尝试次数
    
    Args:
        max_attempts (int): 最大尝试次数，默认为20
        interval (float): 每次尝试之间的间隔时间（秒），默认为0.2
    
    Returns:
        bool: 如果在最大尝试次数内检测到elysia_star，返回True；否则返回False
    """
    print(f"开始持续检测elysia_star，最大尝试次数: {max_attempts}，间隔: {interval}秒")
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n尝试 {attempt}/{max_attempts}:")
        
        # 对BH3窗口进行截图并使用YOLO模型进行元素检测
        result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
        
        if not result.get("success", False):
            print("元素检测失败，继续尝试")
            time.sleep(interval)
            continue
        
        predictions = result.get("predictions", [])
        
        # 检查是否存在elysia_star元素
        for pred in predictions:
            class_name = pred.get("class_name", "")
            if class_name == "elysia_star":
                print("检测到elysia_star元素")
                return True
        
        print("未检测到elysia_star元素，继续尝试")
        time.sleep(interval)
    
    print(f"已达到最大尝试次数({max_attempts})，未检测到elysia_star元素")
    return False

if __name__ == "__main__":
    # 测试函数
    exists = check_elysia_star_exists()
    print(f"elysia_star存在: {exists}")
