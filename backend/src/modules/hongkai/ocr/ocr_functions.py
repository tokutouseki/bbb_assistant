import cv2
import numpy as np
import time
import os
import pyautogui
from datetime import datetime
import sys
import socket
import json
import subprocess

from rapidocr_onnxruntime import RapidOCR

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import all_log.save_output
try:
    from ..on_window import focus_bh3_window, run_as_admin, is_admin
except ImportError:
    from on_window import focus_bh3_window, run_as_admin, is_admin

try:
    from ..templates.clicks_keyboard import click_at_position
except ImportError:
    from photos.clicks_keyboard import click_at_position

# 使用用户指定的模型目录
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_dir = os.path.join(current_dir, 'ocr', 'models')

if not os.path.exists(model_dir):
    os.makedirs(model_dir)
    print(f"[{time.strftime('%H:%M:%S')}] 创建目录: {model_dir}")

os.environ['PADDLEX_MODEL_HOME'] = model_dir
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

_ocr_instance = None
_ocr_initialized = False

# OCR服务配置
OCR_SERVER_HOST = '127.0.0.1'
OCR_SERVER_PORT = 5002

# 检查OCR服务是否运行
def check_ocr_service_running():
    """
    检查OCR服务是否在运行
    
    Returns:
        bool: 服务是否运行
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((OCR_SERVER_HOST, OCR_SERVER_PORT))
        s.close()
        return True
    except ConnectionRefusedError:
        return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 检查OCR服务状态时出错: {e}")
        return False

# 启动OCR服务
def start_ocr_service():
    """
    启动OCR服务
    
    Returns:
        bool: 服务是否启动成功
    """
    print(f"[{time.strftime('%H:%M:%S')}] OCR服务未运行，正在启动...")
    
    # 获取启动脚本路径 — 直接启动 ocr_server_final.py
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    start_script = os.path.join(script_dir, 'ocr', 'ocr_server_final.py')
    python_executable = sys.executable
    if not os.path.exists(python_executable):
        python_executable = os.path.join(script_dir, 'Python3.11', 'python.exe')

    if not os.path.exists(start_script):
        print(f"[{time.strftime('%H:%M:%S')}] 启动脚本不存在: {start_script}")
        return False

    if not os.path.exists(python_executable):
        print(f"[{time.strftime('%H:%M:%S')}] Python解释器不存在: {python_executable}")
        return False
    
    try:
        # 启动OCR服务（最小化启动，不置顶）
        cmd_command = f'cmd.exe /c start /MIN "OCR服务" "{python_executable}" "{start_script}"'
        subprocess.Popen(cmd_command, shell=True)
        
        # 等待服务启动
        print(f"[{time.strftime('%H:%M:%S')}] 等待OCR服务启动...")
        time.sleep(5)  # 给服务足够的启动时间
        
        # 检查服务是否启动成功
        if check_ocr_service_running():
            print(f"[{time.strftime('%H:%M:%S')}] ✓ OCR服务启动成功！")
            print(f"[{time.strftime('%H:%M:%S')}] OCR服务正在新的命令行窗口中运行")
            return True
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ OCR服务启动失败")
            return False
            
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 启动OCR服务时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

# 通过OCR服务识别文本
def ocr_using_service(image_path=None, screen_region=None, conf_threshold=0.5, preprocess=False, enhance_contrast=False, denoise=False, threshold=False):
    """
    通过OCR服务识别文本
    
    :param image_path: 图片文件路径
    :param screen_region: 屏幕区域 [x1, y1, x2, y2]
    :param conf_threshold: 置信度阈值
    :param preprocess: 是否预处理
    :param enhance_contrast: 是否增强对比度
    :param denoise: 是否降噪
    :param threshold: 是否二值化
    :return: 识别结果
    """
    try:
        # 创建socket连接
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((OCR_SERVER_HOST, OCR_SERVER_PORT))
        
        # 构建请求
        request = {
            'image_path': image_path,
            'screen_region': screen_region,
            'conf_threshold': conf_threshold,
            'preprocess': preprocess,
            'enhance_contrast': enhance_contrast,
            'denoise': denoise,
            'threshold': threshold
        }
        
        # 发送请求
        request_str = json.dumps(request, ensure_ascii=False) + '\nEOF\n'
        s.sendall(request_str.encode('utf-8'))
        
        # 接收响应
        response_data = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b'\nEOF\n' in response_data:
                break
        
        s.close()
        
        # 解析响应
        response_str = response_data.decode('utf-8').replace('\nEOF\n', '')
        response = json.loads(response_str)
        
        if response.get('success'):
            return response
        else:
            print(f"[{time.strftime('%H:%M:%S')}] OCR服务错误: {response.get('message')}")
            return None
            
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 调用OCR服务时出错: {e}")
        return None

def get_ocr_instance():
    """
    获取OCR实例（懒加载模式）
    只在第一次调用时初始化，避免重复初始化浪费时间
    
    :return: RapidOCR实例
    """
    global _ocr_instance, _ocr_initialized
    
    if _ocr_initialized:
        return _ocr_instance
    
    # 检查OCR服务是否运行
    if not check_ocr_service_running():
        # 启动OCR服务
        if not start_ocr_service():
            print(f"[{time.strftime('%H:%M:%S')}] OCR服务启动失败，使用本地OCR实例")
            # 继续使用本地OCR实例作为后备方案
    else:
        print(f"[{time.strftime('%H:%M:%S')}] OCR服务已在运行，使用服务端处理")
    
    print(f"[{time.strftime('%H:%M:%S')}] 正在初始化RapidOCR（懒加载模式）")
    print(f"[{time.strftime('%H:%M:%S')}] 模型路径: {model_dir}")
    start_time = time.time()
    
    # 使用指定目录中的PP-OCRv4模型文件
    det_model_path = os.path.join(model_dir, 'ch_PP-OCRv4_det_infer.onnx')
    rec_model_path = os.path.join(model_dir, 'ch_PP-OCRv4_rec_infer.onnx')
    cls_model_path = os.path.join(model_dir, 'ch_ppocr_mobile_v2.0_cls_infer.onnx')
    
    print(f"[{time.strftime('%H:%M:%S')}] 检测模型: {det_model_path}")
    print(f"[{time.strftime('%H:%M:%S')}] 识别模型: {rec_model_path}")
    print(f"[{time.strftime('%H:%M:%S')}] 分类模型: {cls_model_path}")
    
    _ocr_instance = RapidOCR(
        det_model_path=det_model_path,  # 使用指定路径的PP-OCRv4检测模型
        rec_model_path=rec_model_path,  # 使用指定路径的PP-OCRv4识别模型
        cls_model_path=cls_model_path,  # 使用指定路径的PP-OCRv4分类模型
        use_angle_cls=True,
        use_text_det=True,
        print_verbose=False
    )
    
    init_time = time.time() - start_time
    print(f"[{time.strftime('%H:%M:%S')}] RapidOCR初始化完成，耗时: {init_time:.2f}秒")
    _ocr_initialized = True
    
    return _ocr_instance

def preprocess_image(image, enhance_contrast=False, denoise=False, threshold=False):
    """
    预处理图像以提高OCR识别准确率
    
    预处理步骤：
    1. 边缘填充：在图像四周添加padding，防止边缘文字被裁切
       - padding大小：宽度的5%，至少20像素
    2. 灰度化：将彩色图像转换为灰度图像
    3. 对比度增强：使用CLAHE（限制对比度自适应直方图均衡化）增强对比度
       - clipLimit: 对比度限制阈值，默认2.0
       - tileGridSize: 网格大小，默认(8, 8)
    4. 降噪：使用非局部均值去噪
       - h: 滤波强度，默认10
       - templateWindowSize: 模板窗口大小，默认7
       - searchWindowSize: 搜索窗口大小，默认21
    5. 二值化：使用自适应阈值进行二值化（可选）
       - blockSize: 邻域大小，默认11
       - C: 常数，默认2
    6. 转换回3通道：将处理后的灰度图像转换为BGR格式，供PaddleOCR使用
    
    :param image: 输入图像（numpy数组）
    :param enhance_contrast: 是否增强对比度，默认False
    :param denoise: 是否降噪，默认False
    :param threshold: 是否进行二值化，默认False
    :return: (预处理后的图像, padding_size) 元组
    """
    print(f"[{time.strftime('%H:%M:%S')}] 开始图像预处理...")
    
    padding_size = max(20, int(image.shape[1] * 0.05))
    image = cv2.copyMakeBorder(image, padding_size, padding_size, padding_size, padding_size, 
                                cv2.BORDER_CONSTANT, value=(255, 255, 255))
    print(f"[{time.strftime('%H:%M:%S')}]   - 已添加边缘padding: {padding_size}像素")
    
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        print(f"[{time.strftime('%H:%M:%S')}]   - 已应用CLAHE对比度增强")
    
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        print(f"[{time.strftime('%H:%M:%S')}]   - 已应用非局部均值降噪")
    
    if threshold:
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        print(f"[{time.strftime('%H:%M:%S')}]   - 已应用自适应阈值二值化")
    
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    print(f"[{time.strftime('%H:%M:%S')}] 图像预处理完成")
    return result, padding_size

def normalize_text(text):
    """
    规范化文本，移除或替换常见的标点符号差异
    
    :param text: 原始文本
    :return: 规范化后的文本
    """
    import re
    # 移除所有标点符号、特殊字符和数字，只保留中文字符和字母
    normalized = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', '', text)
    return normalized

def calculate_text_similarity(target_text, recognized_text):
    """
    计算目标文本和识别文本的相似度
    
    算法规则：
    1. 比较两个方面：字数，对应字的相同个数
    2. 每个方面占0.5分
    3. 字数每差一个，字数的0.5就减少（0.5/目标文本字数）
    4. 对应字的相同个数每不相同一个，它的0.5就减少（0.5/目标文本字数）
    5. 返回计算后的和值（0-1之间）
    
    :param target_text: 目标文本
    :param recognized_text: 识别到的文本
    :return: 相似度分数（0-1之间）
    """
    target_len = len(target_text)
    recognized_len = len(recognized_text)
    
    if target_len == 0:
        return 0.0
    
    # 计算字数得分（占0.5分）
    length_diff = abs(target_len - recognized_len)
    length_score = 0.5 - (length_diff * (0.5 / target_len))
    length_score = max(0.0, length_score)
    
    # 计算对应字的相同个数得分（占0.5分）
    # 使用最长公共子序列（LCS）算法计算相同字符数
    def lcs_length(s1, s2):
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]
    
    same_chars = lcs_length(target_text, recognized_text)
    diff_chars = target_len - same_chars
    char_match_score = 0.5 - (diff_chars * (0.5 / target_len))
    char_match_score = max(0.0, char_match_score)
    
    # 总相似度
    similarity = length_score + char_match_score
    
    return similarity

def is_ocr_text(text, description=None, region=(748, 267, 1864, 933), confidence=0.8, preprocess=False, time_sleep=0):
    """
    在屏幕上查找指定的文本内容，不执行点击操作
    
    识别流程：
    1. 截取屏幕截图（可指定识别区域）
    2. 图像预处理（可选）
    3. 使用RapidOCR进行文本识别
    4. 匹配识别结果与目标文本（支持标点符号差异）
    
    :param text: 要查找的文本内容
    :param description: 文本描述（用于日志输出）
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，默认(748, 267, 1864, 933)
    :param confidence: 文本匹配置信度阈值（0-1），默认0.5
    :param preprocess: 是否进行图像预处理，默认False
    :param time_sleep: 操作前等待时间（秒），默认0
    :return: 如果找到文本则返回 (True, center_x, center_y, match_region, recognized_text)，否则返回 (False, None, None, None, None)
    """
    # 对目标文本进行标准化
    normalized_target = normalize_text(text)
    print(f"[{time.strftime('%H:%M:%S')}] 查找文本: '{text}' (标准化后: '{normalized_target}')")
    
    if time_sleep > 0:
        time.sleep(time_sleep)
    
    try:
        screenshot = pyautogui.screenshot()
        screenshot_np = np.array(screenshot)
        
        if region is not None:
            x1, y1, x2, y2 = region
            screenshot_np = screenshot_np[y1:y2, x1:x2]
        
        if preprocess:
            processed_image, padding_size = preprocess_image(screenshot_np, enhance_contrast=False, denoise=False, threshold=False)
        else:
            processed_image = screenshot_np
            padding_size = 0
        
        result, elapse = get_ocr_instance()(processed_image)
        
        if result and len(result) > 0:
            for line in result:
                box = line[0]
                recognized_text = line[1]
                text_confidence = float(line[2])
                
                # 对识别到的文本进行标准化
                normalized_recognized = normalize_text(recognized_text)
                
                # 计算文本相似度
                similarity = calculate_text_similarity(normalized_target, normalized_recognized)
                
                # 使用相似度算法进行匹配
                if similarity >= confidence:
                    x_coords = [point[0] for point in box]
                    y_coords = [point[1] for point in box]
                    
                    # 计算中心坐标，减去padding
                    center_x = int(sum(x_coords) / 4) - padding_size
                    center_y = int(sum(y_coords) / 4) - padding_size
                    
                    # 计算边界坐标，减去padding
                    x_min = int(min(x_coords)) - padding_size
                    x_max = int(max(x_coords)) - padding_size
                    y_min = int(min(y_coords)) - padding_size
                    y_max = int(max(y_coords)) - padding_size
                    
                    # 确保坐标不为负数
                    x_min = max(0, x_min)
                    y_min = max(0, y_min)
                    
                    match_region = screenshot_np[y_min:y_max, x_min:x_max]
                    
                    if region is not None:
                        center_x += region[0]
                        center_y += region[1]
                    
                    text_desc = f"{description} " if description else ""
                    print(f"[{time.strftime('%H:%M:%S')}] ✓ 找到{text_desc}文本: '{recognized_text}' (标准化: '{normalized_recognized}')，相似度: {similarity:.4f}，置信度: {text_confidence:.4f}，坐标: ({center_x}, {center_y})")
                    
                    return True, center_x, center_y, match_region, recognized_text
            
            print(f"[{time.strftime('%H:%M:%S')}] ✗ 未找到文本: '{text}' (标准化后: '{normalized_target}')")
            return False, None, None, None, None
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ 未找到文本: '{text}' (标准化后: '{normalized_target}')，OCR未识别到任何文本")
            return False, None, None, None, None
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ 执行错误: {e}")
        import traceback
        print(f"[{time.strftime('%H:%M:%S')}] 错误详情:\n{traceback.format_exc()}")
        return False, None, None, None, None

def click_ocr_text(text, description=None, region=(748, 267, 1864, 933), confidence=0.8, preprocess=False, time_sleep=0):
    """
    在屏幕上查找并点击指定的文本内容
    
    :param text: 要查找并点击的文本内容
    :param description: 文本描述（用于日志输出）
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，默认(748, 267, 1864, 933)
    :param confidence: 文本匹配置信度阈值（0-1），默认0.5
    :param preprocess: 是否进行图像预处理，默认False
    :param time_sleep: 操作前等待时间（秒），默认0
    :return: 如果找到并点击则返回True，否则返回False
    """
    print(f"[{time.strftime('%H:%M:%S')}] 查找并点击文本: '{text}'")
    
    found, center_x, center_y, match_region, recognized_text = is_ocr_text(text, description, region, confidence, preprocess, time_sleep)
    
    if found:
        try:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.05
            
            click_at_position(center_x, center_y - 25)
            
            text_desc = f"{description} " if description else ""
            print(f"[{time.strftime('%H:%M:%S')}] ✓ 成功点击{text_desc}文本: '{recognized_text}'，坐标: ({center_x}, {center_y - 25})")
            
            return True
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ 点击执行错误: {e}")
            import traceback
            print(f"[{time.strftime('%H:%M:%S')}] 错误详情:\n{traceback.format_exc()}")
            return False
    else:
        return False

def get_all_recognized_text(region=(748, 267, 1864, 933), preprocess=False, target_text=None):
    """
    获取识别范围内的所有文本
    
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，默认(748, 267, 1864, 933)
    :param preprocess: 是否进行图像预处理，默认False
    :param target_text: 目标文本（用于计算相似度），默认None
    :return: 识别结果列表，每个元素为 (文本, 标准化文本, 置信度, 中心坐标, 相似度) 元组
    """
    try:
        screenshot = pyautogui.screenshot()
        screenshot_np = np.array(screenshot)
        
        if region is not None:
            x1, y1, x2, y2 = region
            screenshot_np = screenshot_np[y1:y2, x1:x2]
        
        if preprocess:
            processed_image, padding_size = preprocess_image(screenshot_np, enhance_contrast=False, denoise=False, threshold=False)
        else:
            processed_image = screenshot_np
            padding_size = 0
        
        result, elapse = get_ocr_instance()(processed_image)
        
        recognized_texts = []
        if result and len(result) > 0:
            for line in result:
                box = line[0]
                recognized_text = line[1]
                text_confidence = float(line[2])
                
                # 对识别到的文本进行标准化
                normalized_recognized = normalize_text(recognized_text)
                
                # 计算相似度（如果提供了目标文本）
                similarity = 0.0
                if target_text:
                    normalized_target = normalize_text(target_text)
                    similarity = calculate_text_similarity(normalized_target, normalized_recognized)
                
                x_coords = [point[0] for point in box]
                y_coords = [point[1] for point in box]
                # 计算中心坐标，减去padding
                center_x = int(sum(x_coords) / 4) - padding_size
                center_y = int(sum(y_coords) / 4) - padding_size
                
                if region is not None:
                    center_x += region[0]
                    center_y += region[1]
                
                recognized_texts.append((recognized_text, normalized_recognized, text_confidence, (center_x, center_y), similarity))
        
        return recognized_texts
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取识别文本失败: {e}")
        return []

def test_ocr_performance(test_text='赤骨·赤血·赤练', region=(748, 267, 1864, 933), confidence=0.8, preprocess=False, num_tests=3):
    """
    测试OCR性能
    
    测试内容包括：
    1. OCR初始化时间
    2. 单次识别时间
    3. 多次识别平均时间
    4. 识别成功率
    
    :param test_text: 测试文本，默认'赤骨·赤血·赤练'
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，默认(748, 267, 1864, 933)
    :param confidence: 文本匹配置信度阈值（0-1），默认0.5
    :param preprocess: 是否进行图像预处理，默认False
    :param num_tests: 测试次数，默认3
    :return: 性能测试结果字典
    """
    print("=" * 70)
    print("OCR性能测试")
    print("=" * 70)
    print(f"测试参数:")
    print(f"  - 测试文本: '{test_text}'")
    print(f"  - 识别区域: {region}")
    print(f"  - 置信度阈值: {confidence}")
    print(f"  - 图像预处理: {preprocess}")
    print(f"  - 测试次数: {num_tests}")
    print("=" * 70)
    
    results = {
        'init_time': 0,
        'recognition_times': [],
        'success_count': 0,
        'avg_recognition_time': 0,
        'success_rate': 0
    }
    
    # 测试OCR初始化时间
    print(f"\n1. 测试OCR初始化时间...")
    init_start = time.time()
    ocr = get_ocr_instance()
    init_end = time.time()
    init_time = init_end - init_start
    results['init_time'] = init_time
    print(f"   OCR初始化耗时: {init_time:.2f}秒")
    
    # 测试识别时间
    print(f"\n2. 测试OCR识别时间（{num_tests}次测试）...")
    for i in range(num_tests):
        print(f"\n   测试 {i+1}/{num_tests}:")
        recog_start = time.time()
        found, x, y, region_img, text = is_ocr_text(test_text, confidence=confidence, preprocess=preprocess, region=region)
        recog_end = time.time()
        recog_time = recog_end - recog_start
        results['recognition_times'].append(recog_time)
        
        if found:
            results['success_count'] += 1
            print(f"   ✓ 识别成功！耗时: {recog_time:.2f}秒，坐标: ({x}, {y})")
        else:
            print(f"   ✗ 识别失败！耗时: {recog_time:.2f}秒")
        
        # 输出识别范围内的所有文本
        print(f"\n   识别范围内的所有文本:")
        all_texts = get_all_recognized_text(region=region, preprocess=preprocess, target_text=test_text)
        if all_texts:
            for j, (recognized_text, normalized_text, text_confidence, (center_x, center_y), similarity) in enumerate(all_texts, 1):
                print(f"     [{j}] '{recognized_text}' (标准化: '{normalized_text}', 置信度: {text_confidence:.4f}, 相似度: {similarity:.4f}, 坐标: ({center_x}, {center_y}))")
        else:
            print(f"     未识别到任何文本")
    
    # 计算统计数据
    if results['recognition_times']:
        results['avg_recognition_time'] = sum(results['recognition_times']) / len(results['recognition_times'])
        results['success_rate'] = (results['success_count'] / num_tests) * 100
    
    # 输出测试结果
    print("\n" + "=" * 70)
    print("测试结果汇总:")
    print("=" * 70)
    print(f"OCR初始化时间: {results['init_time']:.2f}秒")
    print(f"识别时间统计:")
    print(f"  - 最快: {min(results['recognition_times']):.2f}秒")
    print(f"  - 最慢: {max(results['recognition_times']):.2f}秒")
    print(f"  - 平均: {results['avg_recognition_time']:.2f}秒")
    print(f"识别成功率: {results['success_rate']:.1f}% ({results['success_count']}/{num_tests})")
    print("=" * 70)
    
    # 性能评估
    if results['avg_recognition_time'] > 10:
        print("\n⚠️  平均识别时间超过10秒，建议优化方案:")
        print("1. 使用更轻量的OCR模型")
        print("2. 进一步缩小识别区域")
        print("3. 降低图像分辨率")
        print("4. 考虑使用GPU加速（如果尚未启用）")
    elif results['avg_recognition_time'] > 5:
        print("\n⚡ 平均识别时间在5-10秒之间，可考虑进一步优化")
    else:
        print("\n✓ 平均识别时间在可接受范围内（<5秒）")
    
    if results['success_rate'] < 80:
        print("\n⚠️  识别成功率较低，建议:")
        print("1. 启用图像预处理: preprocess=True")
        print("2. 调整置信度阈值: confidence=0.6")
        print("3. 检查识别区域是否正确")
    else:
        print("\n✓ 识别成功率良好")
    
    return results

def find_keyin(region=(333, 106, 1861, 935), confidence=0.5, preprocess=False, use_similarity=False, similarity_threshold=0.76, category=None, show_debug=False, use_special_matching=False):
    """
    在指定区域内查找属于keyin.json列表中的文字
    
    识别流程：
    1. 加载keyin.json字典
    2. 根据类别筛选keyin文本（可选）
    3. 截取屏幕截图（可指定识别区域）
    4. 图像预处理（可选）
    5. 使用RapidOCR进行文本识别
    6. 将识别结果与keyin.json中的文字进行匹配
    7. 返回匹配到的文字列表
    
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，默认(333, 106, 1861, 935)
    :param confidence: OCR识别置信度阈值（0-1），默认0.5
    :param preprocess: 是否进行图像预处理，默认False
    :param use_similarity: 是否使用相似度匹配（用于处理OCR识别误差），默认False
    :param similarity_threshold: 相似度匹配阈值（0-1），默认0.7
    :param category: 要匹配的keyin类别，如"jiushi"，默认None（匹配所有类别）
    :param show_debug: 是否显示调试信息，默认False
    :param use_special_matching: 是否使用特殊匹配（针对偏僻字"鏖"的识别错误），默认False
    :return: 匹配到的文字列表，每个元素为 (类别, 刻印名称, 坐标) 元组
    """
    import json
    import os
    import time
    
    start_time = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] 开始查找keyin.json中的文字...")
    print(f"[{time.strftime('%H:%M:%S')}] 识别区域: {region}")
    print(f"[{time.strftime('%H:%M:%S')}] OCR置信度阈值: {confidence}")
    print(f"[{time.strftime('%H:%M:%S')}] 图像预处理: {'启用' if preprocess else '禁用'}")
    print(f"[{time.strftime('%H:%M:%S')}] 相似度匹配: {'启用' if use_similarity else '禁用'} (阈值: {similarity_threshold})")
    print(f"[{time.strftime('%H:%M:%S')}] 匹配类别: {'所有类别' if category is None else category}")
    print(f"[{time.strftime('%H:%M:%S')}] 调试信息: {'显示' if show_debug else '隐藏'}")
    print(f"[{time.strftime('%H:%M:%S')}] 特殊匹配: {'启用' if use_special_matching else '禁用'}")
    
    # 加载keyin.json字典
    keyin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keyin.json")
    try:
        with open(keyin_path, 'r', encoding='utf-8') as f:
            keyin_data = json.load(f)
        print(f"[{time.strftime('%H:%M:%S')}] ✓ 成功加载keyin.json，共包含{len(keyin_data)}个类别")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ 加载keyin.json失败: {e}")
        return []
    
    # 根据类别筛选keyin文本
    all_keyin_texts = set()
    normalized_keyin_map = {}  # 标准化文本 → 原始keyin文本
    text_category_map = {}     # 原始keyin文本 → 类别名称
    
    if category is None:
        # 匹配所有类别
        for cat_name, cat_texts in keyin_data.items():
            all_keyin_texts.update(cat_texts)
            for text in cat_texts:
                normalized_keyin_map[normalize_text(text)] = text
                text_category_map[text] = cat_name
        print(f"[{time.strftime('%H:%M:%S')}] ✓ 合并所有类别，共{len(all_keyin_texts)}个keyin文本")
    else:
        # 匹配指定类别
        if category in keyin_data:
            cat_texts = keyin_data[category]
            all_keyin_texts.update(cat_texts)
            for text in cat_texts:
                normalized_keyin_map[normalize_text(text)] = text
                text_category_map[text] = category
            print(f"[{time.strftime('%H:%M:%S')}] ✓ 筛选类别'{category}'，共{len(all_keyin_texts)}个keyin文本")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ 类别'{category}'不存在于keyin.json中")
            print(f"[{time.strftime('%H:%M:%S')}]   可用类别: {list(keyin_data.keys())}")
            return []
    
    # 获取指定区域内的所有识别文本
    ocr_start = time.time()
    recognized_texts = get_all_recognized_text(region=region, preprocess=preprocess)
    ocr_time = time.time() - ocr_start
    print(f"[{time.strftime('%H:%M:%S')}] ✓ OCR识别完成，耗时{ocr_time:.2f}秒，共识别到{len(recognized_texts)}个文本")
    
    # 显示调试信息
    if show_debug and recognized_texts:
        print(f"[{time.strftime('%H:%M:%S')}] 识别到的文本列表:")
        for i, (original, normalized, conf, coords, _) in enumerate(recognized_texts):
            print(f"[{time.strftime('%H:%M:%S')}]   {i}. '{original}' (标准化: '{normalized}', 置信度: {conf:.4f}, 坐标: {coords})")
    # 匹配识别结果与keyin文本
    match_start = time.time()
    matched_results = []
    
    # 预计算标准化的keyin文本集合，提高匹配速度
    normalized_keyin_set = set(normalized_keyin_map.keys())
    
    for recognized_text, normalized_recognized, text_confidence, center_coords, _ in recognized_texts:
        # 特殊匹配处理
        special_matched = False
        
        if use_special_matching:
            # 特殊匹配：基于核心关键字提取匹配
            # 从识别文本中提取核心关键字进行匹配，提高匹配成功率
            special_matches = {
                # 1. 核心关键字 "斗战杀灭" 对应 "鏖斗鏖战鏖杀鏖灭"
                "斗战杀灭": "鏖斗鏖战鏖杀鏖灭",
                
                # 2. 核心关键字 "兵剪灭" 对应 "鏖兵鏖剪鏖馘鏖灭"
                "兵剪灭": "鏖兵鏖剪鏖馘鏖灭",
            }
            
            # 执行特殊匹配
            print(f"[{time.strftime('%H:%M:%S')}] 开始特殊匹配，当前识别文本: '{recognized_text}' (标准化: '{normalized_recognized}')")
            for keyword, target_text in special_matches.items():
                print(f"[{time.strftime('%H:%M:%S')}] 检查核心关键字: '{keyword}' → 目标文本: '{target_text}'")
                if keyword in normalized_recognized:
                    print(f"[{time.strftime('%H:%M:%S')}] ✓ 从识别文本中提取到核心关键字: '{keyword}'")
                    # 尝试获取目标文本的类别
                    matched_category = None
                    normalized_target = normalize_text(target_text)
                    # 遍历所有keyin文本，查找目标文本（使用标准化匹配）
                    for cat_name, cat_texts in keyin_data.items():
                        for text in cat_texts:
                            normalized_text = normalize_text(text)
                            if normalized_text == normalized_target:
                                matched_category = cat_name
                                print(f"[{time.strftime('%H:%M:%S')}] ✓ 找到目标文本类别: '{matched_category}'")
                                break
                        if matched_category:
                            break
                    
                    if matched_category:
                        # 只返回(类别, 刻印名称, 坐标)三个值
                        matched_results.append((matched_category, target_text, center_coords))
                        print(f"[{time.strftime('%H:%M:%S')}] ✓ 特殊匹配: '{recognized_text}' → '{target_text}' (类别: {matched_category}, 坐标: {center_coords})")
                        special_matched = True
                        break
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ✗ 未找到目标文本类别: '{target_text}'")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ✗ 未找到核心关键字: '{keyword}'")
        
        if special_matched:
            # 特殊匹配成功，跳过后续处理
            continue
        
        # 跳过置信度低的识别结果
        if text_confidence < confidence:
            if show_debug:
                print(f"[{time.strftime('%H:%M:%S')}] ✗ 跳过低置信度文本: '{recognized_text}' (置信度: {text_confidence:.4f})")
            continue
        
        # 精确匹配（O(1)复杂度）
        if normalized_recognized in normalized_keyin_set:
            matched_keyin = normalized_keyin_map[normalized_recognized]
            matched_category = text_category_map[matched_keyin]
            # 只返回(类别, 刻印名称, 坐标)三个值
            matched_results.append((matched_category, matched_keyin, center_coords))
            print(f"[{time.strftime('%H:%M:%S')}] ✓ 精确匹配: '{recognized_text}' → '{matched_keyin}' (类别: {matched_category}, 坐标: {center_coords})")
        # 相似度匹配
        elif use_similarity:
            # 检查标准化文本长度是否在3-12字范围内
            text_length = len(normalized_recognized)
            if 3 <= text_length <= 12:
                max_similarity = 0.0
                best_match = None
                
                # 只对标准化后的文本进行相似度计算，减少计算量
                for normalized_keyin, original_keyin in normalized_keyin_map.items():
                    similarity = calculate_text_similarity(normalized_keyin, normalized_recognized)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_match = original_keyin
                
                if max_similarity >= similarity_threshold:
                    matched_category = text_category_map[best_match]
                    # 只返回(类别, 刻印名称, 坐标)三个值
                    matched_results.append((matched_category, best_match, center_coords))
                    print(f"[{time.strftime('%H:%M:%S')}] ✓ 相似度匹配: '{recognized_text}' → '{best_match}' (类别: {matched_category}, 相似度: {max_similarity:.4f}, 坐标: {center_coords})")
                elif show_debug:
                    print(f"[{time.strftime('%H:%M:%S')}] ✗ 相似度不足: '{recognized_text}' (最高相似度: {max_similarity:.4f})")
            elif show_debug:
                print(f"[{time.strftime('%H:%M:%S')}] ✗ 文本长度不在3-12字范围内，跳过相似度匹配: '{recognized_text}' (长度: {text_length})")
        elif show_debug:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ 未匹配: '{recognized_text}'")
    
    match_time = time.time() - match_start
    total_time = time.time() - start_time
    
    print(f"[{time.strftime('%H:%M:%S')}] ✓ 匹配完成，耗时{match_time:.2f}秒")
    print(f"[{time.strftime('%H:%M:%S')}] ✓ 共匹配到{len(matched_results)}个keyin文本")
    print(f"[{time.strftime('%H:%M:%S')}] ✓ 总耗时: {total_time:.2f}秒")
    
    return matched_results

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
    
    click_ocr_text("剑锋剑冢剑痕")
