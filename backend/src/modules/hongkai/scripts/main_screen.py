import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from on_window import focus_bh3_window
from call_YOLO import call_yolo_model
import templates.clicks_keyboard as ck

# 识别elysia_star是否存在的函数
def detect_elysia_star():
    """
    使用YOLO模型检测当前屏幕中是否存在elysia_star
    
    Returns:
        bool: 如果检测到elysia_star返回True，否则返回False
    """
    import tempfile
    from PIL import Image
    from src.modules.vision.screen_capture import ScreenCapture

    # 截取游戏客户区
    screenshot_np = ScreenCapture().capture_game_client_area()
    screenshot = Image.fromarray(screenshot_np)

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        temp_image_path = tmp_file.name
        screenshot.save(temp_image_path)
    
    try:
        # 调用YOLO模型进行检测
        print("\n执行YOLO模型检测elysia_star：")
        result = call_yolo_model(
            image_path=temp_image_path,
            conf_threshold=0.7
        )
        
        # 检查结果
        if result.get("success", False):
            predictions = result.get("predictions", [])
            # 遍历所有预测结果，检查是否有elysia_star
            for pred in predictions:
                class_name = pred.get("class_name", "")
                if class_name == "elysia_star":
                    confidence = pred.get("confidence", 0)
                    print(f"检测到elysia_star，置信度: {confidence:.4f}")
                    return True
            print("未检测到elysia_star")
            focus_bh3_window()
        else:
            print(f"YOLO检测失败: {result.get('message', '未知错误')}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except Exception as e:
                print(f"清理临时文件时出错: {e}")

# 清理消息函数
def clear_messages(max_retries=10):
    """
    清理消息，最多尝试max_retries次
    
    Args:
        max_retries: 最大尝试次数，默认10次
        
    Returns:
        bool: 是否成功清理消息
    """
    retry_count = 0
    
    while retry_count < max_retries:
        retry_count += 1
        # 检测elysia_star
        print(f"\n执行elysia_star检测（{retry_count}/{max_retries}）：")
        has_elysia_star = detect_elysia_star()
        
        if has_elysia_star:
            # 再次检测一次
            print("\n再次执行elysia_star检测：")
            has_elysia_star_second = detect_elysia_star()
            
            if has_elysia_star_second:
                # 若两次都检测到则退出循环
                print("两次检测都到elysia_star，退出清理消息操作！")
                time.sleep(2)
                return True
            else:
                # 若无则使用ck.keyboard_esc_press_release函数
                print("\n第二次未检测到elysia_star，执行ESC键操作：")
                success_esc = ck.keyboard_esc_press_release()
                if success_esc:
                    print("成功按下并释放了'ESC'键！")
                else:
                    print("按下并释放'ESC'键失败！")
                time.sleep(1.5)
                # 继续循环
        else:
            # 若没检测到elysia_star，则使用ck.keyboard_esc_press_release函数
            print("\n未检测到elysia_star，执行ESC键操作：")
            success_esc = ck.keyboard_esc_press_release()
            if success_esc:
                print("成功按下并释放了'ESC'键！")
            else:
                print("按下并释放'ESC'键失败！")
            time.sleep(1.5)
            # 继续循环
    
    print(f"\n已达到最大重试次数{max_retries}次，退出清理消息操作！")
    time.sleep(2)
    return False

# 主界面处理函数
def make_on_main():
    """
    处理主界面操作，包括检测elysia_star和清理消息
    
    Returns:
        bool: 操作是否成功
    """
    # 清理消息，最多尝试10次
    print("\n执行清理消息操作...")
    success = clear_messages(max_retries=10)
    
    # 确保窗口聚焦
    focus_bh3_window()
    
    print("\n主界面处理完成！")
    return success

if __name__ == "__main__":
    make_on_main()