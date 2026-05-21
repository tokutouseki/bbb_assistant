import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
from custom_datetime import save_datetime_data
from main_screen import make_on_main
from vedio_log import get_video_logger

# 登录领取函数
def login_claim():
    max_total_attempts = 5
    total_attempts = 0
    
    # 至少执行前两次尝试
    while total_attempts < max_total_attempts:
        print(f"\n第{total_attempts+1}次尝试执行登录领取操作：")
        
        # 执行第一次点击尝试
        print("1. 执行ck.click_meiri()函数：")
        success_click = ck.click_meiri()
        total_attempts += 1
        
        if success_click:
            print("点击了'领取'按钮！")
            time.sleep(2)
            # 执行ck.keyboard_esc_press_release()函数
            print("2. 执行ck.keyboard_esc_press_release()函数：")
            success_esc = ck.keyboard_esc_press_release()
            if success_esc:
                print("成功按下并释放了'ESC'键！")
                time.sleep(1.5)
            else:
                print("按下并释放'ESC'键失败！")
                # 如果ESC键操作失败，第二次只重试ESC键操作
                if total_attempts < max_total_attempts:
                    time.sleep(1.5)
                    print(f"\n第{total_attempts+1}次尝试执行登录领取操作：")
                    print("2. 只重试执行ck.keyboard_esc_press_release()函数：")
                    success_esc = ck.keyboard_esc_press_release()
                    total_attempts += 1

                    if success_esc:
                        print("成功按下并释放了'ESC'键！")
                        time.sleep(1.5)
                    else:
                        print("按下并释放'ESC'键失败！")
                        print("两次尝试均失败，退出操作！")
                        break
                else:
                    print("已达到最大尝试次数，退出操作！")
                    break
        else:
            print("未识别到领取")
            ck.keyboard_esc_press_release()
            time.sleep(1.5)
            # 如果click操作失败，第二次只重试click操作
            if total_attempts < max_total_attempts:
                time.sleep(1.5)
                print(f"\n第{total_attempts+1}次尝试执行登录领取操作：")
                print("1. 只重试执行ck.click_meiri()函数：")
                success_click = ck.click_meiri()
                total_attempts += 1

                if success_click:
                    print("点击了'领取'按钮！")
                    time.sleep(2)
                    # 执行ck.keyboard_esc_press_release()函数
                    print("2. 执行ck.keyboard_esc_press_release()函数：")
                    success_esc = ck.keyboard_esc_press_release()
                    if success_esc:
                        print("成功按下并释放了'ESC'键！")
                        time.sleep(1.5)
                    else:
                        print("按下并释放'ESC'键失败！")
                else:
                    print("未识别到领取")
                    print("两次尝试均失败，退出操作！")
                    break
            else:
                print("已达到最大次数，退出操作！")
                break
    
    if total_attempts >= max_total_attempts:
        print("\n已达到最大次数5次")

    time.sleep(5)

# 领取金币函数
def claim_gold():
    # 3.1 执行ck.click_jinbi()函数
    print("\n3.1 执行ck.click_jinbi()函数：")
    success_jinbi = ck.click_jinbi()
    if success_jinbi:
        print("点击了'金币'按钮！")
    else:
        print("点击'金币'按钮失败！")

    # 3.2 执行ck.click_qvchujinbi()函数
    print("\n3.2 执行ck.click_qvchujinbi()函数：")
    success_qvchujinbi = ck.click_qvchujinbi()
    if success_qvchujinbi:
        print("点击了'领取金币'按钮！")
    else:
        print("点击'领取金币'按钮失败！")

    # 3.3 执行ck.click_lingqv()函数
    print("\n3.3 执行ck.click_lingqv()函数：")
    success_lingqv = ck.click_lingqv()
    if success_lingqv:
        print("点击了'领取'按钮！")
    else:
        print("点击'领取'按钮失败！")

    time.sleep(4)

    # 3.4 执行ck.keyboard_esc_press_release()函数
    print("\n3.4 执行ck.keyboard_esc_press_release()函数：")
    success_esc = ck.keyboard_esc_press_release()
    if success_esc:
        print("成功按下并释放了'ESC'键！")
    else:
        print("按下并释放'ESC'键失败！")

# 出击一键减负函数
def attack_with_reduction():
     # 3.5 执行ck.click_chuji()函数
    print("\n3.5 执行ck.click_chuji()函数：")
    success_chuji = ck.click_chuji()
    if success_chuji:
        print("点击了'出击'按钮！")
    else:
        print("点击'出击'按钮失败！")
    
    # 4.执行ck.click_chuji_tuijian()函数
    print("\n4. 执行ck.click_chuji_tuijian()函数：")
    success_tuijian = ck.click_chuji_tuijian()
    if success_tuijian:
        print("点击了'推荐'按钮！")
    else:
        print("点击'推荐'按钮失败！")
        success_is_tuijian = ck.is_tuijian()
        if success_is_tuijian:
            print("推荐按钮可见，目前为推荐界面")
        else:
            print("推荐按钮不可见，出错了")
    
    # 5.执行ck.click_chuji_chuji()函数
    print("\n5. 执行ck.click_chuji_chuji()函数：")
    success_chuji_chuji = ck.click_chuji_chuji()
    if success_chuji_chuji:
        print("点击了'出击_出击'按钮！")
    else:
        print("点击'出击_出击'按钮失败！")

    # 6.执行ck.click_cailiaoyuanzheng()函数
    print("\n6. 执行ck.click_cailiaoyuanzheng()函数：")
    success_cailiaoyuanzheng = ck.click_cailiaoyuanzheng()
    if success_cailiaoyuanzheng:
        print("点击了'材料远征'按钮！")
    else:
        print("点击'材料远征'按钮失败！")

    # 7.执行ck.click_jianfu()函数
    print("\n7. 执行ck.click_jianfu()函数：")
    success_jianfu = ck.click_jianfu()
    if success_jianfu:
        print("点击了'一键减负'按钮！")
    else:
        print("点击'一键减负'按钮失败！")

    # 8.执行ck.click_jianfu_jianfu()函数
    print("\n8. 执行ck.click_jianfu_jianfu()函数：")
    success_jianfu_jianfu = ck.click_jianfu_jianfu()
    if success_jianfu_jianfu:
        print("点击了'一键减负_一键减负'按钮！")
    else:
        print("点击'一键减负_一键减负'按钮失败！")
    
    # 9.执行返回主界面流程
    print("\n9. 执行返回主界面流程：")
    for i in range(3):
        success_esc = ck.keyboard_esc_press_release()
        if success_esc:
            print(f"第{i+1}次成功按下并释放了'ESC'键！")
        else:
            print(f"第{i+1}次按下并释放'ESC'键失败！")

# 舰团函数
def fleet_functions(done_count = 0):
    # 进入委托函数
    def enter_delegation():
        # 10.执行ck.click_jiantuan()函数
        print("\n10. 执行ck.click_jiantuan()函数：")
        success_jiantuan = ck.click_jiantuan()
        if success_jiantuan:
            print("点击了'舰团'按钮！")
        else:
            print("点击'舰团'按钮失败！")
        
        # 11.执行ck.click_weituohuishou()函数
        print("\n11. 执行ck.click_weituohuishou()函数：")
        success_weituohuishou = ck.click_weituohuishou()
        if success_weituohuishou:
            print("点击了'委托回收'按钮！")
        else:
            print("点击'委托回收'按钮失败！")

        # 12.执行ck.click_huishouweituo()函数
        print("\n12. 执行ck.click_huishouweituo()函数：")
        success_huishouweituo = ck.click_huishouweituo()
        if success_huishouweituo:
            print("点击了'回收委托'按钮！")
        else:
            print("点击'回收委托'按钮失败！")
            success_is_huishouweituo = ck.is_huishouweituo()
            if success_is_huishouweituo:
                print("回收委托按钮可见，目前为回收委托界面")
            else:
                print("回收委托按钮不可见，出错了")
    
    # 申请委托函数
    def apply_delegation():
        # 13.执行ck.click_xinweituo()函数
        print("\n13. 执行ck.click_xinweituo()函数：")
        success_xinweituo = ck.click_xinweituo()
        if success_xinweituo:
            print("点击了'申请新委托'按钮！")
        else:
            print("点击'申请新委托'按钮失败！")
        
        # 14.执行ck.click_xinweituo_jieshou()函数
        print("\n14. 执行ck.click_xinweituo_jieshou()函数：")
        success_xinweituo_jieshou = ck.click_xinweituo_jieshou()
        if success_xinweituo_jieshou:
            print("点击了'接受'按钮！")
        else:
            print("点击'接受'按钮失败！")
        
        #等待界面清晰
        time.sleep(2)
    
    # 提交委托函数
    def submit_delegation(done_count):
        # 15.执行提交委托流程8次
        print("\n15. 执行提交委托流程8次：")
        print(f"当前已完成{done_count}次提交")
        for i in range(8 - done_count):
            success_xinweituo_tijiao = ck.click_xinweituo_tijiao()
            if success_xinweituo_tijiao:
                print(f"第{i+1}次点击了'提交'按钮！")
                time.sleep(1)
                success_xinweituo_tijiaowetuo = ck.click_xinweituo_tijiaoweituo()
                if success_xinweituo_tijiaowetuo:
                    print(f"第{i+1}次点击了'提交委托'按钮！")
                    time.sleep(1)
                    done_count += 1
                    success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
                    if success_keyboard_esc_press_release:
                        print(f"第{i+1}次成功按下并释放了'ESC'键！")
                    else:
                        print(f"第{i+1}次按下并释放'ESC'键失败！")
                        # 如果ESC键操作失败，返回当前done_count并退出函数
                        return done_count
                else:
                    print(f"第{i+1}次点击'提交委托'按钮失败！")
                    # 如果提交委托失败，返回当前done_count并退出函数
                    return done_count
            else:
                print(f"第{i+1}次点击'提交'按钮失败！")
                # 如果提交按钮失败，返回当前done_count并退出函数
                return done_count

            #等待界面清晰
            time.sleep(2)
        return done_count
    
    # 舰团奖池函数
    def fleet_prize_pool():
        # 15plus.执行ck.click_jiantuanjiangchi()函数
        print("\n15plus. 执行ck.click_jiantuanjiangchi()函数：")
        success_jiantuanjiangchi = ck.click_jiantuanjiangchi()
        if success_jiantuanjiangchi:
            print("点击了'舰团_舰团奖池'按钮！")
        else:
            print("点击'舰团_舰团奖池'按钮失败！")
            success_is_jiantuanjiangchi = ck.is_jiantuanjiangchi()
            if success_is_jiantuanjiangchi:
                print("舰团_舰团奖池按钮可见，目前为舰团_舰团奖池界面") 
            else:
                print("舰团_舰团奖池按钮不可见，出错了")

        # 15plus.执行ck.click_jiantuanjiangchi_lingqv()函数尝试3次
        for i in range(3):
            print(f"\n15plus. 执行ck.click_jiantuanjiangchi_lingqv()函数第{i+1}次尝试：")
            success_jiantuanjiangchi_lingqv = ck.click_jiantuanjiangchi_lingqv()
            if success_jiantuanjiangchi_lingqv:
                print("点击了'舰团_舰团奖池_一键领取'按钮！")
                break
            else:
                print("点击'舰团_舰团奖池_一键领取'按钮失败！")
           
            #等待界面清晰
            time.sleep(1)
    
    # 返回主界面函数
    def return_to_main():
        # 16.执行返回主界面流程
        print("\n16. 执行返回主界面流程：")
        for i in range(3):
            success_esc = ck.keyboard_esc_press_release()
            if success_esc:
                print(f"第{i+1}次成功按下并释放了'ESC'键！")
            else:
                print(f"第{i+1}次按下并释放'ESC'键失败！")
    
    # 将内部函数赋值为外部函数的属性
    fleet_functions.enter_delegation = enter_delegation
    fleet_functions.apply_delegation = apply_delegation
    fleet_functions.submit_delegation = submit_delegation
    fleet_functions.fleet_prize_pool = fleet_prize_pool
    fleet_functions.return_to_main = return_to_main
    
    # 调用内部函数
    enter_delegation()
    apply_delegation()
    done_count = submit_delegation(done_count)
    fleet_prize_pool()
    return_to_main()

    # 函数结束时返回done_count
    return done_count

# 家园函数
def home_functions():
    # 17.执行ck.click_jiayuan()函数
    print("\n17. 执行ck.click_jiayuan()函数：")
    success_jiayuan = ck.click_jiayuan()
    if success_jiayuan:
        print("点击了'家园'按钮！")
    else:
        print("点击'家园'按钮失败！")   

    #等待界面清晰
    time.sleep(0.5)

    # 21.执行ck.click_yuanzheng()函数
    print("\n21. 执行ck.click_yuanzheng()函数：")
    success_yuanzheng = ck.click_yuanzheng()
    if success_yuanzheng:
        print("点击了'家园_远征'按钮！")
    else:
        print("点击'家园_远征'按钮失败！")
    
    # 22.执行ck.click_yuanzheng_wancheng()函数
    print("\n22. 执行ck.click_yuanzheng_wancheng()函数：")
    success_yuanzheng_wancheng = ck.click_yuanzheng_wancheng()
    if success_yuanzheng_wancheng:
        print("点击了'家园_远征_完成'按钮！")
    else:
        print("点击'家园_远征_完成'按钮失败！")
    
    # 23.执行ck.keyboard_esc_press_release()函数
    print("\n23. 执行ck.keyboard_esc_press_release()函数：")
    success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
    if success_keyboard_esc_press_release:
        print("成功按下并释放了'ESC'键！")
    else:
        print("按下并释放'ESC'键失败！")

    time.sleep(1)
    # 24.执行ck.click_yuanzheng_yijian()函数
    print("\n24. 执行ck.click_yuanzheng_yijian()函数：")
    success_yuanzheng_yijian = ck.click_yuanzheng_yijian()
    if success_yuanzheng_yijian:
        print("点击了'家园_远征_一键'按钮！")
    else:
        print("点击'家园_远征_一键'按钮失败！")
    
    time.sleep(1)
    # 25.执行ck.click_yuanzheng_paiqian()函数
    print("\n25. 执行ck.click_yuanzheng_paiqian()函数：")
    success_yuanzheng_paiqian = ck.click_yuanzheng_paiqian()
    if success_yuanzheng_paiqian:
        print("点击了'家园_远征_派遣'按钮！")
        time.sleep(2)
        if ck.click_qvchutili():
            time.sleep(2)
            ck.keyboard_esc_press_release()
            time.sleep(2)
            ck.click_yuanzheng_paiqian()
    else:
        print("点击'家园_远征_派遣'按钮失败！")

    # 等待界面清晰
    time.sleep(2)

    # 26.执行ck.keyboard_esc_press_release()函数
    print("\n26. 执行ck.keyboard_esc_press_release()函数：")
    success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
    if success_keyboard_esc_press_release:
        print("成功按下并释放了'ESC'键！")
    else:
        print("按下并释放'ESC'键失败！")
     
    # 27.执行ck.click_dagong()函数
    print("\n27. 执行ck.click_dagong()函数：")
    success_dagong = ck.click_dagong()
    if success_dagong:
        print("点击了'家园_打工'按钮！")
    else:
        print("点击'家园_打工'按钮失败！")
    
    # 28.执行ck.click_dagong_lingqv()函数
    print("\n28. 执行ck.click_dagong_lingqv()函数：")
    success_dagong_lingqv = ck.click_dagong_lingqv()
    if success_dagong_lingqv:
        print("点击了'家园_打工_领取'按钮！")
    else:
        print("点击'家园_打工_领取'按钮失败！")
    
    # 29.执行ck.keyboard_esc_press_release()函数
    print("\n29. 执行ck.keyboard_esc_press_release()函数：")
    success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
    if success_keyboard_esc_press_release:
        print("成功按下并释放了'ESC'键！")
    else:
        print("按下并释放'ESC'键失败！")

    # 30.执行ck.click_yijiandagong()函数
    print("\n30. 执行ck.click_yijiandagong()函数：")
    success_yijiandagong = ck.click_yijiandagong()
    if success_yijiandagong:
        print("点击了'家园_打工_一键'按钮！")
    else:
        print("点击'家园_打工_一键'按钮失败！")

    # 30.执行ck.click_yijiandagong_yijiandagong()函数
    print("\n30. 执行ck.click_yijiandagong_yijiandagong()函数：")
    success_yijiandagong = ck.click_yijiandagong_yijiandagong()
    if success_yijiandagong:
        print("点击了'家园_打工_一键_一键'按钮！")
    else:
        print("点击'家园_打工_一键_一键'按钮失败！")

    # 等待界面清晰
    time.sleep(2)

    # 31.执行返回主界面流程
    print("\n31. 执行返回主界面流程：")
    for i in range(2):
        success_esc = ck.keyboard_esc_press_release()
        if success_esc:
            print(f"第{i+1}次成功按下并释放了'ESC'键！")
        else:
            print(f"第{i+1}次按下并释放'ESC'键失败！")

# 任务奖励函数
def task_rewards():
    # 32.执行ck.click_renwu()函数
    print("\n32. 执行ck.click_renwu()函数：")
    success_renwu = ck.click_renwu()
    if success_renwu:
        print("点击了'任务'按钮！")
    else:
        print("点击'任务'按钮失败！")

    # 33.执行ck.click_zuozhanrenwu()函数
    print("\n33. 执行ck.click_zuozhanrenwu()函数：")
    success_zuozhanrenwu = ck.click_zuozhanrenwu()
    if success_zuozhanrenwu:
        print("点击了'作战任务'按钮！")
    else:
        print("点击'作战任务'按钮失败！")

    # 34.执行ck.click_yijianlingqv()函数
    print("\n34. 执行ck.click_yijianlingqv()函数：")
    success_yijianlingqv = ck.click_yijianlingqv()
    if success_yijianlingqv:
        print("点击了'一键领取'按钮！")
    else:
        print("点击'一键领取'按钮失败！")

    # 34.执行ck.keyboard_esc_press_release()函数
    print("\n34. 执行ck.keyboard_esc_press_release()函数：")
    success_keyboard_esc_press_release = ck.keyboard_esc_press_release()
    if success_keyboard_esc_press_release:
        print("成功按下并释放了'ESC'键！")
    else:
        print("按下并释放'ESC'键失败！")

    # 35.执行ck.click_meirijiangli()函数三次
    print("\n35. 执行ck.click_meirijiangli()函数三次：")
    for i in range(3):
        success_meirijiangli = ck.click_meirijiangli()
        if success_meirijiangli:
            print(f"第{i+1}次点击了'每日奖励'按钮！")
        else:
            print(f"第{i+1}次点击'每日奖励'按钮失败！")

    # 36.执行返回主界面流程
    print("\n36. 执行返回主界面流程：")
    for i in range(2):
        success_esc = ck.keyboard_esc_press_release()
        if success_esc:
            print(f"第{i+1}次成功按下并释放了'ESC'键！")
        else:
            print(f"第{i+1}次按下并释放'ESC'键失败！")

def daily_operations():
    # 初始化并启动视频记录
    video_logger = get_video_logger(enabled=True, fps=30, resolution=(640, 360))
    print("\n开始视频记录...")
    video_logger.start()
    
    try:
        # 执行登录领取函数
        print("\n执行登录领取函数：")
        login_claim()

        time.sleep(3)

        # 执行主界面处理函数
        print("\n执行主界面处理函数：")
        make_on_main()

        time.sleep(2)

        # 执行领取金币函数
        print("\n执行领取金币函数：")
        claim_gold()

        # 执行出击一键减负函数
        print("\n执行出击一键减负函数：")
        attack_with_reduction()

        # 执行舰团函数
        print("\n执行舰团函数：")
        done_count = 0
        done_count = fleet_functions(done_count)
        print(f"舰团函数执行完成，已完成{done_count}次提交")
        try_count = 0
        while done_count < 8 and try_count <= 3:
            fleet_functions.enter_delegation()
            done_count = fleet_functions.submit_delegation(done_count)
            fleet_functions.return_to_main()
            try_count += 1


        # 执行家园函数
        print("\n执行家园函数：")
        home_functions()

        # 执行任务奖励函数
        print("\n执行任务奖励函数：")
        task_rewards()

        make_on_main()
    
    finally:
        # 停止视频记录
        print("\n停止视频记录...")
        video_logger.stop()

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

    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")
    
    daily_operations()