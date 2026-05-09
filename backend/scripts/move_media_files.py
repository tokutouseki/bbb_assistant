#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动需要修正的媒体资源
"""

import json
import shutil
from pathlib import Path

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")

media_moves = [
    ("休伯利安11号.png", "图鉴/材料/media", "第二部探索指南/洛星博物纪/media"),
    ("勿忘我.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("坠星绽露_1.png", "图鉴/材料/media", "第二部探索指南/道具/media"),
    ("天霜之斯卡蒂_1.png", "图鉴/材料/media", "图鉴/武器/media"),
    ("始生之鳞.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("将逝的火种_1.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("抉择之石.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("旋灭死涎_1.png", "图鉴/材料/media", "第二部探索指南/道具/media"),
    ("无瑕之钥.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("旧世遗尘.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("昴弋流光_1.png", "图鉴/材料/media", "第二部探索指南/道具/media"),
    ("松雀.png", "档案/角色/media", "第二部探索指南/收藏品/media"),
    ("极夜之赫卡忒_1.png", "图鉴/材料/media", "图鉴/武器/media"),
    ("水晶蔷薇.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("永夜之城·瑞木.png", "图鉴/材料/media", "第二部探索指南/洛星博物纪/media"),
    ("汲星凝澜_1.png", "图鉴/材料/media", "第二部探索指南/道具/media"),
    ("瑞木高塔·神之居所.png", "图鉴/材料/media", "第二部探索指南/洛星博物纪/media"),
    ("瑟拉珮姆.png", "档案/角色/media", "第二部探索指南/收藏品/media"),
    ("禁忌之种.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("经验_1.png", "图鉴/材料/media", "第二部探索指南/道具/media"),
    ("虚假的希望.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("行识驻痕_1.png", "图鉴/材料/media", "第二部探索指南/道具/media"),
    ("轻，如一叶菩提.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("重，似万千生命.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("锈蚀之徽.png", "图鉴/材料/media", "往世乐土/物品/media"),
    ("闪亮的银币.png", "图鉴/材料/media", "往世乐土/物品/media"),
]

def move_media_files():
    print("=" * 60)
    print("移动媒体资源到正确位置")
    print("=" * 60)
    
    moved_count = 0
    not_found_count = 0
    already_exists_count = 0
    
    for filename, source_rel, target_rel in media_moves:
        source_path = DATA_DIR / source_rel / filename
        target_path = DATA_DIR / target_rel / filename
        
        print(f"\n处理: {filename}")
        print(f"  源位置: {source_path}")
        print(f"  目标: {target_path}")
        
        if not source_path.exists():
            print(f"  [未找到] 源文件不存在")
            not_found_count += 1
            continue
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if target_path.exists():
            print(f"  [跳过] 目标位置已存在")
            already_exists_count += 1
            continue
        
        try:
            shutil.move(str(source_path), str(target_path))
            print(f"  [成功] 已移动")
            moved_count += 1
        except Exception as e:
            print(f"  [错误] {e}")
    
    print("\n" + "=" * 60)
    print("移动完成!")
    print(f"成功移动: {moved_count}")
    print(f"目标已存在: {already_exists_count}")
    print(f"源文件未找到: {not_found_count}")
    print("=" * 60)

if __name__ == "__main__":
    move_media_files()
