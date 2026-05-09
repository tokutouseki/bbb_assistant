#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：重命名武器目录中的文件，根据title提取名称
使用方法：直接运行此脚本
"""

import os
import json
import re

WEAPON_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\武器"

def main():
    print("开始重命名武器目录中的文件...")
    print("=" * 80)
    
    renamed_count = 0
    skipped_count = 0
    error_count = 0
    no_match_files = []
    
    json_files = [f for f in os.listdir(WEAPON_DIR) if f.endswith('.json')]
    total_files = len(json_files)
    print(f"共有 {total_files} 个JSON文件需要处理")
    
    for file_name in sorted(json_files):
        file_path = os.path.join(WEAPON_DIR, file_name)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            title = data.get('title', '')
            
            match = re.search(r'^(.+?)-圣芙蕾雅档案馆-', title)
            if match:
                new_name = match.group(1).strip()
            else:
                match = re.search(r'^米哈游官方社区_(.+?)-圣芙蕾雅档案馆-', title)
                if match:
                    new_name = match.group(1).strip()
                else:
                    no_match_files.append({'file_name': file_name, 'title': title})
                    skipped_count += 1
                    continue
            
            new_json_path = os.path.join(WEAPON_DIR, f"{new_name}.json")
            new_txt_path = os.path.join(WEAPON_DIR, f"{new_name}.txt")
            old_txt_path = file_path.replace('.json', '.txt')
            
            if new_json_path == file_path:
                skipped_count += 1
                continue
            
            if os.path.exists(new_json_path):
                print(f"跳过: {file_name} -> {new_name}.json (目标已存在)")
                skipped_count += 1
                continue
            
            os.rename(file_path, new_json_path)
            if os.path.exists(old_txt_path):
                os.rename(old_txt_path, new_txt_path)
            
            print(f"重命名: {file_name} -> {new_name}.json")
            renamed_count += 1
            
        except Exception as e:
            print(f"处理文件 {file_name} 时出错: {e}")
            error_count += 1
    
    print("\n" + "=" * 80)
    print(f"重命名完成！")
    print(f"成功重命名: {renamed_count} 个")
    print(f"跳过: {skipped_count} 个")
    print(f"错误: {error_count} 个")
    
    if no_match_files:
        print(f"\n未找到匹配的标题格式 ({len(no_match_files)} 个):")
        for item in no_match_files:
            print(f"  文件: {item['file_name']}")
            print(f"  标题: {item['title']}")
            print()

if __name__ == "__main__":
    main()
