#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR持久化服务端（最终版）

文件说明：
    本模块实现了OCR持久化服务端，启动时加载一次OCR模型，
    通过TCP协议接收客户端请求，持续提供文本识别服务。服务端采用多线程设计，
    可以同时处理多个客户端请求，大幅提高OCR模型的调用效率。

主要功能：
    - 启动时加载一次OCR模型，避免重复加载的开销
    - 支持多客户端并发请求
    - 通过TCP协议与客户端通信
    - 支持屏幕区域识别和图片文件识别
    - 支持置信度阈值设置
    - 支持图像预处理选项
    - 提供详细的日志输出
    - 支持优雅关闭

使用说明：
    1. 直接运行：
       ```
       python ocr_server_final.py
       ```
    
    2. 作为模块调用：
       ```python
       import subprocess
       import os
       
       # 启动服务端
       server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr_server_final.py')
       python_executable = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Python3.11', 'python.exe')
       
       server_process = subprocess.Popen(
           [python_executable, server_script],
           stdout=subprocess.PIPE,
           stderr=subprocess.PIPE,
           text=True,
           encoding='utf-8'
       )
       ```
    
    3. 服务端状态查看：
       - 服务端会输出详细的日志信息，包括模型加载、客户端连接、请求处理等
       - 默认监听127.0.0.1:5002

通信协议：
    - 请求格式：JSON字符串 + "\nEOF\n"
    - 响应格式：JSON字符串 + "\nEOF\n"
    - 端口：默认5002
    - 编码：UTF-8
    - 请求字段：
      - image_path: 图片文件路径（二选一）
      - screen_region: 屏幕区域 [x1, y1, x2, y2]（二选一）
      - conf_threshold: 置信度阈值（可选，默认0.5）
      - preprocess: 是否预处理图像（可选，默认False）
      - enhance_contrast: 是否增强对比度（可选，默认False）
      - denoise: 是否降噪（可选，默认False）
      - threshold: 是否二值化（可选，默认False）
    - 响应字段：
      - success: 是否成功
      - message: 错误信息（如果失败）
      - total_texts: 识别到的文本数量
      - texts: 识别结果列表
      - processing_time: 处理时间（秒）

依赖文件：
    - RapidOCR库：用于OCR模型推理
    - Python标准库：socket, json, os, time, threading, pyautogui, cv2, numpy

注意事项：
    - 服务端需要在Python 3.11环境中运行
    - 首次启动时会加载模型，可能需要几秒钟时间
    - 支持多个客户端同时连接和请求
    - 服务端会自动处理客户端连接和断开
    - 可以通过Ctrl+C优雅关闭服务端
    - 建议配合ocr_client.py模块使用，自动管理服务端生命周期

性能优势：
    - 模型只加载一次，避免每次调用都重新加载模型的开销
    - 支持并发请求，提高系统吞吐量
    - 减少了Python进程创建和销毁的开销
    - 适合频繁调用OCR模型的场景
"""

import socket
import json
import os
import time
import threading
import psutil
from rapidocr_onnxruntime import RapidOCR
import pyautogui
import cv2
import numpy as np

# 配置
HOST = '0.0.0.0'
PORT = 5002


class ClientHandler(threading.Thread):
    """
    客户端请求处理器
    """
    def __init__(self, client_socket, client_addr, ocr_model, model_dir):
        super().__init__()
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.ocr_model = ocr_model
        self.model_dir = model_dir
        self.running = True
        # 获取当前进程信息，用于资源监控
        self.process = psutil.Process()
    
    def run(self):
        """
        处理客户端请求
        """
        print(f"[{time.strftime('%H:%M:%S')}] 新客户端连接: {self.client_addr}")
        
        # 设置客户端连接超时
        try:
            self.client_socket.settimeout(60)  # 60秒超时
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 设置客户端超时失败: {e}")
        
        try:
            while self.running:
                # 接收客户端数据
                data = b""
                print(f"[{time.strftime('%H:%M:%S')}] 开始接收客户端数据")
                while True:
                    try:
                        chunk = self.client_socket.recv(4096)
                        if not chunk:
                            print(f"[{time.strftime('%H:%M:%S')}] 客户端断开连接: {self.client_addr}")
                            self.running = False
                            break
                        data += chunk
                        print(f"[{time.strftime('%H:%M:%S')}] 接收到数据，长度: {len(chunk)} 字节，累计: {len(data)} 字节")
                        # 检查是否包含结束标记
                        if b"\nEOF\n" in data:
                            print(f"[{time.strftime('%H:%M:%S')}] 接收到完整数据，开始处理")
                            break
                    except socket.timeout:
                        print(f"[{time.strftime('%H:%M:%S')}] 接收数据超时")
                        self.running = False
                        break
                    except Exception as e:
                        print(f"[{time.strftime('%H:%M:%S')}] 接收数据出错: {e}")
                        self.running = False
                        break
                
                if not self.running:
                    break
                
                # 解析请求
                request_str = data.decode('utf-8').replace('\nEOF\n', '')
                request = json.loads(request_str)
                print(f"[{time.strftime('%H:%M:%S')}] 收到请求: {request}")
                
                # 检查是否为健康检查请求
                if request.get('health_check'):
                    print(f"[{time.strftime('%H:%M:%S')}] 处理健康检查请求")
                    
                    # 获取资源占用情况
                    cpu_percent = self.process.cpu_percent(interval=0.1)
                    memory_info = self.process.memory_info()
                    memory_percent = self.process.memory_percent()
                    
                    # 记录资源占用
                    print(f"[{time.strftime('%H:%M:%S')}] 资源占用 - CPU: {cpu_percent:.2f}%, 内存: {memory_percent:.2f}% ({memory_info.rss / 1024 / 1024:.2f}MB)")
                    
                    response = {
                        'success': True,
                        'message': 'OCR服务端运行正常',
                        'timestamp': time.time(),
                        'model_path': self.model_dir,
                        'resource_usage': {
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory_percent,
                            'memory_rss_mb': memory_info.rss / 1024 / 1024
                        }
                    }
                else:
                    # 执行识别
                    image_path = request.get('image_path')
                    screen_region = request.get('screen_region')
                    conf_threshold = request.get('conf_threshold', 0.5)
                    preprocess = request.get('preprocess', False)
                    enhance_contrast = request.get('enhance_contrast', False)
                    denoise = request.get('denoise', False)
                    threshold = request.get('threshold', False)
                
                # 验证请求参数
                if not image_path and not screen_region:
                    response = {
                        'success': False,
                        'message': '必须提供image_path或screen_region参数'
                    }
                else:
                    try:
                        # 获取图像
                        if image_path:
                            if not os.path.exists(image_path):
                                response = {
                                    'success': False,
                                    'message': f'图片文件不存在: {image_path}'
                                }
                                continue
                            # 读取图片
                            image = cv2.imread(image_path)
                        else:
                            # 截取屏幕区域
                            x1, y1, x2, y2 = screen_region
                            screenshot = pyautogui.screenshot(region=(x1, y1, x2-x1, y2-y1))
                            image = np.array(screenshot)
                            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                        
                        # 图像预处理
                        if preprocess:
                            image = self.preprocess_image(image, enhance_contrast, denoise, threshold)
                        
                        # 执行OCR识别
                        start_time = time.time()
                        result, elapse = self.ocr_model(image)
                        end_time = time.time()
                        
                        # 解析结果
                        texts = []
                        if result:
                            for line in result:
                                box = line[0]
                                text = line[1]
                                confidence = float(line[2])
                                
                                # 过滤低置信度文本
                                if confidence >= conf_threshold:
                                    # 计算中心坐标
                                    x_coords = [point[0] for point in box]
                                    y_coords = [point[1] for point in box]
                                    center_x = int(sum(x_coords) / 4)
                                    center_y = int(sum(y_coords) / 4)
                                    
                                    # 如果是屏幕区域，转换为全局坐标
                                    if screen_region:
                                        center_x += screen_region[0]
                                        center_y += screen_region[1]
                                    
                                    texts.append({
                                        'text': text,
                                        'confidence': round(confidence, 4),
                                        'center_x': center_x,
                                        'center_y': center_y,
                                        'box': box
                                    })
                        
                        processing_time = end_time - start_time
                        
                        response = {
                            'success': True,
                            'total_texts': len(texts),
                            'texts': texts,
                            'processing_time': round(processing_time, 3)
                        }
                        
                    except Exception as e:
                        response = {
                            'success': False,
                            'message': f'识别过程出错: {e}'
                        }
                
                # 发送响应
                response_str = json.dumps(response, ensure_ascii=False) + '\nEOF\n'
                self.client_socket.sendall(response_str.encode('utf-8'))
                print(f"[{time.strftime('%H:%M:%S')}] 响应已发送")
                
        except json.JSONDecodeError as e:
            print(f"[{time.strftime('%H:%M:%S')}] JSON解析错误: {e}")
            error_response = {
                'success': False,
                'message': f'JSON解析错误: {e}'
            }
            response_str = json.dumps(error_response, ensure_ascii=False) + '\nEOF\n'
            self.client_socket.sendall(response_str.encode('utf-8'))
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 处理请求出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 发送错误响应
            error_response = {
                'success': False,
                'message': f'处理请求出错: {e}'
            }
            response_str = json.dumps(error_response, ensure_ascii=False) + '\nEOF\n'
            self.client_socket.sendall(response_str.encode('utf-8'))
        finally:
            self.client_socket.close()
            print(f"[{time.strftime('%H:%M:%S')}] 客户端连接已关闭: {self.client_addr}")
    
    def preprocess_image(self, image, enhance_contrast=False, denoise=False, threshold=False):
        """
        预处理图像以提高OCR识别准确率
        """
        # 边缘填充
        padding_size = max(20, int(image.shape[1] * 0.05))
        image = cv2.copyMakeBorder(image, padding_size, padding_size, padding_size, padding_size, 
                                   cv2.BORDER_CONSTANT, value=(255, 255, 255))
        
        # 灰度化
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 对比度增强
        if enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        
        # 降噪
        if denoise:
            gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # 二值化
        if threshold:
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # 转换回3通道
        result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return result

def main():
    """
    主函数
    """
    print(f"[{time.strftime('%H:%M:%S')}] 正在加载OCR模型...")
    start_time = time.time()
    
    # 使用与ocr_functions.py相同的模型目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, 'models')
    
    # 确保模型目录存在
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"[{time.strftime('%H:%M:%S')}] 创建模型目录: {model_dir}")
    
    # 设置环境变量
    os.environ['PADDLEX_MODEL_HOME'] = model_dir
    os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    
    # 初始化OCR模型（使用PP-OCRv4配置）
    det_model_path = os.path.join(model_dir, 'ch_PP-OCRv4_det_infer.onnx')
    rec_model_path = os.path.join(model_dir, 'ch_PP-OCRv4_rec_infer.onnx')
    cls_model_path = os.path.join(model_dir, 'ch_ppocr_mobile_v2.0_cls_infer.onnx')
    
    print(f"[{time.strftime('%H:%M:%S')}] 检测模型: {det_model_path}")
    print(f"[{time.strftime('%H:%M:%S')}] 识别模型: {rec_model_path}")
    print(f"[{time.strftime('%H:%M:%S')}] 分类模型: {cls_model_path}")
    
    ocr_model = RapidOCR(
        det_model_path=det_model_path,  # 使用指定路径的PP-OCRv4检测模型
        rec_model_path=rec_model_path,  # 使用指定路径的PP-OCRv4识别模型
        cls_model_path=cls_model_path,  # 使用指定路径的PP-OCRv4分类模型
        use_angle_cls=True,
        use_text_det=True,
        print_verbose=False
    )
    
    end_time = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] OCR模型加载完成，耗时: {end_time - start_time:.2f}秒")
    
    # 创建服务器socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"[{time.strftime('%H:%M:%S')}] OCR服务端已启动，监听: {HOST}:{PORT}")
        print(f"[{time.strftime('%H:%M:%S')}] 运行环境: Python 3.11")
        print(f"[{time.strftime('%H:%M:%S')}] 模型目录: {model_dir}")
        print(f"[{time.strftime('%H:%M:%S')}] 模型类型: PP-OCRv4（内置模型）")
        
        while True:
            print(f"[{time.strftime('%H:%M:%S')}] 等待客户端连接...")
            client_socket, client_addr = server_socket.accept()
            
            # 创建新线程处理客户端请求
            client_thread = ClientHandler(client_socket, client_addr, ocr_model, model_dir)
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        print(f"[{time.strftime('%H:%M:%S')}] 收到终止信号，正在关闭服务...")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 服务端出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        server_socket.close()
        print(f"[{time.strftime('%H:%M:%S')}] OCR服务端已关闭")


if __name__ == "__main__":
    main()
