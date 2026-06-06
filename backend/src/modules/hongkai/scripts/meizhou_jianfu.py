import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window
from replay_keyboard import replay_keyboard_events
import templates.clicks_keyboard as ck
from main_screen import make_on_main

def meizhou_jianfu():
    # 1.ck.click_renwu()函数
    print("\n1. 执行ck.click_renwu()函数：")
    success_renwu = ck.click_renwu()
    if success_renwu:
        print("任务已成功点击！")
    else:
        print("任务点击失败！")
    
    # 2.ck.click_zuozhanrenwu()函数
    print("\n2. 执行ck.click_zuozhanrenwu()函数：")
    success_zuozhanrenwu = ck.click_zuozhanrenwu()
    if success_zuozhanrenwu:
        print("作战任务已成功点击！")
    else:
        print("作战任务点击失败！")

    # 3.ck.click_renwu_jianfu()函数
    print("\n3. 执行ck.click_renwu_jianfu()函数：")
    success_renwu_jianfu = ck.click_renwu_jianfu()
    if success_renwu_jianfu:
        print("任务_减负已成功点击！")
    else:
        print("任务_减负点击失败！")
        
    # 4.执行replay_keyboard_events()函数
    print("\n4. 执行replay_keyboard_events()函数：")
    success_replay = replay_keyboard_events(r"reproduce\renwu_jianfu.json")
    if success_replay:
        print("键盘事件已成功回放！")
    else:
        print("键盘事件回放失败！")

    # 5.返回主界面
    print("\n5. 返回主界面：")
    for i in range(2):
        success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
        if success_keyboard_esc_press_release:
            print(f"第{i+1}次esc成功！")
        else:
            print(f"第{i+1}次esc失败！")
    # 6.执行make_on_main()函数
    print("\n6. 执行make_on_main()函数：")
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

     # 执行每周减负
    meizhou_jianfu()