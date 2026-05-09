#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据检查报告修正文件分类
同时移动对应的媒体资源文件
"""

import json
import shutil
import os
import re
from pathlib import Path

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")
REPORT_PATH = DATA_DIR / "category_fix_report.json"


def find_file_in_data(filename: str) -> Path:
    """
    在整个data目录中查找文件
    """
    for json_path in DATA_DIR.rglob(filename):
        if json_path.is_file():
            return json_path
    return None


def find_media_file(json_filename: str, source_dir: Path, target_dir: Path) -> tuple:
    """
    查找对应的媒体文件
    返回 (源媒体文件路径, 目标媒体文件路径)
    """
    base_name = Path(json_filename).stem
    media_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    
    for ext in media_extensions:
        media_name = base_name + ext
        
        source_media = source_dir / "media" / media_name
        if source_media.exists():
            target_media_dir = target_dir / "media"
            target_media_dir.mkdir(parents=True, exist_ok=True)
            return source_media, target_media_dir / media_name
        
        for media_path in DATA_DIR.rglob(f"media/{media_name}"):
            target_media_dir = target_dir / "media"
            target_media_dir.mkdir(parents=True, exist_ok=True)
            return media_path, target_media_dir / media_name
    
    return None, None


def fix_categories_from_report():
    """
    根据检查报告修正文件分类
    """
    print("=" * 60)
    print("根据检查报告修正文件分类")
    print("=" * 60)
    
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    need_fix = [r for r in report["results"] if r.get("needs_fix")]
    
    print(f"\n需要修正的文件数量: {len(need_fix)}")
    
    fixed_count = 0
    moved_count = 0
    media_moved_count = 0
    already_correct = 0
    not_found = 0
    
    for item in need_fix:
        filename = item["file"]
        correct_main = item["correct_category_main"]
        correct_sub = item["correct_category_sub"]
        
        current_path = find_file_in_data(filename)
        
        if not current_path:
            print(f"\n[未找到] {filename}")
            not_found += 1
            continue
        
        current_main = current_path.parent.parent.name
        current_sub = current_path.parent.name
        
        target_dir = DATA_DIR / correct_main
        if correct_sub:
            target_dir = target_dir / correct_sub
        
        if current_path.parent == target_dir:
            print(f"\n[已正确] {filename} -> {correct_main}/{correct_sub}")
            already_correct += 1
            continue
        
        print(f"\n处理: {filename}")
        print(f"  当前位置: {current_path.parent}")
        print(f"  目标位置: {target_dir}")
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            with open(current_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data["category_main"] = correct_main
            data["category_sub"] = correct_sub
            
            with open(current_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            fixed_count += 1
            print(f"  [修正] JSON分类已更新")
            
            txt_path = current_path.with_suffix('.txt')
            target_json = target_dir / filename
            target_txt = target_dir / txt_path.name
            
            shutil.move(str(current_path), str(target_json))
            print(f"  [移动] JSON -> {target_dir}")
            
            if txt_path.exists():
                shutil.move(str(txt_path), str(target_txt))
                print(f"  [移动] TXT -> {target_dir}")
            
            moved_count += 1
            
            source_media, target_media = find_media_file(filename, current_path.parent, target_dir)
            if source_media and target_media:
                if source_media.exists() and source_media != target_media:
                    shutil.move(str(source_media), str(target_media))
                    print(f"  [移动] 媒体文件 -> {target_media.parent}")
                    media_moved_count += 1
                else:
                    print(f"  [提示] 媒体文件已在正确位置")
            else:
                print(f"  [提示] 未找到对应的媒体文件")
            
        except Exception as e:
            print(f"  [错误] {e}")
    
    print("\n" + "=" * 60)
    print("修正完成!")
    print(f"已正确位置: {already_correct} 个文件")
    print(f"修正分类: {fixed_count} 个文件")
    print(f"移动文件: {moved_count} 个文件")
    print(f"移动媒体: {media_moved_count} 个文件")
    print(f"未找到: {not_found} 个文件")
    print("=" * 60)


if __name__ == "__main__":
    fix_categories_from_report()
