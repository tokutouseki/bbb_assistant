# 在战斗准备界面启用
import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from replay_keyboard import replay_keyboard_events
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
import config

def shenzhijian(open=False):
    if not open:
        print("神之键功能未启用！")
        return
    
    shenzhijian_done = config.load_config("shenzhijian_done", False)
    
    if shenzhijian_done:
        print("神之键已完成！")
    else:
        # 1.执行ck.click_shenzhijian()函数
        print("\n1. 执行ck.click_shenzhijian()函数：")
        success_shenzhijian = ck.click_shenzhijian(confidence=0.8)
        if success_shenzhijian:
            print("点击了'神之键'按钮！")
        else:
            print("点击'神之键'按钮失败！")
    
        # 2.复现shenzhijian.json文件中的键盘事件和鼠标事件
        print("\n2. 复现shenzhijian.json文件中的键盘事件和鼠标事件：")
        success_replay = replay_keyboard_events(r"reproduce\shenzhijian.json")
        if success_replay:
            print("键盘事件已成功回放！")
        else:
            print("键盘事件回放失败！")

        # 3.ck.keyboard_esc_press_release()函数
        print("\n3. 执行ck.keyboard_esc_press_release()函数：")
        success_esc = ck.keyboard_esc_press_release()
        if success_esc:
            print("成功按下了'ESC'键！")
        else:
            print("按下'ESC'键失败！")
        
        config.update_config("shenzhijian_done", True)
    

        
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

    shenzhijian(open=True)