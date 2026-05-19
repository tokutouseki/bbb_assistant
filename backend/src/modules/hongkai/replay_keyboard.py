import json
import time
import os
import pyautogui
import sys

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import all_log.save_output
from on_window import focus_bh3_window, run_as_admin, is_admin

def replay_keyboard_events(json_file_path, stop_event=None, debug=False):
    """
    复现JSON文件中记录的键盘事件和鼠标事件
    :param json_file_path: JSON文件路径
    :param stop_event: 用于接收停止信号的事件对象，可选
    :param debug: 是否显示调试信息，默认False
    :return: None
    """
    # 检查文件是否存在
    if not os.path.exists(json_file_path):
        print(f"文件不存在: {json_file_path}")
        return
    
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 获取所有事件并合并排序
    all_events = []
    
    # 添加键盘事件
    keyboard_events = data.get("键盘事件", [])
    for event in keyboard_events:
        all_events.append({
            "type": "keyboard",
            "event": event,
            "start_time": event.get("按下时间(秒)")
        })
    
    # 添加鼠标事件
    mouse_events = data.get("鼠标事件", [])
    for event in mouse_events:
        all_events.append({
            "type": "mouse",
            "event": event,
            "start_time": event.get("按下时间(秒)") or event.get("开始滑动时间(秒)")
        })
    
    # 按开始时间排序所有事件
    all_events.sort(key=lambda x: x["start_time"])
    
    if not all_events:
        print("JSON文件中没有找到可复现的事件")
        return
    
    if debug:
        print(f"开始复现事件，共 {len(all_events)} 个事件")
    
    # 用于跟踪按键状态
    current_keys = {}
    
    # 按时间顺序处理事件
    for i, item in enumerate(all_events):
        # 检查是否收到停止信号
        if stop_event and stop_event.is_set():
            print("收到停止信号，停止复现")
            return
            
        event_type = item["type"]
        event = item["event"]
        start_time = item["start_time"]
        
        if debug:
            print(f"\n事件 {i+1}/{len(all_events)}:")
        
        # 等待到指定时间点
        if i == 0:
            # 第一个操作，等待从记录开始到该操作的时间间隔
            wait_time = start_time
            if wait_time > 0:
                if debug:
                    print(f"  等待 {wait_time:.2f} 秒（记录开始到第一个操作的时间）")
                # 在等待过程中检查停止信号
                time_remaining = wait_time
                while time_remaining > 0:
                    # 每次等待0.1秒
                    sleep_time = min(0.1, time_remaining)
                    time.sleep(sleep_time)
                    time_remaining -= sleep_time
                    
                    # 检查是否收到停止信号
                    if stop_event and stop_event.is_set():
                        print("收到停止信号，停止复现")
                        return
                
                # 如果还有剩余时间，继续等待
                time.sleep(time_remaining) if time_remaining > 0 else None
        else:
            prev_item = all_events[i-1]
            prev_start_time = prev_item["start_time"]
            
            # 计算上一个事件的结束时间
            if prev_item["type"] == "keyboard":
                prev_end_time = prev_item["event"].get("松开时间(秒)")
            elif prev_item["event"].get("类型") == "左键按下":
                prev_end_time = prev_item["event"].get("松开时间(秒)")
            else:  # 滑轮滚动等瞬间事件
                prev_end_time = prev_start_time
            
            # 计算需要等待的时间
            wait_time = start_time - prev_end_time
            if wait_time > 0:
                if debug:
                    print(f"  等待 {wait_time:.2f} 秒")
                # 在等待过程中检查停止信号
                time_remaining = wait_time
                while time_remaining > 0:
                    # 每次等待0.1秒
                    sleep_time = min(0.1, time_remaining)
                    time.sleep(sleep_time)
                    time_remaining -= sleep_time
                    
                    # 检查是否收到停止信号
                    if stop_event and stop_event.is_set():
                        print("收到停止信号，停止复现")
                        return
                
                # 如果还有剩余时间，继续等待
                time.sleep(time_remaining) if time_remaining > 0 else None
        
        # 处理键盘事件
        if event_type == "keyboard":
            key = event.get("按键")
            press_time = event.get("按下时间(秒)")
            release_time = event.get("松开时间(秒)")
            duration = event.get("持续时长(秒)", 0)
            
            if debug:
                print(f"  类型: 键盘事件")
                print(f"  按键: {key}")
                print(f"  按下时间: {press_time} 秒")
                print(f"  松开时间: {release_time} 秒")
                print(f"  持续时长: {duration} 秒")
            
            # 转换中文键名为英文键名
            key_map = {
                "大写锁定键": "caps_lock",
                "前进": "w",
                "左移": "a",
                "后退": "s",
                "右移": "d",
                "普攻": "j",
                "闪避": "k",
                "星之环": "l",
                "武器": "u",
                "大招": "i",
                "1": "1",
                "2": "2"
            }
            
            # 如果是中文键名，转换为英文
            if key in key_map:
                english_key = key_map[key]
            else:
                # 直接使用键名
                english_key = key
            
            # 执行按键按下
            print(f"按下 {key} 键")
            pyautogui.keyDown(english_key)
            
            # 等待到松开时间
            if release_time > press_time:
                hold_time = release_time - press_time
                if debug:
                    print(f"  按住 {hold_time:.2f} 秒")
                
                # 在按住过程中检查停止信号
                time_remaining = hold_time
                while time_remaining > 0:
                    # 每次等待0.1秒
                    sleep_time = min(0.1, time_remaining)
                    time.sleep(sleep_time)
                    time_remaining -= sleep_time
                    
                    # 检查是否收到停止信号
                    if stop_event and stop_event.is_set():
                        print("收到停止信号，停止复现")
                        # 确保松开当前按键
                        pyautogui.keyUp(english_key)
                        return
                
                # 如果还有剩余时间，继续等待
                time.sleep(time_remaining) if time_remaining > 0 else None
            
            # 执行按键松开
            print(f"松开 {key} 键")
            pyautogui.keyUp(english_key)
        
        # 处理鼠标事件
        elif event_type == "mouse":
            mouse_type = event.get("类型")
            x = event.get("x坐标")
            y = event.get("y坐标")
            
            if mouse_type == "左键按下":
                press_time = event.get("按下时间(秒)")
                release_time = event.get("松开时间(秒)")
                duration = event.get("持续时长(秒)", 0)
                
                if debug:
                    print(f"  类型: 鼠标左键点击")
                    print(f"  坐标: ({x}, {y})")
                    print(f"  按下时间: {press_time} 秒")
                    print(f"  松开时间: {release_time} 秒")
                    print(f"  持续时长: {duration} 秒")
                
                # 移动鼠标到指定位置
                if debug:
                    print(f"  执行: 移动鼠标到 ({x}, {y})")
                pyautogui.moveTo(x, y)
                
                # 执行鼠标按下
                if debug:
                    print(f"  执行: 按下鼠标左键")
                pyautogui.mouseDown(button='left')
                
                # 等待到松开时间
                if release_time > press_time:
                    hold_time = release_time - press_time
                    if debug:
                        print(f"  按住 {hold_time:.2f} 秒")
                    
                    # 在按住过程中检查停止信号
                    time_remaining = hold_time
                    while time_remaining > 0:
                        # 每次等待0.1秒
                        sleep_time = min(0.1, time_remaining)
                        time.sleep(sleep_time)
                        time_remaining -= sleep_time
                        
                        # 检查是否收到停止信号
                        if stop_event and stop_event.is_set():
                            print("收到停止信号，停止复现")
                            # 确保松开当前鼠标按钮
                            pyautogui.mouseUp(button='left')
                            return
                    
                    # 如果还有剩余时间，继续等待
                    time.sleep(time_remaining) if time_remaining > 0 else None
                
                # 执行鼠标松开
                if debug:
                    print(f"  执行: 松开鼠标左键")
                pyautogui.mouseUp(button='left')
            
            elif mouse_type == "滑轮滚动":
                scroll_time = event.get("开始滑动时间(秒)")
                scroll_direction = event.get("滚动方向")
                if debug:
                    print(f"  类型: 鼠标滑轮滚动")
                    print(f"  坐标: ({x}, {y})")
                    print(f"  滚动时间: {scroll_time} 秒")
                    print(f"  滚动方向: {scroll_direction}")
                
                # 移动鼠标到指定位置
                if debug:
                    print(f"  执行: 移动鼠标到 ({x}, {y})")
                pyautogui.moveTo(x, y)
                
                # 根据滚动方向执行滑轮滚动
                scroll_amount = 1 if scroll_direction == "向上" else -1
                if debug:
                    print(f"  执行: 滑轮{scroll_direction}滚动")
                pyautogui.scroll(scroll_amount)  # 正数表示向上滚动，负数表示向下滚动
    
    if debug:
        print(f"\n所有事件复现完成")


if __name__ == "__main__":
    """
    主函数，用于直接运行脚本
    """
    
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
    
    # 调用复现函数
    replay_keyboard_events(json_file_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "reproduce", "letu_elysia_star_jiaxin_fangting_loop.json"))


