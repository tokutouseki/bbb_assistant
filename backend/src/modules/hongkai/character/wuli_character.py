import sys
import os
# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import keyin_all as ka

# 救世
def jiushi_wuli():
    ka.jiushi(all=False,wuli=True)
# 戒律
def jielv_wuli():
    ka.jielv(all=False,wuli=True)

# 黄金  
def huangjin_wuli():
    ka.huangjin(all=False,wuli=True)
#螺旋  
def luoxuan_wuli():
    ka.luoxuan(all=False,wuli=True)
# 鏖灭
def aomie_wuli():
    ka.aomie(all=False,wuli=True)

# 天慧
def tianhui_wuli():
    ka.tianhui(all=False,wuli=True)

# 刹那
def chana_wuli():
    ka.chana(all=False,wuli=True)

# 旭光
def xvguang_wuli():
    ka.xvguang(all=False,wuli=True)
        
# 无限
def wuxian_wuli():
    ka.wuxian(all=False,wuli=True)

# 繁星
def fanxing_wuli(): 
    ka.fanxing(all=False,wuli=True)

# 浮生
def fusheng_wuli():
    ka.fusheng(all=False,wuli=True)

# 空梦
def kongmeng_wuli():
    ka.kongmeng(all=False,wuli=True)
        
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

    # 执行ujiushi函数
    print("\n1. 执行ujiushi函数：")
    jiushi_wuli()
