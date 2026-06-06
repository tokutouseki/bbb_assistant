#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR持久化客户端

文件说明：
    本模块实现了OCR客户端，通过TCP协议与OCR服务端通信，
    用于发送屏幕区域或图片文件识别请求并接收识别结果。客户端采用单例设计模式，
    支持自动重连机制，确保与服务端的稳定通信。

主要功能：
    - 与OCR服务端建立TCP连接
    - 发送屏幕区域识别请求
    - 发送图片文件识别请求
    - 接收并解析识别结果
    - 支持自动重连，提高服务稳定性
    - 支持置信度阈值设置
    - 支持图像预处理选项

使用说明：
    1. 基本使用：
       ```python
       from ocr_client import OCRClient
       
       # 创建客户端实例
       client = OCRClient()
       
       # 发送屏幕区域识别请求（自动处理连接和重连）
       result = client.recognize_with_reconnect(
           screen_region=[748, 267, 1864, 933],  # x1, y1, x2, y2
           conf_threshold=0.5,
           preprocess=True
       )
       ```
    
    2. 发送图片文件识别请求：
       ```python
       result = client.recognize_with_reconnect(
           image_path="path/to/image.jpg",
           conf_threshold=0.6,
           preprocess=True,
           enhance_contrast=True,
           denoise=True
       )
       ```
    
    3. 手动连接和识别：
       ```python
       client = OCRClient()
       
       if client.connect():
           result = client.recognize(
               screen_region=[0, 0, 1920, 1080],
               conf_threshold=0.5
           )
           client.close()
       ```
    
    4. 结果解析：
       ```python
       if result.get("success"):
           total_texts = result.get("total_texts")
           texts = result.get("texts")
           for text_info in texts:
               text = text_info.get("text")
               confidence = text_info.get("confidence")
               center_x = text_info.get("center_x")
               center_y = text_info.get("center_y")
               box = text_info.get("box")  # 文本边界框
       ```

通信协议：
    - 请求格式：JSON字符串 + "\nEOF\n"
    - 响应格式：JSON字符串 + "\nEOF\n"
    - 端口：默认5002
    - 编码：UTF-8

依赖文件：
    - 无外部依赖，仅使用Python标准库
    - 需要ocr_server_final.py服务端配合使用

注意事项：
    - 客户端会自动处理连接和重连逻辑
    - 每次识别请求后，客户端会保持连接，避免重复建立连接的开销
    - 建议使用recognize_with_reconnect方法，它会自动处理连接和重连
    - 服务端需要先启动，否则客户端会自动重试连接
"""

import socket
import json
import time
import sys
import os
import subprocess
import threading

# 模块级标志：OCR 服务后台启动状态
_ocr_server_started = False
_ocr_server_ready = False
_ocr_server_lock = threading.Lock()


def _start_ocr_server_background(host='127.0.0.1', port=5002):
    """在后台线程中启动 OCR 服务，不阻塞调用方。

    首次调用时启动后台线程，后续调用立即返回。
    使用 _ocr_server_ready 标志表示服务是否就绪。
    """
    global _ocr_server_started, _ocr_server_ready

    with _ocr_server_lock:
        if _ocr_server_started:
            return  # 已经在启动中
        _ocr_server_started = True

    # 快速检查是否已在运行
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        if s.connect_ex((host, port)) == 0:
            s.close()
            with _ocr_server_lock:
                _ocr_server_ready = True
            return
        s.close()
    except Exception:
        pass

    # 在后台线程启动服务
    def _do_start():
        global _ocr_server_ready
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_script = os.path.join(script_dir, 'ocr_server_final.py')
        if not os.path.isfile(server_script):
            print(f"[OCR] 服务脚本不存在: {server_script}")
            return

        print(f"[OCR] 服务未运行，正在后台启动 (模型加载约需 30-60 秒)...")
        try:
            if sys.platform == 'win32':
                proc = subprocess.Popen(
                    [sys.executable, server_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                proc = subprocess.Popen(
                    [sys.executable, server_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # 轮询等待就绪（后台，不阻塞主脚本）
            waited = 0
            while waited < 90:
                time.sleep(1)
                waited += 1
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    if s.connect_ex((host, port)) == 0:
                        s.close()
                        with _ocr_server_lock:
                            _ocr_server_ready = True
                        print(f"[OCR] 服务启动成功 (耗时 {waited}s)")
                        return
                    s.close()
                except Exception:
                    pass
            print(f"[OCR] 服务启动超时 (90s)，请检查 ocr_server_final.py 是否正常")
        except Exception as e:
            print(f"[OCR] 启动失败: {e}")

    t = threading.Thread(target=_do_start, daemon=True)
    t.start()


def _wait_ocr_ready(host='127.0.0.1', port=5002, timeout=90):
    """等待 OCR 服务就绪（带进度提示），用于实际需要 OCR 时调用。"""
    global _ocr_server_ready

    # 启动后台启动流程
    _start_ocr_server_background(host, port)

    # 等待就绪，每 5 秒打印进度
    waited = 0
    while waited < timeout:
        with _ocr_server_lock:
            if _ocr_server_ready:
                return True
        time.sleep(1)
        waited += 1
        if waited % 5 == 0:
            print(f"[OCR] 等待服务就绪... ({waited}s)")

    print(f"[OCR] 等待超时 ({timeout}s)")
    return False


class OCRClient:
    def __init__(self, host='127.0.0.1', port=5002, timeout=30):
        """
        初始化OCR客户端

        :param host: 服务端IP地址
        :param port: 服务端端口号
        :param timeout: 超时时间（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_socket = None

    def connect(self):
        """
        连接到OCR服务端
        
        :return: 是否连接成功
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.timeout)
            self.client_socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"连接OCR服务端失败: {e}")
            return False
    
    def close(self):
        """
        关闭与OCR服务端的连接
        """
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
    
    def recognize(self, image_path=None, screen_region=None, conf_threshold=0.5, 
                  preprocess=False, enhance_contrast=False, denoise=False, threshold=False):
        """
        发送识别请求并获取结果
        
        :param image_path: 图片文件路径（二选一）
        :param screen_region: 屏幕区域 [x1, y1, x2, y2]（二选一）
        :param conf_threshold: 置信度阈值
        :param preprocess: 是否预处理图像
        :param enhance_contrast: 是否增强对比度
        :param denoise: 是否降噪
        :param threshold: 是否二值化
        :return: 识别结果
        """
        # 创建请求数据
        request = {
            "image_path": image_path,
            "screen_region": screen_region,
            "conf_threshold": conf_threshold,
            "preprocess": preprocess,
            "enhance_contrast": enhance_contrast,
            "denoise": denoise,
            "threshold": threshold
        }
        
        try:
            # 发送请求
            request_str = json.dumps(request, ensure_ascii=False) + "\nEOF\n"
            self.client_socket.sendall(request_str.encode('utf-8'))
            
            # 接收响应
            response_data = b""
            while True:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    # 连接已关闭，需要重新连接
                    self.close()
                    break
                response_data += chunk
                # 检查是否包含结束标记
                if b"\nEOF\n" in response_data:
                    break
            
            if not response_data:
                # 连接已关闭，返回失败
                return {
                    "success": False,
                    "message": "服务端关闭了连接"
                }
            
            # 移除结束标记
            response_data = response_data.replace(b"\nEOF\n", b"")
            
            # 解析响应
            response = json.loads(response_data.decode('utf-8'))
            return response
            
        except ConnectionResetError:
            self.close()
            return {
                "success": False,
                "message": "连接被重置"
            }
        except Exception as e:
            # 发生异常时关闭连接，后续请求会自动重连
            self.close()
            return {
                "success": False,
                "message": f"识别请求出错: {e}"
            }
    
    def recognize_with_reconnect(self, image_path=None, screen_region=None, conf_threshold=0.5, 
                                preprocess=False, enhance_contrast=False, denoise=False, 
                                threshold=False, max_retries=3):
        """
        发送识别请求并获取结果，失败时自动重连
        
        :param image_path: 图片文件路径（二选一）
        :param screen_region: 屏幕区域 [x1, y1, x2, y2]（二选一）
        :param conf_threshold: 置信度阈值
        :param preprocess: 是否预处理图像
        :param enhance_contrast: 是否增强对比度
        :param denoise: 是否降噪
        :param threshold: 是否二值化
        :param max_retries: 最大重试次数
        :return: 识别结果
        """
        # 确保 OCR 服务在运行（首次后台启动，后续等待就绪）
        _start_ocr_server_background(self.host, self.port)

        for retry in range(max_retries):
            # 每次重试前先等一下服务就绪（带进度提示）
            if not _ocr_server_ready:
                remaining = max_retries - retry - 1
                if remaining == 0:
                    if not _wait_ocr_ready(self.host, self.port, timeout=90):
                        return {
                            "success": False,
                            "message": "OCR 服务启动超时，请检查 ocr_server_final.py"
                        }
                else:
                    time.sleep(2)  # 首次尝试等待 2 秒让服务有时间启动

            # 如果未连接或连接已关闭，尝试连接
            # 如果未连接或连接已关闭，尝试连接
            if not self.client_socket:
                if not self.connect():
                    if retry < max_retries - 1:
                        print(f"连接失败，{retry+1}/{max_retries}，正在重试...")
                        time.sleep(1)
                        continue
                    else:
                        return {
                            "success": False,
                            "message": "连接OCR服务端失败，已达到最大重试次数"
                        }
            
            # 发送识别请求
            result = self.recognize(
                image_path=image_path,
                screen_region=screen_region,
                conf_threshold=conf_threshold,
                preprocess=preprocess,
                enhance_contrast=enhance_contrast,
                denoise=denoise,
                threshold=threshold
            )
            
            # 如果请求成功，返回结果
            if result.get("success", False):
                return result
            
            # 识别方法已自动关闭连接，无需再次关闭
            
            if retry < max_retries - 1:
                print(f"请求失败，{retry+1}/{max_retries}，正在重试...")
                time.sleep(1)
        
        return result


def main():
    """
    主函数，用于测试OCR客户端
    """
    # 创建OCR客户端
    client = OCRClient()
    
    try:
        # 测试屏幕区域识别
        print("测试屏幕区域识别...")
        screen_region = [0, 0, 1920, 1080]  # 整个屏幕
        
        result = client.recognize_with_reconnect(
            screen_region=screen_region,
            conf_threshold=0.5,
            preprocess=True
        )
        
        # 输出结果
        print("识别结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 如果识别成功，输出详细信息
        if result.get("success", False):
            total_texts = result.get("total_texts")
            texts = result.get("texts")
            
            print(f"\n成功识别到{total_texts}个文本:")
            for i, text_info in enumerate(texts[:10], 1):
                text = text_info.get("text")
                confidence = text_info.get("confidence")
                center_x = text_info.get("center_x")
                center_y = text_info.get("center_y")
                print(f"[{i}] {text} (置信度: {confidence:.4f}, 坐标: ({center_x}, {center_y}))")
            
            if len(texts) > 10:
                print(f"... 还有{len(texts) - 10}个文本未显示")
                
    finally:
        # 关闭连接
        client.close()
        print("\n客户端连接已关闭")


if __name__ == "__main__":
    main()
