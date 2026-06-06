# 选择角色：爱莉希雅——嗨 爱愿妖精 
import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck

def elysia_star():

    # 2.执行ck.click_shaixuan()函数
    print("\n2. 执行ck.click_shaixuan()函数：")
    success_shaixuan = ck.click_shaixuan()
    if success_shaixuan:
        print("点击了'筛选'按钮！")
    else:
        print("点击'筛选'按钮失败！")

    # 执行move_mouse_to_center()函数
    print("\n1. 执行move_mouse_to_center()函数：")
    success_move = ck.move_mouse_to_center()
    if success_move:
        print("鼠标已移动到屏幕中心！")
    else:
        print("鼠标移动到屏幕中心失败！")

    # 执行ck.mouse_scroll_up()函数10次
    print("\n1. 执行ck.mouse_scroll_up()函数10次：")
    for i in range(10):
        success_scroll_up = ck.mouse_scroll_up()
        if success_scroll_up:
            print(f"第{i+1}次鼠标滚动上！")
        else:
            print(f"第{i+1}次鼠标滚动上失败！")

    # ck.click_tianyanzhibei()函数
    print("\n1. 执行ck.click_tianyanzhibei()函数：")
    success_tianyanzhibei = ck.click_tianyanzhibei()
    if success_tianyanzhibei:
        print("点击了'天衍之杯'按钮！")
    else:
        print("点击'天衍之杯'按钮失败！")

    # ck.click_ailixiya()函数
    print("\n2. 执行ck.click_ailixiya()函数：")
    success_ailixiya = ck.click_ailixiya()
    if success_ailixiya:
        print("点击了'爱莉希雅'按钮！")
    else:
        print("点击'爱莉希雅'按钮失败！")
        # 执行ck.mouse_scroll_down()函数
        print("\n2. 执行ck.mouse_scroll_down()函数：")
        success_scroll_down = ck.mouse_scroll_down()
        if success_scroll_down:
            print("鼠标已滚动向下！")
        else:
            print("鼠标滚动向下失败！")

    # ck.click_charactor_ensure()函数
    print("\n3. 执行ck.click_charactor_ensure()函数：")
    success_charactor_ensure = ck.click_charactor_ensure()
    if success_charactor_ensure:
        print("点击了'确认'按钮！")
    else:
        print("点击'确认'按钮失败！")

    # 4.ck.click_at_position()函数
    time.sleep(1)
    print("\n4. 执行ck.click_at_position()函数：")
    success_click = ck.click_at_position(113, 239)
    if success_click:
        print("选择爱莉希雅_嗨 爱愿妖精 ！")
    else:
        print("选择爱莉希雅_嗨 爱愿妖精 失败！")

    # 5.ck.click_at_position()函数
    time.sleep(1)
    print("\n5. 执行ck.click_at_position()函数：")
    success_click = ck.click_at_position(1738, 989)
    if success_click:
        print("点击了确认队伍！")
    else:
        print("点击确认队伍失败！")


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

    # 2.执行ck.click_shaixuan()函数
    print("\n2. 执行ck.click_shaixuan()函数：")
    success_shaixuan = ck.click_shaixuan()
    if success_shaixuan:
        print("点击了'筛选'按钮！")
    else:
        print("点击'筛选'按钮失败！")    

    # 执行move_mouse_to_center()函数
    print("\n1. 执行move_mouse_to_center()函数：")
    success_move = ck.move_mouse_to_center()
    if success_move:
        print("鼠标已移动到屏幕中心！")
    else:
        print("鼠标移动到屏幕中心失败！")

    # 执行ck.mouse_scroll_up()函数20次
    print("\n1. 执行ck.mouse_scroll_up()函数20次：")
    for i in range(20):
        success_scroll_up = ck.mouse_scroll_up()
        if success_scroll_up:
            print(f"第{i+1}次鼠标滚动上！")
        else:
            print(f"第{i+1}次鼠标滚动上失败！")

    # ck.click_tianyanzhibei()函数
    print("\n1. 执行ck.click_tianyanzhibei()函数：")
    success_tianyanzhibei = ck.click_tianyanzhibei()
    if success_tianyanzhibei:
        print("点击了'天衍之杯'按钮！")
    else:
        print("点击'天衍之杯'按钮失败！")

    # ck.click_ailixiya()函数
    print("\n2. 执行ck.click_ailixiya()函数：")
    success_ailixiya = ck.click_ailixiya()
    if success_ailixiya:
        print("点击了'爱莉希雅'按钮！")
    else:
        print("点击'爱莉希雅'按钮失败！")
        # 执行ck.mouse_scroll_down()函数
        print("\n2. 执行ck.mouse_scroll_down()函数：")
        success_scroll_down = ck.mouse_scroll_down()
        if success_scroll_down:
            print("鼠标已滚动向下！")
        else:
            print("鼠标滚动向下失败！")

    # ck.click_charactor_ensure()函数
    print("\n3. 执行ck.click_charactor_ensure()函数：")
    success_charactor_ensure = ck.click_charactor_ensure()
    if success_charactor_ensure:
        print("点击了'确认'按钮！")
    else:
        print("点击'确认'按钮失败！")

    # 4.ck.click_at_position()函数
    time.sleep(1)
    print("\n4. 执行ck.click_at_position()函数：")
    success_click = ck.click_at_position(113, 239)
    if success_click:
        print("选择爱莉希雅_嗨 爱愿妖精 ！")
    else:
        print("选择爱莉希雅_嗨 爱愿妖精 失败！")

    # 5.ck.click_at_position()函数
    time.sleep(1)
    print("\n5. 执行ck.click_at_position()函数：")
    success_click = ck.click_at_position(1738, 989)
    if success_click:
        print("点击了确认队伍！")
    else:
        print("点击确认队伍失败！")
