import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from replay_keyboard import replay_keyboard_events
from on_window import focus_bh3_window, run_as_admin, is_admin
from shenzhijian import shenzhijian
from character.letu_elysia_star import letu_elysia_star
import templates.clicks_keyboard as ck
import config
from main_screen import make_on_main

def letu():
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

    # 3.执行ck.click_letu()函数
    print("\n3. 执行ck.click_letu()函数：")
    success_letu = ck.click_letu()
    if success_letu:
        print("点击了'往世乐土'按钮！")
    else:
        print("点击'往世乐土'按钮失败！")
    
    # 4.执行ck.keyboard_f_press_release()函数
    print("\n4. 执行ck.keyboard_f_press_release()函数：")
    success_f_press_release = ck.keyboard_f_press_release()
    if success_f_press_release:
        print("成功按下并释放了'F'键！")
    else:
        print("按下并释放'F'键失败！")

    # 5.执行ck.click_shencengxvlie()函数
    print("\n5. 执行ck.click_shencengxvlie()函数：")
    success_shencengxvlie = ck.click_shencengxvlie()
    if success_shencengxvlie:
        print("点击了'深层序列'按钮！")
    else:
        print("点击'深层序列'按钮失败！")

    ck.click_current_position()

    # 6.复现letu_level.json文件中的键盘事件和鼠标事件
    print("\n6. 复现letu_level.json文件中的键盘事件和鼠标事件：")
    letu_level_done = config.load_config("letu_level_done", False)
    
    if letu_level_done:
        print("letu_level已设置！")
    else:
        replay_keyboard_events(r"reproduce\letu_level.json")
        config.update_config("letu_level_done", True)
    
    # 7.执行ck.click_letu_jianfuzhandou()函数
    print("\n7. 执行ck.click_letu_jianfuzhandou()函数：")
    success_letu_jianfuzhandou = ck.click_letu_jianfuzhandou()
    if success_letu_jianfuzhandou:
        print("点击了'乐土_减负战斗'按钮！")
    else:
        print("点击'乐土_减负战斗'按钮失败！")
        
    # 8.执行shenzhijian()函数
    print("\n8. 执行shenzhijian()函数：")
    shenzhijian()

    # 8.复现追忆之证.json文件中的键盘事件和鼠标事件
    print("\n8. 复现追忆之证.json文件中的键盘事件和鼠标事件：")
    check_zhuiyizhizheng = ck.is_letu_zhuiyizhizheng()
    if check_zhuiyizhizheng:
        print("已确认追忆之证！")
    else:
        print("追忆之证未设置好！")
        config.update_config("zhuiyizhizheng_done", False)
        

    zhuiyizhizheng_done = config.load_config("zhuiyizhizheng_done", False)
    
    if zhuiyizhizheng_done:
        print("追忆之证已设置！")
    else:
        success_replay = replay_keyboard_events(r"reproduce\zhuiyizhizheng.json")
        if success_replay:
            print("键盘事件已成功回放！")
            check_zhuiyizhizheng = ck.is_letu_zhuiyizhizheng()
            if check_zhuiyizhizheng:
                print("已确认追忆之证！")
                config.update_config("zhuiyizhizheng_done", True)
            else:
                print("追忆之证设置失败，请手动设置！")
                sys.exit(1)
            
        else:
            print("键盘事件回放失败！请检查文件是否存在reproduce\\zhuiyizhizheng.json")
            sys.exit(1)

    time.sleep(6)

    # 9.执行letu_elysia_star()函数
    print("\n9. 执行letu_elysia_star()函数：")
    letu_elysia_star()

    # 10.执行make_on_main()函数
    print("\n10. 执行make_on_main()函数：")
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
        print("BH3窗口聚焦失败！")

    letu()

    