#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正「化物诸相」相关文件的分类
将这些文件从 图鉴/材料 移动到 第二部探索指南/道具
"""

import json
import shutil
from pathlib import Path

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")


def fix_huawuzhuxiang_files():
    """
    修正「化物诸相」相关文件的分类
    """
    print("=" * 60)
    print("修正「化物诸相」相关文件的分类")
    print("=" * 60)
    
    materials_dir = DATA_DIR / "图鉴" / "材料"
    target_dir = DATA_DIR / "第二部探索指南" / "道具"
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_files = [
        "「化物诸相」随机箱：结合.json",
        "「化物诸相」随机箱：器用.json",
        "「化物诸相」随机箱：殉死.json",
        "「化物诸相」自选箱：结合-星蚀.json",
        "「化物诸相」自选箱：结合-罹厄.json",
        "「化物诸相」自选箱：器用-罹厄.json",
        "「化物诸相」自选箱：器用-星蚀.json",
    ]
    
    fixed_count = 0
    moved_count = 0
    
    for filename in target_files:
        json_path = materials_dir / filename
        txt_path = json_path.with_suffix('.txt')
        
        if not json_path.exists():
            print(f"[跳过] {filename} - 文件不存在")
            continue
        
        print(f"\n处理: {filename}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            old_main = data.get("category_main", "")
            old_sub = data.get("category_sub", "")
            
            data["category_main"] = "第二部探索指南"
            data["category_sub"] = "道具"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"  分类已修正: {old_main}/{old_sub} -> 第二部探索指南/道具")
            fixed_count += 1
            
            target_json = target_dir / filename
            target_txt = target_dir / txt_path.name
            
            shutil.move(str(json_path), str(target_json))
            print(f"  JSON已移动: {target_json}")
            
            if txt_path.exists():
                shutil.move(str(txt_path), str(target_txt))
                print(f"  TXT已移动: {target_txt}")
            
            moved_count += 1
            
        except Exception as e:
            print(f"  [错误] {e}")
    
    print("\n" + "=" * 60)
    print("修正完成!")
    print(f"修正分类: {fixed_count} 个文件")
    print(f"移动文件: {moved_count} 个文件")
    print(f"目标目录: {target_dir}")
    print("=" * 60)


if __name__ == "__main__":
    fix_huawuzhuxiang_files()
