import sys
import os
import time
import json

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window
import templates.clicks_keyboard as ck
from main_screen import make_on_main

def Tuesday():
    ck.click_at_position(231, 217)
    print("选择强敌一")

def Wednesday():
    ck.click_at_position(226, 382)
    print("选择强敌二")

def Thursday():
    ck.click_at_position(237, 549)
    print("选择强敌三")

def run_by_weekday():
    """
    根据current_datetime.json文件中的星期几信息运行相应的函数
    """
    times = 0  # 默认值为0，确保始终返回整数值
    try:
        # 读取JSON文件
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'current_datetime.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            datetime_data = json.load(f)
        
        # 获取星期几信息
        weekday = datetime_data.get('weekday', '')
        print(f"当前星期: {weekday}")
        
        # 根据星期几运行相应的函数
        if weekday == 'Tuesday':
            print("运行周二函数...")
            Tuesday()
            times = 5
        elif weekday == 'Wednesday':
            print("运行周三函数...")
            Wednesday()
            times = 5
        elif weekday == 'Thursday':
            print("运行周四函数...")
            Thursday()
            times = 4
        else:
            print(f"不支持的星期: {weekday}")
            times = 0  # 不支持的星期返回0
        
        return times
    except Exception as e:
        print(f"执行错误: {e}")
        return 0  # 异常情况下返回0

def zhanchang_jianfu():
    # 1.执行ck.click_chuji()函数
    print("\n1. 执行ck.click_chuji()函数：")
    success_chuji = ck.click_chuji()
    if success_chuji:
        print("点击了'出击'按钮！")
    else:
        print("点击'出击'按钮失败！")
    
    # 2.执行ck.click_chuji_tiaozhan()函数
    print("\n2. 执行ck.click_chuji_tiaozhan()函数：")
    success_tiaozhan = ck.click_chuji_tiaozhan()
    if success_tiaozhan:
        print("点击了'挑战'按钮！")
    else:
        print("点击'挑战'按钮失败！")
        success_is_tiaozhan = ck.is_tiaozhan()
        if success_is_tiaozhan:
            print("挑战按钮可见，目前为挑战界面")
        else:
            print("挑战按钮不可见，出错了")

    # 3.执行ck.click_jiyizhanchang()函数
    print("\n3. 执行ck.click_jiyizhanchang()函数：")
    success_jiyizhanchang = ck.click_jiyizhanchang()
    if success_jiyizhanchang:
        print("点击了'记忆战场'按钮！")
    else:
        print("点击'记忆战场'按钮失败！")

    # 选择强敌
    time.sleep(1)
    times = run_by_weekday()

    # 4.执行ck.click_zhanchang_jianfu()函数
    if times > 0:
        print(f"\n4. 执行ck.click_zhanchang_jianfu()函数{times}次")
        for i in range(times):
            success_zhanchang_jianfu = ck.click_zhanchang_jianfu()
            if success_zhanchang_jianfu:
                print("点击了'战场减负'按钮！")
                time.sleep(2)
                ck.keyboard_esc_press_release()
            else:
                print("点击'战场减负'按钮失败！")
    else:
        print(f"\n4. 由于星期不支持或执行错误，跳过ck.click_zhanchang_jianfu()函数执行")

    # 返回主角面
    for i in range(4):
        ck.keyboard_esc_press_release()
        time.sleep(1)

    # 5.执行make_on_main()函数
    print("\n5. 执行make_on_main()函数：")
    make_on_main()
    print("已返回主界面！")
if __name__ == "__main__":

            
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！")

     # 执行战场减负
    zhanchang_jianfu()