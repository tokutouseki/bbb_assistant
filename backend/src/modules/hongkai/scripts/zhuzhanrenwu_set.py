import sys
import os
import time

# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window
import templates.clicks_keyboard as ck

if __name__ == "__main__":

            
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！")

    # 1.执行ck.click_chuzhanrenwu()函数
    print("\n1. 执行ck.click_chuzhanrenwu()函数：")
    success_chuzhanrenwu = ck.click_chuzhanrenwu()
    if success_chuzhanrenwu:
        print("点击了'出战人物'按钮！")
    else:
        print("点击'出战人物'按钮失败！")

    # 2.执行ck.click_shaixuan()函数
    print("\n2. 执行ck.click_shaixuan()函数：")
    success_shaixuan = ck.click_shaixuan()
    if success_shaixuan:
        print("点击了'筛选'按钮！")
    else:
        print("点击'筛选'按钮失败！")
