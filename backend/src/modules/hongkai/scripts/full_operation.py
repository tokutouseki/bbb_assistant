import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import everyday
import jiantuangongxian
import letu
import maoxian_weituo
import meizhou_jianfu
import zhanchang
import simulation_combat_room
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
from custom_datetime import save_datetime_data, get_datetime
from main_screen import make_on_main

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
    
    # 保存日期和时间数据
    print("\n0. 执行save_datetime_data函数：")
    saved_file = save_datetime_data()
    print(f"时间数据已保存到: {saved_file}")

    # 打印日期和星期
    datetime_info = get_datetime()
    print(f"当前日期: {datetime_info['date']}")
    print(f"当前星期: {datetime_info['weekday_cn']}")

    # 基于星期的任务分配映射
    todo_mapping = {
        "星期一": [
            "everyday.daily_operations()", # 每日任务
            "meizhou_jianfu.meizhou_jianfu()", # 每周减负
            "everyweek_gift.get_gift()", # 每周礼包
        ],
        "星期二": [
            "everyday.daily_operations()",
            "zhanchang.zhanchang_jianfu()", # 战场
            "simulation_combat_room.simulation_combat_room()"  # 模拟作战室
        ],
        "星期三": [
            "everyday.daily_operations()",
            "zhanchang.zhanchang_jianfu()", # 战场
        ],
        "星期四": [
            "everyday.daily_operations()",
            "zhanchang.zhanchang_jianfu()"
        ],
        "星期五": [
            "everyday.daily_operations()"
        ],
        "星期六": [
            "everyday.daily_operations()",
            
        ],
        "星期日": [
            "everyday.daily_operations()",
            "jiantuangongxian.jiantuangongxian()",  # 舰团贡献
            "simulation_combat_room.simulation_combat_room()"
        ]
    }
    
    # 根据当前星期获取任务列表
    current_weekday = datetime_info['weekday_cn']
    todo_list = todo_mapping.get(current_weekday, [])
    
    print(f"\n根据当前星期 {current_weekday}，计划执行以下任务：")
    for i, task in enumerate(todo_list, 1):
        print(f"{i}. {task}")
    
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")
    
    # 执行任务列表
    print("\n开始执行任务：")
    for i, task in enumerate(todo_list, 1):
        print(f"\n{i}. 执行 {task}：")
        try:
            # 动态执行任务函数
            exec(task)
            print(f"任务 {task} 执行完成！")
        except Exception as e:
            print(f"任务 {task} 执行失败：{e}")
            # 继续执行下一个任务
            continue

    # 所有任务执行完毕后，返回主界面并清理消息
    make_on_main()