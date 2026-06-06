import sys
import os
import time
import datetime
import json
import math
import win32gui
import win32ui
import win32con
import logging
import threading
from PIL import Image

# 设置日志配置，将日志同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'letu_find_way.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
# 导入YOLO调用函数
from call_YOLO import call_yolo_model, reset_yolo_client, _last_success_time, filter_guaiwu_ui_upper_half
# 导入键盘鼠标操作库
import templates.clicks_keyboard as ck


# 替换print函数为logging.info
print = logging.info


def take_bh3_screenshot(window_title="崩坏3", save_path=None):
    """
    对崩坏3窗口进行截图
    
    Args:
        window_title (str): 窗口标题，默认为"崩坏3"
        save_path (str, optional): 截图保存路径，如果为None则不保存
    
    Returns:
        str: 截图保存的路径，如果save_path为None则返回临时文件路径
    """
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
    
    # 使用临时文件保存截图，以便进行YOLO检测
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
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
        im.save(temp_path, 'JPEG')
        
        # 如果指定了保存路径，将图片保存到指定路径
        if save_path is not None:
            # 只有当明确指定保存路径时才保存截图到photos目录
            photos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "photos", "bh3_screenshot")
            os.makedirs(photos_dir, exist_ok=True)
            save_path = os.path.join(photos_dir, f"bh3_screenshot_{int(time.time())}.jpg")
            im.save(save_path, 'JPEG')
            print(f"截图已保存到: {save_path}")
            return save_path
        
        # 返回临时文件路径
        return temp_path
    except Exception as e:
        print(f"保存截图失败: {e}")
        return None
    finally:
        # 释放资源
        win32gui.DeleteObject(save_bit_map.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


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
    _backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
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

def get_center(bbox):
    """
    计算边界框的中心点坐标
    
    Args:
        bbox (list): 边界框坐标 [x1, y1, x2, y2]
    
    Returns:
        tuple: 中心点坐标 (x, y)
    """
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def should_use_ad_keys(target_element, bbox, x_diff=None):
    """
    判断是否应该使用ad键（左右移动），而不是qe键（视角旋转）
    
    Args:
        target_element (str): 目标元素名称
        bbox (list): 边界框坐标 [x1, y1, x2, y2]
        x_diff (float, optional): self元素与目标元素的x轴差值
    
    Returns:
        bool: 是否应该使用ad键
    """
    # 计算当前边界框的宽高比
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    current_ratio = width / height if height != 0 else 0
    
    # 获取元素的宽高标准配置（所有元素现在都是range类型）
    config = element_size_config.get(target_element, element_size_config["default"])
    
    # 计算目标宽高比范围（所有元素都是range类型）
    min_width = config["width_range"][0]
    max_width = config["width_range"][1]
    min_height = config["height_range"][0]
    max_height = config["height_range"][1]
    
    # 计算最小和最大可能的宽高比
    min_target_ratio = min_width / max_height if max_height != 0 else 0
    max_target_ratio = max_width / min_height if min_height != 0 else float('inf')
    
    # 增加宽高比公差，避免因轻微偏差导致频繁旋转
    tolerance = 0.10  # 10%的公差
    adjusted_min_ratio = min_target_ratio * (1 - tolerance)
    adjusted_max_ratio = max_target_ratio * (1 + tolerance)
    
    # 检查宽高是否大致符合要求（不仅仅是宽高比）
    is_width_approx = min_width * 0.8 <= width <= max_width * 1.2
    is_height_approx = min_height * 0.8 <= height <= max_height * 1.2
    
    # 判断当前宽高比是否在调整后的范围内，并且宽高大致符合要求
    is_approx_correct_ratio = adjusted_min_ratio <= current_ratio <= adjusted_max_ratio
    
    # 添加对x差值的判断：当x差值符合要求时，使用qe调整而不是ad移动
    # 符合要求的x差值：绝对值小于150px
    is_x_diff_acceptable = x_diff is None or abs(x_diff) < 150
    
    # 逻辑：
    # - 如果当前宽高比在调整后的范围内，并且宽高大致符合要求，并且x差值不符合要求：使用ad键（左右移动）
    # - 否则：使用qe键（旋转视角，使其宽高比符合要求）
    return is_approx_correct_ratio and is_width_approx and is_height_approx and not is_x_diff_acceptable


def is_approx_230px(bbox, target=230, tolerance=50):
    """
    判断边界框的宽高是否近似为目标值
    
    Args:
        bbox (list): 边界框坐标 [x1, y1, x2, y2]
        target (int): 目标值
        tolerance (int): 允许的误差范围
    
    Returns:
        bool: 是否近似为目标值
    """
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    return abs(width - target) <= tolerance and abs(height - target) <= tolerance


def test_qe_effect(target_element, current_bbox):
    """
    测试按下q或e键前后的宽高比变化，选择效果更好的按键
    
    Args:
        target_element (str): 目标元素名称
        current_bbox (list): 当前边界框坐标 [x1, y1, x2, y2]
    
    Returns:
        str: 选择的按键 ('q', 'e' 或 None)
    """
    # 获取元素的宽高标准配置
    config = element_size_config.get(target_element, element_size_config["default"])
    min_width = config["width_range"][0]
    max_width = config["width_range"][1]
    min_height = config["height_range"][0]
    max_height = config["height_range"][1]
    
    # 计算目标宽高比范围
    min_target_ratio = min_width / max_height if max_height != 0 else 0
    max_target_ratio = max_width / min_height if min_height != 0 else float('inf')
    
    # 计算当前宽高比
    x1, y1, x2, y2 = current_bbox
    current_width = x2 - x1
    current_height = y2 - y1
    current_ratio = current_width / current_height if current_height != 0 else 0
    
    print(f"调试信息：测试q/e键效果 - 当前宽高比：{current_ratio:.2f}")
    print(f"调试信息：目标宽高比范围：{min_target_ratio:.2f}-{max_target_ratio:.2f}")
    
    # 定义评估函数：使用正态分布评估宽度
    def evaluate_ratio(width):
        # 计算宽度差距（使用正态分布评价）
        # 取目标元素的宽范围的中心值
        target_width_center = (min_width + max_width) / 2
        # 计算标准差（使用宽范围的1/4作为标准差）
        std_dev = (max_width - min_width) / 4
        
        # 使用正态分布计算宽度分数（评分范围0~1，中心点为1，离中心点越远分数越低）
        if std_dev > 0:
            # 正态分布函数：f(x) = exp(-(x-μ)²/(2σ²))
            width_score = math.exp(-((width - target_width_center) ** 2) / (2 * (std_dev ** 2)))
        else:
            width_score = 0
        
        # 不考虑高的评价，因为高的评价是交给ws的
        # 只返回宽度评分，越接近1越好
        return width_score
    
    # 初始状态的评估值
    initial_score = evaluate_ratio(current_width)
    
    # 测试按下q键的效果
    print("调试信息：测试按下q键的效果...")
    ck.keyboard_q_hold_release(0.01)
    time.sleep(0.5)
    
    q_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
    q_score = initial_score
    q_bbox = None
    
    if q_result.get("success", False):
        q_predictions = q_result.get("predictions", [])
        q_target_bboxes = [pred.get("bbox") for pred in q_predictions 
                         if pred.get("class_name") == target_element and pred.get("bbox")]
        
        if q_target_bboxes:
            q_bbox = q_target_bboxes[0]
            q_width = q_bbox[2] - q_bbox[0]
            q_height = q_bbox[3] - q_bbox[1]
            q_ratio = q_width / q_height if q_height != 0 else 0
            q_score = evaluate_ratio(q_width)
            print(f"调试信息：按下q键后宽高：{q_width:.2f}x{q_height:.2f}，评分：{q_score:.4f}")
    
    # 测试按下e键的效果
    print("调试信息：测试按下e键的效果...")
    # 按下e键0.02秒，避免回到原位
    ck.keyboard_e_hold_release(0.02)
    time.sleep(0.5)
    
    e_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
    e_score = initial_score
    e_bbox = None
    
    if e_result.get("success", False):
        e_predictions = e_result.get("predictions", [])
        e_target_bboxes = [pred.get("bbox") for pred in e_predictions 
                         if pred.get("class_name") == target_element and pred.get("bbox")]
        
        if e_target_bboxes:
            e_bbox = e_target_bboxes[0]
            e_width = e_bbox[2] - e_bbox[0]
            e_height = e_bbox[3] - e_bbox[1]
            e_ratio = e_width / e_height if e_height != 0 else 0
            e_score = evaluate_ratio(e_width)
            print(f"调试信息：按下e键后宽高：{e_width:.2f}x{e_height:.2f}，评分：{e_score:.4f}")
    
    # 比较三种情况，选择评分最高的（最接近目标范围）
    scores = {
        'initial': initial_score,
        'q': q_score,
        'e': e_score
    }
    
    print(f"调试信息：评分对比 - 初始：{initial_score:.4f}, q键：{q_score:.4f}, e键：{e_score:.4f}")
    
    # 找出最佳选择
    max_score = max(scores.values())
    best_choices = [k for k, v in scores.items() if v == max_score]
    
    # 决策逻辑：选择评分最高且高于初始评分的按键
    if 'q' in best_choices and q_score > initial_score:
        print("调试信息：选择按下q键，宽度更接近目标范围")
        return 'q'
    elif 'e' in best_choices and e_score > initial_score:
        print("调试信息：选择按下e键，宽度更接近目标范围")
        return 'e'
    else:
        print("调试信息：q/e键效果不明显，不执行操作")
        return None


# 定义元素宽高标准配置字典（全局变量，避免重复创建）
element_size_config = {
    "shangdian_open": {
        "width_range": (460, 610),  # 增大10px
        "height_range": (460, 610),  # 增大10px
        "type": "range",
        "size_text": "460px-610px"
    },
    "jiushi": {
        "width_range": (135, 225),  # 110-250 减小25px → 135-225
        "height_range": (235, 325),  # 210-350 减小25px → 235-325
        "type": "range",
        "size_text": "135px-225px×235px-325px"
    },
    "fusheng": {
        "width_range": (230, 300),
        "height_range": (150, 220),
        "type": "range",
        "size_text": "230px-300px×150px-220px"
    },
    # 其他元素的默认配置
    "default": {
        "width_range": (205, 275),  # 下限提高25px
        "height_range": (205, 275),  # 下限提高25px
        "type": "range",
        "size_text": "205px~275px"
    }
}

# 定义元素前后移动配置字典（全局变量，避免重复创建）
element_movement_config = {
    "shangdian_open": {
        "forward_threshold": (460, 460),  # 增大10px
        "backward_threshold": (610, 610)  # 增大10px
    },
    "jiushi": {
        "forward_threshold": (200, 300),
        "backward_threshold": (250, 350)
    },
    "fusheng": {
        "forward_threshold": (230, 150),
        "backward_threshold": (300, 220)
    },
    "default": {
        "forward_threshold": (205, 205),  # 下限提高25px
        "backward_threshold": (275, 275)  # 保持不变
    }
}


def to_there(target_element, elements, last_target=None):
    """
    根据目标元素和self类型元素的位置关系执行相应操作，直到两者位置差距在±100px内且面积基本不变
    
    函数流程：
    1. 初始化变量：存储上一次的面积和位置、连续没有检测到目标元素的次数、连续按下移动键的次数等
    2. 进入主循环，最多执行100次迭代
    3. 每次迭代执行以下操作：
       - 重新检测元素
       - 提取目标元素和self类型元素的边界框
       - 处理目标元素消失的情况
       - 处理self元素消失的情况
       - 计算目标元素和self元素的中心点
       - 检查是否满足结束条件
       - 根据位置关系执行相应操作
       - 按下r键执行交互操作
       - 检测r键效果
    4. 如果达到最大迭代次数，返回False
    
    变量说明：
    - prev_target_area: 上一次检测到的目标元素面积
    - prev_self_area: 上一次检测到的self元素面积
    - prev_target_center: 上一次检测到的目标元素中心点
    - prev_self_center: 上一次检测到的self元素中心点
    - last_target_bbox: 最后一次检测到的目标元素边界框
    - missing_target_count: 连续没有检测到目标元素的次数
    - s_key_count: 连续按下移动键的次数
    - last_ad_key: 上一次按下的ad键，用于调整中心点计算
    - rotation_count: 旋转次数，防止无限循环
    - max_rotations: 最大旋转次数，默认为5
    - element_cache: 元素识别缓存，记录之前检测到的元素及其出现次数
    - current_target_count: 当前目标元素连续检测次数
    - continuous_element_count: 记录其他元素的连续检测次数
    
    情况处理：
    1. 目标元素消失的情况：
       - 如果连续两次未检测到目标元素，根据最后一次检测到的元素大小决定按下w还是s键
       - 如果连续8次检测到只有self元素，尝试按下w键0.5秒
       - 如果连续12次检测到只有self元素，退出程序
       - 如果检测到其他可能的目标元素，检查是否有元素连续出现3次，如果有，切换为新目标
    
    2. self元素消失的情况：
       - 等待0.5秒后重新检测
       - 执行简单的按键操作，帮助重新定位
    
    3. 位置关系处理：
       - 左：self元素在目标元素的左方，执行按键e（视角右转）或d（向右移动）
       - 右：self元素在目标元素的右方，执行按键q（视角左转）或a（向左移动）
       - 正对着但宽高不符合要求：根据宽高比执行按键w或s
    
    4. r键交互操作：
       - 按下r键后等待1秒
       - 检测三次r键效果：
         * 检查目标元素是否仍然存在
         * 检查位置是否发生明显变化
         * 如果目标元素消失或位置无明显变化，操作成功，返回True
         * 否则，执行e键尝试（最多两次）
    
    Args:
        target_element (str): 目标元素名称
        elements (list): 初始检测到的元素列表
    
    Returns:
        bool: 操作是否成功
            - True: 成功将角色移动到目标元素位置并执行交互操作
            - False: 达到最大迭代次数，未能成功移动到目标元素位置
    """
    
    
    # 存储上一次的面积和位置，用于判断是否稳定
    prev_target_area = None
    prev_self_area = None
    prev_target_center = None
    prev_self_center = None
    prev_target_element = None  # 记录上一次的目标元素名称
    last_target_bbox = None  # 保存最后一次检测到的目标元素边界框
    
    # 记录连续没有检测到目标元素的次数
    missing_target_count = 0
    
    # 记录连续按下移动键的次数
    s_key_count = 0
    
    # 记录上一次按下的ad键，用于调整中心点计算
    # None: 未使用ad键，'a': 上一次按下a键，'d': 上一次按下d键
    last_ad_key = None
    
    # 记录旋转次数，防止无限循环
    rotation_count = 0
    max_rotations = 5
    
    # 元素识别缓存：记录之前检测到的元素及其出现次数
    element_cache = {target_element: 1}  # 初始目标元素
    
    # 记录当前目标元素的连续检测次数
    current_target_count = 0
    
    # 记录其他元素的连续检测次数
    continuous_element_count = {}  # 键：元素名，值：连续出现次数
    
    # 记录keyin目标的失效次数
    keyin_target_fail_count = 0
    # 记录当前选择的keyin目标索引
    current_keyin_target_index = 0
    
    max_iterations = 100
    iteration = 0
    
    # 死循环计数器，用于检测连续的self元素消失情况
    self_missing_count = 0
    max_self_missing_count = 10
    
    # 读取keyin_detail.json文件获取权重配置
    keyin_detail_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")
    with open(keyin_detail_path, "r", encoding="utf-8") as f:
        keyin_detail = json.load(f)
    
    while iteration < max_iterations:
        iteration += 1
        
        # 重新检测元素
        result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
        if not result.get("success", False):
            time.sleep(0.5)
            continue
        
        predictions = result.get("predictions", [])
        
        # 提取目标元素和self类型元素的边界框
        target_bboxes = []
        self_bbox = None
        
        # 定义表示"我"的元素类型列表
        self_elements = ["elysia_star"]
        
        # 记录当前检测到的所有元素
        current_elements = set()
        
        for pred in predictions:
            class_name = pred.get("class_name", "")
            bbox = pred.get("bbox", [])
            
            # 记录所有检测到的元素
            if class_name and bbox:
                current_elements.add(class_name)
                
            if class_name == target_element and bbox:
                target_bboxes.append(bbox)
            elif class_name in self_elements and bbox:
                self_bbox = bbox
        
        # 更新元素缓存和连续出现次数
        for elem in current_elements:
            # 只缓存非self元素，且不记录keyin元素和keyin_open元素
            if elem not in self_elements and elem != 'keyin' and elem != 'keyin_open':
                # 更新总出现次数
                element_cache[elem] = element_cache.get(elem, 0) + 1
                # 更新连续出现次数，上限为2
                continuous_element_count[elem] = min(continuous_element_count.get(elem, 0) + 1, 2)
        
        # 重置未出现元素的连续出现次数
        for elem in list(continuous_element_count.keys()):
            if elem not in current_elements or elem in self_elements or elem == 'keyin' or elem == 'keyin_open':
                continuous_element_count[elem] = 0
        
        # 打印元素缓存信息和连续出现次数
        print(f"调试信息：元素缓存状态：{element_cache}")
        print(f"调试信息：连续出现次数：{continuous_element_count}")
        
        # 确保两者都被检测到
        if not target_bboxes or not self_bbox:
            # 处理目标元素消失的情况
            if not target_bboxes and self_bbox:
                missing_target_count += 1
                print(f"调试信息：目标元素{target_element}消失，连续消失次数：{missing_target_count}")
                
                # 检查当前是否检测到其他可能的目标元素
                other_elements = [elem for elem in current_elements if elem not in self_elements and elem != target_element]
                
                # 如果last_target为shangdian_open，排除shangdian_open作为目标元素
                if last_target == "shangdian_open" or "已处理shangdian_open" in str(last_target):
                    other_elements = [elem for elem in other_elements if elem != 'shangdian_open']
                    print("\n调试信息：上一次的返回值是 shangdian_open，本次不将 shangdian_open 作为目标元素")
                
                if other_elements:
                    print(f"调试信息：检测到其他可能的目标元素：{other_elements}")
                    
                    # 特殊逻辑：当当前target为keyin时，按照三类情况的优先级切换到新出现的非keyin元素
                    if target_element == 'keyin':
                        # 定义三类情况的元素集合，参考find_elements函数
                        case1_elements = {'shangdian', 'shangdian_open', 'BOSS'}
                        case2_elements = {'aomie', 'zhenwo', 'kongmeng', 'jielv', 'luoxuan', 'tianhui', 'fanxing', 
                                         'wuxian', 'chana', 'huangjin', 'jiushi', 'xvguang', 'fusheng'}
                        
                        # 如果last_target为shangdian_open，排除shangdian_open作为情况1元素
                        if last_target == "shangdian_open" or "已处理shangdian_open" in str(last_target):
                            case1_elements = case1_elements - {'shangdian_open'}
                        
                        # 按照优先级选择目标元素
                        # 1. 首先检查情况1的元素
                        case1_match = [elem for elem in other_elements if elem in case1_elements]
                        if case1_match:
                            elem = case1_match[0]
                            print(f"调试信息：当前target为keyin，优先切换到情况1元素 {elem} 作为目标")
                        # 2. 然后检查情况2的元素
                        else:
                            case2_match = [elem for elem in other_elements if elem in case2_elements]
                            if case2_match:
                                # 对于情况2元素，按照权重选择最高的
                                
                                # 读取keyin_detail.json文件获取权重配置
                                keyin_detail_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")
                                with open(keyin_detail_path, "r", encoding="utf-8") as f:
                                    keyin_detail = json.load(f)
                                
                                max_score = -1
                                selected_elem = None
                                for elem in case2_match:
                                    weight = keyin_detail.get(f"{elem}_weight", 0)
                                    consecutive_count = keyin_detail.get(f"{elem}_consecutive_count", 1)
                                    consecutive_count = min(consecutive_count, 3)
                                    score = consecutive_count * weight
                                    if score > max_score:
                                        max_score = score
                                        selected_elem = elem
                                
                                if selected_elem:
                                    elem = selected_elem
                                    print(f"调试信息：当前target为keyin，切换到情况2元素 {elem} 作为目标（得分：{max_score:.4f}）")
                                else:
                                    elem = case2_match[0]
                                    print(f"调试信息：当前target为keyin，切换到情况2元素 {elem} 作为目标")
                            # 3. 最后选择其他元素
                            else:
                                elem = other_elements[0]
                                print(f"调试信息：当前target为keyin，切换到新元素 {elem} 作为目标")
                        
                        # 更新目标元素
                        target_element = elem
                        last_target_bbox = None
                        prev_target_area = None
                        prev_target_center = None
                        prev_target_element = None
                        missing_target_count = 0
                        current_target_count = 0
                        # 重置移动键计数
                        s_key_count = 0
                        # 重置连续出现次数记录
                        continuous_element_count.clear()
                        continuous_element_count[elem] = 0
                        continue
                    
                    # 检查是否有元素连续出现3次
                    target_changed = False
                    
                    # 首先检查当前目标元素的连续出现次数
                    current_target_continuous = continuous_element_count.get(target_element, 0)
                    print(f"调试信息：当前目标元素 {target_element} 的连续出现次数 = {current_target_continuous}")
                    
                    for elem in other_elements:
                        continuous_count = continuous_element_count.get(elem, 0)
                        print(f"调试信息：元素 {elem} 的连续出现次数 = {continuous_count}")
                        
                        # 如果元素连续出现2次，且当前目标元素没有连续出现2次，切换为新目标
                        # 当当前目标和其他目标都连续出现2次时，不切换目标
                        if continuous_count >= 2 and current_target_continuous < 2:
                            print(f"调试信息：动态更新目标元素，从 {target_element} 切换到 {elem}，连续出现次数 = {continuous_count}")
                            # 更新目标元素
                            target_element = elem
                            last_target_bbox = None
                            prev_target_area = None
                            prev_target_center = None
                            missing_target_count = 0
                            current_target_count = 0
                            # 重置移动键计数
                            s_key_count = 0
                            # 重置连续出现次数记录
                            continuous_element_count.clear()
                            continuous_element_count[elem] = 0
                            target_changed = True
                            break
                        elif continuous_count >= 2 and current_target_continuous >= 2:
                            print(f"调试信息：当前目标 {target_element} 和元素 {elem} 都连续出现2次，保持当前目标")
                    
                    if target_changed:
                        continue
                    
                    print("调试信息：没有元素连续出现2次，继续寻找当前目标元素")
                
                # 处理没有之前目标元素信息的情况（初始检测或完全丢失）
                if prev_target_area is None:
                    print(f"调试信息：没有之前的目标元素信息，连续检测到self元素次数：{missing_target_count}")
                    
                    # 在第8次后，尝试按下w0.5s，再次检测
                    if missing_target_count == 8:
                        print("调试信息：第8次检测到只有self元素，尝试按下w键0.5秒")
                        ck.keyboard_w_hold_release(0.5)
                        time.sleep(0.5)
                        
                        # 再次检测
                        retry_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                        if retry_result.get("success", False):
                            retry_predictions = retry_result.get("predictions", [])
                            retry_target_bboxes = [pred.get("bbox") for pred in retry_predictions if pred.get("class_name") == target_element and pred.get("bbox")]
                            if retry_target_bboxes:
                                print("调试信息：重试检测到目标元素，继续执行")
                                missing_target_count = 0
                                continue
                    
                    # 尝试转换四次后，无果就抛出异常
                    elif missing_target_count >= 12:  # 8次初始检测 + 4次转换尝试
                        error_msg = f"错误：连续12次检测到只有self元素{self_elements[0]}，未检测到目标元素{target_element}，程序退出"
                        print(error_msg)
                        raise Exception(error_msg)
                
                # 只有连续两次没有检测到目标元素，才执行移动操作并调整视角
                elif missing_target_count >= 2:
                    # 获取目标元素的大小配置
                    config = element_size_config.get(target_element, element_size_config["default"])
                    min_width, max_width = config["width_range"]
                    min_height, max_height = config["height_range"]
                    
                    # 计算目标元素的平均大小（基于配置）
                    avg_config_width = (min_width + max_width) / 2
                    avg_config_height = (min_height + max_height) / 2
                    avg_config_area = avg_config_width * avg_config_height
                    
                    # 计算最后一次检测到的目标元素大小
                    last_target_width = last_target_bbox[2] - last_target_bbox[0] if last_target_bbox else avg_config_width
                    last_target_height = last_target_bbox[3] - last_target_bbox[1] if last_target_bbox else avg_config_height
                    last_target_area = last_target_width * last_target_height
                    
                    # 设置适应范围：可按下r键大小的1/2以上（无上限）
                    min_scale = 0.5  # 1/2
                    is_in_range = last_target_area >= min_scale * avg_config_area
                    
                    # 根据大小比较结果决定按下w还是s
                    if is_in_range:
                        # 在允许范围内，默认按下s
                        print(f"调试信息：连续两次未检测到目标元素{target_element}，元素大小在适应范围内（≥{min_scale*100:.0f}%），按下s键0.5秒")
                        ck.keyboard_s_hold_release(0.5)
                    else:
                        # 比适应范围小，按下w
                        print(f"调试信息：连续两次未检测到目标元素{target_element}，元素太小（<{min_scale*100:.0f}%），按下w键0.5秒")
                        ck.keyboard_w_hold_release(0.5)
                    
                    time.sleep(0.5)
                    
                    # 根据最后一次目标元素位置调整视角
                    if prev_target_center and prev_self_center:
                        last_target_x, _ = prev_target_center
                        last_self_x, _ = prev_self_center
                        if last_target_x > last_self_x + 100:  # 目标在右边，向左转
                            print(f"调试信息：根据最后位置关系，目标在右边，按下q键调整视角")
                            ck.keyboard_q_hold_release(0.02)
                        elif last_target_x < last_self_x - 100:  # 目标在左边，向右转
                            print(f"调试信息：根据最后位置关系，目标在左边，按下e键调整视角")
                            ck.keyboard_e_hold_release(0.02)
                    
                    # 增加连续按下移动键的次数
                    s_key_count += 1
                    print(f"调试信息：连续按下移动键0.5秒的次数：{s_key_count}")
                    
                    # 如果连续按下移动键0.5秒达到3次，重置为没有之前目标元素信息的状态
                    if s_key_count >= 3:
                        print(f"调试信息：连续3次按下移动键0.5秒后仍未检测到目标元素{target_element}，重置为初始状态")
                        # 重置为没有之前目标元素信息的状态
                        prev_target_area = None
                        last_target_bbox = None
                        prev_target_center = None
                        prev_target_element = None
                        s_key_count = 0  # 重置移动键计数
                        missing_target_count = 0  # 重置目标元素消失计数器
                        continue
                    
                    # 重置目标元素消失计数器
                    missing_target_count = 0
                else:
                    time.sleep(0.5)
                continue
            else:
                # 处理self元素消失的情况或其他情况
                if not self_bbox:
                    print(f"调试信息：self元素消失，等待0.5秒后重新检测")
                    time.sleep(0.5)  # 更长的等待时间
                    # 执行简单的按键操作，帮助重新定位
                    ck.keyboard_s_hold_release(1)  # 向后移动一点
                    time.sleep(0.2)
                    # 重置所有相关变量，避免死循环
                    print(f"调试信息：重置所有相关变量，避免死循环")
                    prev_target_area = None
                    prev_self_area = None
                    prev_target_center = None
                    prev_self_center = None
                    prev_target_element = None
                    last_target_bbox = None
                    rotation_count = 0
                    # 增加self元素消失计数器
                    self_missing_count += 1
                    print(f"调试信息：self元素消失计数器 = {self_missing_count}/{max_self_missing_count}")
                    
                    # 当计数器达到最大值时，尝试按下w和a键30秒
                    if self_missing_count >= max_self_missing_count:
                        print("\n调试信息：self元素连续消失10次，开始按下w和a键30秒，持续检测元素...")
                        
                        stop_event = threading.Event()
                        shared_state = {'detected': False}
                        
                        def hold_key_with_ck(key, stop_event):
                            try:
                                # 使用ck库的pyautogui模块持续按住按键
                                ck.pyautogui.keyDown(key)
                                print(f"调试信息：开始按住{key}键")
                                # 等待停止事件或超时
                                stop_event.wait(timeout=30)
                            finally:
                                ck.pyautogui.keyUp(key)
                                print(f"调试信息：释放{key}键")
                        
                        def detect_elements(stop_event, shared_state):
                            start_time = time.time()
                            while not stop_event.is_set() and time.time() - start_time < 30:
                                # 检测元素
                                result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                                if result.get("success", False):
                                    predictions = result.get("predictions", [])
                                    detected_elements = {pred.get("class_name", "") for pred in predictions}
                                    
                                    # 定义self元素
                                    self_elements = ["elysia_star"]
                                    
                                    # 如果检测到非self元素，停止并重新处理
                                    if not detected_elements.issubset(set(self_elements)):
                                        print("\n调试信息：检测到其他元素，停止w和a键，重新处理...")
                                        shared_state['detected'] = True
                                        stop_event.set()
                                        return
                                # 等待0.5秒
                                time.sleep(0.5)
                        
                        # 创建线程
                        w_thread = threading.Thread(target=hold_key_with_ck, args=('w', stop_event))
                        a_thread = threading.Thread(target=hold_key_with_ck, args=('a', stop_event))
                        detect_thread = threading.Thread(target=detect_elements, args=(stop_event, shared_state))
                        
                        # 启动线程
                        w_thread.start()
                        a_thread.start()
                        detect_thread.start()
                        
                        # 等待检测线程完成（最多30秒）
                        detect_thread.join(timeout=30)
                        
                        # 设置停止事件以确保按键线程停止
                        stop_event.set()
                        
                        # 等待按键线程结束
                        w_thread.join(timeout=1)
                        a_thread.join(timeout=1)
                        
                        if shared_state['detected']:
                            # 重置计数器并重新检测
                            self_missing_count = 0
                            continue
                        else:
                            # 30秒后仍无元素，退出函数
                            print("\n调试信息：按下w和a键30秒后仍未检测到其他元素，退出函数")
                            return False, target_element
                else:
                    # self元素存在，重置计数器
                    self_missing_count = 0
                # 重置计数器
                missing_target_count = 0
                continue
        else:
            # 检测到目标元素，更新当前目标元素连续检测次数
            current_target_count += 1
            print(f"调试信息：连续检测到目标元素{target_element} {current_target_count}次")
            
            # 重置所有计数器
            missing_target_count = 0
            s_key_count = 0
            rotation_count = 0
            
            # 更新最后一次检测到的目标元素边界框
            last_target_bbox = target_bboxes[0]
            
            # 计算当前目标元素的面积和中心位置
            current_target_bbox = target_bboxes[0]
            current_target_area = (current_target_bbox[2] - current_target_bbox[0]) * (current_target_bbox[3] - current_target_bbox[1])
            current_target_center = ((current_target_bbox[0] + current_target_bbox[2]) / 2, (current_target_bbox[1] + current_target_bbox[3]) / 2)
            
            # 特殊处理keyin元素：记录上一次的中心点，如果下一次还检测到keyin元素，则按下w0.5s，这次不记录中心点
            if target_element == "keyin" and prev_target_element == "keyin":
                print(f"调试信息：连续检测到keyin元素，按下w键0.5秒，不记录本次中心点")
                ck.keyboard_w_hold_release(0.5)
                # 不更新prev_target_area、prev_target_center和prev_target_element，保持上一次的值
            else:
                # 更新上一次的面积和位置
                prev_target_area = current_target_area
                prev_target_center = current_target_center
                prev_target_element = target_element
            
            # 计算当前self元素的面积和中心位置
            current_self_center = ((self_bbox[0] + self_bbox[2]) / 2, (self_bbox[1] + self_bbox[3]) / 2)
            current_self_area = (self_bbox[2] - self_bbox[0]) * (self_bbox[3] - self_bbox[1])
            prev_self_area = current_self_area
            prev_self_center = current_self_center
        
        # 计算目标元素的中心点（如果有多个keyin，先使用指定索引的元素，失效3次后使用平均值）
        if target_element == "keyin" and len(target_bboxes) > 1:
            # 检查是否需要使用平均值方法
            if keyin_target_fail_count >= 3:
                # 多个keyin，取所有中心点的平均值
                centers = [get_center(bbox) for bbox in target_bboxes]
                target_center_x = sum(cx for cx, cy in centers) / len(centers)
                target_center_y = sum(cy for cx, cy in centers) / len(centers)
                # 使用第一个边界框的面积作为代表
                target_bbox = target_bboxes[0]
                print(f"调试信息：keyin目标失效{keyin_target_fail_count}次，使用平均值方法")
            else:
                # 确保索引在有效范围内
                if current_keyin_target_index >= len(target_bboxes):
                    current_keyin_target_index = 0
                # 使用指定索引的keyin元素
                target_bbox = target_bboxes[current_keyin_target_index]
                target_center_x, target_center_y = get_center(target_bbox)
                print(f"调试信息：使用第{current_keyin_target_index+1}个keyin目标，失效次数：{keyin_target_fail_count}")
        else:
            # 单个目标元素
            target_bbox = target_bboxes[0]
            target_center_x, target_center_y = get_center(target_bbox)
        
        # 计算self元素的中心点，根据上一次按下的ad键调整
        x1, y1, x2, y2 = self_bbox
        if last_ad_key == 'a':
            # 上一次按下a键（向左移动），取左侧三分之一作为中心点x坐标
            # 计算左侧三分之一位置：x1 + (x2 - x1) * (1/3)
            self_center_x = x1 + (x2 - x1) * (1/3)
            self_center_y = (y1 + y2) / 2
            print(f"调试信息：上一次按下a键，使用左侧三分之一作为self中心点：({self_center_x:.2f}, {self_center_y:.2f})")
        elif last_ad_key == 'd':
            # 上一次按下d键（向右移动），取右侧三分之一作为中心点x坐标
            # 计算右侧三分之一位置：x1 + (x2 - x1) * (2/3)
            self_center_x = x1 + (x2 - x1) * (2/3)
            self_center_y = (y1 + y2) / 2
            print(f"调试信息：上一次按下d键，使用右侧三分之一作为self中心点：({self_center_x:.2f}, {self_center_y:.2f})")
        else:
            # 其他情况，使用默认中心点计算
            self_center_x, self_center_y = get_center(self_bbox)
        
        # 计算中心距离
        center_diff_x = abs(target_center_x - self_center_x)
        center_diff_y = abs(target_center_y - self_center_y)
        
        # 计算面积
        target_area = (target_bbox[2] - target_bbox[0]) * (target_bbox[3] - target_bbox[1])
        self_area = (self_bbox[2] - self_bbox[0]) * (self_bbox[3] - self_bbox[1])
        
        # 获取元素的宽高标准配置（使用全局配置字典）
        width = target_bbox[2] - target_bbox[0]
        height = target_bbox[3] - target_bbox[1]
        config = element_size_config.get(target_element, element_size_config["default"])
        
        # 根据配置类型判断宽高是否符合要求
        if config["type"] == "range":
            # 范围判断：min <= value <= max
            is_approx_size = config["width_range"][0] <= width <= config["width_range"][1] and \
                            config["height_range"][0] <= height <= config["height_range"][1]
        elif config["type"] == "tolerance":
            # 公差判断：abs(value - target) <= tolerance
            is_approx_size = abs(width - config["width_target"]) <= config["width_tolerance"] and \
                            abs(height - config["height_target"]) <= config["height_tolerance"]
        else:
            # 默认使用范围判断
            is_approx_size = 220 <= width <= 300 and 220 <= height <= 300
        
        # 计算位置关系
        x_diff = target_center_x - self_center_x
        
        # 检查宽度和高度是否符合要求（分开判断）
        if config["type"] == "range":
            is_width_ok = config["width_range"][0] <= width <= config["width_range"][1]
            is_height_ok = config["height_range"][0] <= height <= config["height_range"][1]
        elif config["type"] == "tolerance":
            is_width_ok = abs(width - config["width_target"]) <= config["width_tolerance"]
            is_height_ok = abs(height - config["height_target"]) <= config["height_tolerance"]
        else:
            is_width_ok = 220 <= width <= 300
            is_height_ok = 220 <= height <= 300
        
        # 只在特定条件下测试q/e键效果：
        # 1. 正对着（x差值在许可范围，绝对值小于150px）
        # 2. 高符合要求但宽不符合要求
        should_test_qe = abs(x_diff) < 150 and is_height_ok and not is_width_ok
        
        # 检查是否应该使用ad键
        temp_should_use_ad = should_use_ad_keys(target_element, target_bbox, x_diff)
        # 调整should_test_qe：当高符合要求但宽不符合要求时，不使用ad键，应该使用qe键
        should_test_qe = should_test_qe and not temp_should_use_ad
        
        if should_test_qe:
            print("调试信息：满足条件，测试q/e键效果...")
            best_key = test_qe_effect(target_element, target_bbox)
            if best_key:
                print(f"调试信息：执行测试后选择的按键：{best_key}")
                if best_key == 'q':
                    ck.keyboard_q_hold_release(0.02)
                else:
                    ck.keyboard_e_hold_release(0.02)
                time.sleep(0.5)
                # 重新检测元素
                retry_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                if retry_result.get("success", False):
                    retry_predictions = retry_result.get("predictions", [])
                    new_target_bboxes = [pred.get("bbox") for pred in retry_predictions 
                                       if pred.get("class_name") == target_element and pred.get("bbox")]
                    if new_target_bboxes:
                        new_target_bbox = new_target_bboxes[0]
                        new_width = new_target_bbox[2] - new_target_bbox[0]
                        new_height = new_target_bbox[3] - new_target_bbox[1]
                        print(f"调试信息：重新检测后宽高：{new_width:.2f}x{new_height:.2f}")
                        # 更新宽高和判断结果
                        width, height = new_width, new_height
                        if config["type"] == "range":
                            is_approx_size = config["width_range"][0] <= width <= config["width_range"][1] and \
                                            config["height_range"][0] <= height <= config["height_range"][1]
                        elif config["type"] == "tolerance":
                            is_approx_size = abs(width - config["width_target"]) <= config["width_tolerance"] and \
                                            abs(height - config["height_target"]) <= config["height_tolerance"]
                        else:
                            is_approx_size = 220 <= width <= 300 and 220 <= height <= 300
                        print(f"调试信息：重新检测后宽高是否符合要求：{is_approx_size}")
        
        size_text = config["size_text"]
        
        # 检查是否满足结束条件：位置差距±100px且面积基本不变且宽高符合要求
        if (center_diff_x <= 100 and center_diff_y <= 100 and 
            prev_target_area is not None and prev_self_area is not None and 
            abs(target_area - prev_target_area) < 500 and 
            abs(self_area - prev_self_area) < 500 and
            is_approx_size):
            return True, target_element
        
        # 更新上一次的面积和位置
        prev_target_area = target_area
        prev_self_area = self_area
        prev_target_center = (target_center_x, target_center_y)
        prev_self_center = (self_center_x, self_center_y)
        
        # 计算位置关系
        # x_diff = target_center_x - self_center_x  # 已在前面计算
        target_width = target_bbox[2] - target_bbox[0]
        target_height = target_bbox[3] - target_bbox[1]
        
        print(f"\n调试信息：迭代 {iteration}")
        print(f"调试信息：目标元素 {target_element} 中心点：({target_center_x:.2f}, {target_center_y:.2f})")
        print(f"调试信息：self元素中心点：({self_center_x:.2f}, {self_center_y:.2f})")
        print(f"调试信息：X轴差值：{x_diff:.2f}，位置关系判断阈值：±30px")
        print(f"调试信息：目标元素宽高：{target_width:.2f}x{target_height:.2f}")
        print(f"调试信息：宽高是否符合要求：{is_approx_size} ({size_text})")
        
        # 检查是否满足结束条件：正对着且宽高符合要求
        is_facing = abs(x_diff) <= 150
        
        # 两次检测机制：只有两次都满足条件才执行r键
        if is_facing and is_approx_size:
            print(f"调试信息：第一次检测满足条件：正对着且宽高近似{size_text}")
            # 等待0.5秒后进行第二次检测
            time.sleep(0.5)
            # 第二次检测
            second_check_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
            if second_check_result.get("success", False):
                second_predictions = second_check_result.get("predictions", [])
                # 检查第二次检测是否仍有目标元素和self元素
                second_target_bboxes = [pred.get("bbox") for pred in second_predictions 
                                      if pred.get("class_name") == target_element and pred.get("bbox")]
                second_self_elements = [pred.get("bbox") for pred in second_predictions 
                                      if pred.get("class_name") in ["elysia_star"] and pred.get("bbox")]
                if second_target_bboxes and second_self_elements:
                    # 计算第二次检测的位置关系和大小
                    second_target_bbox = second_target_bboxes[0]
                    second_self_bbox = second_self_elements[0]
                    second_target_center = get_center(second_target_bbox)
                    second_self_center = get_center(second_self_bbox)
                    second_x_diff = second_target_center[0] - second_self_center[0]
                    second_is_facing = abs(second_x_diff) <= 150
                    
                    # 计算第二次检测的大小
                    second_width = second_target_bbox[2] - second_target_bbox[0]
                    second_height = second_target_bbox[3] - second_target_bbox[1]
                    second_is_approx_size = config["width_range"][0] <= second_width <= config["width_range"][1] and \
                                         config["height_range"][0] <= second_height <= config["height_range"][1]
                    
                    if second_is_facing and second_is_approx_size:
                        print(f"调试信息：第二次检测也满足条件，执行按键r后结束")
                        ck.keyboard_r_hold_release(0.5)
                    else:
                        print(f"调试信息：第二次检测不满足条件，继续循环")
                        # 重置状态，继续循环
                        prev_target_area = None
                        prev_self_area = None
                        prev_target_center = None
                        prev_self_center = None
                        time.sleep(0.5)
                        continue
                else:
                    print(f"调试信息：第二次检测未找到目标元素或self元素，继续循环")
                    # 重置状态，继续循环
                    prev_target_area = None
                    prev_self_area = None
                    prev_target_center = None
                    prev_self_center = None
                    time.sleep(0.5)
                    continue
            else:
                print(f"调试信息：第二次检测失败，继续循环")
                # 重置状态，继续循环
                prev_target_area = None
                prev_self_area = None
                prev_target_center = None
                prev_self_center = None
                prev_target_element = None
                prev_target_element = None
                time.sleep(0.5)
                continue
            
            # 按下r键后等待1秒
            print("调试信息：按下r键后等待1秒...")
            time.sleep(1)
            
            # 按下r键后，检测三次，x位移明显变化阈值：175px
            success = False
            fail = False
            fail_count = 0
            max_fail_count = 5
            
            # 记录原始位置用于比较
            original_center = (target_center_x, target_center_y)
            
            print("调试信息：按下r键后开始检测，x位移明显变化阈值：175px，最大失败次数：5")
            
            # 第一次检测：三次检测r键效果
            for check in range(3):
                print(f"调试信息：r键后第{check+1}/3次检测...")
                # 短暂等待后重新检测
                time.sleep(0.5)
                check_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                
                if not check_result.get("success", False):
                    fail_count += 1
                    print(f"调试信息：检测失败，当前失败次数：{fail_count}/{max_fail_count}")
                    if fail_count >= max_fail_count:
                        print("调试信息：达到最大失败次数，标记为操作失败")
                        fail = True
                        break
                    continue
                
                check_predictions = check_result.get("predictions", [])
        
                # 检查目标元素是否仍然存在（成功条件1）
                check_target_bboxes = [pred.get("bbox") for pred in check_predictions 
                                     if pred.get("class_name") == target_element and pred.get("bbox")]
                
                # 检查self元素是否存在
                check_self_elements = [pred.get("bbox") for pred in check_predictions 
                                     if pred.get("class_name") in ["elysia_star"] and pred.get("bbox")]
                
                if not check_target_bboxes:
                    if not check_self_elements:
                        print(f"调试信息：r键后第{check+1}次检测发现目标元素和self元素都消失，操作成功")
                    else:
                        print(f"调试信息：r键后第{check+1}次检测发现目标元素消失，操作成功")
                    success = True
                    break
                
                # 计算当前位置与原始位置的x位移（失败条件：x位移明显变化>175px）
                check_target_bbox = check_target_bboxes[0]
                check_center_x, check_center_y = get_center(check_target_bbox)
                check_x_diff = abs(check_center_x - original_center[0])
                check_y_diff = abs(check_center_y - original_center[1])  # 保留y位移用于调试
                
                # 检查self元素是否存在（失败条件：检测到self元素）
                check_self_elements = [pred.get("bbox") for pred in check_predictions 
                                     if pred.get("class_name") in ["elysia_star"] and pred.get("bbox")]
                
                print(f"调试信息：r键后第{check+1}次检测 - x位移：{check_x_diff:.2f}px, y位移：{check_y_diff:.2f}px, elysia_star存在：{bool(check_self_elements)}")
                
                # 如果x位移发生明显变化且检测到self元素，标记为失败
                if check_x_diff > 175 and check_self_elements:
                    print(f"调试信息：r键后第{check+1}次检测发现x位移明显变化（>175px）且elysia_star存在，操作失败")
                    # 添加按下q键0.01s的操作，用于凸显位置变化
                    print("调试信息：添加按下q键0.01s的操作，用于凸显位置变化")
                    ck.keyboard_q_hold_release(0.01)
                    fail = True
                    break
            
            # 如果r键检测失败，不再执行后续操作
            if fail:
                print("调试信息：r键检测失败，继续执行to_there函数")
                # 添加按下s键0.5s的操作，用于离开模糊的位置地带
                print("调试信息：添加按下s键0.5s的操作，用于离开模糊的位置地带")
                ck.keyboard_s_hold_release(0.5)
                # 如果目标元素是keyin，增加失效次数
                if target_element == "keyin":
                    keyin_target_fail_count += 1
                    print(f"调试信息：keyin目标失效次数增加到：{keyin_target_fail_count}")
                # 重置上一次的状态，继续循环
                prev_target_area = None
                prev_self_area = None
                prev_target_center = None
                prev_self_center = None
                prev_target_element = None
                time.sleep(0.5)
                continue
            
            # 如果r键检测成功且未达到成功条件，执行e键尝试（最多两次）
            if not success:
                print("调试信息：r键检测未发现明显变化，开始执行e键尝试（最多2次）")
                
                for e_attempt in range(2):
                    print(f"调试信息：e键尝试 {e_attempt+1}/2...")
                    
                    # 按下e键
                    ck.keyboard_e_press_release()
                    time.sleep(0.5)
                    
                    # 检测按下e键后的状态
                    e_check_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                    if not e_check_result.get("success", False):
                        continue
                    
                    e_predictions = e_check_result.get("predictions", [])
                    
                    # 检查目标元素是否仍然存在（成功条件1）
                    e_target_bboxes = [pred.get("bbox") for pred in e_predictions 
                                     if pred.get("class_name") == target_element and pred.get("bbox")]
                    
                    if not e_target_bboxes:
                        print(f"调试信息：e键尝试{str(e_attempt+1)}发现目标元素消失，操作成功")
                        success = True
                        break
                    
                    # 计算e键后位置与原始位置的x位移（成功条件：x位移无明显变化≤50px）
                    e_target_bbox = e_target_bboxes[0]
                    e_center_x, e_center_y = get_center(e_target_bbox)
                    e_x_diff = abs(e_center_x - original_center[0])
                    e_y_diff = abs(e_center_y - original_center[1])  # 保留y位移用于调试
                    
                    print(f"调试信息：e键尝试{str(e_attempt+1)} - x位移：{e_x_diff:.2f}px, y位移：{e_y_diff:.2f}px")
                    
                    if e_x_diff <= 50:
                        print(f"调试信息：e键尝试{str(e_attempt+1)}发现x位移无明显变化（≤50px），操作成功")
                        success = True
                        break
                    else:
                        print(f"调试信息：e键尝试{str(e_attempt+1)}发现x位移明显变化（>50px），操作失败")
                        # 不立即退出，继续尝试第二次
            
            if success:
                print("调试信息：操作成功，结束to_there函数")
                # 如果目标元素是keyin，重置失效次数
                if target_element == "keyin":
                    keyin_target_fail_count = 0
                    print(f"调试信息：keyin目标操作成功，重置失效次数为：{keyin_target_fail_count}")
                return True, target_element
            else:
                print("调试信息：e键尝试全部失败，开始重新进行r键检测")
                # 修改为重新进行r键检测，最大重试2次
                retry_count = 0
                max_retry = 2
                
                while retry_count < max_retry:
                    retry_count += 1
                    print(f"调试信息：重新进行r键检测，第{retry_count}/{max_retry}次")
                    
                    # 重新按下r键
                    print("调试信息：重新按下r键...")
                    ck.keyboard_r_hold_release(0.5)
                    time.sleep(1)
                    
                    # 重新检测r键效果
                    retry_success = False
                    retry_fail = False
                    
                    for check in range(3):
                        print(f"调试信息：重试r键后第{check+1}/3次检测...")
                        time.sleep(0.5)
                        retry_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                        
                        if not retry_result.get("success", False):
                            continue
                        
                        retry_predictions = retry_result.get("predictions", [])
                        
                        # 检查目标元素是否仍然存在
                        retry_target_bboxes = [pred.get("bbox") for pred in retry_predictions 
                                             if pred.get("class_name") == target_element and pred.get("bbox")]
                        
                        if not retry_target_bboxes:
                            print(f"调试信息：重试r键后第{check+1}次检测发现目标元素消失，操作成功")
                            retry_success = True
                            break
                        
                        # 计算当前位置与原始位置的x位移
                        retry_target_bbox = retry_target_bboxes[0]
                        retry_center_x, retry_center_y = get_center(retry_target_bbox)
                        retry_x_diff = abs(retry_center_x - original_center[0])
                        retry_y_diff = abs(retry_center_y - original_center[1])  # 保留y位移用于调试
                        
                        # 检查self元素是否存在
                        retry_self_elements = [pred.get("bbox") for pred in retry_predictions 
                                             if pred.get("class_name") in ["elysia_star"] and pred.get("bbox")]
                        
                        print(f"调试信息：重试r键后第{check+1}次检测 - x位移：{retry_x_diff:.2f}px, y位移：{retry_y_diff:.2f}px, elysia_star存在：{bool(retry_self_elements)}")
                        
                        # 如果x位移发生明显变化且检测到self元素，标记为失败
                        if retry_x_diff > 175 and retry_self_elements:
                            print(f"调试信息：重试r键后第{check+1}次检测发现x位移明显变化（>175px）且elysia_star存在，操作失败")
                            # 添加按下q键0.01s的操作
                            print("调试信息：添加按下q键0.01s的操作，用于凸显位置变化")
                            ck.keyboard_q_hold_release(0.01)
                            retry_fail = True
                            break
                    
                    if retry_success:
                        print("调试信息：重试r键操作成功，结束to_there函数")
                        # 如果目标元素是keyin，重置失效次数
                        if target_element == "keyin":
                            keyin_target_fail_count = 0
                            print(f"调试信息：keyin目标操作成功，重置失效次数为：{keyin_target_fail_count}")
                        return True, target_element
                    elif retry_fail:
                        print("调试信息：重试r键操作失败，继续下一次重试")
                        # 添加按下s键0.5s的操作
                        print("调试信息：添加按下s键0.5s的操作，用于离开模糊的位置地带")
                        ck.keyboard_s_hold_release(0.5)
                        time.sleep(0.5)
                    else:
                        print("调试信息：重试r键操作无明显变化，继续下一次重试")
                        time.sleep(0.5)
                
                # 所有重试都失败，进行最后的保险检测：检查self元素是否存在
                print("调试信息：进行最后的保险检测，检查self元素是否存在...")
                final_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                
                if final_result.get("success", False):
                    final_predictions = final_result.get("predictions", [])
                    final_self_elements = [pred.get("bbox") for pred in final_predictions 
                                         if pred.get("class_name") in ["elysia_star"] and pred.get("bbox")]
                    
                    if not final_self_elements:
                        print("调试信息：保险检测发现self元素不存在，认为操作成功")
                        # 如果目标元素是keyin，重置失效次数
                        if target_element == "keyin":
                            keyin_target_fail_count = 0
                            print(f"调试信息：keyin目标操作成功，重置失效次数为：{keyin_target_fail_count}")
                        return True, target_element
                
                # 保险检测未通过，继续执行to_there函数
                print("调试信息：所有r键重试都失败，继续执行to_there函数")
                # 如果目标元素是keyin，增加失效次数
                if target_element == "keyin":
                    keyin_target_fail_count += 1
                    print(f"调试信息：keyin目标失效次数增加到：{keyin_target_fail_count}")
                # 重置上一次的状态，继续循环
                prev_target_area = None
                prev_self_area = None
                prev_target_center = None
                prev_self_center = None
                prev_target_element = None
                time.sleep(0.5)
                continue
        
        # 根据距离动态调整按键时间，距离越远，按键时间越长，但不超过0.1秒
        # 基础按键时间0.02秒，根据距离动态调整
        base_time = 0.02
        max_time = 0.08
        # 根据X轴差值计算按键时间，差值越大，按键时间越长
        abs_diff = abs(x_diff)
        if abs_diff < 100:
            press_time = base_time
        elif abs_diff < 150:
            press_time = base_time * 1.5  # 减小旋转角度
        elif abs_diff < 300:
            press_time = base_time * 2    # 进一步减小旋转角度
        else:
            press_time = max_time
        
        print(f"调试信息：X轴差值绝对值：{abs_diff:.2f}，计算得到按键时间：{press_time:.3f}秒")
        
        # 1. 左：self元素在目标元素的左方
        if x_diff > 100:
            print(f"调试信息：self元素在目标元素的左方，x_diff = {x_diff:.2f} > 100")
            should_use_ad = should_use_ad_keys(target_element, target_bbox, x_diff)
            
            # 计算当前边界框的宽高比，用于调试
            x1, y1, x2, y2 = target_bbox
            width = x2 - x1
            height = y2 - y1
            current_ratio = width / height if height != 0 else 0
            
            # 获取元素的宽高标准配置，用于调试
            config = element_size_config.get(target_element, element_size_config["default"])
            
            # 计算目标宽高比范围，用于调试（所有元素都是range类型）
            min_width = config["width_range"][0]
            max_width = config["width_range"][1]
            min_height = config["height_range"][0]
            max_height = config["height_range"][1]
            min_ratio = min_width / max_height if max_height != 0 else 0
            max_ratio = max_width / min_height if min_height != 0 else float('inf')
            ratio_info = f"目标宽高比范围：{min_ratio:.2f}-{max_ratio:.2f}"
            
            print(f"调试信息：元素 {target_element} - 当前宽高比：{current_ratio:.2f}")
            print(f"调试信息：{ratio_info}")
            print(f"调试信息：是否使用ad键（左右移动）：{should_use_ad}")
            print(f"调试信息：当前旋转次数：{rotation_count}/{max_rotations}")
            
            # 检查是否已达到最大旋转次数
            if not should_use_ad and rotation_count < max_rotations:
                print(f"调试信息：执行操作：按键e（视角右转）持续{press_time:.3f}秒")
                ck.keyboard_e_hold_release(press_time)
                # 视角旋转，不记录ad键
                last_ad_key = None
                # 增加旋转次数
                rotation_count += 1
            else:
                # 达到最大旋转次数或应该使用ad键，改用ad键移动
                print(f"调试信息：执行操作：按键d（向右移动）持续{press_time:.3f}秒")
                ck.keyboard_d_hold_release(press_time)
                # 记录按下d键
                last_ad_key = 'd'
                # 重置旋转次数
                rotation_count = 0
        # 2. 右：self元素在目标元素的右方
        elif x_diff < -100:
            print(f"调试信息：self元素在目标元素的右方，x_diff = {x_diff:.2f} < -100")
            should_use_ad = should_use_ad_keys(target_element, target_bbox, x_diff)
            
            # 计算当前边界框的宽高比，用于调试
            x1, y1, x2, y2 = target_bbox
            width = x2 - x1
            height = y2 - y1
            current_ratio = width / height if height != 0 else 0
            
            # 获取元素的宽高标准配置，用于调试
            config = element_size_config.get(target_element, element_size_config["default"])
            
            # 计算目标宽高比范围，用于调试（所有元素都是range类型）
            min_width = config["width_range"][0]
            max_width = config["width_range"][1]
            min_height = config["height_range"][0]
            max_height = config["height_range"][1]
            min_ratio = min_width / max_height if max_height != 0 else 0
            max_ratio = max_width / min_height if min_height != 0 else float('inf')
            ratio_info = f"目标宽高比范围：{min_ratio:.2f}-{max_ratio:.2f}"
            
            print(f"调试信息：元素 {target_element} - 当前宽高比：{current_ratio:.2f}")
            print(f"调试信息：{ratio_info}")
            print(f"调试信息：是否使用ad键（左右移动）：{should_use_ad}")
            print(f"调试信息：当前旋转次数：{rotation_count}/{max_rotations}")
            
            # 检查是否已达到最大旋转次数
            if not should_use_ad and rotation_count < max_rotations:
                print(f"调试信息：执行操作：按键q（视角左转）持续{press_time:.3f}秒")
                ck.keyboard_q_hold_release(press_time)
                # 视角旋转，不记录ad键
                last_ad_key = None
                # 增加旋转次数
                rotation_count += 1
            else:
                # 达到最大旋转次数或应该使用ad键，改用ad键移动
                print(f"调试信息：执行操作：按键a（向左移动）持续{press_time:.3f}秒")
                ck.keyboard_a_hold_release(press_time)
                # 记录按下a键
                last_ad_key = 'a'
                # 重置旋转次数
                rotation_count = 0
        # 3. 正对着但宽高不符合要求
        else:
            print(f"调试信息：self元素与目标元素正对着，x_diff = {x_diff:.2f} 在±100px范围内")
            print(f"调试信息：目标元素宽高是否符合要求：{is_approx_size}")
            
            # 获取元素的前后移动配置（使用全局配置字典）
            width = target_bbox[2] - target_bbox[0]
            height = target_bbox[3] - target_bbox[1]
            movement_config = element_movement_config.get(target_element, element_movement_config["default"])
            
            # 根据配置执行前后移动操作
            if width < movement_config["forward_threshold"][0] and height < movement_config["forward_threshold"][1]:
                print(f"调试信息：目标元素宽高({width:.2f}x{height:.2f}) < {movement_config['forward_threshold'][0]}px×{movement_config['forward_threshold'][1]}px，执行操作：按键w持续{press_time:.3f}秒")
                ck.keyboard_w_hold_release(press_time)
            elif width > movement_config["backward_threshold"][0] and height > movement_config["backward_threshold"][1]:
                print(f"调试信息：目标元素宽高({width:.2f}x{height:.2f}) > {movement_config['backward_threshold'][0]}px×{movement_config['backward_threshold'][1]}px，执行操作：按键s持续{press_time:.3f}秒")
                ck.keyboard_s_hold_release(press_time)
            # 否则：宽高在合理范围内，不执行操作
        
        # 等待一段时间后再次检测
        time.sleep(0.5)
    
    # 达到最大迭代次数，返回错误状态
    print(f"调试信息：达到最大迭代次数 {max_iterations}，返回错误状态")
    return False, "最大迭代次数错误"


def find_elements(last_target=None):
    """
    查找崩坏3窗口中的所有元素，并根据检测结果执行相应操作
    
    函数流程：
    1. 对BH3窗口进行截图并使用YOLO模型进行元素检测
    2. 检查检测结果是否成功
    3. 根据检测到的元素类型执行不同的操作
    
    变量说明：
    - last_target: 上一次的目标元素，用于避免重复处理 shangdian_open
    - result: YOLO模型的检测结果
    - predictions: 检测到的元素预测结果列表
    - detected_elements: 检测到的元素类型集合
    
    情况处理：
    1. 情况1：包含特定元素（shangdian、keyin、shangdian_open、BOSS）
       - 检查上一次的返回值是否为 shangdian_open，如果是，则这次不将 shangdian_open 作为目标元素
       - 计算检测到的元素与特定元素的交集
       - 处理第一个匹配的元素，调用 to_there 函数移动到该元素位置
       - 返回处理结果，格式为 "已处理{target_element}"
    
    2. 情况2：包含多种特定元素（aomie、zhenwo、kongmeng、jielv、luoxuan、tianhui、fanxing、wuxian、chana、huangjin、jiushi、xvguang、fusheng）
       - 计算检测到的元素与多种特定元素的交集
       - 读取 keyin_detail.json 文件，获取各元素的权重
       - 比较各元素的权重，选择权重最大的元素
       - 检查 letu_reset_weight 是否大于最大元素权重
       - 如果是，执行按键u重置，重新检测
       - 否则，调用 to_there 函数移动到该元素位置
       - 返回该元素名称
    
    3. 情况3：只有self类型元素（elysia_star）
       - 进入重试逻辑，最多尝试8次常规重试
       - 每次重试执行按键e持续0.47秒，尝试检测其他元素
       - 如果检测到其他元素，进入元素数量变化检测逻辑：
         * 按下e键直到元素数量不再增加
         * 元素数量减少或不变时，按下q键
         * 使用最多元素时的预测结果或当前预测结果
         * 检测final_predictions中的元素，进入to_there函数处理
         * 如果没有匹配的元素，返回 "无匹配情况"
       - 第8次重试后，尝试按下w键0.5秒，再次检测
       - 如果仍只检测到self元素，开始4次转换尝试：
         * 每次转换尝试执行按键e持续0.5秒，尝试检测其他元素
         * 如果检测到其他元素，进入元素数量变化检测逻辑
       - 如果转换4次后仍只检测到self元素，退出程序
    
    4. 其他情况：
       - 返回 "无匹配情况"
    
    Args:
        last_target (str, optional): 上一次的目标元素，默认为 None
    
    Returns:
        str: 执行结果或目标元素名称
            - "检测失败": 元素检测失败
            - "{target_element}": 处理特定元素成功，返回to_there函数的最终目标元素
            - "无匹配情况": 没有匹配的元素
    """
    # 对BH3窗口进行截图并使用YOLO模型进行元素检测
    result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
    
    if not result.get("success", False):
        return "检测失败"
    
    predictions = result.get("predictions", [])
    detected_elements = {pred.get("class_name", "") for pred in predictions}
    
    # 检查是否检测到怪物UI（guaiwu_xueliang_UI），如果检测到，认为战斗未结束，返回特殊值
    if 'guaiwu_xueliang_UI' in detected_elements:
        print("\n调试信息：检测到怪物UI（guaiwu_xueliang_UI），认为战斗未结束")
        return "战斗未结束，检测到怪物UI"
    
    # 情况1：包含特定元素
    case1_elements = {'shangdian', 'keyin', 'shangdian_open'}
    
    # 只有当last_target为shangdian_open时，才将BOSS作为目标元素
    if last_target == "shangdian_open" or "已处理shangdian_open" in str(last_target):
        case1_elements.add('BOSS')
        case1_elements = case1_elements - {'shangdian_open'}
        print("\n调试信息：上一次的返回值是 shangdian_open，本次BOSS可作为目标元素，不将 shangdian_open 作为目标元素")
    
    case1_match = detected_elements.intersection(case1_elements)
    
    if case1_match:
            # 处理第一个匹配的元素
            target_element = case1_match.pop()
            print(f"\n调试信息：检测到特定元素: {target_element}，调用to_there函数处理")
            success, final_target = to_there(target_element, predictions, last_target=last_target)
            print(f"调试信息：to_there函数返回：success={success}, final_target={final_target}")
            return final_target
    
    # 情况2：包含多种特定元素
    case2_elements = {'aomie', 'zhenwo', 'kongmeng', 'jielv', 'luoxuan', 'tianhui', 'fanxing', 
                     'wuxian', 'chana', 'huangjin', 'jiushi', 'xvguang', 'fusheng'}
    case2_match = detected_elements.intersection(case2_elements)
    
    if case2_match:
        
        
        # 读取keyin_detail.json文件
        keyin_detail_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")
        with open(keyin_detail_path, "r", encoding="utf-8") as f:
            keyin_detail = json.load(f)
        
        # 比较weight和letu_reset_weight
        max_score = -1
        max_element = None
        letu_reset_weight = keyin_detail.get("letu_reset_weight", 0)
        
        print(f"\n调试信息：检测到多种特定元素: {list(case2_match)}")
        print(f"调试信息：letu_reset_weight = {letu_reset_weight}")
        
        # 初始化连续出现次数字典（从to_there函数的continuous_element_count获取）
        # 由于continuous_element_count在to_there函数中维护，这里我们需要从元素缓存中获取
        # 注意：这里的连续出现次数是基于相邻yolo识别的计数，上限为2
        consecutive_counts = {}
        for elem in case2_match:
            # 初始化为1，因为至少出现了一次
            consecutive_counts[elem] = 1
        
        # 计算所有元素连续出现次数的最大值
        max_consecutive_count = 1
        for elem, count in consecutive_counts.items():
            if count > max_consecutive_count:
                max_consecutive_count = count
        
        # 计算每个元素的得分
        for elem in case2_match:
            # 获取元素权重
            weight = keyin_detail.get(f"{elem}_weight", 0)
            # 连续出现次数
            consecutive_count = consecutive_counts[elem]
            # 计算得分：(1 / max_consecutive_count) * 权重 * 连续出现次数
            score = (1 / max_consecutive_count) * weight * consecutive_count
            print(f"调试信息：元素 {elem} 的权重 = {weight}，连续出现次数 = {consecutive_count}，max_consecutive_count = {max_consecutive_count}，得分 = {score:.4f}")
            if score > max_score:
                max_score = score
                max_element = elem
        
        print(f"调试信息：选定的最大得分元素是 {max_element}，得分为 {max_score:.4f}")
        
        if letu_reset_weight > max_score:
            # 模拟按键u一次，重新检测

            print(f"调试信息：letu_reset_weight({letu_reset_weight}) > 最大元素得分({max_score:.4f})，执行按键u重置")
            ck.keyboard_u_press_release()
            time.sleep(2)
            # 更新letu_reset_count
            current_reset_count = keyin_detail.get("letu_reset_count", 0)
            new_reset_count = current_reset_count + 1
            keyin_detail["letu_reset_count"] = new_reset_count
            # 更新letu_reset_weight，3次过后权重为0
            if new_reset_count >= 3:
                keyin_detail["letu_reset_weight"] = 0
                print(f"调试信息：letu_reset_count达到{new_reset_count}次，重置letu_reset_weight为0")
            else:
                # 保持权重为0.5，与letu_elysia_star中的逻辑一致
                keyin_detail["letu_reset_weight"] = 0.5
                print(f"调试信息：letu_reset_count为{new_reset_count}次，letu_reset_weight保持为0.5")
            # 保存更新后的权重配置
            with open(keyin_detail_path, "w", encoding="utf-8") as f:
                json.dump(keyin_detail, f, ensure_ascii=False, indent=4)
            return find_elements(last_target=last_target)
        else:
            # 使用to_there函数
            if max_element:
                print(f"调试信息：执行to_there函数，目标元素为 {max_element}")
                success, final_target = to_there(max_element, predictions, last_target=last_target)
                print(f"调试信息：to_there函数返回：success={success}, final_target={final_target}")
                
                # 连续出现次数逻辑已修改：现在每次find_elements调用都是新的开始，不再需要更新连续出现次数
                
                return final_target
    
    # 情况3：只有self类型元素
    # 定义表示"我"的元素类型列表
    self_elements = ["elysia_star"]
    if detected_elements.issubset(set(self_elements)):

        
        retry_count = 0
        max_retries = 8  # 前8次常规重试
        transform_count = 0
        max_transforms = 4  # 转换次数限制
        
        print(f"\n调试信息：只检测到self类型元素，进入重试逻辑，最大重试次数：{max_retries}")
        
        while retry_count < max_retries:
            retry_count += 1
            print(f"调试信息：重试 {retry_count}/{max_retries}，执行操作：按键e持续0.47秒")
            ck.keyboard_e_hold_release(0.47)
            time.sleep(0.5)
            
            # 重新检测
            result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
            if not result.get("success", False):
                continue
            
            predictions = result.get("predictions", [])
            detected_elements = {pred.get("class_name", "") for pred in predictions}
            
            if not detected_elements.issubset(set(self_elements)):
                print("\n调试信息：检测到其他元素，进入元素数量变化检测逻辑")
                
                # 检测元素数量变化
                prev_element_count = len(predictions)
                prev_predictions = predictions  # 初始化prev_predictions
                element_count_increasing = True
                
                while element_count_increasing:
                    # 按下e键
                    print(f"调试信息：当前元素数量{prev_element_count}，按下e键继续寻找...")
                    ck.keyboard_e_hold_release(0.5)
                    time.sleep(0.5)
                    
                    # 重新检测
                    new_result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                    if not new_result.get("success", False):
                        continue
                    
                    new_predictions = new_result.get("predictions", [])
                    new_element_count = len(new_predictions)
                    
                    print(f"调试信息：新元素数量{new_element_count}")
                    
                    if new_element_count > prev_element_count:
                        # 元素数量增加，继续按下e键
                        prev_element_count = new_element_count
                        prev_predictions = new_predictions
                    elif new_element_count < prev_element_count:
                        # 元素数量减少，按下q键
                        print(f"调试信息：元素数量从{prev_element_count}减少到{new_element_count}，按下q键")
                        ck.keyboard_q_hold_release(0.5)
                        element_count_increasing = False
                        
                        # 使用最多元素时的预测结果
                        final_predictions = prev_predictions
                    else:
                        # 元素数量不变，按下q键
                        print(f"调试信息：元素数量保持{prev_element_count}不变，按下q键")
                        ck.keyboard_q_hold_release(0.5)
                        element_count_increasing = False
                        
                        # 使用当前预测结果
                        final_predictions = new_predictions
                
                # 检测final_predictions中的元素，进入to_there函数
                final_detected_elements = {pred.get("class_name", "") for pred in final_predictions}
                
                # 情况1：包含特定元素
                case1_elements = {'shangdian', 'keyin', 'shangdian_open'}
                
                # 只有当last_target为shangdian_open时，才将BOSS作为目标元素
                if last_target == "shangdian_open" or "已处理shangdian_open" in str(last_target):
                    case1_elements.add('BOSS')
                    case1_elements = case1_elements - {'shangdian_open'}
                    print("\n调试信息：上一次的返回值是 shangdian_open，本次BOSS可作为目标元素，不将 shangdian_open 作为目标元素")
                
                case1_match = final_detected_elements.intersection(case1_elements)
                
                if case1_match:
                    target_element = case1_match.pop()
                    print(f"\n调试信息：检测到特定元素: {target_element}，调用to_there函数处理")
                    success, final_target = to_there(target_element, final_predictions, last_target=last_target)
                    print(f"调试信息：to_there函数返回：success={success}, final_target={final_target}")
                    return final_target
                
                # 情况2：包含多种特定元素
                case2_elements = {'aomie', 'zhenwo', 'kongmeng', 'jielv', 'luoxuan', 'tianhui', 'fanxing', 
                                 'wuxian', 'chana', 'huangjin', 'jiushi', 'xvguang', 'fusheng'}
                case2_match = final_detected_elements.intersection(case2_elements)
                
                if case2_match:
                    
                    
                    # 读取keyin_detail.json文件
                    keyin_detail_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")
                    with open(keyin_detail_path, "r", encoding="utf-8") as f:
                        keyin_detail = json.load(f)
                    
                    # 比较score和letu_reset_weight
                    max_score = -1
                    max_element = None
                    letu_reset_weight = keyin_detail.get("letu_reset_weight", 0)
                    
                    # 初始化连续出现次数字典（从to_there函数的continuous_element_count获取）
                    # 由于continuous_element_count在to_there函数中维护，这里我们需要从元素缓存中获取
                    # 注意：这里的连续出现次数是基于相邻yolo识别的计数，上限为2
                    consecutive_counts = {}
                    for elem in case2_match:
                        # 初始化为1，因为至少出现了一次
                        consecutive_counts[elem] = 1
                    
                    # 计算所有元素连续出现次数的最大值
                    max_consecutive_count = 1
                    for elem, count in consecutive_counts.items():
                        if count > max_consecutive_count:
                            max_consecutive_count = count
                    
                    # 计算每个元素的得分
                    for elem in case2_match:
                        # 获取元素权重
                        weight = keyin_detail.get(f"{elem}_weight", 0)
                        # 连续出现次数
                        consecutive_count = consecutive_counts[elem]
                        # 计算得分：(1 / max_consecutive_count) * 权重 * 连续出现次数
                        score = (1 / max_consecutive_count) * weight * consecutive_count
                        print(f"调试信息：元素 {elem} 的权重 = {weight}，连续出现次数 = {consecutive_count}，max_consecutive_count = {max_consecutive_count}，得分 = {score:.4f}")
                        if score > max_score:
                            max_score = score
                            max_element = elem
                    
                    print(f"调试信息：选定的最大得分元素是 {max_element}，得分为 {max_score:.4f}")
                    
                    if letu_reset_weight > max_score:
                        # 模拟按键u一次，重新检测
                        print(f"调试信息：letu_reset_weight({letu_reset_weight}) > 最大元素得分({max_score:.4f})，执行按键u重置")
                        ck.keyboard_u_press_release()
                        time.sleep(2)
                        # 更新letu_reset_count
                        current_reset_count = keyin_detail.get("letu_reset_count", 0)
                        new_reset_count = current_reset_count + 1
                        keyin_detail["letu_reset_count"] = new_reset_count
                        # 更新letu_reset_weight，3次过后权重为0
                        if new_reset_count >= 3:
                            keyin_detail["letu_reset_weight"] = 0
                            print(f"调试信息：letu_reset_count达到{new_reset_count}次，重置letu_reset_weight为0")
                        else:
                            # 保持权重为0.5，与letu_elysia_star中的逻辑一致
                            keyin_detail["letu_reset_weight"] = 0.5
                            print(f"调试信息：letu_reset_count为{new_reset_count}次，letu_reset_weight保持为0.5")
                        # 保存更新后的权重配置
                        with open(keyin_detail_path, "w", encoding="utf-8") as f:
                            json.dump(keyin_detail, f, ensure_ascii=False, indent=4)
                        return find_elements(last_target=last_target)
                    else:
                        # 使用to_there函数
                        if max_element:
                            print(f"\n调试信息：执行to_there函数，目标元素为 {max_element}")
                            success, final_target = to_there(max_element, final_predictions, last_target=last_target)
                            print(f"调试信息：to_there函数返回：success={success}, final_target={final_target}")
                            
                            # 连续出现次数逻辑已修改：现在每次find_elements调用都是新的开始，不再需要更新连续出现次数
                            
                            return final_target
                
                # 如果没有匹配的元素，按下w和a键30秒，持续检测元素
                
                print("\n调试信息：没有匹配的元素，开始按下w和a键30秒，持续检测元素...")
                
                stop_event = threading.Event()
                shared_state = {'detected': False}
                
                def hold_key_with_ck(key, stop_event):
                    try:
                        # 使用ck库的pyautogui模块持续按住按键
                        # 这里使用ck.pyautogui而不是直接import pyautogui，确保使用ck库的内容
                        ck.pyautogui.keyDown(key)
                        print(f"调试信息：开始按住{key}键")
                        # 等待停止事件或超时（由主线程控制）
                        stop_event.wait(timeout=30)
                    finally:
                        ck.pyautogui.keyUp(key)
                        print(f"调试信息：释放{key}键")
                
                def detect_elements(stop_event, shared_state):
                    start_time = time.time()
                    while not stop_event.is_set() and time.time() - start_time < 30:
                        # 检测元素
                        result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
                        if result.get("success", False):
                            predictions = result.get("predictions", [])
                            detected_elements = {pred.get("class_name", "") for pred in predictions}
                            
                            # 定义self元素
                            self_elements = ["elysia_star"]
                            
                            # 如果检测到非self元素，停止并重新处理
                            if not detected_elements.issubset(set(self_elements)):
                                print("\n调试信息：检测到其他元素，停止w和a键，重新处理...")
                                shared_state['detected'] = True
                                stop_event.set()
                                return
                        # 等待0.5秒
                        time.sleep(0.5)
                
                # 创建线程
                w_thread = threading.Thread(target=hold_key_with_ck, args=('w', stop_event))
                a_thread = threading.Thread(target=hold_key_with_ck, args=('a', stop_event))
                detect_thread = threading.Thread(target=detect_elements, args=(stop_event, shared_state))
                
                # 启动线程
                w_thread.start()
                a_thread.start()
                detect_thread.start()
                
                # 等待检测线程完成（最多30秒）
                detect_thread.join(timeout=30)
                
                # 设置停止事件以确保按键线程停止
                stop_event.set()
                
                # 等待按键线程结束
                w_thread.join(timeout=1)
                a_thread.join(timeout=1)
                
                if shared_state['detected']:
                    return find_elements(last_target=last_target)
                
                # 30秒后仍无元素，退出程序
                print("\n调试信息：按下w和a键30秒后仍未检测到其他元素，退出程序")
                return "无匹配情况"
        
        # 第8次重试后，尝试按下w键0.5秒
        print(f"\n调试信息：前{max_retries}次重试失败，尝试按下w键0.5秒")
        ck.keyboard_w_hold_release(0.5)
        time.sleep(0.5)
        
        # 再次检测
        result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
        if result.get("success", False):
            predictions = result.get("predictions", [])
            detected_elements = {pred.get("class_name", "") for pred in predictions}
            
            if not detected_elements.issubset(set(self_elements)):
                print("\n调试信息：按下w键后检测到其他元素，进入元素数量变化检测逻辑")
                return find_elements(last_target=last_target)  # 重新调用find_elements处理
        
        # 尝试转换四次
        print(f"\n调试信息：按下w键后仍只检测到self元素，开始{max_transforms}次转换尝试")
        while transform_count < max_transforms:
            transform_count += 1
            print(f"调试信息：转换尝试 {transform_count}/{max_transforms}，执行操作：按键e持续0.5秒")
            ck.keyboard_e_hold_release(0.5)
            time.sleep(0.5)
            
            # 重新检测
            result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
            if not result.get("success", False):
                continue
            
            predictions = result.get("predictions", [])
            detected_elements = {pred.get("class_name", "") for pred in predictions}
            
            if not detected_elements.issubset(set(self_elements)):
                print("\n调试信息：转换尝试中检测到其他元素，进入元素数量变化检测逻辑")
                return find_elements(last_target=last_target)  # 重新调用find_elements处理
        
        # 转换四次后仍无果，抛出异常
        print(f"\n调试信息：转换{max_transforms}次后仍只检测到self元素，抛出异常")
        error_msg = "错误：多次尝试后仍未检测到其他元素"
        print(error_msg)
        raise Exception(error_msg)
    
    # 如果没有匹配的元素，按下w和a键30秒，持续检测元素
    
    print("\n调试信息：没有匹配的元素，开始按下w和a键30秒，持续检测元素...")
    
    stop_event = threading.Event()
    shared_state = {'detected': False}
    
    def hold_key_with_ck(key, stop_event):
        try:
            # 使用ck库的pyautogui模块持续按住按键
            # 这里使用ck.pyautogui而不是直接import pyautogui，确保使用ck库的内容
            ck.pyautogui.keyDown(key)
            print(f"调试信息：开始按住{key}键")
            # 等待停止事件或超时（由主线程控制）
            stop_event.wait(timeout=30)
        finally:
            ck.pyautogui.keyUp(key)
            print(f"调试信息：释放{key}键")
    
    def detect_elements(stop_event, shared_state):
        start_time = time.time()
        while not stop_event.is_set() and time.time() - start_time < 30:
            # 检测元素
            result = detect_bh3_elements(save_screenshot=False, save_detection_result=False)
            if result.get("success", False):
                predictions = result.get("predictions", [])
                detected_elements = {pred.get("class_name", "") for pred in predictions}
                
                # 定义self元素
                self_elements = ["elysia_star"]
                
                # 如果检测到非self元素，停止并重新处理
                if not detected_elements.issubset(set(self_elements)):
                    print("\n调试信息：检测到其他元素，停止w和a键，重新处理...")
                    shared_state['detected'] = True
                    stop_event.set()
                    return
            # 等待0.5秒
            time.sleep(0.5)
    
    # 创建线程
    w_thread = threading.Thread(target=hold_key_with_ck, args=('w', stop_event))
    a_thread = threading.Thread(target=hold_key_with_ck, args=('a', stop_event))
    detect_thread = threading.Thread(target=detect_elements, args=(stop_event, shared_state))
    
    # 启动线程
    w_thread.start()
    a_thread.start()
    detect_thread.start()
    
    # 等待检测线程完成（最多30秒）
    detect_thread.join(timeout=30)
    
    # 设置停止事件以确保按键线程停止
    stop_event.set()
    
    # 等待按键线程结束
    w_thread.join(timeout=1)
    a_thread.join(timeout=1)
    
    if shared_state['detected']:
        return find_elements(last_target=last_target)
    
    # 30秒后仍无元素，退出程序
    print("\n调试信息：按下w和a键30秒后仍未检测到其他元素，退出程序")
    return "无匹配情况"


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
            
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！")
    
    # 执行find_elements函数进行检测和处理
    print("\n1. 执行find_elements函数：")
    # 设置上一次的返回值为 shangdian_open，这样本次就不会以 shangdian_open 为目标元素
    last_target = "shangdian_open"
    print("调试信息：手动设置上一次的返回值为 shangdian_open，本次不将 shangdian_open 作为目标元素")
    target_element = find_elements(last_target=last_target)
    
    # 输出处理结果
    print(f"\n2. 处理结果：{target_element}")