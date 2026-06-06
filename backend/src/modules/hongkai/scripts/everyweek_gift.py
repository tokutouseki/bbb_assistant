import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window
import templates.clicks_keyboard as ck
from main_screen import make_on_main

def get_gift():
    # 点击商城
    print("\n1. 执行click_shangcheng函数：")
    success_click = ck.click_shangcheng()
    if success_click:
        print("商城已点击！")
        time.sleep(1)
        # 点击礼包
        print("\n2. 执行click_libao函数：")
        success_click = ck.click_libao()
        if success_click:
            print("礼包已点击！")
            time.sleep(1)
            success_click = ck.click_zhouqi()
            if success_click:
                print("周期已点击！")
                time.sleep(1)
                # 点击免费
                print("\n3. 执行click_mianfei函数：")
                success_click = ck.click_mianfei()
                if success_click:
                    print("免费已点击！")
                     # 点击免费
                    print("\n3. 执行click_mianfei函数：")
                    success_click = ck.click_mianfei()
                    if success_click:
                        print("免费已点击！")
                    else:
                        print("免费点击失败！")
                        sys.exit(1)
                else:
                    print("免费点击失败！")
                    sys.exit(1)
            else:
                print("周期点击失败！")
                sys.exit(1)
        else:
            print("礼包点击失败！")
            sys.exit(1)
    else:
        print("商城点击失败！\n请尝试手动改变舰桥为永恒的礼堂\n或更改显示模式为1980*1080全屏")
        sys.exit(1)

    # 4. 执行2次esc键
    for i in range(2):
        print(f"\n第{i+1}次按下esc键")
        ck.keyboard_esc_press_release()

    make_on_main()
        

        
if __name__ == "__main__":

    
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")
    get_gift()

