#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BH3窗口YOLO识别工具

文件说明：
    本工具用于截取BH3（崩坏3）游戏窗口内容，使用YOLO模型进行元素识别，
    保存结果并输出识别元素的标签和坐标。适合用于自动化测试、游戏辅助等场景。

主要功能：
    - 自动截取BH3游戏窗口
    - 使用YOLO模型识别窗口中的元素
    - 输出识别元素的标签和坐标
    - 支持保存原始截图
    - 支持保存检测结果图片
    - 将识别结果保存为JSON格式
    - 提供命令行参数支持

使用说明：
    1. 命令行使用：
       ```
       # 基本使用（不保存截图）
       python bh3_yolo_recognizer.py
       
       # 保存原始截图
       python bh3_yolo_recognizer.py --save-screenshot
       
       # 保存检测结果图片
       python bh3_yolo_recognizer.py --save-detection
       
       # 同时保存原始截图和检测结果
       python bh3_yolo_recognizer.py --save-screenshot --save-detection
       ```
    
    2. 作为模块调用：
       ```python
       from bh3_yolo_recognizer import bh3_yolo_recognize
       
       # 基本使用
       result = bh3_yolo_recognize()
       
       # 保存原始截图和检测结果
       result = bh3_yolo_recognize(
           save_screenshot=True,
           save_detection_result=True
       )
       ```
    
    3. 结果解析：
       ```python
       if result.get("success"):
           print(f"共识别到 {result.get('total_objects')} 个元素")
           for elem in result.get('elements', []):
               class_name = elem.get('class_name')
               confidence = elem.get('confidence')
               bbox = elem.get('bbox')  # [x1, y1, x2, y2]
               print(f"{class_name}: 置信度={confidence:.4f}, 坐标={bbox}")
       ```

依赖文件：
    - character/letu_find_way.py：用于截取BH3窗口
    - call_YOLO.py：用于调用YOLO模型
    - yolo_client.py：YOLO客户端实现
    - yolo_server_final.py：YOLO服务端实现
    - YOLO模型文件：默认存放在Python3.11/yolo/models目录下

输出结果：
    - 控制台输出：识别元素的标签、置信度和坐标
    - 原始截图：默认保存到photos/bh3_screenshot目录
    - 检测结果图片：默认保存到photos/bh3_YOLO_checked目录

注意事项：
    - 确保BH3游戏窗口已经打开且可见
    - 首次运行时会自动启动YOLO服务端，可能需要几秒钟时间
    - 识别结果的置信度阈值默认为0.5
    - 支持的元素类型由YOLO模型决定
    - 输出的坐标格式为[x1, y1, x2, y2]，表示元素的左上角和右下角坐标

示例输出：
    ==================================================
    BH3窗口YOLO识别工具
    ==================================================
    
    1. 正在截取BH3窗口...
    ✅ 截图成功，保存路径: d:\TokusCode\python\hongkai\photos\bh3_screenshot\bh3_screenshot_1768540917.jpg
    
    2. 正在使用YOLO模型识别...
    ✅ 识别完成，耗时: 0.35秒
    
    3. 识别结果：
    📊 共识别到 3 个元素
    
    4. 元素详细信息：
    ==============================
    | 标签	| 置信度	| 坐标			|
    ==============================
    | kongmeng	| 0.9234	| [100.5, 200.3, 300.2, 400.1]	|
    | elysia_star	| 0.8765	| [400.2, 500.1, 500.3, 600.2]	|
    | xvguang	| 0.7890	| [600.1, 700.2, 800.3, 900.4]	|
    ==============================
    ```
"""

import os
import sys
import time
import json

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入所需模块
from character.letu_find_way import take_bh3_screenshot
from call_YOLO import call_yolo_model, filter_guaiwu_ui_upper_half


def bh3_yolo_recognize(save_screenshot=False, save_detection_result=False):
    """
    截取BH3窗口内容，使用YOLO模型识别，保存结果并输出识别元素的标签和坐标
    
    Args:
        save_screenshot (bool): 是否保存原始截图
        save_detection_result (bool): 是否保存检测结果图片
        
    Returns:
        dict: 识别结果，包含成功状态、识别元素列表等
    """
    print("=" * 50)
    print("BH3窗口YOLO识别工具")
    print("=" * 50)
    
    # 1. 截取BH3窗口
    print("\n1. 正在截取BH3窗口...")
    screenshot_path = take_bh3_screenshot()
    
    if not screenshot_path:
        print("❌ 截取BH3窗口失败")
        return {
            "success": False,
            "message": "截取BH3窗口失败"
        }
    
    print(f"✅ 截图成功，保存路径: {screenshot_path}")
    
    # 2. 设置输出目录
    output_dir = None
    if save_detection_result:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos", "bh3_YOLO_checked")
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 检测结果将保存到: {output_dir}")
    
    # 3. 使用YOLO模型进行识别
    print("\n2. 正在使用YOLO模型识别...")
    start_time = time.time()
    
    result = call_yolo_model(
        image_path=screenshot_path,
        conf_threshold=0.5,
        output_dir=output_dir
    )
    
    end_time = time.time()
    print(f"✅ 识别完成，耗时: {end_time - start_time:.2f}秒")
    
    # 4. 输出识别结果
    print("\n3. 识别结果：")
    if result.get("success", False):
        predictions = result.get("predictions", [])
        predictions = filter_guaiwu_ui_upper_half(screenshot_path, predictions)
        result["predictions"] = predictions
        total_objects = len(predictions)
        print(f"📊 共识别到 {total_objects} 个元素")

        print("\n4. 元素详细信息：")
        print("=" * 30)
        print("| 标签\t| 置信度\t| 坐标\t		|")
        print("=" * 30)

        for i, pred in enumerate(predictions, 1):
            class_name = pred.get("class_name", "未知")
            confidence = pred.get("confidence", 0.0)
            bbox = pred.get("bbox", [])

            # 格式化输出
            print(f"| {class_name}\t| {confidence:.4f}\t| {bbox}\t|")

        print("=" * 30)

        return {
            "success": True,
            "message": "识别成功",
            "total_objects": total_objects,
            "elements": predictions,
            "screenshot_path": screenshot_path
        }
    else:
        print(f"❌ 识别失败: {result.get('message', '未知错误')}")
        return {
            "success": False,
            "message": f"识别失败: {result.get('message', '未知错误')}"
        }


def main():
    """
    主函数
    """
    print("BH3窗口YOLO识别工具")
    print("=" * 50)
    
    # 解析命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description="BH3窗口YOLO识别工具")
    parser.add_argument("--save-screenshot", action="store_true", help="保存原始截图")
    parser.add_argument("--save-detection", action="store_true", help="保存检测结果图片")
    
    args = parser.parse_args()
    
    # 执行识别
    result = bh3_yolo_recognize(
        save_screenshot=args.save_screenshot,
        save_detection_result=args.save_detection
    )
    
    # 返回结果
    if result["success"]:
        print("\n🎉 识别完成！")
        sys.exit(0)
    else:
        print("\n💥 识别失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
