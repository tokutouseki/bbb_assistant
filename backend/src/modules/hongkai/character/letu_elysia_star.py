#使用爱莉希雅——嗨 爱愿妖精 用于周常乐土的内容
import sys
import os
import time
import json

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from character.elysia_star import elysia_star
from character.letu_fight import letu_fight
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
import config
from replay_keyboard import replay_keyboard_events
from bh3_yolo_recognizer import bh3_yolo_recognize
import character.yuansu_character as yc
from character.letu_find_way import find_elements
from character.letu_normal_keyin import single_select_keyin, double_select_keyin
from character.shangdian_buy import shangdian_buy
from character.check_next_done import check_elysia_star_exists
from character.select_core_keyin import check_keyin_counts
from ocr.ocr_client import OCRClient
# 定义keyin_detail.json文件路径
KEYIN_DETAIL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")

# 读取keyin_detail.json文件
def read_keyin_detail():
    """读取keyin_detail.json文件内容"""
    if os.path.exists(KEYIN_DETAIL_PATH):
        with open(KEYIN_DETAIL_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 如果文件不存在，返回默认值
        return {
            "jiushi_count": 0,
            "jiushi_weight": 0.73,
            "zhenwo_count": 2,
            "zhenwo_weight": 1.0,
            "jielv_count": 0,
            "jielv_weight": 0.1,
            "huangjin_count": 0,
            "huangjin_weight": 0.72,
            "luoxuan_count": 0,
            "luoxuan_weight": 0.1,
            "aomie_count": 0,
            "aomie_weight": 0.70,
            "tianhui_count": 0,
            "tianhui_weight": 0.1,
            "chana_count": 0,
            "chana_weight": 0.4,
            "xvguang_count": 0,
            "xvguang_weight": 0.1,
            "wuxian_count": 0,
            "wuxian_weight": 0.1,
            "fanxing_count": 0,
            "fanxing_weight": 0.48,
            "fusheng_count": 0,
            "fusheng_weight": 0.71,
            "kongmeng_count": 0,
            "kongmeng_weight": 0.49,
            "letu_reset_count": 0,
            "letu_reset_weight": 0.5
        }

# 写入keyin_detail.json文件
def write_keyin_detail(data):
    """写入内容到keyin_detail.json文件"""
    with open(KEYIN_DETAIL_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_keyin_core_files(need_init_value=False):
    """
    初始化keyin_detail.json和core_done.json文件
    
    Args:
        need_init_value (bool): keyin_detail.json文件中need_init字段的值，默认为False
    """
    print("\n初始化keyin_detail.json和core_done.json文件...")
    
    # 重置keyin_detail.json文件
    # 默认权重列表（按照原始优先级顺序）
    default_weight = [
        ("jiushi", 0.73),
        ("zhenwo", 1.00),
        ("jielv", 0.10),
        ("huangjin", 0.72),
        ("luoxuan", 0.10),
        ("aomie", 0.70),
        ("tianhui", 0.10),
        ("chana", 0.40),
        ("xvguang", 0.10),
        ("wuxian", 0.10),
        ("fanxing", 0.48),
        ("fusheng", 0.71),
        ("kongmeng", 0.49),
        ("letu_reset", 0.51),
    ]
    
    keyin_data = {}
    # 将默认权重写入JSON文件
    for keyin_name, weight in default_weight:
        weight_key = f"{keyin_name}_weight"
        keyin_data[weight_key] = weight
    
    # 确保所有count值都存在
    for keyin_name, _ in default_weight:
        count_key = f"{keyin_name}_count"
        if keyin_name == "zhenwo":
            keyin_data[count_key] = 2
        else:
            keyin_data[count_key] = 0
    
    # 设置need_init的值
    keyin_data["need_init"] = need_init_value
    
    write_keyin_detail(keyin_data)
    print("已初始化刻印权重配置")
    
    # 重置core_done.json文件
    core_done_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_done.json")
    core_done_data = {}
    # 为每个刻印类别设置done标志为False
    for keyin_name, _ in default_weight:
        if keyin_name != "letu_reset" and keyin_name != "zhenwo":  # 跳过letu_reset和zhenwo
            core_done_data[f"{keyin_name}_done"] = False
    # 写入core_done.json文件
    with open(core_done_path, 'w', encoding='utf-8') as f:
        json.dump(core_done_data, f, ensure_ascii=False, indent=4)
    print("已初始化core_done.json文件")

def letu_chuzhan_set():
    """设置乐土出战配置（仅首次运行时设置）"""
    check = ck.is_letu_elysia_star() and ck.is_letu_zhiyuan_yunmo() and ck.is_letu_zhiyuan_haitu()
    letu_chuzhan_set_done = config.load_config("letu_chuzhan_set_done", False)
    if not check:
        config.update_config("letu_chuzhan_set_done", False)
        print("需要设置出战配置！")
        return

    if letu_chuzhan_set_done:
        print("已设置出战配置！")
        return
    else:
        print("开始设置出战配置")
        # 1.执行ck.click_chuzhanwei()函数
        print("\n1. 执行ck.click_chuzhanwei()函数：")
        success_chuzhanwei = ck.click_chuzhanwei()
        if success_chuzhanwei:
            print("点击了'出战位'按钮！")
        else:
            ck.click_at_position(197, 500)
            print("点击'出战位'按钮失败！")

        # 3.执行elysia_star()函数
        print("\n3. 执行elysia_star()函数：用于设置爱莉希雅")
        elysia_star()

        # 6.执行ck.click_zhiyuanwei()函数
        print("\n6. 执行ck.click_zhiyuanwei()函数：")
        success_zhiyuanwei = ck.click_zhiyuanwei()
        if success_zhiyuanwei:
            print("点击了'支援位'按钮！")
            for i in range(4):
                ck.mouse_scroll_up() # 滚动鼠标滚轮向上
            print("执行ck.click_michenghaitu()函数：")
            success_michenghaitu = ck.click_michenghaitu()
            if success_michenghaitu:
                print("点击了'迷城骇兔'按钮！")
            else:
                print("点击'迷城骇兔'按钮失败！")
        else:
            print("点击'支援位'按钮失败！")

        # 7.执行ck.click_letuxuanze()函数
        print("\n7. 执行ck.click_letuxuanze()函数：")
        success_letuxuanze = ck.click_letuxuanze()
        if success_letuxuanze:
            print("点击了'选择'按钮！")
        else:
            print("点击'选择'按钮失败！")

        # 8.执行ck.click_zhiyuanwei()函数
        print("\n8. 执行ck.click_zhiyuanwei()函数：")
        success_zhiyuanwei = ck.click_zhiyuanwei()
        if success_zhiyuanwei:
            print("点击了'支援位'按钮！")
            for i in range(4):
                ck.mouse_scroll_up() # 滚动鼠标滚轮向上
            print("执行ck.click_yunmodanxin()函数：")
            success_yunmodan = ck.click_yunmodanxin()
            if success_yunmodan:
                print("点击了'云墨丹心'按钮！")
            else:
                print("点击'云墨丹心'按钮失败！")
        else:
            print("点击'支援位'按钮失败！")

        # 9.执行ck.click_letuxuanze()函数
        print("\n9. 执行ck.click_letuxuanze()函数：")
        success_letuxuanze = ck.click_letuxuanze()
        if success_letuxuanze:
            print("点击了'选择'按钮！")
        else:
            print("点击'选择'按钮失败！")

       
        if check:
            print("已设置爱莉希雅出战配置！")
        else:
            print("设置爱莉希雅出战配置失败！")
            replay_keyboard_events(r"reproduce\clear_letu_chuzhan_set.json")
            print("已重置出队配置！")
            config.update_config("letu_chuzhan_set_done", False)
            sys.exit(1)


        config.update_config("letu_chuzhan_set_done", True)

        

def jiaxin_fangting():
    """选择佳信和芳庭刻印（每个选择2次）"""
    i = 0
    keyin_data = read_keyin_detail()
    zhenwo_count = keyin_data.get("zhenwo_count", 0)
    while i < 2:
        if ck.click_elysia_star_jiaxin():
            print("点击了'爱莉希雅_星环_佳信'按钮！")
            # 选择	
            ck.keyboard_i_press_release()
            i += 1
            zhenwo_count += 1
            keyin_data["zhenwo_count"] = zhenwo_count
            write_keyin_detail(keyin_data)
            print("选择了'爱莉希雅_星环_佳信'！")
            time.sleep(1)
        elif ck.click_elysia_star_fangting():
            print("点击了'爱莉希雅_星环_芳庭'按钮！")   
            # 选择	
            ck.keyboard_i_press_release()
            i += 1
            zhenwo_count += 1
            keyin_data["zhenwo_count"] = zhenwo_count
            write_keyin_detail(keyin_data)
            print("选择了'爱莉希雅_星环_芳庭'！")
            time.sleep(1)
        else:
            print("没有'爱莉希雅_星环_佳信'或'爱莉希雅_星环_芳庭'刻印！")
            # 重置刻印
            print("开始重置刻印...")
            success_reset = ck.keyboard_u_press_release()
            if success_reset:
                print("成功重置刻印！")
                time.sleep(1)
            else:
                print("重置刻印失败！")
                break

def zhenwo():
    """真我刻印处理函数"""
    keyin_data = read_keyin_detail()
    zhenwo_count = keyin_data.get("zhenwo_count", 2)
    ck.click_zhenwo()
    time.sleep(1)
    ck.click_elysia_star_jinjian(confidence=0.8)
    ck.keyboard_i_press_release()
    zhenwo_count += 1
    keyin_data["zhenwo_count"] = zhenwo_count
    write_keyin_detail(keyin_data)
    # 更新权重值
    zhenwo_weights()

def letu_reset():
    """重置乐土刻印函数"""
    keyin_data = read_keyin_detail()
    letu_reset_count = keyin_data.get("letu_reset_count", 0)
    ck.keyboard_u_press_release()
    letu_reset_count += 1
    keyin_data["letu_reset_count"] = letu_reset_count
    write_keyin_detail(keyin_data)
    # 更新权重值
    letu_reset_weights()

def jiushi_weights():
    """救世权重计算函数
    
    权重计算逻辑：
    - count=0: 0.73
    - count=1: 0.73 + 1*0.09 = 0.82
    - count=2: 0.73 + 2*0.09 = 0.91
    - count=3: 0.73 + 3*0.09 = 1.00
    - count=4: 0.75 - (4-3)*0.02 = 0.73
    - count=5: 0.75 - (5-3)*0.02 = 0.71
    - count>=6: 0.3
    """
    keyin_data = read_keyin_detail()
    jiushi_count = keyin_data.get("jiushi_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.73,
        1: 0.82,
        2: 0.91,
        3: 1.00,
        4: 0.73,
        5: 0.71
    }
    
    # 获取权重值
    if jiushi_count >= 6:
        jiushi_weight = 0.3
    elif jiushi_count in weight_map:
        jiushi_weight = weight_map[jiushi_count]
    else:
        jiushi_weight = 0
        print("jiushi_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["jiushi_weight"] = jiushi_weight
    write_keyin_detail(keyin_data)
    print(f"jiushi_weights: count={jiushi_count}, weight={jiushi_weight}")
    return jiushi_weight

def zhenwo_weights():
    """真我权重计算函数
    
    权重计算逻辑：
    - count=0: 1.00
    - count=1: 1.00
    - count=2: 1.00
    - count>=3: 0
    """
    keyin_data = read_keyin_detail()
    zhenwo_count = keyin_data.get("zhenwo_count", 0)
    
    # 获取权重值
    if zhenwo_count < 3:
        zhenwo_weight = 1.00
    else:
        zhenwo_weight = 0
    
    keyin_data["zhenwo_weight"] = zhenwo_weight
    write_keyin_detail(keyin_data)
    print(f"zhenwo_weights: count={zhenwo_count}, weight={zhenwo_weight}")
    return zhenwo_weight

def jielv_weights():
    """戒律权重计算函数
    
    权重计算逻辑：
    - count=0: 0.10
    - count=1: 0.10 + 1*0.4 = 0.50
    - count=2: 0.10 + 2*0.4 = 0.90
    - count>=3: 0.3
    """
    keyin_data = read_keyin_detail()
    jielv_count = keyin_data.get("jielv_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.10,
        1: 0.50,
        2: 0.90
    }
    
    # 获取权重值
    if jielv_count >= 3:
        jielv_weight = 0.3
    elif jielv_count in weight_map:
        jielv_weight = weight_map[jielv_count]
    else:
        jielv_weight = 0
        print("jielv_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["jielv_weight"] = jielv_weight
    write_keyin_detail(keyin_data)
    print(f"jielv_weights: count={jielv_count}, weight={jielv_weight}")
    return jielv_weight

def huangjin_weights():
    """黄金权重计算函数
    
    权重计算逻辑：
    - count=0: 0.72
    - count=1: 0.72 + 1*0.09 = 0.81
    - count=2: 0.72 + 2*0.09 = 0.90
    - count=3: 0.72 + 3*0.09 = 0.99
    - count=4: 0.75 - (4-3)*0.02 = 0.73
    - count=5: 0.75 - (5-3)*0.02 = 0.71
    - count=6: 0.75 - (6-3)*0.02 = 0.69
    - count>=7: 0.3
    """
    keyin_data = read_keyin_detail()
    huangjin_count = keyin_data.get("huangjin_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.72,
        1: 0.81,
        2: 0.90,
        3: 0.99,
        4: 0.73,
        5: 0.71,
        6: 0.69
    }
    
    # 获取权重值
    if huangjin_count >= 7:
        huangjin_weight = 0.3
    elif huangjin_count in weight_map:
        huangjin_weight = weight_map[huangjin_count]
    else:
        huangjin_weight = 0
        print("huangjin_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["huangjin_weight"] = huangjin_weight
    write_keyin_detail(keyin_data)
    print(f"huangjin_weights: count={huangjin_count}, weight={huangjin_weight}")
    return huangjin_weight

def luoxuan_weights():
    """螺旋权重计算函数
    
    权重计算逻辑：
    - count=0: 0.10
    - count=1: 0.10 + 1*0.4 = 0.50
    - count=2: 0.10 + 2*0.4 = 0.90
    - count>=3: 0.3
    """
    keyin_data = read_keyin_detail()
    luoxuan_count = keyin_data.get("luoxuan_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.10,
        1: 0.50,
        2: 0.90
    }
    
    # 获取权重值
    if luoxuan_count >= 3:
        luoxuan_weight = 0.3
    elif luoxuan_count in weight_map:
        luoxuan_weight = weight_map[luoxuan_count]
    else:
        luoxuan_weight = 0
        print("luoxuan_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["luoxuan_weight"] = luoxuan_weight
    write_keyin_detail(keyin_data)
    print(f"luoxuan_weights: count={luoxuan_count}, weight={luoxuan_weight}")
    return luoxuan_weight

def aomie_weights():
    """鏖灭权重计算函数
    
    权重计算逻辑：
    - count=0: 0.70
    - count=1: 0.70 + 1*0.09 = 0.79
    - count=2: 0.70 + 2*0.09 = 0.88
    - count=3: 0.70 + 3*0.09 = 0.97
    - count=4: 0.75 - (4-3)*0.02 = 0.73
    - count=5: 0.75 - (5-3)*0.02 = 0.71
    - count=6: 0.75 - (6-3)*0.02 = 0.69
    - count>=7: 0.3
    """
    keyin_data = read_keyin_detail()
    aomie_count = keyin_data.get("aomie_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.70,
        1: 0.79,
        2: 0.88,
        3: 0.97,
        4: 0.73,
        5: 0.71,
        6: 0.69
    }
    
    # 获取权重值
    if aomie_count >= 7:
        aomie_weight = 0.3
    elif aomie_count in weight_map:
        aomie_weight = weight_map[aomie_count]
    else:
        aomie_weight = 0
        print("aomie_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["aomie_weight"] = aomie_weight
    write_keyin_detail(keyin_data)
    print(f"aomie_weights: count={aomie_count}, weight={aomie_weight}")
    return aomie_weight

def tianhui_weights():
    """天慧权重计算函数
    
    权重计算逻辑：
    - count=0: 0.10
    - count=1: 0.10 + 1*0.4 = 0.50
    - count=2: 0.10 + 2*0.4 = 0.90
    - count>=3: 0.3
    """
    keyin_data = read_keyin_detail()
    tianhui_count = keyin_data.get("tianhui_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.10,
        1: 0.50,
        2: 0.90
    }
    
    # 获取权重值
    if tianhui_count >= 3:
        tianhui_weight = 0.3
    elif tianhui_count in weight_map:
        tianhui_weight = weight_map[tianhui_count]
    else:
        tianhui_weight = 0
        print("tianhui_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["tianhui_weight"] = tianhui_weight
    write_keyin_detail(keyin_data)
    print(f"tianhui_weights: count={tianhui_count}, weight={tianhui_weight}")
    return tianhui_weight

def chana_weights():
    """刹那权重计算函数
    
    权重计算逻辑：
    - count=0: 0.40
    - count=1: 0.40 + 1*0.15 = 0.55
    - count=2: 0.40 + 2*0.15 = 0.70
    - count=3: 0.40 + 3*0.15 = 0.85
    - count>=4: 0.3
    """
    keyin_data = read_keyin_detail()
    chana_count = keyin_data.get("chana_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.40,
        1: 0.55,
        2: 0.70,
        3: 0.85
    }
    
    # 获取权重值
    if chana_count >= 4:
        chana_weight = 0.3
    elif chana_count in weight_map:
        chana_weight = weight_map[chana_count]
    else:
        chana_weight = 0
        print("chana_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["chana_weight"] = chana_weight
    write_keyin_detail(keyin_data)
    print(f"chana_weights: count={chana_count}, weight={chana_weight}")
    return chana_weight

def xvguang_weights():
    """旭光权重计算函数
    
    权重计算逻辑：
    - count=0: 0.10
    - count=1: 0.10 + 1*0.4 = 0.50
    - count=2: 0.10 + 2*0.4 = 0.90
    - count>=3: 0.3
    """
    keyin_data = read_keyin_detail()
    xvguang_count = keyin_data.get("xvguang_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.10,
        1: 0.50,
        2: 0.90
    }
    
    # 获取权重值
    if xvguang_count >= 3:
        xvguang_weight = 0.3
    elif xvguang_count in weight_map:
        xvguang_weight = weight_map[xvguang_count]
    else:
        xvguang_weight = 0
        print("xvguang_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["xvguang_weight"] = xvguang_weight
    write_keyin_detail(keyin_data)
    print(f"xvguang_weights: count={xvguang_count}, weight={xvguang_weight}")
    return xvguang_weight

def wuxian_weights():
    """无限权重计算函数
    
    权重计算逻辑：
    - count=0: 0.10
    - count=1: 0.10 + 1*0.4 = 0.50
    - count=2: 0.10 + 2*0.4 = 0.90
    - count>=3: 0.3
    """
    keyin_data = read_keyin_detail()
    wuxian_count = keyin_data.get("wuxian_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.10,
        1: 0.50,
        2: 0.90
    }
    
    # 获取权重值
    if wuxian_count >= 3:
        wuxian_weight = 0.3
    elif wuxian_count in weight_map:
        wuxian_weight = weight_map[wuxian_count]
    else:
        wuxian_weight = 0
        print("wuxian_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["wuxian_weight"] = wuxian_weight
    write_keyin_detail(keyin_data)
    print(f"wuxian_weights: count={wuxian_count}, weight={wuxian_weight}")
    return wuxian_weight

def fanxing_weights():
    """繁星权重计算函数
    
    权重计算逻辑：
    - count=0: 0.48
    - count=1: 0.48 + 1*0.15 = 0.63
    - count=2: 0.48 + 2*0.15 = 0.78
    - count=3: 0.48 + 3*0.15 = 0.93
    - count>=4: 0.3
    """
    keyin_data = read_keyin_detail()
    fanxing_count = keyin_data.get("fanxing_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.48,
        1: 0.63,
        2: 0.78,
        3: 0.93
    }
    
    # 获取权重值
    if fanxing_count >= 4:
        fanxing_weight = 0.3
    elif fanxing_count in weight_map:
        fanxing_weight = weight_map[fanxing_count]
    else:
        fanxing_weight = 0
        print("fanxing_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["fanxing_weight"] = fanxing_weight
    write_keyin_detail(keyin_data)
    print(f"fanxing_weights: count={fanxing_count}, weight={fanxing_weight}")
    return fanxing_weight

def fusheng_weights():
    """浮生权重计算函数
    
    权重计算逻辑：
    - count=0: 0.71
    - count=1: 0.71 + 1*0.09 = 0.80
    - count=2: 0.71 + 2*0.09 = 0.89
    - count=3: 0.71 + 3*0.09 = 0.98
    - count=4: 0.75 - (4-3)*0.02 = 0.73
    - count=5: 0.75 - (5-3)*0.02 = 0.71
    - count=6: 0.75 - (6-3)*0.02 = 0.69
    - count>=7: 0.3
    """
    keyin_data = read_keyin_detail()
    fusheng_count = keyin_data.get("fusheng_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.71,
        1: 0.80,
        2: 0.89,
        3: 0.98,
        4: 0.73,
        5: 0.71,
        6: 0.69
    }
    
    # 获取权重值
    if fusheng_count >= 7:
        fusheng_weight = 0.3
    elif fusheng_count in weight_map:
        fusheng_weight = weight_map[fusheng_count]
    else:
        fusheng_weight = 0
        print("fusheng_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["fusheng_weight"] = fusheng_weight
    write_keyin_detail(keyin_data)
    print(f"fusheng_weights: count={fusheng_count}, weight={fusheng_weight}")
    return fusheng_weight

def kongmeng_weights():
    """空梦权重计算函数
    
    权重计算逻辑：
    - count=0: 0.49
    - count=1: 0.49 + 1*0.15 = 0.64
    - count=2: 0.49 + 2*0.15 = 0.79
    - count=3: 0.49 + 3*0.15 = 0.94
    - count>=4: 0.3
    """
    keyin_data = read_keyin_detail()
    kongmeng_count = keyin_data.get("kongmeng_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.49,
        1: 0.64,
        2: 0.79,
        3: 0.94
    }
    
    # 获取权重值
    if kongmeng_count >= 4:
        kongmeng_weight = 0.3
    elif kongmeng_count in weight_map:
        kongmeng_weight = weight_map[kongmeng_count]
    else:
        kongmeng_weight = 0
        print("kongmeng_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["kongmeng_weight"] = kongmeng_weight
    write_keyin_detail(keyin_data)
    print(f"kongmeng_weights: count={kongmeng_count}, weight={kongmeng_weight}")
    return kongmeng_weight

def letu_reset_weights():
    """乐土重置权重计算函数
    
    权重计算逻辑：
    - count=0: 0.5
    - count=1: 0.5
    - count=2: 0.5
    - count>=3: 0
    """
    keyin_data = read_keyin_detail()
    letu_reset_count = keyin_data.get("letu_reset_count", 0)
    
    # 使用字典实现switch语句功能
    weight_map = {
        0: 0.5,
        1: 0.5,
        2: 0.5
    }
    
    # 获取权重值
    if letu_reset_count >= 3:
        letu_reset_weight = 0
    elif letu_reset_count in weight_map:
        letu_reset_weight = weight_map[letu_reset_count]
    else:
        letu_reset_weight = 0
        print("letu_reset_count超出范围！keyin_detail.json文件损坏")
    
    keyin_data["letu_reset_weight"] = letu_reset_weight
    write_keyin_detail(keyin_data)
    print(f"letu_reset_weights: count={letu_reset_count}, weight={letu_reset_weight}")
    return letu_reset_weight

def jianfu_keyin(need_init=None, selected_category=None):
    """减负刻印选择主函数 - 基于权重优先级系统
    
    Args:
        need_init (bool): 是否需要初始化权重配置
        selected_category (tuple): 已选择的类别信息 (category_name, category_key)，用于double选择情况
        
    Returns:
        str: 选中的类别名称，如 "fusheng"、"jiushi"、"jielv"，或 None 表示重置
    """
    # 初始化默认权重配置（仅首次运行）
    keyin_data = read_keyin_detail()
    
    # 检查是否需要初始化默认权重
    # 如果need_init参数为None，则使用keyin_data中的need_init字段
    if need_init is None:
        need_init = keyin_data.get("need_init", True)
    
    if need_init:
        # 调用初始化函数
        init_keyin_core_files(need_init_value=False)
    
    # 刻印选项列表（名称、权重函数、点击函数、key值）
    keyin_options = [
        ("jiushi", jiushi_weights, ck.click_jiushi, 1),
        ("zhenwo", zhenwo_weights, ck.click_zhenwo, 2),
        ("jielv", jielv_weights, ck.click_jielv, 3),
        ("huangjin", huangjin_weights, ck.click_huangjin, 4),
        ("luoxuan", luoxuan_weights, ck.click_luoxuan, 5),
        ("aomie", aomie_weights, ck.click_aomie, 6),
        ("tianhui", tianhui_weights, ck.click_tianhui, 7),
        ("chana", chana_weights, ck.click_chana, 8),
        ("xvguang", xvguang_weights, ck.click_xvguang, 9),
        ("wuxian", wuxian_weights, ck.click_wuxian, 10),
        ("fanxing", fanxing_weights, ck.click_fanxing, 11),
        ("fusheng", fusheng_weights, ck.click_fusheng, 12),
        ("kongmeng", kongmeng_weights, ck.click_kongmeng, 13),
        ("letu_reset", letu_reset_weights, letu_reset, 14),
    ]

    # 元素函数映射表（key值 -> 对应的函数）
    yuansu_func_map = {
        1: yc.jiushi_yuansu,
        2: zhenwo,
        3: yc.jielv_yuansu,
        4: yc.huangjin_yuansu,
        5: yc.luoxuan_yuansu,
        6: yc.aomie_yuansu,
        7: yc.tianhui_yuansu,
        8: yc.chana_yuansu,
        9: yc.xvguang_yuansu,
        10: yc.wuxian_yuansu,
        11: yc.fanxing_yuansu,
        12: yc.fusheng_yuansu,
        13: yc.kongmeng_yuansu,
        14: None,
    }

    # 权重选择主循环
    excluded_indices = set()  # 记录已排除的选项索引
    success = False
    attempt_count = 0  # 尝试次数计数器
    selected_name = None
    selected_key = None

    print("\n" + "="*50)
    print("开始权重选择流程")
    print("="*50)

    # 如果有已选择的类别，直接使用该类别，跳过权重选择
    if selected_category:
        category_name, category_key = selected_category
        print(f"\n使用已选择的类别: {category_name} (key: {category_key})")
        
        # 找到对应的选项索引
        category_idx = None
        for idx, (name, _, _, key) in enumerate(keyin_options):
            if name == category_name and key == category_key:
                category_idx = idx
                break
        
        if category_idx is not None:
            # 直接使用已选择的类别，不参与权重排序
            max_name, max_weight_func, max_click_func, max_key = keyin_options[category_idx]
            print(f"  直接使用已选择的类别: {max_name}")
            
            # 尝试点击刻印
            print(f"  尝试点击刻印: {max_name}")
            if max_click_func():
                print(f"  ✓ 点击{max_name}成功")
                
                # 执行对应的元素函数
                if max_key in yuansu_func_map and yuansu_func_map[max_key] is not None:
                    print(f"  执行元素函数: yuansu_func_map[{max_key}]")
                    time.sleep(0.5)
                    yuansu_func_map[max_key]()
                    print(f"  ✓ 元素函数执行成功")
                    # 执行后重新计算权重
                    new_weight = max_weight_func()
                    print(f"  ✓ 权重已更新: {max_name} = {new_weight:.4f}")
                else:
                    print(f"  ! 元素函数为 None 或不存在")
                success = True
                selected_name = max_name
                selected_key = max_key
            else:
                print(f"  ✗ 点击{max_name}失败")
                success = False
    else:
        # 循环尝试所有选项，直到成功或全部排除
        while len(excluded_indices) < len(keyin_options):
            attempt_count += 1
            print(f"\n--- 第 {attempt_count} 次尝试 ---")
            
            weights = []
            # 读取最新的keyin数据
            keyin_data = read_keyin_detail()
            
            # 计算所有未被排除选项的权重
            for idx, (name, weight_func, click_func, key) in enumerate(keyin_options):
                if idx not in excluded_indices:
                    weight = keyin_data.get(f"{name}_weight", 0)
                    weights.append((weight, idx, name, click_func, key))
                    print(f"  [{idx}] {name}: 权重 = {weight:.4f}")

            if not weights:
                print("  没有可用的选项，退出循环")
                break

            # 按权重降序排序，选择权重最大的
            weights.sort(key=lambda x: x[0], reverse=True)
            max_weight, max_idx, max_name, max_click_func, max_key = weights[0]

            print(f"\n  排序后权重最高的选项: {max_name} (索引: {max_idx}, 权重: {max_weight:.4f})")
            
            if len(excluded_indices) > 0:
                print(f"  已排除的选项索引: {sorted(excluded_indices)}")

            print(f"\n尝试运行权重最大的刻印: {max_name} (权重: {max_weight:.4f})")

            # 如果点击函数是 letu_reset，直接执行（该函数内部已处理计数）
            if max_click_func is letu_reset:
                print(f"  执行 letu_reset 函数（内部已处理计数）")
                max_click_func()
                success = True
                print(f"  ✓ letu_reset 执行成功")
                print(f"  重置后重新运行权重选择流程")
                # 重置后再次运行自己，但保持need_init参数不变
                return jianfu_keyin(need_init=False, selected_category=selected_category)
            # 如果没有点击函数（其他特殊情况），直接执行对应的元素函数
            elif max_click_func is None:
                print(f"  点击函数为 None，执行元素函数: yuansu_func_map[{max_key}]")
                if max_key in yuansu_func_map and yuansu_func_map[max_key] is not None:
                    time.sleep(0.5)
                    yuansu_func_map[max_key]()
                    print(f"  ✓ 元素函数执行成功")
                     # 执行后重新计算权重
                    max_weight_func = keyin_options[max_idx][1]
                    new_weight = max_weight_func()
                    print(f"  ✓ 权重已更新: {max_name} = {new_weight:.4f}")
                else:
                    print(f"  ! 元素函数为 None 或不存在")
                success = True
                selected_name = max_name
                selected_key = max_key
                break
            else:
                # 尝试点击刻印
                print(f"  尝试点击刻印: {max_name}")
                if max_click_func():
                    print(f"  ✓ 点击{max_name}成功")
                    
                    # 执行对应的元素函数
                    if max_key in yuansu_func_map and yuansu_func_map[max_key] is not None:
                        print(f"  执行元素函数: yuansu_func_map[{max_key}]")
                        time.sleep(1.5)
                        yuansu_func_map[max_key]()
                        print(f"  ✓ 元素函数执行成功")
                        # 执行后重新计算权重
                        max_weight_func = keyin_options[max_idx][1]
                        new_weight = max_weight_func()
                        print(f"  ✓ 权重已更新: {max_name} = {new_weight:.4f}")
                    else:
                        print(f"  ! 元素函数为 None 或不存在")
                    success = True
                    selected_name = max_name
                    selected_key = max_key
                    break
                else:
                    # 点击失败，排除该选项
                    print(f"  ✗ 点击{max_name}失败，排除该选项")
                    excluded_indices.add(max_idx)
                    print(f"  已排除索引: {max_idx}，剩余可用选项: {len(keyin_options) - len(excluded_indices)}")

    # 所有选项都尝试失败
    if not success:
        print("\n" + "="*50)
        print("所有刻印选项都已尝试，没有成功的")
        print(f"总共尝试了 {attempt_count} 次")
        print(f"最终排除的选项索引: {sorted(excluded_indices)}")
        print("="*50)
        return None
    else:
        print("\n" + "="*50)
        print(f"✓ 成功执行刻印选择，总共尝试了 {attempt_count} 次")
        print("="*50)
        return selected_name


def double_jianfu_keyin(need_init=False):
    """双倍减负刻印选择主函数 - 基于权重优先级系统
    
    处理double选择的情况：一次选择keyin的类别，两次选择具体的keyin
    """
    print("\n" + "="*60)
    print("开始双倍减负刻印选择流程")
    print("="*60)
    
    # 元素函数映射表（key值 -> 对应的函数）
    yuansu_func_map = {
        1: yc.jiushi_yuansu,
        2: zhenwo,
        3: yc.jielv_yuansu,
        4: yc.huangjin_yuansu,
        5: yc.luoxuan_yuansu,
        6: yc.aomie_yuansu,
        7: yc.tianhui_yuansu,
        8: yc.chana_yuansu,
        9: yc.xvguang_yuansu,
        10: yc.wuxian_yuansu,
        11: yc.fanxing_yuansu,
        12: yc.fusheng_yuansu,
        13: yc.kongmeng_yuansu,
        14: None,
    }
    
    # 刻印选项列表（名称、权重函数、点击函数、key值）
    keyin_options = [
        ("jiushi", jiushi_weights, ck.click_jiushi, 1),
        ("zhenwo", zhenwo_weights, ck.click_zhenwo, 2),
        ("jielv", jielv_weights, ck.click_jielv, 3),
        ("huangjin", huangjin_weights, ck.click_huangjin, 4),
        ("luoxuan", luoxuan_weights, ck.click_luoxuan, 5),
        ("aomie", aomie_weights, ck.click_aomie, 6),
        ("tianhui", tianhui_weights, ck.click_tianhui, 7),
        ("chana", chana_weights, ck.click_chana, 8),
        ("xvguang", xvguang_weights, ck.click_xvguang, 9),
        ("wuxian", wuxian_weights, ck.click_wuxian, 10),
        ("fanxing", fanxing_weights, ck.click_fanxing, 11),
        ("fusheng", fusheng_weights, ck.click_fusheng, 12),
        ("kongmeng", kongmeng_weights, ck.click_kongmeng, 13),
        ("letu_reset", letu_reset_weights, letu_reset, 14),
    ]
    
    # 第一次刻印选择 - 选择类别并获取类别信息
    print("\n" + "="*60)
    print("第一次刻印选择（选择类别）")
    print("="*60)
    category_name = jianfu_keyin(need_init=need_init)
    
    # 循环处理重置情况，直到成功选择类别且不是zhenwo
    while category_name is None or category_name == "zhenwo":
        if category_name == "zhenwo":
            print("\n" + "="*60)
            print("选择了zhenwo刻印，重新开始选择")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("重置后重新开始第一次刻印选择")
            print("="*60)
        category_name = jianfu_keyin(need_init=False)
    
    # 找到对应的category_key
    category_key = None
    for name, _, _, key in keyin_options:
        if name == category_name:
            category_key = key
            break
    
    if category_key is None:
        print(f"未找到{category_name}对应的category_key")
        return None
    
    # 第二次刻印选择 - 直接执行对应类别的元素函数
    print("\n" + "="*60)
    print(f"第二次刻印选择（直接执行{category_name}的元素函数）")
    print("="*60)
    
    # 找到对应的权重函数和key值
    max_weight_func = None
    for name, weight_func, _, key in keyin_options:
        if name == category_name and key == category_key:
            max_weight_func = weight_func
            break
    
    # 执行对应的元素函数
    if category_key in yuansu_func_map and yuansu_func_map[category_key] is not None:
        print(f"  执行元素函数: yuansu_func_map[{category_key}]")
        time.sleep(1.5)
        yuansu_func_map[category_key]()
        print(f"  ✓ 元素函数执行成功")
        # 执行后重新计算权重
        if max_weight_func is not None:
            new_weight = max_weight_func()
            print(f"  ✓ 权重已更新: {category_name} = {new_weight:.4f}")
    else:
        print(f"  ! 元素函数为 None 或不存在")
    
    print("\n" + "="*60)
    print("双倍减负刻印选择流程完成")
    print("="*60)
    
    # 返回选择的刻印类别信息
    return category_name


def restart():
    # 重新开始该层
    ck.keyboard_esc_press_release()
    time.sleep(1)
    ck.keyboard_u_press_release()
    time.sleep(1)
    ck.keyboard_u_press_release()
    time.sleep(1)
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    ck.click_at_position(990,540)
    time.sleep(2)
    ck.keyboard_f_press_release()
    time.sleep(2)
    ck.click_shencengxvlie()
    time.sleep(2)
    ck.click_letu_jixvtiaozhan()
    check_elysia_star_exists()


def handle_fight_error(target_element):
    """
    处理战斗错误的函数
    
    Args:
        target_element: 目标元素
        
    Returns:
        tuple: (fight_error, target_element) - 战斗错误状态和更新后的目标元素
    """
    max_retries = 3
    fight_error = True
    
    for retry in range(max_retries):
        print(f"\n检测到未检测到怪物UI错误，尝试第 {retry+1}/{max_retries} 次修复")
        
        # 按下S键，可能有助于重新定位
        print("  按下S键...")
        ck.keyboard_s_hold_release(1)
        time.sleep(1)
        
        # 重新运行find_element函数，尝试找到正确的目标元素
        print("  重新运行find_element函数...")
        target_element = find_elements(last_target=target_element)
        print(f"  find_elements返回: {target_element}")
        
        # 短暂延迟后重新执行战斗操作
        time.sleep(2)
        
        # 重新执行letu_fight
        print("  重新执行战斗操作...")
        fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
        
        # 如果战斗成功，退出循环
        if not fight_error:
            print("  战斗操作成功！")
            break
        
        # 如果不是最后一次尝试，执行restart操作
        if retry < max_retries - 1:
            print("  仍然未检测到怪物UI，执行restart操作")
            restart()
        else:
            print("  达到最大重试次数，仍未成功")
    
    return fight_error, target_element


def init_jianfu_layer(target_element):
    # 初始减负层
    print("\n1. 执行初始减负层")
    ceng = 0
    jiaxin_fangting()
    time.sleep(2)
    keyin_returned = jianfu_keyin(need_init=True)  # 第一次调用时初始化
    print(f"jianfu_keyin返回: {keyin_returned}")
    time.sleep(2)
    returned = jianfu_keyin(need_init=False)  # 后续调用不初始化
    print(f"jianfu_keyin返回: {returned}")
    time.sleep(2)
    returned = double_jianfu_keyin(need_init=False)  # 不初始化
    print(f"double_jianfu_keyin返回: {returned}")
    check_keyin_counts(target = returned)
    returned = jianfu_keyin(need_init=False)  # 不初始化
    print(f"jianfu_keyin返回: {returned}")
    check_keyin_counts(target= returned)
    time.sleep(2)
    returned = jianfu_keyin(need_init=False)  # 不初始化
    print(f"jianfu_keyin返回: {returned}")
    check_keyin_counts(target= returned)
    time.sleep(2)
    returned = double_jianfu_keyin(need_init=False)  # 不初始化
    print(f"double_jianfu_keyin返回: {returned}")
    check_keyin_counts(target= returned)
    time.sleep(4)
    target_element = find_elements()
    print(f"find_elements返回: {target_element}")
    time.sleep(2)
    check_elysia_star_exists()
    return target_element


def layer_8(target_element):
    # 第8层
    print("\n2. 执行第8层")
    ceng = 8
    time.sleep(2)
    # 调用letu_fight并检查返回值
    fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
    
    # 如果检测到未检测到怪物UI错误，调用处理函数
    if fight_error:
        fight_error, target_element = handle_fight_error(target_element)
    
    time.sleep(5)
    returned = single_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
    print(f"single_select_keyin返回: {returned}")
    time.sleep(2)
    check_keyin_counts(target= returned)
    time.sleep(3)
    target_element = find_elements(last_target=target_element)
    print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_9(target_element):
    # 第9层
    print("\n3. 执行第9层")
    ceng = 9
    time.sleep(2)
    if target_element == "shangdian":
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
        if target_element == "shangdian_open":
            shangdian_buy()
            target_element = find_elements(last_target=target_element)
            print(f"find_elements返回: {target_element}")
    else:
        # 调用letu_fight并检查返回值
        fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
        
        # 如果检测到未检测到怪物UI错误，调用处理函数
        if fight_error:
            fight_error, target_element = handle_fight_error(target_element)
        
        time.sleep(5)
        returned = single_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
        print(f"single_select_keyin返回: {returned}")
        time.sleep(2)
        check_keyin_counts(target= returned)
        time.sleep(3)
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
    
    time.sleep(2)
    check_elysia_star_exists()
    return target_element


def layer_10(target_element):
    # 第10层
    print("\n4. 执行第10层")
    ceng = 10
    time.sleep(2)
    check_elysia_star_exists()
    if target_element == "shangdian":
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
        if target_element == "shangdian_open":
            shangdian_buy()
            target_element = find_elements(last_target=target_element)
            print(f"find_elements返回: {target_element}")
    else:
        # 调用letu_fight并检查返回值
        fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
        
        # 如果检测到未检测到怪物UI错误，调用处理函数
        if fight_error:
            fight_error, target_element = handle_fight_error(target_element)
        
        time.sleep(5)
        returned = single_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
        print(f"single_select_keyin返回: {returned}")
        time.sleep(2)
        check_keyin_counts(target= returned)
        time.sleep(3)
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_11(target_element):
    # 第11层
    print("\n5. 执行第11层")
    ceng = 11
    time.sleep(2)
    check_elysia_star_exists()
    # 调用letu_fight并检查返回值
    fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
    
    # 如果检测到未检测到怪物UI错误，调用处理函数
    if fight_error:
        fight_error, target_element = handle_fight_error(target_element)
    
    time.sleep(5)
    returned = double_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
    print(f"double_select_keyin返回: {returned}")
    time.sleep(2)
    check_keyin_counts(target= returned)
    time.sleep(3)
    target_element = find_elements(last_target=target_element)
    print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_12(target_element):
    # 第12层
    print("\n6. 执行第12层")
    ceng = 12
    time.sleep(2)
    check_elysia_star_exists()
    # 调用letu_fight并检查返回值
    fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
    
    # 如果检测到未检测到怪物UI错误，调用处理函数
    if fight_error:
        fight_error, target_element = handle_fight_error(target_element)
    
    time.sleep(5)
    returned = single_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
    print(f"single_select_keyin返回: {returned}")
    time.sleep(2)
    check_keyin_counts(target= returned)
    time.sleep(3)
    target_element = find_elements(last_target=target_element)
    print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_13(target_element):
    # 第13层
    print("\n7. 执行第13层")
    ceng = 13
    time.sleep(2)
    check_elysia_star_exists()
    if target_element == "shangdian":
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
        if target_element == "shangdian_open":
            shangdian_buy()
            target_element = find_elements(last_target=target_element)
            print(f"find_elements返回: {target_element}")
    else:
        # 调用letu_fight并检查返回值
        fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
        
        # 如果检测到未检测到怪物UI错误，调用处理函数
        if fight_error:
            fight_error, target_element = handle_fight_error(target_element)
        
        time.sleep(5)
        returned = single_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
        print(f"single_select_keyin返回: {returned}")
        time.sleep(2)
        check_keyin_counts(target= returned)
        time.sleep(3)
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_14(target_element):
    # 第14层
    print("\n8. 执行第14层")
    ceng = 14
    time.sleep(2)
    check_elysia_star_exists()
    if target_element == "shangdian":
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
        if target_element == "shangdian_open":
            shangdian_buy()
            target_element = find_elements(last_target=target_element)
            print(f"find_elements返回: {target_element}")
    else:
        # 调用letu_fight并检查返回值
        fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
        
        # 如果检测到未检测到怪物UI错误，调用处理函数
        if fight_error:
            fight_error, target_element = handle_fight_error(target_element)
        
        time.sleep(5)
        returned = single_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
        print(f"single_select_keyin返回: {returned}")
        time.sleep(2)
        check_keyin_counts(target= returned)
        time.sleep(3)
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_15(target_element):
    # 第15层
    print("\n9. 执行第15层")
    ceng = 15   
    time.sleep(2)
    check_elysia_star_exists()
    # 调用letu_fight并检查返回值
    fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
    
    # 如果检测到未检测到怪物UI错误，调用处理函数
    if fight_error:
        fight_error, target_element = handle_fight_error(target_element)
    
    time.sleep(5)
    returned = double_select_keyin(region=(748, 267, 1864, 933), category=target_element, character_type="yuansu")
    print(f"double_select_keyin返回: {returned}")
    time.sleep(2)
    check_keyin_counts(target= returned)
    time.sleep(3)
    target_element = find_elements(last_target=target_element)
    print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_16(target_element):
    # 第16层
    print("\n10. 执行第16层")
    ceng = 16   
    time.sleep(2)
    check_elysia_star_exists()
    target_element = find_elements(last_target=target_element)
    print(f"find_elements返回: {target_element}")
    time.sleep(2)
    if target_element == "shangdian_open":
        shangdian_buy()
        time.sleep(2)
        target_element = find_elements(last_target=target_element)
        print(f"find_elements返回: {target_element}")
        time.sleep(1)
    check_elysia_star_exists()
    return target_element


def layer_17(target_element):
    # 第17层
    print("\n11. 执行第17层")
    ceng = 17   
    time.sleep(2)
    check_elysia_star_exists()
    # 调用letu_fight并检查返回值
    fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
    
    # 如果检测到未检测到怪物UI错误，调用处理函数
    if fight_error:
        fight_error, target_element = handle_fight_error(target_element)
    
    time.sleep(6)
    target_element = find_elements(last_target=target_element)
    print(f"find_elements返回: {target_element}")
    time.sleep(1)
    check_elysia_star_exists()
    return target_element


def execute_layer(layer_func, target_element):
    """执行层函数，包含异常处理和重启逻辑
    
    Args:
        layer_func (function): 要执行的层函数
        target_element (str): 目标元素
        
    Returns:
        str: 新的目标元素
    """
    max_retries = 3  # 最大重试次数
    for retry in range(max_retries):
        try:
            # 保存当前keyin状态
            print(f"\n执行层函数，重试次数: {retry+1}/{max_retries}")
            # 只有init_jianfu_layer函数没有自己的层数输出，需要在这里添加
            layer_name = layer_func.__name__
            if layer_name == "init_jianfu_layer":
                print("当前是第 0 层 (初始减负层)")
            print("  保存当前keyin状态...")
            current_keyin_state = read_keyin_detail()
            print("  keyin状态保存成功")
            
            # 保存当前core_done状态
            print("  保存当前core_done状态...")
            core_done_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_done.json")
            try:
                if os.path.exists(core_done_path):
                    with open(core_done_path, 'r', encoding='utf-8') as f:
                        current_core_done_state = json.load(f)
                else:
                    current_core_done_state = {}
                print("  core_done状态保存成功")
            except Exception as e:
                print(f"  保存core_done状态失败: {str(e)}")
                current_core_done_state = {}
            
            new_target_element = layer_func(target_element)
            # 检查返回值是否为异常情况
            if new_target_element in ["检测失败", "无匹配情况", "最大迭代次数错误"]:
                raise Exception(f"find_elements返回异常: {new_target_element}")
            # 检查是否检测到怪物UI但战斗被认为已结束
            if new_target_element == "战斗未结束，检测到怪物UI":
                print("! 检测到战斗状态不一致：怪物UI存在但战斗被认为已结束，执行重启")
                raise Exception("战斗状态不一致：怪物UI存在但战斗被认为已结束")
            print(f"✓ 层执行成功，新的target_element: {new_target_element}")
            return new_target_element
        except Exception as e:
            print(f"! 层执行失败: {str(e)}")
            if retry < max_retries - 1:
                print("  执行重启操作...")
                # 还原keyin状态
                print("  还原keyin状态...")
                write_keyin_detail(current_keyin_state)
                print("  keyin状态还原成功")
                
                # 还原core_done状态
                print("  还原core_done状态...")
                core_done_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_done.json")
                try:
                    with open(core_done_path, 'w', encoding='utf-8') as f:
                        json.dump(current_core_done_state, f, ensure_ascii=False, indent=4)
                    print("  core_done状态还原成功")
                except Exception as e:
                    print(f"  还原core_done状态失败: {str(e)}")
                
                restart()
                time.sleep(3)  # 重启后等待3秒
            else:
                raise


def layer_18(target_element):
    # 第18层
    print("\n12. 执行第18层")
    ceng = 18
    check_elysia_star_exists()
    # 调用letu_fight并检查返回值
    fight_error = letu_fight(recording_file_path=r"reproduce\letu_elysia_star_jiaxin_fangting_loop.json", stop_image_path=r"templates\letu_stop_fight_loop.png", region=(1598, 945, 1719, 1064))
    
    # 如果检测到未检测到怪物UI错误，调用处理函数
    if fight_error:
        fight_error, target_element = handle_fight_error(target_element)
    
    time.sleep(1)
    # 验证战斗是否真正结束，直接检测怪物UI是否存在
    print("  验证战斗是否真正结束...")
    yolo_result = bh3_yolo_recognize(save_screenshot=False, save_detection_result=False)
    if yolo_result.get("success"):
        elements = yolo_result.get("elements", [])
        for elem in elements:
            if elem.get("class_name") == "guaiwu_xueliang_UI":
                print("  ! 检测到战斗状态不一致：怪物UI存在但战斗被认为已结束")
                raise Exception("战斗状态不一致：怪物UI存在但战斗被认为已结束")
    print("  ✓ 战斗验证通过，无怪物UI")
    
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    for i in range(3):
        ck.keyboard_esc_press_release()
    
    # 初始化keyin_detail.json和core_done.json文件
    init_keyin_core_files(need_init_value=True)
    print("\n✓ 所有层执行完成！")
    return target_element

def letu_elysia_star():
    """乐土爱莉希雅星环主流程函数"""
    letu_chuzhan_set()
    # 10.执行ck.click_letu_kaishizhandou()函数
    print("\n10. 执行ck.click_letu_kaishizhandou()函数：")
    success_letu_kaishizhandou = ck.click_letu_kaishizhandou()
    if success_letu_kaishizhandou:
        print("点击了'乐土开始战斗'按钮！")
        # 执行所有层
        print("\n执行所有层...")
        time.sleep(6)
    try:
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 初始减负层
        target_element = execute_layer(init_jianfu_layer, None)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第8层
        target_element = execute_layer(layer_8, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第9层
        target_element = execute_layer(layer_9, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第10层
        target_element = execute_layer(layer_10, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第11层
        target_element = execute_layer(layer_11, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第12层
        target_element = execute_layer(layer_12, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第13层
        target_element = execute_layer(layer_13, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第14层
        target_element = execute_layer(layer_14, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第15层
        target_element = execute_layer(layer_15, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第16层
        target_element = execute_layer(layer_16, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第17层
        target_element = execute_layer(layer_17, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        # 第18层
        target_element = execute_layer(layer_18, target_element)
        
        # 查看当前实际层数
        current_layer = get_current_layer()
        print(f"当前实际层数: {current_layer}")
        
        print("\n🎉 所有层执行完成，程序结束！")
        time.sleep(5)
        ck.click_current_position()
        # 尝试回到主界面
        for i in range(4):
            print(f"\n第{i+1}次按下esc键")
            ck.keyboard_esc_press_release()
        ck.click_current_position()
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")
        print("请检查游戏状态或联系开发者")
    else:
        print("点击'乐土开始战斗'按钮失败！")

def get_current_layer():
    """
    使用OCR查看当前层数
    
    查看范围: (147, 20) - (312, 45)
    
    Returns:
        int: 当前层数，如果识别失败返回None
    """
    print("\n使用OCR查看当前层数...")
    start_time = time.time()
    
    # 初始化OCR客户端
    ocr_client = OCRClient()
    
    # 定义屏幕区域 (x1, y1, x2, y2)
    screen_region = [138, 14, 316, 81]
    
    try:
        # 发送识别请求，使用优化的参数以提高识别准确率
        result = ocr_client.recognize_with_reconnect(
            screen_region=screen_region,
            conf_threshold=0.5,  # 使用默认置信度阈值，平衡准确率和召回率
            preprocess=True,    # 启用预处理，提高识别准确率
            enhance_contrast=True,  # 启用对比度增强，提高文本清晰度
            denoise=False,       # 关闭降噪，提高速度
            threshold=False,     # 关闭二值化，提高速度
            max_retries=2        # 减少重试次数，提高速度
        )
        
        # 计算识别时间
        elapsed_time = time.time() - start_time
        print(f"OCR识别耗时: {elapsed_time:.2f}秒")
        
        # 解析识别结果
        if result and result.get("success"):
            texts = result.get("texts", [])
            print(f"识别到 {len(texts)} 个文本")
            
            # 遍历识别到的文本，查找层数信息
            for text_info in texts:
                text = text_info.get("text", "")
                confidence = text_info.get("confidence", 0)
                print(f"  识别结果: '{text}' (置信度: {confidence:.4f})")
                
                # 提取层数信息
                import re
                # 检查是否为减负层
                if "减负" in text:
                    print("✓ 识别到减负层，认为是初始减负层 (第0层)")
                    return 0
                # 匹配类似 "抵达层数-10/17" 或 "10/17" 的格式
                layer_match = re.search(r'\d+', text)
                if layer_match:
                    layer = int(layer_match.group())
                    print(f"✓ 成功识别到层数: {layer}")
                    return layer
            
            # 如果没有识别到层数信息
            print("✗ 未识别到层数信息")
            return None
        else:
            print(f"✗ OCR识别失败: {result.get('message', '未知错误') if result else '无响应'}")
            return None
    except Exception as e:
        print(f"✗ 获取当前层数时出错: {e}")
        return None
    finally:
        # 关闭OCR客户端连接
        ocr_client.close()

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
    
    letu_elysia_star()