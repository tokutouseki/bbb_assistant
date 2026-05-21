import sys
import os
import time

from requests.cookies import merge_cookies

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
from main_screen import make_on_main

def jiantuangongxian():
    # 确保在主界面
    print("\n0. 执行make_on_main函数：")
    success_main = make_on_main()
    if success_main:
        print("已成功进入主界面！")
    else:
        print("进入主界面失败！")

     # 1.执行ck.click_jiantuan()函数
    print("\n1. 执行ck.click_jiantuan()函数：")
    success_jiantuan = ck.click_jiantuan()
    if success_jiantuan:
        print("点击了'舰团'按钮！")
    else:
        print("点击'舰团'按钮失败！")

    # 2.执行ck.click_jiantuangongxian()函数
    print("\n2. 执行ck.click_jiantuangongxian()函数：")
    success_jiantuangongxian = ck.click_jiantuangongxian()
    if success_jiantuangongxian:
        print("点击了'舰团贡献'按钮！")
    else:
        print("点击'舰团贡献'按钮失败！")

    # 3.执行ck.click_jiantuangongxian_5000()函数
    print("\n3. 执行ck.click_jiantuangongxian_5000()函数：")
    success_jiantuangongxian = ck.click_jiantuangongxian_5000()
    if success_jiantuangongxian:
        print("点击了'舰团贡献_5000'按钮！")
    else:
        print("点击'舰团贡献_5000'按钮失败！")

    # 4.执行ck.keyboard_esc_press_release()函数三次
    print("\n4. 执行ck.keyboard_esc_press_release()函数三次：")
    for i in range(3):
        success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
        if success_keyboard_esc_press_release:
            print("成功按下并释放了'ESC'键！")
        else:
            print("按下并释放'ESC'键失败！")

    make_on_main()

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
        print("BH3窗口聚焦失败！")

    jiantuangongxian()
