#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO持久化客户端

文件说明：
    本模块实现了YOLO客户端，通过TCP协议与YOLO服务端通信，
    用于发送图片路径并接收预测结果。客户端采用单例设计模式，
    支持自动重连机制，确保与服务端的稳定通信。

主要功能：
    - 与YOLO服务端建立TCP连接
    - 发送图片预测请求
    - 接收并解析预测结果
    - 支持自动重连，提高服务稳定性
    - 支持置信度阈值设置
    - 支持检测结果保存

使用说明：
    1. 基本使用：
       ```python
       from yolo_client import YOLOClient
       
       # 创建客户端实例
       client = YOLOClient()
       
       # 发送预测请求（自动处理连接和重连）
       result = client.predict_with_reconnect(
           image_path="path/to/image.jpg",
           conf_threshold=0.5
       )
       ```
    
    2. 手动连接和预测：
       ```python
       client = YOLOClient()
       
       if client.connect():
           result = client.predict(
               image_path="path/to/image.jpg",
               conf_threshold=0.5,
               save_result=True,
               output_dir="path/to/output"
           )
           client.close()
       ```
    
    3. 结果解析：
       ```python
       if result.get("success"):
           total_objects = result.get("total_objects")
           predictions = result.get("predictions")
           for pred in predictions:
               class_name = pred.get("class_name")
               confidence = pred.get("confidence")
               bbox = pred.get("bbox")  # [x1, y1, x2, y2]
       ```

通信协议：
    - 请求格式：JSON字符串 + "\nEOF\n"
    - 响应格式：JSON字符串 + "\nEOF\n"
    - 端口：默认5001
    - 编码：UTF-8

依赖文件：
    - 无外部依赖，仅使用Python标准库
    - 需要yolo_server_final.py服务端配合使用

注意事项：
    - 客户端会自动处理连接和重连逻辑
    - 每次预测请求后，客户端会保持连接，避免重复建立连接的开销
    - 建议使用predict_with_reconnect方法，它会自动处理连接和重连
    - 服务端需要先启动，否则客户端会自动重试连接
"""

import socket
import json
import time
import os


class YOLOClient:
    def __init__(self, host='127.0.0.1', port=5001, timeout=30):
        """
        初始化YOLO客户端
        
        :param host: 服务端IP地址
        :param port: 服务端端口号
        :param timeout: 超时时间（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_socket = None
        print(f"[{time.strftime('%H:%M:%S')}] YOLO客户端初始化，将连接到 {host}:{port}")
    
    def connect(self):
        """
        连接到YOLO服务端
        
        :return: 是否连接成功
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.timeout)
            self.client_socket.connect((self.host, self.port))
            return True
        except Exception as e:
            return False
    
    def close(self):
        """
        关闭与YOLO服务端的连接
        """
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
    
    def predict(self, image_path, conf_threshold=0.5, save_result=False, output_dir=None):
        """
        发送预测请求并获取结果
        
        :param image_path: 图片文件路径
        :param conf_threshold: 置信度阈值
        :param save_result: 是否保存结果图片
        :param output_dir: 结果图片保存目录
        :return: 预测结果
        """
        # 创建请求数据
        request = {
            "image_path": image_path,
            "conf_threshold": conf_threshold,
            "save_result": save_result,
            "output_dir": output_dir
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
                "message": f"预测请求出错: {e}"
            }
    
    def predict_with_reconnect(self, image_path, conf_threshold=0.5, save_result=False, output_dir=None, max_retries=3):
        """
        发送预测请求并获取结果，失败时自动重连
        
        :param image_path: 图片文件路径
        :param conf_threshold: 置信度阈值
        :param save_result: 是否保存结果图片
        :param output_dir: 结果图片保存目录
        :param max_retries: 最大重试次数
        :return: 预测结果
        """
        for retry in range(max_retries):
            print(f"[{time.strftime('%H:%M:%S')}] YOLO客户端尝试预测（{retry+1}/{max_retries}）...")
            
            # 如果未连接或连接已关闭，尝试连接
            if not self.client_socket:
                print(f"[{time.strftime('%H:%M:%S')}] 尝试连接YOLO服务端...")
                if not self.connect():
                    print(f"[{time.strftime('%H:%M:%S')}] 连接失败，将在1秒后重试")
                    if retry < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        return {
                            "success": False,
                            "message": "连接YOLO服务端失败，已达到最大重试次数"
                        }
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 连接成功")
            
            # 发送预测请求
            result = self.predict(image_path, conf_threshold, save_result, output_dir)
            
            # 如果请求成功，返回结果
            if result.get("success", False):
                print(f"[{time.strftime('%H:%M:%S')}] 预测成功")
                return result
            
            # 预测方法已自动关闭连接，无需再次关闭
            print(f"[{time.strftime('%H:%M:%S')}] 预测失败: {result.get('message')}")
            
            if retry < max_retries - 1:
                print(f"[{time.strftime('%H:%M:%S')}] 将在1秒后重试...")
                time.sleep(1)
        
        print(f"[{time.strftime('%H:%M:%S')}] 已达到最大重试次数，预测失败")
        return result


def main():
    """
    主函数，用于测试YOLO客户端
    """
    # 创建YOLO客户端
    client = YOLOClient()
    
    try:
        # 连接到服务端
        if client.connect():
            # 示例：发送预测请求
            image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Python3.11", "yolo", "To_test", "example.jpg")
            result = client.predict(image_path, conf_threshold=0.5)
            
            # 输出结果
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # 如果预测成功，输出详细信息
            if result.get("success", False):
                print(f"\n🎉 成功识别到 {result.get('total_objects', 0)} 个目标")
                
                for i, pred in enumerate(result.get('predictions', []), 1):
                    print(f"\n📌 目标 {i}:")
                    print(f"   类别: {pred['class_name']}")
                    print(f"   置信度: {pred['confidence']:.4f}")
                    print(f"   边界框: {pred['bbox']}")
    finally:
        # 关闭连接
        client.close()


if __name__ == "__main__":
    main()
