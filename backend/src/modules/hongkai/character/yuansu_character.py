import sys
import os
# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import character.keyin_all as ka

# 救世
def jiushi_yuansu():
    ka.jiushi(all=False,yuansu=True)
# 戒律
def jielv_yuansu():
    ka.jielv(all=False,yuansu=True)

# 黄金  
def huangjin_yuansu():
    ka.huangjin(all=False,yuansu=True)
#螺旋  
def luoxuan_yuansu():
    ka.luoxuan(all=False,yuansu=True)
# 鏖灭
def aomie_yuansu():
    ka.aomie(all=False,yuansu=True)

# 天慧
def tianhui_yuansu():
    ka.tianhui(all=False,yuansu=True)

# 刹那
def chana_yuansu():
    ka.chana(all=False,yuansu=True)

# 旭光
def xvguang_yuansu():
    ka.xvguang(all=False,yuansu=True)
        
# 无限
def wuxian_yuansu():
    ka.wuxian(all=False,yuansu=True)

# 繁星
def fanxing_yuansu():
    ka.fanxing(all=False,yuansu=True)

# 浮生
def fusheng_yuansu():
    ka.fusheng(all=False,yuansu=True)

# 空梦
def kongmeng_yuansu():
    ka.kongmeng(all=False,yuansu=True)
        
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

    aomie_yuansu()