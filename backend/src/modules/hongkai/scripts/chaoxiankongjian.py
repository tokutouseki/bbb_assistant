import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck

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

    # 3.执行ck.click_chaoxiankongjian()函数
    print("\n3. 执行ck.click_chaoxiankongjian()函数：")
    success_chaoxiankongjian = ck.click_chaoxiankongjian()
    if success_chaoxiankongjian:
        print("点击了'超弦空间'按钮！")
    else:
        print("点击'超弦空间'按钮失败！")

    # 4.执行ck.click_kongjian_zhandou()函数
    print("\n4. 执行ck.click_kongjian_zhandou()函数：")
    success_kongjian_zhandou = ck.click_kongjian_zhandou()
    if success_kongjian_zhandou:
        print("点击了'空间_战斗'按钮！")
    else:
        print("点击'空间_战斗'按钮失败！")

    # 5.执行ck.click_zhandouzhunbei()函数
    print("\n5. 执行ck.click_zhandouzhunbei()函数：")
    success_zhandouzhunbei = ck.click_zhandouzhunbei()
    if success_zhandouzhunbei:
        print("点击了'战斗_准备'按钮！")
    else:
        print("点击'战斗_准备'按钮失败！")
