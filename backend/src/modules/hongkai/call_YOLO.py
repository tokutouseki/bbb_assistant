#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO模型调用模块

文件说明：
    本模块提供了YOLO模型的调用接口，支持两种调用方式：
    1. TCP客户端-服务端模式（优先）：通过TCP连接调用持久化的YOLO服务端，
       模型只加载一次，支持并发请求，大幅提高调用效率
    2. Subprocess模式（回退）：通过subprocess直接调用YOLO模型，
       每次调用都会重新加载模型，适合服务端无法启动的情况

主要功能：
    - 自动管理YOLO服务端的启动和状态检查
    - 提供单例YOLO客户端，避免重复创建连接
    - 支持自动重连机制，提高服务稳定性
    - 支持置信度阈值设置
    - 支持检测结果保存
    - 提供统一的调用接口，屏蔽底层实现细节

使用说明：
    1. 基本调用：
       ```python
       from call_YOLO import call_yolo_model
       result = call_yolo_model(image_path="path/to/image.jpg")
       ```
    
    2. 带参数调用：
       ```python
       result = call_yolo_model(
           image_path="path/to/image.jpg",
           conf_threshold=0.6,  # 设置置信度阈值为0.6
           output_dir="path/to/output"  # 保存检测结果
       )
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

依赖文件：
    - yolo_client.py：YOLO客户端实现
    - yolo_server_final.py：YOLO服务端实现
    - YOLO模型文件：默认存放在Python3.11/yolo/models目录下

注意事项：
    - 首次调用时会自动启动YOLO服务端，可能需要几秒钟时间
    - 服务端会在后台持续运行，直到程序退出
    - 支持自动重连机制，服务端异常退出后会自动重启
    - 日志信息会输出到控制台，便于调试
"""

import subprocess
import json
import os
import sys
import datetime
import time
import socket
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))

_yolo_client = None
_yolo_server_process = None
_yolo_server_running = False
_last_success_time = 0
CLIENT_TIMEOUT = 60


def reset_yolo_client():
    """
    重置YOLO客户端（关闭旧连接并创建新连接）
    在检测到客户端卡死时调用
    """
    global _yolo_client
    print(f"YOLO调试：正在重置YOLO客户端...")
    if _yolo_client:
        try:
            _yolo_client.close()
        except Exception as e:
            print(f"YOLO调试：关闭旧客户端连接时出错: {e}")
        _yolo_client = None
    print(f"YOLO调试：YOLO客户端已重置")


def _start_yolo_server():
    """
    启动YOLO服务端
    
    Returns:
        bool: 服务端是否启动成功
    """
    global _yolo_server_process, _yolo_server_running
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5001))
        s.close()
        print(f"YOLO调试：YOLO服务端已经在运行")
        _yolo_server_running = True
        return True
    except ConnectionRefusedError:
        pass
    except Exception as e:
        print(f"YOLO调试：检查服务端状态时出错: {e}")
    
    server_script = os.path.join(current_dir, 'yolo_server_final.py')
    # 优先使用系统 Python（bbb-assistant 环境），回退到 hongkai_done 自带的 Python 3.11
    python_executable = sys.executable
    if not os.path.exists(python_executable):
        python_executable = os.path.join(current_dir, 'Python3.11', 'python.exe')
        # 如果当前目录没有，尝试原 hongkai_done 路径
        if not os.path.exists(python_executable):
            python_executable = r"D:\hongkai_done\Python3.11\python.exe"
    
    try:
        print(f"YOLO调试：正在启动YOLO服务端...")
        log_dir = os.path.join(current_dir, 'all_log')
        os.makedirs(log_dir, exist_ok=True)
        yolo_log_path = os.path.join(log_dir, 'yolo_server.log')
        yolo_log = open(yolo_log_path, 'a', encoding='utf-8')
        yolo_log.write(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] YOLO服务端启动\n")
        yolo_log.flush()

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        _yolo_server_process = subprocess.Popen(
            [python_executable, server_script],
            stdout=yolo_log,
            stderr=yolo_log,
            text=True,
            encoding='utf-8',
            env=env,
            shell=False
        )

        max_wait_time = 20
        wait_time = 0
        while wait_time < max_wait_time:
            time.sleep(1)
            wait_time += 1
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('127.0.0.1', 5001))
                s.close()
                print(f"YOLO调试：YOLO服务端启动成功，耗时 {wait_time} 秒")
                _yolo_server_running = True
                return True
            except ConnectionRefusedError:
                print(f"YOLO调试：等待服务端启动中... ({wait_time}/{max_wait_time}秒)")
                continue
            except Exception as e:
                print(f"YOLO调试：检查服务端启动状态时出错: {e}")
                continue
        
        print(f"YOLO调试：YOLO服务端启动超时，无法连接")
        try:
            _yolo_server_process.terminate()
            _yolo_server_process.wait(timeout=5)
        except:
            pass
        _yolo_server_process = None
        _yolo_server_running = False
        return False
    except Exception as e:
        print(f"YOLO调试：启动YOLO服务端时出错: {e}")
        _yolo_server_running = False
        return False


def _get_yolo_client():
    """
    获取单例YOLO客户端实例
    
    Returns:
        YOLOClient: 单例YOLO客户端实例
    """
    global _yolo_client
    if _yolo_client is None:
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from yolo_client import YOLOClient
            _yolo_client = YOLOClient()
        except Exception as e:
            print(f"YOLO调试：创建YOLO客户端失败，将回退到subprocess调用: {e}")
            import traceback
            traceback.print_exc()
    return _yolo_client


def _check_yolo_server_health():
    """
    检查YOLO服务端健康状态
    
    Returns:
        bool: 服务端是否健康
    """
    print("\n执行YOLO服务端健康检查...")
    
    client = _get_yolo_client()
    if not client:
        print("YOLO调试：无法创建客户端，服务端可能未启动")
        return False
    
    try:
        # 发送健康检查请求
        # 创建健康检查请求数据
        request = {
            "health_check": True
        }
        
        # 连接到服务端
        if not client.client_socket:
            if not client.connect():
                print("YOLO调试：无法连接到服务端")
                return False
        
        # 发送请求
        request_str = json.dumps(request, ensure_ascii=False) + "\nEOF\n"
        client.client_socket.sendall(request_str.encode('utf-8'))
        
        # 接收响应
        response_data = b""
        start_time = time.time()
        
        while (time.time() - start_time) < 10:  # 健康检查超时时间为10秒
            chunk = client.client_socket.recv(4096)
            if not chunk:
                # 连接已关闭
                client.close()
                print("YOLO调试：服务端连接已关闭")
                return False
            response_data += chunk
            if b"\nEOF\n" in response_data:
                break
        
        if not response_data:
            print("YOLO调试：健康检查请求超时")
            return False
        
        # 解析响应
        response_data = response_data.replace(b"\nEOF\n", b"")
        response = json.loads(response_data.decode('utf-8'))
        
        if response.get("success", False):
            # 检查资源占用情况
            resource_usage = response.get('resource_usage', {})
            if resource_usage:
                cpu_percent = resource_usage.get('cpu_percent', 0)
                memory_percent = resource_usage.get('memory_percent', 0)
                print(f"YOLO调试：服务端资源占用 - CPU: {cpu_percent:.2f}%, 内存: {memory_percent:.2f}%")
                
                # 如果资源占用过高，返回不健康
                if cpu_percent > 90 or memory_percent > 90:
                    print("YOLO调试：服务端资源占用过高，需要重启")
                    return False
            
            print(f"YOLO调试：服务端健康检查通过: {response.get('message')}")
            return True
        else:
            print(f"YOLO调试：服务端健康检查失败: {response.get('message')}")
            return False
    except ConnectionResetError:
        print("YOLO调试：连接被服务端重置")
        client.close()
        return False
    except ConnectionAbortedError:
        print("YOLO调试：连接被中止")
        client.close()
        return False
    except Exception as e:
        print(f"YOLO调试：健康检查过程中出错: {e}")
        client.close()
        return False


def _call_yolo_server(image_path, conf_threshold=0.5, output_dir=None):
    """
    调用YOLO服务端进行预测
    
    Args:
        image_path (str): 图片文件路径
        conf_threshold (float): 置信度阈值
        output_dir (str, optional): 输出结果目录
    
    Returns:
        dict: 预测结果
    """
    global _last_success_time
    
    # 检查服务端健康状态
    health_check = _check_yolo_server_health()
    if not health_check:
        print("\nYOLO服务端不健康，尝试重启服务端...")
        reset_yolo_client()
        _start_yolo_server()
    elif not _yolo_server_running:
        print("\nYOLO服务端未运行，尝试启动服务端...")
        _start_yolo_server()
    
    client = _get_yolo_client()
    if client:
        result = client.predict_with_reconnect(image_path, conf_threshold, bool(output_dir), output_dir)
        
        # 检查服务端是否无响应或连接异常
        if not result.get("success", False):
            message = result.get("message", "")
            if any(error in message for error in ["timed out", "服务端关闭了连接", "连接被重置", "连接被中止"]):
                print("\nYOLO服务端连接异常，尝试重启服务端...")
                
                # 重置客户端
                reset_yolo_client()
                
                # 重启服务端
                _start_yolo_server()
                
                # 重新获取客户端并尝试预测
                client = _get_yolo_client()
                if client:
                    print("\n服务端重启完成，重新尝试预测...")
                    result = client.predict_with_reconnect(image_path, conf_threshold, bool(output_dir), output_dir)
        
        if result.get("success", False):
            _last_success_time = time.time()
            print("YOLO调试：预测成功，服务端运行正常")
        else:
            print(f"YOLO调试：预测失败，服务端可能存在问题: {result.get('message')}")
        return result
    print("YOLO调试：无法创建客户端，将回退到subprocess调用")
    return None


def _call_yolo_subprocess(image_path, 
                          model_path=None,
                          conf_threshold=0.5,
                          python_executable=None,
                          output_dir=None):
    """
    使用subprocess调用YOLO模型进行图像预测（回退方案）
    """
    if python_executable is None:
        python_executable = os.path.join(current_dir, 'Python3.11', 'python.exe')
        print(f"YOLO调试：使用默认Python解释器: {python_executable}")
    else:
        print(f"YOLO调试：使用指定Python解释器: {python_executable}")
    
    predict_script = os.path.join(current_dir, 'Python3.11', 'yolo', 'To_use', 'predict.py')
    print(f"YOLO调试：predict.py脚本路径: {predict_script}")
    
    cmd = [
        python_executable,
        predict_script,
        '--img', image_path,
        '--conf', str(conf_threshold),
        '--json', 'True'
    ]
    
    if model_path:
        cmd.extend(['--model', model_path])
        print(f"YOLO调试：使用指定模型路径: {model_path}")
    else:
        print(f"YOLO调试：使用默认模型")
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        cmd.extend(['--save', 'True'])
        print(f"YOLO调试：保存检测结果到目录: {output_dir}")
    else:
        print(f"YOLO调试：不保存检测结果")
    
    print(f"YOLO调试：完整命令: {' '.join(cmd)}")
    
    try:
        subprocess_start = time.time()
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"YOLO调试：开始执行subprocess命令，时间: {current_time}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            timeout=60
        )
        
        subprocess_end = time.time()
        print(f"YOLO调试：subprocess命令执行完成，耗时: {subprocess_end - subprocess_start:.2f}秒")
        print(f"YOLO调试：subprocess返回码: {result.returncode}")
        
        if result.returncode == 0:
            print(f"YOLO调试：开始解析JSON输出")
            parse_start = time.time()
            try:
                raw_output = result.stdout
                if len(raw_output) > 200:
                    print(f"YOLO调试：原始输出前100字符: {raw_output[:100]}...")
                    print(f"YOLO调试：原始输出后100字符: ...{raw_output[-100:]}")
                else:
                    print(f"YOLO调试：原始输出: {raw_output}")
                
                json_start_pos = raw_output.find('{')
                if json_start_pos != -1:
                    json_end_pos = raw_output.rfind('}') + 1
                    if json_end_pos > json_start_pos:
                        json_content = raw_output[json_start_pos:json_end_pos]
                        print(f"YOLO调试：提取到JSON内容，长度: {len(json_content)}字符")
                        output_data = json.loads(json_content)
                        parse_end = time.time()
                        print(f"YOLO调试：JSON解析完成，耗时: {parse_end - parse_start:.2f}秒")
                        return output_data
                return {
                    "success": False,
                    "message": "未找到有效的JSON内容",
                    "raw_output": raw_output
                }
            except json.JSONDecodeError as e:
                parse_end = time.time()
                print(f"YOLO调试：JSON解析失败，耗时: {parse_end - parse_start:.2f}秒，错误: {e}")
                return {
                    "success": False,
                    "message": "JSON解析失败",
                    "error": str(e),
                    "raw_output": raw_output
                }
        else:
            print(f"YOLO调试：命令执行失败，stderr: {result.stderr[:200]}...")
            print(f"YOLO调试：命令执行失败，stdout: {result.stdout[:200]}...")
            return {
                "success": False,
                "message": "命令执行失败",
                "return_code": result.returncode,
                "stderr": result.stderr,
                "stdout": result.stdout
            }
    
    except subprocess.TimeoutExpired:
        print(f"YOLO调试：subprocess调用超时（60秒）")
        return {
            "success": False,
            "message": "subprocess调用超时"
        }
    except Exception as e:
        print(f"YOLO调试：subprocess调用过程中发生异常: {e}")
        return {
            "success": False,
            "message": "subprocess调用过程中发生异常",
            "error": str(e)
        }


def call_yolo_model(image_path, 
                   model_path=None,
                   conf_threshold=0.5,
                   python_executable=None,
                   output_dir=None):
    """
    调用YOLO模型进行图像预测
    
    Args:
        image_path (str): 图片文件路径
        model_path (str, optional): 模型文件路径
        conf_threshold (float, optional): 置信度阈值
        python_executable (str, optional): Python解释器路径
        output_dir (str, optional): 输出结果目录
    
    Returns:
        dict: 预测结果（JSON格式解析后的数据）
    """
    global _last_success_time
    
    if not os.path.exists(image_path):
        return {
            "success": False,
            "message": f"图片文件不存在: {image_path}"
        }
    
    result = _call_yolo_server(image_path, conf_threshold, output_dir)
    if result is not None:
        return result
    
    result = _call_yolo_subprocess(image_path, model_path, conf_threshold, python_executable, output_dir)
    return result


def filter_guaiwu_ui_upper_half(screenshot_path, predictions):
    """
    过滤 guaiwu_xueliang_UI 检测结果，仅保留屏幕上半区的检测。
    避免下半区的怪物血条干扰检测。
    """
    from PIL import Image
    img = Image.open(screenshot_path)
    img_height = img.height

    filtered = []
    for pred in predictions:
        if pred.get("class_name") == "guaiwu_xueliang_UI":
            bbox = pred.get("bbox", [])
            if len(bbox) == 4:
                center_y = (bbox[1] + bbox[3]) / 2
                if center_y >= img_height / 2:
                    continue
        filtered.append(pred)

    return filtered


if __name__ == "__main__":
    example_image = os.path.join(current_dir, 'Python3.11', 'yolo', 'To_test', 'example.jpg')
    example_model = None
    conf_threshold = 0.5
    output_dir = os.path.join(current_dir, 'Python3.11', 'yolo', 'To_use', 'predict_results')
    
    print("正在调用YOLO模型进行预测...")
    print(f"图片路径: {example_image}")
    if example_model:
        print(f"模型路径: {example_model}")
    print(f"置信度阈值: {conf_threshold}")
    print(f"输出目录: {output_dir}")
    
    prediction_result = call_yolo_model(
        image_path=example_image,
        model_path=example_model,
        conf_threshold=conf_threshold,
        output_dir=output_dir
    )
    
    print("\n预测结果:")
    print(json.dumps(prediction_result, ensure_ascii=False, indent=2))
    
    if prediction_result.get("success", False):
        print(f"\n🎉 成功识别到 {prediction_result.get('total_objects', 0)} 个目标")
        
        for i, obj in enumerate(prediction_result.get('predictions', []), 1):
            class_name = obj.get('class_name', '未知')
            confidence = obj.get('confidence', 0.0)
            bbox = obj.get('bbox', [])
            
            print(f"\n📌 目标 {i}:")
            print(f"   类别: {class_name}")
            print(f"   置信度: {confidence:.4f}")
            print(f"   边界框: {bbox}")
            
            if bbox:
                print(f"   位置: 左上角({bbox[0]:.2f}, {bbox[1]:.2f}), 右下角({bbox[2]:.2f}, {bbox[3]:.2f})")
