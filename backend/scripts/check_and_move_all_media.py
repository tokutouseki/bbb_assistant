#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查并移动所有需要修正的媒体资源
支持一个JSON对应多个媒体文件的情况
"""

import json
import shutil
from pathlib import Path
import re

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")
REPORT_PATH = DATA_DIR / "category_fix_report.json"


def find_all_media_for_json(json_filename: str) -> list:
    """
    根据JSON文件名查找所有相关的媒体文件
    例如: 休伯利安11号.json -> 休伯利安11号.png, 休伯利安11号_1.png, 休伯利安11号_2.png
    """
    base_name = Path(json_filename).stem
    media_files = []
    
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        for media_path in DATA_DIR.rglob(f"{base_name}{ext}"):
            if media_path.is_file():
                media_files.append(media_path)
        
        pattern = re.compile(rf"^{re.escape(base_name)}_\d+{re.escape(ext)}$")
        for media_path in DATA_DIR.rglob(f"*{ext}"):
            if media_path.is_file() and pattern.match(media_path.name):
                media_files.append(media_path)
    
    return list(set(media_files))


def find_json_location(json_filename: str) -> Path:
    """
    查找JSON文件的当前位置
    """
    for json_path in DATA_DIR.rglob(json_filename):
        if json_path.is_file():
            return json_path
    return None


def check_and_move_media():
    """
    检查并移动所有需要修正的媒体资源
    """
    print("=" * 60)
    print("检查并移动所有需要修正的媒体资源")
    print("=" * 60)
    
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    need_fix = [r for r in report['results'] if r.get('needs_fix')]
    
    print(f"\n需要检查的JSON文件: {len(need_fix)} 个")
    
    moved_count = 0
    already_correct = 0
    not_found = 0
    
    for item in need_fix:
        filename = item['file']
        correct_main = item['correct_category_main']
        correct_sub = item['correct_category_sub']
        
        json_path = find_json_location(filename)
        if not json_path:
            continue
        
        correct_dir = json_path.parent
        correct_media_dir = correct_dir / 'media'
        
        media_files = find_all_media_for_json(filename)
        
        for media_path in media_files:
            if media_path.parent == correct_media_dir:
                already_correct += 1
                continue
            
            print(f"\n处理: {media_path.name}")
            print(f"  源位置: {media_path.parent}")
            print(f"  JSON位置: {correct_dir}")
            print(f"  目标位置: {correct_media_dir}")
            
            try:
                correct_media_dir.mkdir(parents=True, exist_ok=True)
                target_path = correct_media_dir / media_path.name
                
                if target_path.exists():
                    print(f"  [跳过] 目标位置已存在")
                    continue
                
                shutil.move(str(media_path), str(target_path))
                print(f"  [成功] 已移动")
                moved_count += 1
                
            except Exception as e:
                print(f"  [错误] {e}")
    
    print("\n" + "=" * 60)
    print("移动完成!")
    print(f"成功移动: {moved_count}")
    print(f"已在正确位置: {already_correct}")
    print("=" * 60)


if __name__ == "__main__":
    check_and_move_media()
