#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正媒体资源位置
将媒体资源移动到对应JSON文件所在目录的media文件夹中
"""

import json
import shutil
from pathlib import Path

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")


def find_all_media_files():
    """
    查找所有媒体文件
    """
    media_files = []
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        for media_path in DATA_DIR.rglob(f"*{ext}"):
            media_files.append(media_path)
    return media_files


def find_json_for_media(media_path: Path) -> Path:
    """
    根据媒体文件名查找对应的JSON文件
    """
    base_name = media_path.stem
    
    for json_path in DATA_DIR.rglob(f"{base_name}.json"):
        if json_path.is_file():
            return json_path
    
    return None


def fix_media_locations():
    """
    修正媒体资源位置
    """
    print("=" * 60)
    print("修正媒体资源位置")
    print("=" * 60)
    
    media_files = find_all_media_files()
    print(f"\n找到 {len(media_files)} 个媒体文件")
    
    moved_count = 0
    already_correct = 0
    no_json = 0
    
    for media_path in media_files:
        current_dir = media_path.parent
        
        if current_dir.name == "media":
            json_dir = current_dir.parent
        else:
            json_dir = current_dir
        
        json_path = find_json_for_media(media_path)
        
        if not json_path:
            if current_dir.name == "media" and json_dir.name not in ["图鉴", "档案", "第二部探索指南", "往世乐土", "后崩坏书2专章", "主线章节资料", "新手入门", "攻略推荐"]:
                print(f"\n[无JSON] {media_path.name} 在 {current_dir}")
                no_json += 1
            continue
        
        correct_dir = json_path.parent
        correct_media_dir = correct_dir / "media"
        correct_media_path = correct_media_dir / media_path.name
        
        if media_path == correct_media_path:
            already_correct += 1
            continue
        
        if media_path.parent.name == "media" and media_path.parent.parent == correct_dir:
            already_correct += 1
            continue
        
        print(f"\n处理: {media_path.name}")
        print(f"  当前位置: {media_path.parent}")
        print(f"  JSON位置: {json_path.parent}")
        print(f"  目标位置: {correct_media_dir}")
        
        try:
            correct_media_dir.mkdir(parents=True, exist_ok=True)
            
            if correct_media_path.exists():
                print(f"  [跳过] 目标位置已存在同名文件")
                continue
            
            shutil.move(str(media_path), str(correct_media_path))
            print(f"  [移动] 成功")
            moved_count += 1
            
        except Exception as e:
            print(f"  [错误] {e}")
    
    print("\n" + "=" * 60)
    print("修正完成!")
    print(f"已正确位置: {already_correct} 个文件")
    print(f"已移动: {moved_count} 个文件")
    print(f"无对应JSON: {no_json} 个文件")
    print("=" * 60)


if __name__ == "__main__":
    fix_media_locations()
