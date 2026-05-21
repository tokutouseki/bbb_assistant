import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
from main_screen import make_on_main

def maoxian_weituo():
    # 3.执行ck.click_chuji()函数
    print("\n3. 执行ck.click_chuji()函数：")
    success_chuji = ck.click_chuji()
    if success_chuji:
        print("点击了'出击'按钮！")
    else:
        print("点击'出击'按钮失败！")

    # 3.1 执行ck.click_chuji_chuji()函数
    print("\n3.1 执行ck.click_chuji_chuji()函数：")
    success_chuji_chuji = ck.click_chuji_chuji()
    if success_chuji_chuji:
        print("点击了'出击_出击'按钮！")
    else:
        print("点击'出击_出击'按钮失败！")
        success_chuji = ck.is_chuji()
        if success_chuji:
            print("当前在'出击'！")
        else:
            print("当前不再'出击'，出错了！")
    
    # 4.执行ck.click_kaifangshijie()函数
    print("\n4. 执行ck.click_kaifangshijie()函数：")
    success_kaifangshijie = ck.click_kaifangshijie()
    if success_kaifangshijie:
        print("点击了'开放世界'按钮！")
    else:
        print("点击'开放世界'按钮失败！")

    # 5.执行ck.click_ditu_xuanze1()函数
    print("\n5. 执行ck.click_ditu_xuanze1()函数：")
    success_ditu_xuanze1 = ck.click_ditu_xuanze1()
    success_ditu_xuanze2 = ck.click_ditu_xuanze2()
    if success_ditu_xuanze1 or success_ditu_xuanze2:
        print("点击了'地图_选择'按钮！")
        success_houbenghuaishu1 = ck.click_houbenghuaishu1(confidence=0.95)
        if success_houbenghuaishu1:
            print("点击了'后崩坏书1'按钮！")
        else:
            print("点击'后崩坏书1'按钮失败！")
        success_ditu_jinru = ck.click_ditu_jinru()
        if success_ditu_jinru:
            print("点击了'地图_进入'按钮！")
        else:
            print("点击'地图_进入'按钮失败！")
    else:
        print("无'地图_选择'按钮！")

    # 6.执行ck.click_houbenghuai1_weituo()函数
    print("\n6. 执行ck.click_houbenghuai1_weituo()函数：")
    success_houbenghuai1_weituo = ck.click_houbenghuai1_weituo()
    if success_houbenghuai1_weituo:
        print("点击了'后崩坏书1_委托'按钮！")
    else:
        print("点击'后崩坏书1_委托'按钮失败！")

    # 7.执行ck.click_weituo_kaiqi()函数
    print("\n7. 执行ck.click_weituo_kaiqi()函数：")
    success_weituo_kaiqi = ck.click_weituo_kaiqi()
    if success_weituo_kaiqi:
        print("点击了'委托开启'按钮！")
    else:
        print("点击'委托开启'按钮失败！")
        print("再试一次...")
        success_weituo_kaiqi = ck.click_weituo_kaiqi()
        if success_weituo_kaiqi:
            print("点击了'委托开启'按钮！")
        else:
            print("点击'委托开启'按钮失败！")

    time.sleep(1)

    # 8.执行ck.click_at_position(1001, 859)函数
    print("\n8. 执行ck.click_at_position(1001, 859)函数：")
    success_click = ck.click_at_position(1001, 859)
    if success_click:
        print("点击了(1001, 859)位置！")
    else:
        print("点击(1001, 859)位置失败！")

    time.sleep(1)

    # 9.执行ck.keyboard_i_press_release()函数
    print("\n9. 执行ck.keyboard_i_press_release()函数：")
    success_keyboard_i = ck.keyboard_i_press_release()
    if success_keyboard_i:
        print("按下并释放了'i'键！")
    else:
        print("按下并释放'i'键失败！")
    
    # 10.执行ck.click_weituo_kaiqi()函数
    print("\n10. 执行ck.click_weituo_kaiqi()函数：")
    success_weituo_kaiqi = ck.click_weituo_kaiqi()
    if success_weituo_kaiqi:
        print("点击了'开启'按钮！")
    else:
        print("点击'开启'按钮失败！")
    
    for i in range(5):
        # 11.执行ck.click_weituo_xuanze()函数
        print("\n11. 执行ck.click_weituo_xuanze()函数：")
        success_weituo_xuanze = ck.click_weituo_xuanze(confidence=0.8)
        if success_weituo_xuanze:
            print("点击了'委托选择'按钮！")
        else:
            print("点击'委托选择'按钮失败！")

        # 12.执行ck.click_weituo_jieqv()函数
        print("\n12. 执行ck.click_weituo_jieqv()函数：")
        success_weituo_jieqv = ck.click_weituo_jieqv(confidence=0.8)
        if success_weituo_jieqv:
            print("点击了'委托接取'按钮！")
        else:
            print("点击'委托接取'按钮失败！")

        # 13.执行ck.keyboard_i_press_release()函数
        print("\n13. 执行ck.keyboard_i_press_release()函数：")
        success_keyboard_i = ck.keyboard_i_press_release()
        if success_keyboard_i:
            print("按下并释放了'i'键！")
        else:
            print("按下并释放'i'键失败！")
    
    # 14.执行ck.click_weituo_jianfu()函数
    print("\n14. 执行ck.click_weituo_jianfu()函数：")
    success_weituo_jianfu = ck.click_weituo_jianfu(confidence=0.8)
    if success_weituo_jianfu:
        print("点击了'委托减负'按钮！")
    else:
        print("点击'委托减负'按钮失败！")

    # 15.执行ck.click_queding()函数
    print("\n15. 执行ck.click_queding()函数：")
    success_queding = ck.click_queding(confidence=0.8)
    if success_queding:
        print("点击了'确定'按钮！")
    else:
        print("点击'确定'按钮失败！")

    # 返回主界面
    for i in range(4):
        success_keyboard_esc = ck.keyboard_esc_press_release()
        if success_keyboard_esc:
            print("按下并释放了'esc'键！")
        else:
            print("按下并释放'esc'键失败！")

    # 16.执行make_on_main()函数
    print("\n16. 执行make_on_main()函数：")
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

    maoxian_weituo()