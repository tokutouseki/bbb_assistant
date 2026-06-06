import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
import time
import json
from scripts.main_screen import detect_elysia_star
# 导入OCR模块
from ocr.ocr_functions import find_keyin

# 导入letu_find_way模块
from character.letu_find_way import detect_bh3_elements

# 延迟导入权重计算相关函数
# 避免循环导入问题
def lazy_import():
    from character.letu_elysia_star import (
        read_keyin_detail, write_keyin_detail,
        jiushi_weights, zhenwo_weights, jielv_weights, huangjin_weights,
        luoxuan_weights, aomie_weights, tianhui_weights, chana_weights,
        xvguang_weights, wuxian_weights, fanxing_weights, fusheng_weights,
        kongmeng_weights, letu_reset_weights
    )
    return read_keyin_detail, write_keyin_detail, jiushi_weights, zhenwo_weights, jielv_weights, huangjin_weights, luoxuan_weights, aomie_weights, tianhui_weights, chana_weights, xvguang_weights, wuxian_weights, fanxing_weights, fusheng_weights, kongmeng_weights, letu_reset_weights

# 权重计算函数映射
type_weight_map = {
    "jiushi": None,
    "zhenwo": None,
    "jielv": None,
    "huangjin": None,
    "luoxuan": None,
    "aomie": None,
    "tianhui": None,
    "chana": None,
    "xvguang": None,
    "wuxian": None,
    "fanxing": None,
    "fusheng": None,
    "kongmeng": None,
    "letu_reset": None
}

def shangdian_buy():
    """封装商店购买刻印的所有操作"""
    
    # 延迟导入所需函数，避免循环导入问题
    read_keyin_detail, write_keyin_detail, jiushi_weights, zhenwo_weights, jielv_weights, huangjin_weights, luoxuan_weights, aomie_weights, tianhui_weights, chana_weights, xvguang_weights, wuxian_weights, fanxing_weights, fusheng_weights, kongmeng_weights, letu_reset_weights = lazy_import()
    
    # 更新权重计算函数映射
    type_weight_map["jiushi"] = jiushi_weights
    type_weight_map["zhenwo"] = zhenwo_weights
    type_weight_map["jielv"] = jielv_weights
    type_weight_map["huangjin"] = huangjin_weights
    type_weight_map["luoxuan"] = luoxuan_weights
    type_weight_map["aomie"] = aomie_weights
    type_weight_map["tianhui"] = tianhui_weights
    type_weight_map["chana"] = chana_weights
    type_weight_map["xvguang"] = xvguang_weights
    type_weight_map["wuxian"] = wuxian_weights
    type_weight_map["fanxing"] = fanxing_weights
    type_weight_map["fusheng"] = fusheng_weights
    type_weight_map["kongmeng"] = kongmeng_weights
    type_weight_map["letu_reset"] = letu_reset_weights

    for i in range(4):
        elysia_star_exist = detect_elysia_star()
        if elysia_star_exist and i <3:
            print(f"似乎没进入商店，第{i}次尝试")
            ck.keyboard_r_press_release()
        elif elysia_star_exist and i == 3:
            #尝试返回错误使letu_elysia_star重启该层
            print(f"错误：第{i+1}次尝试仍检测到elysia_star存在，未能进入商店，触发重启")
            raise Exception("未能进入商店")
        else:
            print(f"似乎进入了商店，第{i}次尝试")
            break
        
    time.sleep(2)

    # 点击一下
    print("\n2.1 执行ck.click_current_position()函数：")
    success_click = ck.click_at_position(879, 1008)
    if success_click:
        print("点击了(879, 1008)位置！")
    else:
        print("点击失败！")

    # 点击一下
    print("\n2.1 执行ck.click_current_position()函数：")
    success_click = ck.click_at_position(879, 1008)
    if success_click:
        print("点击了(879, 1008)位置！")
    else:
        print("点击失败！")
    time.sleep(1)
    # 1. ocr获取bh3窗口截图识别文字，使用指定的识别范围(333, 106, 1861, 935)
    print("\n1. 执行OCR获取BH3窗口截图识别文字：")
    # 设置OCR识别范围 (x1, y1, x2, y2)
    ocr_region = (333, 106, 1861, 935)
    # 关闭调试信息，关闭预处理，保留相似度匹配和调整后的置信度
    recognized_keyin = find_keyin(region=ocr_region, show_debug=False, preprocess=False, confidence=0.6, use_similarity=True)
    print(f"1.1 识别到的刻印数量：{len(recognized_keyin)}")
    
    # 2. 读取keyin_detail.json获取刻印权重配置
    keyin_detail_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")
    keyin_weights = {}
    
    try:
        with open(keyin_detail_path, 'r', encoding='utf-8') as f:
            keyin_detail = json.load(f)
        print(f"\n2. 成功加载keyin_detail.json")
        
        # 提取所有权重配置
        for key, value in keyin_detail.items():
            if "_weight" in key:
                category = key.replace("_weight", "")
                keyin_weights[category] = value
        print(f"2.1 权重配置：{keyin_weights}")
    except Exception as e:
        print(f"\n2. 加载keyin_detail.json失败: {e}")
        keyin_weights = {}
    
    def process_recognized_keyin(keyin_list, batch_name):
        """处理识别到的刻印列表，检查权重并更新count和权重"""
        processed_count = 0
        total_count = len(keyin_list)
        
        print(f"\n处理{batch_name}，共{total_count}个刻印")
        
        for i, (category, name, coords) in enumerate(keyin_list):
            # 获取当前keyin_detail数据
            keyin_data = read_keyin_detail()
            
            # 获取当前刻印类型的权重
            weight_key = f"{category}_weight"
            weight = keyin_data.get(weight_key, 0.0)
            
            if weight < 0.5:
                print(f"   {i+1}. 跳过低权重刻印: {category} - {name} (权重: {weight:.2f} < 0.5)")
                continue
            
            # 处理权重≥0.5的刻印
            processed_count += 1
            print(f"   {i+1}. 处理刻印: {category} - {name} (权重: {weight:.2f}, 坐标: {coords})")
            
            # 点击并购买刻印
            ck.click_at_position(coords[0], coords[1])
            ck.click_goumaikeyin()
            time.sleep(0.5)
            
            # 更新对应keyin类型的count+1
            count_key = f"{category}_count"
            keyin_data[count_key] = keyin_data.get(count_key, 0) + 1
            print(f"   ✓ {count_key} +1，现在为: {keyin_data[count_key]}")
            
            # 写入更新后的count
            write_keyin_detail(keyin_data)
            
            # 调用对应的权重计算函数重算权重
            if category in type_weight_map and type_weight_map[category]:
                new_weight = type_weight_map[category]()
                print(f"   ✓ 权重已重算: {category} = {new_weight:.2f}")
            else:
                print(f"   ! 未找到{category}对应的权重计算函数")
        
        return processed_count
    
    # 3. 处理第一次OCR识别结果
    processed_1 = process_recognized_keyin(recognized_keyin, "第一次OCR识别结果")
    print(f"\n3. 处理完成，共处理{processed_1}个刻印")
    
    # 4. 鼠标位于窗口中心处，向下滑动11次
    print("\n4. 鼠标位于窗口中心处，向下滑动11次：")
    # 点击中心位置 (333+(1861-333)/2, 106+(935-106)/2) = (1097, 520.5)
    center_x, center_y = 1097, 521
    # 移动鼠标到中心位置
    ck.move_mouse_to_position(center_x, center_y)
    # 点击中心位置
    ck.click_at_position(center_x, center_y)
    time.sleep(0.5)
    # 使用鼠标滚轮向下滑动11次
    for i in range(11):
        ck.mouse_scroll_down(scroll_amount=250)
        time.sleep(0.5)
    print("4.1 向下滑动11次完成！")
    
    # 5. 处理第二次OCR识别结果
    print("\n5. 再次执行OCR获取截图识别文字：")
    # 关闭调试信息，关闭预处理，保留相似度匹配和调整后的置信度
    recognized_keyin_2 = find_keyin(region=ocr_region, show_debug=False, preprocess=False, confidence=0.6, use_similarity=True)
    processed_2 = process_recognized_keyin(recognized_keyin_2, "第二次OCR识别结果")
    
     # 移动鼠标到中心位置
    ck.move_mouse_to_position(center_x, center_y)
    # 点击中心位置
    ck.click_at_position(center_x, center_y)
    time.sleep(0.5)

    # 6. 向下滑动6次
    print("\n6. 向下滑动6次：")
    for i in range(6):
        ck.mouse_scroll_down(scroll_amount=250)
        time.sleep(0.5)
    print("6.1 向下滑动6次完成！")
    
    # 7. 处理第三次OCR识别结果
    print("\n7. 最后一次执行OCR获取截图识别文字：")
    # 关闭调试信息，关闭预处理，保留相似度匹配和调整后的置信度
    recognized_keyin_3 = find_keyin(region=ocr_region, show_debug=False, preprocess=False, confidence=0.6, use_similarity=True)
    processed_3 = process_recognized_keyin(recognized_keyin_3, "第三次OCR识别结果")
    
    total_processed = processed_1 + processed_2 + processed_3
    print(f"\n总处理完成，共处理{total_processed}个刻印")
    
    # 合并所有识别到的刻印
    all_recognized_keyin = recognized_keyin + recognized_keyin_2 + recognized_keyin_3
    print(f"\n合并后识别到的刻印总数：{len(all_recognized_keyin)}")
    print(all_recognized_keyin)
    
    # 12. 执行ck.keyboard_esc_press_release()
    print("\n12. 执行键盘ESC按键：")
    ck.keyboard_esc_press_release()
    time.sleep(0.5)
    
    # 13. 执行键盘操作（三个操作同时进行）
    print("\n13. 执行键盘操作（三个操作同时进行）：")
    
    # 导入多线程模块
    import threading
    
    # 定义三个键盘操作的函数
    def press_a():
        ck.keyboard_a_hold_release(1)
    
    def press_w():
        time.sleep(0.7)  # 等待0.5秒再启动
        ck.keyboard_w_hold_release(0.3)
    
    def press_e():
        time.sleep(0.7)  # 等待0.5秒再启动
        ck.keyboard_e_hold_release(0.3)
    
    # 创建线程
    thread_a = threading.Thread(target=press_a)
    thread_w = threading.Thread(target=press_w)
    thread_e = threading.Thread(target=press_e)
    
    # 启动线程，实现三个操作同时进行
    thread_a.start()
    thread_w.start()
    thread_e.start()
    
    # 等待所有线程完成
    thread_a.join()
    thread_w.join()
    thread_e.join()
    
    print("13.1 键盘操作完成！")
    
    print("\n所有操作执行完成！")

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
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")

    # 调用封装好的shangdian_buy函数
    shangdian_buy()