#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO服务端

提供YOLO模型的网络接口，支持远程调用进行目标检测。

特点：
- 基于Socket通信，轻量高效
- 支持并发请求，提高系统吞吐量
- 减少了Python进程创建和销毁的开销
- 适合频繁调用YOLO模型的场景
"""


import socket
import json
import os
import time
import threading
import psutil
import cv2
import numpy as np
import onnxruntime as ort

# 获取脚本所在目录的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 默认模型文件路径 — 查找 bbb_assistant 项目 data/models/detect 目录
_hongkai_pkg_root = os.path.dirname(script_dir)  # modules/
_backend_root = os.path.dirname(os.path.dirname(_hongkai_pkg_root))  # backend/
_project_root = os.path.dirname(_backend_root)  # bbb_assistant/
_default_model = os.path.join(_project_root, "backend", "data", "models", "detect", "yolo11n_elysian_realm_det.onnx")
_legacy_model = os.path.join(script_dir, "Python3.11", "yolo", "To_use", "best.onnx")
model_path = _default_model if os.path.exists(_default_model) else _legacy_model

# 配置
HOST = '0.0.0.0'
PORT = 5001

# 类别名称映射
CLASS_NAMES = {
    0: 'elysia_star',
    1: 'aomie',
    2: 'zhenwo',
    3: 'kongmeng',
    4: 'shanbiyvjing',
    5: 'xuanze_R',
    6: 'guaiwu_xueliang_UI',
    7: 'xuanze_r',
    8: 'keyin',
    9: 'keyin_open',
    10: 'shangdian',
    11: 'jielv',
    12: 'luoxuan',
    13: 'shangdian_open',
    14: 'tianhui',
    15: 'fanxing',
    16: 'lock_on',
    17: 'wuxian',
    18: 'chana',
    19: 'huangjin',
    20: 'jiushi',
    21: 'xvguang',
    22: 'fusheng',
    23: 'BOSS'
}

def preprocess_image(image, target_size=(640, 384)):
    """
    预处理图片
    
    :param image: 输入图片（OpenCV格式）
    :param target_size: 目标尺寸
    :return: 预处理后的输入数据
    """
    # 保存原始尺寸
    h, w = image.shape[:2]
    
    # 调整图片大小
    img = cv2.resize(image, target_size)
    
    # 转换为RGB格式
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 归一化处理
    img = img.astype(np.float32) / 255.0
    
    # 调整维度顺序 (H, W, C) -> (C, H, W)
    img = np.transpose(img, (2, 0, 1))
    
    # 添加批次维度
    img = np.expand_dims(img, axis=0)
    
    return img, h, w

def postprocess_output(output, conf_threshold=0.25, input_size=(384, 640), original_size=None):
    """
    后处理输出结果
    
    :param output: ONNX模型输出
    :param conf_threshold: 置信度阈值
    :param input_size: 模型输入尺寸
    :param original_size: 原始图片尺寸
    :return: 处理后的预测结果
    """
    predictions = []
    
    # 获取输出数据
    output_data = output[0][0]  # 去除批次维度，得到 (300, 6) 的检测结果
    
    # 处理每个检测结果
    for detection in output_data:
        x1, y1, x2, y2, confidence, class_id = detection
        
        # 过滤低置信度结果
        if confidence < conf_threshold:
            continue
        
        # 转换为整数
        class_id = int(class_id)
        
        # 获取类别名称
        class_name = CLASS_NAMES.get(class_id, f"class_{class_id}")
        
        # 坐标转换（如果提供了原始尺寸）
        if original_size:
            orig_h, orig_w = original_size
            input_h, input_w = input_size
            
            # 计算缩放比例
            scale_x = orig_w / input_w
            scale_y = orig_h / input_h
            
            # 调整边界框坐标
            x1 = x1 * scale_x
            y1 = y1 * scale_y
            x2 = x2 * scale_x
            y2 = y2 * scale_y
        
        # 添加到结果列表
        predictions.append({
            "class_id": class_id,
            "class_name": class_name,
            "confidence": float(confidence),
            "bbox": [float(x1), float(y1), float(x2), float(y2)]
        })
    
    # 按置信度排序
    predictions.sort(key=lambda x: x["confidence"], reverse=True)
    
    return predictions

class ONNXModel:
    """
    ONNX模型包装类
    """
    def __init__(self, model_path):
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self._load_model()
    
    def _load_model(self):
        """
        加载ONNX模型
        """
        try:
            # 只使用CPU执行提供者，避免CUDA依赖问题
            providers = ['CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            # 检查实际使用的执行提供者
            used_providers = self.session.get_providers()
            print(f"✅ ONNX模型加载成功")
            print(f"   执行提供者: {used_providers}")
        except Exception as e:
            print(f"❌ 加载ONNX模型失败: {e}")
            raise
    
    def __call__(self, image_path, conf=0.25):
        """
        执行预测
        
        :param image_path: 图片路径
        :param conf: 置信度阈值
        :return: 预测结果
        """
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            raise Exception(f"无法读取图片: {image_path}")
        
        # 预处理图片
        input_data, orig_h, orig_w = preprocess_image(image)
        
        # 进行推理
        outputs = self.session.run(None, {self.input_name: input_data})
        
        # 后处理输出
        predictions = postprocess_output(
            outputs,
            conf_threshold=conf,
            input_size=(384, 640),
            original_size=(orig_h, orig_w)
        )
        
        return predictions

class ClientHandler(threading.Thread):
    """
    客户端请求处理器
    """
    def __init__(self, client_socket, client_addr, model):
        super().__init__()
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.model = model
        self.running = True
    
    def run(self):
        """
        处理客户端请求
        """
        print(f"[{time.strftime('%H:%M:%S')}] 新客户端连接: {self.client_addr}")
        
        # 获取当前进程信息
        process = psutil.Process()
        try:
            # 设置客户端连接超时
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
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_info = process.memory_info()
                    memory_percent = process.memory_percent()
                    
                    # 记录资源占用
                    print(f"[{time.strftime('%H:%M:%S')}] 资源占用 - CPU: {cpu_percent:.2f}%, 内存: {memory_percent:.2f}% ({memory_info.rss / 1024 / 1024:.2f}MB)")
                    
                    response = {
                        'success': True,
                        'message': 'YOLO服务端运行正常',
                        'timestamp': time.time(),
                        'model_path': model_path,
                        'resource_usage': {
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory_percent,
                            'memory_rss_mb': memory_info.rss / 1024 / 1024
                        }
                    }
                else:
                    # 执行预测
                    image_path = request.get('image_path')
                    conf_threshold = request.get('conf_threshold', 0.5)
                    save_result = request.get('save_result', False)
                    output_dir = request.get('output_dir')
                    
                    if not os.path.exists(image_path):
                        response = {
                            'success': False,
                            'message': f'图片文件不存在: {image_path}'
                        }
                    else:
                        try:
                            # 执行预测
                            start_time = time.time()
                            # 设置预测超时时间为30秒
                            import threading
                            
                            # 用于存储预测结果
                            predict_result = [None]
                            predict_error = [None]
                            
                            def predict_task():
                                try:
                                    predict_result[0] = self.model(image_path, conf=conf_threshold)
                                except Exception as e:
                                    predict_error[0] = e
                            
                            # 创建并启动预测线程
                            predict_thread = threading.Thread(target=predict_task)
                            predict_thread.daemon = True
                            predict_thread.start()
                            
                            # 等待预测完成或超时
                            predict_thread.join(30)  # 30秒超时
                            
                            if predict_error[0]:
                                raise predict_error[0]
                            elif predict_result[0] is None:
                                raise TimeoutError("预测超时")
                            else:
                                predictions = predict_result[0]
                            
                            # 计算预测时间
                            predict_time = time.time() - start_time
                            
                            # 保存结果
                            if save_result and output_dir:
                                # 读取图片
                                image = cv2.imread(image_path)
                                if image is not None:
                                    # 绘制边界框
                                    for pred in predictions:
                                        x1, y1, x2, y2 = pred["bbox"]
                                        class_name = pred["class_name"]
                                        confidence = pred["confidence"]
                                        
                                        # 绘制边界框
                                        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                                        
                                        # 绘制标签
                                        label = f"{class_name}: {confidence:.2f}"
                                        cv2.putText(image, label, (int(x1), int(y1) - 10), 
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                                    
                                    # 确保输出目录存在
                                    os.makedirs(output_dir, exist_ok=True)
                                    
                                    # 保存图片
                                    img_name = os.path.basename(image_path)
                                    save_path = os.path.join(output_dir, f"result_{img_name}")
                                    cv2.imwrite(save_path, image)
                                    print(f"[{time.strftime('%H:%M:%S')}] 结果图片已保存到: {save_path}")
                            
                            # 构建响应
                            response = {
                                'success': True,
                                'total_objects': len(predictions),
                                'predictions': predictions,
                                'predict_time': predict_time
                            }
                            
                        except Exception as e:
                            print(f"[{time.strftime('%H:%M:%S')}] 预测出错: {e}")
                            import traceback
                            traceback.print_exc()
                            response = {
                                'success': False,
                                'message': f'预测过程出错: {e}'
                            }
                
                # 发送响应
                response_str = json.dumps(response, ensure_ascii=False) + '\nEOF\n'
                print(f"[{time.strftime('%H:%M:%S')}] 发送响应: {response_str[:100]}...")
                try:
                    self.client_socket.sendall(response_str.encode('utf-8'))
                    print(f"[{time.strftime('%H:%M:%S')}] 响应发送成功")
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] 发送响应出错: {e}")
                    self.running = False
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 处理请求出错: {e}")
        finally:
            try:
                self.client_socket.close()
                print(f"[{time.strftime('%H:%M:%S')}] 客户端连接已关闭: {self.client_addr}")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] 关闭客户端连接出错: {e}")

def main():
    """
    主函数
    """
    # Ensure UTF-8 output regardless of console/file encoding
    import sys as _sys
    if hasattr(_sys.stdout, 'reconfigure'):
        _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(_sys.stderr, 'reconfigure'):
        _sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 60)
    print("YOLO Server")
    print("=" * 60)
    print(f"Model: {model_path}")
    print(f"Listen: {HOST}:{PORT}")
    print("=" * 60)

    # Load model
    print(f"[{time.strftime('%H:%M:%S')}] Loading ONNX model...")
    start_time = time.time()
    try:
        model = ONNXModel(model_path)
        load_time = time.time() - start_time
        print(f"[{time.strftime('%H:%M:%S')}] ONNX model loaded in {load_time:.2f}s")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Model load failed: {e}")
        return
    
    # 创建服务器套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # 绑定地址
        server_socket.bind((HOST, PORT))
        # 监听连接
        server_socket.listen(5)
        print(f"[{time.strftime('%H:%M:%S')}] YOLO server started on {HOST}:{PORT}")
        print(f"[{time.strftime('%H:%M:%S')}] Model: {model_path}")
        print(f"[{time.strftime('%H:%M:%S')}] Waiting for connections...")
        
        while True:
            # 接受客户端连接
            client_socket, client_addr = server_socket.accept()
            print(f"[{time.strftime('%H:%M:%S')}] 接收到新连接: {client_addr}")
            
            # 创建客户端处理器
            handler = ClientHandler(client_socket, client_addr, model)
            handler.daemon = True
            handler.start()
            
    except KeyboardInterrupt:
        print(f"[{time.strftime('%H:%M:%S')}] 服务端收到中断信号，正在关闭...")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 服务端出错: {e}")
    finally:
        # 关闭服务器套接字
        try:
            server_socket.close()
            print(f"[{time.strftime('%H:%M:%S')}] Server socket closed")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Close socket error: {e}")

if __name__ == "__main__":
    main()