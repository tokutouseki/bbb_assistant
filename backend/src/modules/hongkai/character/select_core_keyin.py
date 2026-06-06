import os
import sys
import json
import time

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入必要的模块
from character.letu_normal_keyin import single_select_keyin
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck


def load_core_done():
    """
    加载已完成的刻印记录
    """
    core_done_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_done.json")
    try:
        with open(core_done_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取core_done.json文件失败: {e}")
        return {}

def save_core_done(core_done):
    """
    保存已完成的刻印记录
    """
    core_done_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_done.json")
    try:
        with open(core_done_path, 'w', encoding='utf-8') as f:
            json.dump(core_done, f, ensure_ascii=False, indent=4)
        print(f"已保存core_done.json文件")
    except Exception as e:
        print(f"保存core_done.json文件失败: {e}")

def check_keyin_counts(target=None):
    """
    检查keyin_detail.json文件中的count值，当≥3时执行single_select_keyin操作
    同样的刻印不能重复触发操作，已执行的刻印记录在core_done.json文件中
    
    Args:
        target (str, optional): 目标元素名称，即刻印类别的名称，如 "fusheng"、"jiushi"、"jielv"，当指定时只检查该元素的刻印
    """
    # 读取keyin_detail.json文件
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取JSON文件失败: {e}")
        return
    
    # 加载已完成的刻印记录
    core_done = load_core_done()
    
    # 定义需要跳过的count键
    skip_keys = ["letu_reset_count", "zhenwo_count"]
    
    # 遍历JSON中的所有键
    for key, value in data.items():
        # 检查是否是count键，并且不是需要跳过的键
        if key.endswith("_count") and key not in skip_keys:
            # 获取刻印类别（去掉_count后缀）
            category = key.replace("_count", "")
            
            # 如果指定了target，只检查target元素
            if target and category != target:
                continue
            
            # 检查count值是否≥3
            if value >= 3:
                # 检查是否已经执行过该刻印的操作
                if not core_done.get(f"{category}_done", False):
                    print(f"发现{category}刻印count值为{value}，≥3，执行操作...")
                    
                    # 执行single_select_keyin操作
                    try:
                        print(f"准备执行{category}刻印操作，等待2秒...")
                        time.sleep(2)
                        ck.click_at_position(1001, 859)
                        time.sleep(2)
                        # 使用默认的region和character_type，开启特殊匹配
                        single_select_keyin(
                            region=(748, 267, 1864, 933),
                            confidence=0.7,
                            preprocess=True,
                            category=category,
                            character_type="yuansu",
                            show_debug=False
                        )
                        
                        # 操作完成后等待1秒
                        time.sleep(1)
                        
                        # 将该刻印类别标记为已完成
                        core_done[f"{category}_done"] = True
                        # 保存已完成的刻印记录
                        save_core_done(core_done)
                        print(f"{category}刻印操作执行完成")
                    except Exception as e:
                        print(f"执行{category}刻印操作失败: {e}")
                else:
                    print(f"{category}刻印已经执行过操作，跳过")
            else:
                print(f"{category}刻印count值为{value}，<3，跳过")
    
    print("\n检查完成，已执行操作的刻印类别:", [k.replace("_done", "") for k, v in core_done.items() if v])


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
    focus_bh3_window()
    check_keyin_counts()