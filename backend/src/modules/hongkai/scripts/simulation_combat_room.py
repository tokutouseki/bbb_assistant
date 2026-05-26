import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
from main_screen import make_on_main

def simulation_combat_room():
    """
    执行模拟作战室操作
    """
    # 1.执行ck.click_jiantuan()函数
    print("\n1. 执行ck.click_jiantuan()函数：")
    success_jiantuan = ck.click_jiantuan()
    if success_jiantuan:
        print("点击了'舰团'按钮！")
    else:
        print("点击'舰团'按钮失败！")
        print("再试一次")
        again = ck.click_jiantuan()
        if again:
            print("点击了'舰团'按钮！")
        else:
            print("点击'舰团'按钮失败！\n请尝试手动改变舰桥为永恒的礼堂\n或更改显示模式为1980*1080全屏")
            sys.exit(1)


    # 2.执行ck.click_monizuozhanshi()函数
    print("\n2. 执行ck.click_monizuozhanshi()函数：")
    success_monizuozhanshi = ck.click_monizuozhanshi()
    if success_monizuozhanshi:
        print("点击了'模拟作战室'按钮！")
    else:
        print("点击'模拟作战室'按钮失败！")
        print("再试一次")
        again = ck.click_monizuozhanshi()
        if again:
            print("点击了'模拟作战室'按钮！")
        else:
            print("点击'模拟作战室'按钮失败！\n请游戏返回主界面后，点击助手模拟作战室重试\n或手动完成模拟作战室的减负\n或联系tokutouseki")
            sys.exit(1)

    # 3.执行ck.click_jiantuan_yijianjianfu()函数
    print("\n3. 执行ck.click_jiantuan_yijianjianfu()函数：")
    success_jiantuan_yijianjianfu = ck.click_jiantuan_yijianjianfu()
    if success_jiantuan_yijianjianfu:
        print("点击了'舰团一键减负'按钮！")
    else:
        print("点击'舰团一键减负'按钮失败！")
        print("再试一次")
        again = ck.click_jiantuan_yijianjianfu()
        if again:
            print("点击了'舰团一键减负'按钮！")
        else:
            print("点击'舰团一键减负'按钮失败！\n请游戏返回主界面后，点击助手模拟作战室重试\n或手动完成模拟作战室的减负\n或联系tokutouseki")
            sys.exit(1)


    # 4.执行ck.click_queding()函数
    print("\n4. 执行ck.click_queding()函数：")
    success_queding = ck.click_queding()
    if success_queding:
        print("点击了'确定'按钮！")
    else:
        print("点击'确定'按钮失败！")
        print("再试一次")
        again = ck.click_queding()
        if again:
            print("点击了'确定'按钮！")
        else:
            print("点击'确定'按钮失败！\n请游戏返回主界面后，点击助手模拟作战室重试\n或手动完成模拟作战室的减负\n或联系tokutouseki")
            sys.exit(1)

    # 5.执行返回主界面操作
    for i in range(4):
        print("正在返回主界面")
        print(f"\n5. 执行ck.keyboard_esc_press_release()函数（第{i+1}次）：")
        success_esc = ck.keyboard_esc_press_release()
        if success_esc:
            print("成功按下并释放了'ESC'键！")
        else:
            print("按下并释放'ESC'键失败！")
            print("再试一次")
            again = ck.keyboard_esc_press_release()
            if again:
                print("成功按下并释放了'ESC'键！")
            else:
                print("按下并释放'ESC'键失败！\n请手动返回游戏主界面\n请联系tokutouseki")
                sys.exit(1)
    
    # 6.执行make_on_main()函数
    print("\n6. 执行make_on_main()函数：")
    make_on_main()
    print("已返回主界面！")


if __name__ == "__main__":
    # 检查是否以管理员身份运行
    if not is_admin():
        print("程序需要以管理员身份运行才能正常工作！")
        print("正在尝试自动提权...")
        
        if run_as_admin():
            print("请在弹出的UAC提示中选择'是'以继续...")
            sys.exit(0)  # 退出当前进程，等待管理员权限进程启动
        else:
            print("自动提权失败，请以管理员身份运行")
            input("按回车键退出...")
            sys.exit(1)
    
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
        # 调用simulation_combat_room函数执行模拟作战室操作
        simulation_combat_room()
    else:
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")
