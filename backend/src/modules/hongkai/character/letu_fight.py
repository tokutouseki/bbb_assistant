import os
import sys
import time
import argparse
import pyautogui
import threading

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入必要的模块
from replay_keyboard import replay_keyboard_events
from templates.clicks_keyboard import is_complex_temp
from bh3_yolo_recognizer import bh3_yolo_recognize

# 取样计数器（防止磁盘爆满）
_sample_counter = [0]
_MAX_SAMPLES = 10


def _sample_stop_vs_yolo(debug=False):
    """当停止图片存在但 YOLO 认为怪物UI还在时，用 YOLO 标注后保存截图。最多 10 张。"""
    global _sample_counter
    if _sample_counter[0] >= _MAX_SAMPLES:
        return
    try:
        from bh3_yolo_recognizer import bh3_yolo_recognize
        _hongkai_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sample_dir = os.path.join(_hongkai_dir, "all_log", "debug_samples")
        os.makedirs(sample_dir, exist_ok=True)

        # 使用 bh3_yolo_recognize 直接生成带标注框的图片
        result = bh3_yolo_recognize(save_detection_result=True)
        if result.get("success"):
            # YOLO 会将标注图保存到 photos/bh3_YOLO_checked，找到并移动
            checked_dir = os.path.join(_hongkai_dir, "photos", "bh3_YOLO_checked")
            import glob as _glob
            detected_files = _glob.glob(os.path.join(checked_dir, "*.jpg"))
            if detected_files:
                import shutil
                latest = max(detected_files, key=os.path.getmtime)
                detected_classes = set()
                for p in result.get("elements", []):
                    detected_classes.add(p.get("class_name", "?"))
                dst = os.path.join(sample_dir, f"stop_vs_yolo_{int(time.time())}_{_sample_counter[0]}.jpg")
                shutil.move(latest, dst)
                _sample_counter[0] += 1
                print(f"[取样] 停止图片+YOLO检测: {detected_classes} ({_sample_counter[0]}/{_MAX_SAMPLES})")
            else:
                # YOLO 无检测，保存原始截图
                if result.get("screenshot_path"):
                    import shutil
                    dst = os.path.join(sample_dir, f"stop_vs_yolo_nodet_{int(time.time())}_{_sample_counter[0]}.jpg")
                    shutil.copy(result["screenshot_path"], dst)
                    _sample_counter[0] += 1
                    print(f"[取样] YOLO无检测，保存原始截图 ({_sample_counter[0]}/{_MAX_SAMPLES})")
        else:
            print(f"[取样] YOLO识别失败: {result.get('message', '未知')}")
    except Exception as e:
        if debug:
            print(f"[取样] 截图失败: {e}")
        else:
            print(f"[取样] 截图失败: {e}")


def detect_monster_ui(monster_detected_event, not_guaiwuUI_event, monster_stop_event, battle_end_event, debug=False):
    """
    检测怪物UI的函数，持续运行直到收到停止信号
    
    :param monster_detected_event: 用于标记是否检测到怪物UI的事件对象
    :param not_guaiwuUI_event: 用于标记是否未检测到怪物UI（连续两次）的事件对象
    :param monster_stop_event: 用于怪物UI线程发送停止信号的事件对象
    :param battle_end_event: 用于标记战斗结束的事件对象
    :param debug: 是否显示调试信息，默认False
    :return: 无返回值
    """
    if debug:
        print("开始检测怪物UI...")
    
    try:
        not_detected_count = 0  # 连续未检测到计数器
        last_elysia_time = time.time()  # 初始化最后检测到elysia_star的时间
        while not monster_stop_event.is_set():
            # 使用YOLO检测guaiwu_xueliang_UI和elysia_star
            yolo_result = bh3_yolo_recognize(save_screenshot=False, save_detection_result=False)
            
            # 检查是否存在guaiwu_xueliang_UI和elysia_star
            guaiwu_xueliang_exists = False
            elysia_star_exists = False
            if yolo_result.get("success"):
                elements = yolo_result.get("elements", [])
                for elem in elements:
                    if elem.get("class_name") == "guaiwu_xueliang_UI":
                        guaiwu_xueliang_exists = True
                        if not monster_detected_event.is_set():
                            if debug:
                                print("检测到怪物UI，标记为已检测")
                            monster_detected_event.set()
                    elif elem.get("class_name") == "elysia_star":
                        elysia_star_exists = True
                        last_elysia_time = time.time()  # 更新最后检测到elysia_star的时间
            
            if guaiwu_xueliang_exists:
                # 检测到怪物UI，重置未检测到计数器并清除not_guaiwuUI_event
                not_detected_count = 0
                not_guaiwuUI_event.clear()
                # 检测到怪物UI时重置elysia_star计时，防止误判战斗结束
                last_elysia_time = time.time()
                if debug:
                    print("怪物UI线程：检测到怪物UI，重置未检测到计数器")
                print(f"[战斗状态] 检测到怪物UI，重置elysia_star计时 (last_elysia_time: {last_elysia_time})")
            else:
                # 未检测到怪物UI
                not_detected_count += 1
                if debug:
                    print(f"怪物UI线程：未检测到怪物UI，计数 {not_detected_count}/2")
                if not_detected_count >= 2:
                    not_guaiwuUI_event.set()
                    if debug:
                        print("怪物UI线程：连续两次未检测到怪物UI，设置not_guaiwuUI_event")
                else:
                    not_guaiwuUI_event.clear()
            
            # 检查是否连续5秒未检测到elysia_star且未检测到怪物UI
            time_since_elysia = time.time() - last_elysia_time
            if time_since_elysia >= 5 and not guaiwu_xueliang_exists:
                # 检查letu_fight_on图片是否存在
                letu_fight_on_result = is_complex_temp("", template_path="templates\\letu_fight_on.png", confidence=0.8, time_sleep=0, region=(1598, 945, 1719, 1064), debug=debug)
                if letu_fight_on_result[0]:
                    print("[战斗状态] 检测到letu_fight_on图片，战斗继续")
                    # 重置elysia_star计时，继续战斗
                    last_elysia_time = time.time()
                    not_detected_count = 0
                    not_guaiwuUI_event.clear()
                else:
                    print(f"[战斗结束] 触发条件：连续{time_since_elysia:.1f}秒未检测到elysia_star，且未检测到怪物UI")
                    print(f"[战斗结束] 最后检测到elysia_star时间: {last_elysia_time}, 当前时间: {time.time()}")
                    print(f"且无[战斗中]图片存在")
                    if debug:
                        print(f"连续{time_since_elysia:.1f}秒未检测到elysia_star，且未检测到怪物UI，认为战斗结束")
                    battle_end_event.set()
                    monster_stop_event.set()  # 明确停止当前线程
                    break
            
            # 每隔0.1秒检测一次
            time.sleep(0.1)
    except Exception as e:
        print(f"怪物UI检测过程中发生错误: {e}")


def detect_stop_image(stop_image_path, confidence, image_stop_event, not_guaiwuUI_event, region=None, debug=False):
    """
    检测停止图片的函数，持续运行直到检测到图片或收到停止信号
    
    :param stop_image_path: 停止图片的路径
    :param confidence: 图片检测的置信度阈值
    :param image_stop_event: 用于停止图片线程发送停止信号的事件对象
    :param not_guaiwuUI_event: 用于标记是否未检测到怪物UI（连续两次）的事件对象
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，表示左上角和右下角坐标，默认为None（全屏）
    :param debug: 是否显示调试信息，默认False
    :return: 无返回值
    """
    if debug:
        print(f"开始检测停止图片: {stop_image_path}")
        if region is not None:
            print(f"识别区域: ({region[0]}, {region[1]}) - ({region[2]}, {region[3]})")
    
    try:
        stop_confirmation_count = 0  # 连续确认计数器
        while not image_stop_event.is_set():
            # 调用is_complex_temp函数，获取返回值
            result = is_complex_temp("", template_path=stop_image_path, confidence=confidence, time_sleep=0, region=region, debug=debug)
            if result[0]:  # 只检查第一个返回值（是否找到图片）
                print("检测到停止图片，检查怪物UI状态...")
                
                # 检查not_guaiwuUI_event是否被设置
                if not_guaiwuUI_event.is_set():
                    stop_confirmation_count += 1
                    print(f"停止图片线程：未检测到怪物UI，确认次数 {stop_confirmation_count}/2")
                    if stop_confirmation_count >= 2:
                        print("停止图片线程：连续两次确认停止，标记为停止")
                        image_stop_event.set()
                else:
                    print("停止图片线程：检测到怪物UI存在，继续战斗")
                    stop_confirmation_count = 0  # 重置计数器
                    # --- 取样：停止图片存在但 YOLO 认为怪物UI还在，截图保存供分析 ---
                    _sample_stop_vs_yolo(debug)
            else:
                # 未检测到停止图片，重置计数器
                stop_confirmation_count = 0
            
            # 检测chongxin_tiaozhan.png图片
            chongxin_result = is_complex_temp("", template_path="templates\\chongxin_tiaozhan.png", confidence=0.8, time_sleep=0, region=(1148, 955, 1495, 1032), debug=debug)
            if chongxin_result[0]:
                print("检测到chongxin_tiaozhan.png图片，准备重新挑战")
                # 发送停止信号
                image_stop_event.set()
                # 等待1秒后按下k键
                time.sleep(1)
                pyautogui.press('k')
                print("按下k键")
                # 等待3秒后重新开始
                time.sleep(3)
                print("重新开始循环")
                # 清除停止信号，重新开始检测
                image_stop_event.clear()
                continue
            
            # 每隔0.1秒检测一次
            time.sleep(0.1)
    except Exception as e:
        print(f"图片检测过程中发生错误: {e}")
        # 发生错误时也发送停止信号
        image_stop_event.set()


def letu_fight(recording_file_path, stop_image_path=r"templates\letu_stop_fight_loop.png", confidence=0.82, region=(1598, 945, 1719, 1064), debug=False):
    """
    循环复现按键操作直到检测到指定图片（使用多线程分离复现和检测）
    
    :param recording_file_path: 记录按键操作的JSON文件路径
    :param stop_image_path: 停止图片的路径，如果提供，则检测到该图片时停止复现
    :param confidence: 图片检测的置信度阈值
    :param region: 识别区域范围，格式为 (x1, y1, x2, y2)，表示左上角和右下角坐标，默认为(1598, 945, 1719, 1064)
    :param debug: 是否显示调试信息，默认False
    :return: bool: True表示未检测到怪物UI错误，False表示正常完成
    """
    # 标记是否检测到未检测到怪物UI的错误
    no_monster_ui_error = False
    if debug:
        print(f"开始循环复现按键操作，记录文件: {recording_file_path}")
        print(f"停止图片: {stop_image_path if stop_image_path else '未指定'}")
        print(f"图片检测置信度: {confidence}")
        if region is not None:
            print(f"识别区域: ({region[0]}, {region[1]}) - ({region[2]}, {region[3]})")
        print("按 Ctrl+C 手动停止循环")
    
    max_fight_time = 5 * 60  # 最大战斗时间5分钟
    
    try:
        loop_count = 0
        total_start_time = time.time()
        battle_ended = False  # 战斗正常结束标志，跳出外层循环

        while time.time() - total_start_time < max_fight_time and not battle_ended:
            loop_count += 1
            if debug:
                print(f"\n=== 第 {loop_count} 次循环开始 ===")
                print(f"已战斗时间: {int(time.time() - total_start_time)}秒，剩余时间: {int(max_fight_time - (time.time() - total_start_time))}秒")
            
            # 创建事件对象
            monster_detected_event = threading.Event()  # 标记是否检测到怪物UI
            not_guaiwuUI_event = threading.Event()      # 标记是否未检测到怪物UI（连续两次）
            monster_stop_event = threading.Event()      # 怪物UI线程的停止信号
            image_stop_event = threading.Event()        # 停止图片线程的停止信号
            battle_end_event = threading.Event()        # 标记战斗结束的事件对象
            global_stop_event = threading.Event()       # 全局停止信号
            
            loop_start_time = time.time()
            
            # 启动怪物UI检测线程
            monster_thread = threading.Thread(
                target=detect_monster_ui,
                args=(monster_detected_event, not_guaiwuUI_event, monster_stop_event, battle_end_event, debug)
            )
            monster_thread.daemon = True  # 设置为守护线程，主程序退出时自动退出
            monster_thread.start()
            
            # 启动检测线程（如果指定了停止图片）
            if stop_image_path:
                detection_thread = threading.Thread(
                    target=detect_stop_image,
                    args=(stop_image_path, confidence, image_stop_event, not_guaiwuUI_event, region, debug)
                )
                detection_thread.daemon = True  # 设置为守护线程，主程序退出时自动退出
                detection_thread.start()
            
            # 执行复现操作（在单独的线程中）
            replay_thread = threading.Thread(
                target=replay_keyboard_events,
                args=(recording_file_path, global_stop_event, debug)
            )
            replay_thread.daemon = True
            replay_thread.start()
            
            # 检查是否需要停止
            if stop_image_path:
                # 持续检查停止条件，直到复现线程结束或检测到停止信号
                while replay_thread.is_alive():
                    # 优先检查战斗结束事件
                    if battle_end_event.is_set():
                        print("检测到战斗结束信号（连续5秒未检测到elysia_star且无怪物UI），停止循环")
                        # 设置所有停止事件以确保线程退出
                        monster_stop_event.set()
                        image_stop_event.set()
                        global_stop_event.set()
                        battle_ended = True  # 跳出外层循环，不再重启战斗

                        # 等待线程结束
                        try:
                            monster_thread.join(timeout=1.0)
                            if stop_image_path:
                                detection_thread.join(timeout=1.0)
                            replay_thread.join(timeout=1.0)
                        except Exception as e:
                            if debug:
                                print(f"等待线程结束时发生错误: {e}")

                        break
                    elif monster_stop_event.is_set():
                        print("检测到怪物UI线程停止信号，停止循环")
                        global_stop_event.set()
                        
                        # 等待线程结束
                        try:
                            monster_thread.join(timeout=1.0)
                            if stop_image_path:
                                detection_thread.join(timeout=1.0)
                            replay_thread.join(timeout=1.0)
                        except Exception as e:
                            if debug:
                                print(f"等待线程结束时发生错误: {e}")
                        
                        break
                    elif image_stop_event.is_set():
                        # 检查是否是因为chongxin_tiaozhan.png触发的停止
                        # 等待检测线程结束，因为它会处理重新开始的逻辑
                        try:
                            if stop_image_path:
                                detection_thread.join(timeout=5.0)  # 给足够时间处理重新挑战逻辑
                        except Exception as e:
                            if debug:
                                print(f"等待检测线程结束时发生错误: {e}")
                        
                        # 检查image_stop_event是否被清除（表示需要重新开始）
                        if not image_stop_event.is_set():
                            print("检测到重新挑战信号，重新开始循环")
                            # 重置所有事件
                            monster_stop_event.set()  # 确保怪物线程停止
                            global_stop_event.set()   # 确保复现线程停止
                            
                            # 等待线程结束
                            try:
                                monster_thread.join(timeout=1.0)
                                replay_thread.join(timeout=1.0)
                            except Exception as e:
                                if debug:
                                    print(f"等待线程结束时发生错误: {e}")
                            
                            # 继续下一次循环
                            break
                        else:
                            print("检测到停止图片信号，停止循环")
                            global_stop_event.set()
                            
                            # 等待线程结束
                            try:
                                monster_thread.join(timeout=1.0)
                                if stop_image_path:
                                    detection_thread.join(timeout=1.0)
                                replay_thread.join(timeout=1.0)
                            except Exception as e:
                                if debug:
                                    print(f"等待线程结束时发生错误: {e}")
                            
                            break
                    time.sleep(0.05)  # 缩短检查间隔
                
                # 检查是否从未检测到怪物UI（排除战斗结束的情况）
                if not battle_end_event.is_set() and not monster_detected_event.is_set() and time.time() - loop_start_time >= 10:
                    print("错误：未检测到怪物UI，可能未进入战斗层")
                    global_stop_event.set()
                    # 设置所有停止事件以确保线程退出
                    monster_stop_event.set()
                    image_stop_event.set()
                    no_monster_ui_error = True
                    
                    # 等待线程结束
                    try:
                        monster_thread.join(timeout=1.0)
                        if stop_image_path:
                            detection_thread.join(timeout=1.0)
                        replay_thread.join(timeout=1.0)
                    except Exception as e:
                        if debug:
                            print(f"等待线程结束时发生错误: {e}")
                    
                    break
                
                if global_stop_event.is_set() and image_stop_event.is_set() and not battle_end_event.is_set():
                    break
            
            if debug:
                print(f"\n本次复现完成")
            
            # 短暂延迟后开始下一次循环
            if not stop_image_path:
                if debug:
                    print("未指定停止图片，继续下一次循环")
                time.sleep(1)
            else:
                if debug:
                    print("继续下一次复现...")
                time.sleep(1)
        
        # 检查是否超时
        if time.time() - total_start_time >= max_fight_time:
            print(f"战斗已持续 {max_fight_time} 秒，超时停止")
            
    except KeyboardInterrupt:
        print("\n用户手动停止循环")
    except Exception as e:
        print(f"\n执行过程中发生错误: {e}")
    
    print("循环复现操作结束")
    return no_monster_ui_error

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="循环复现按键操作直到检测到指定图片")
    
    # 添加参数
    parser.add_argument(
        "-r", "--recording", 
        type=str, 
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reproduce", "letu_elysia_star_jiaxin_fangting_loop.json"),
        help="记录按键操作的JSON文件路径，默认使用reproduce文件夹下的letu_elysia_star_jiaxin_fangting_loop.json"
    )
    
    parser.add_argument(
        "-s", "--stop-image", 
        type=str, 
        default=None,
        help="停止图片的路径，检测到该图片时停止复现"
    )
    
    parser.add_argument(
        "-c", "--confidence", 
        type=float, 
        default=0.6,
        help="图片检测的置信度阈值，默认0.6"
    )
    
    parser.add_argument(
        "--region", 
        type=str, 
        default=None,
        help="识别区域范围，格式为 'x1,y1,x2,y2'，表示左上角和右下角坐标，默认为None（全屏）"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="是否显示调试信息，默认False"
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 处理 region 参数
    region = None
    if args.region:
        try:
            region = tuple(map(int, args.region.split(',')))
            if len(region) != 4:
                raise ValueError("区域参数必须包含4个数值")
        except ValueError as e:
            print(f"错误: 区域参数格式不正确，应为 'x1,y1,x2,y2' 格式")
            sys.exit(1)
    
    # 执行主函数
    # 根据参数情况调用letu_fight函数
    if args.stop_image is not None and region is not None:
        # 如果同时指定了stop_image和region
        letu_fight(args.recording, args.stop_image, args.confidence, region, debug=args.debug)
    elif args.stop_image is not None:
        # 如果只指定了stop_image
        letu_fight(args.recording, args.stop_image, args.confidence, debug=args.debug)
    elif region is not None:
        # 如果只指定了region
        letu_fight(args.recording, region=region, debug=args.debug)
    else:
        # 如果都未指定，使用默认值
        letu_fight(args.recording, debug=args.debug)
