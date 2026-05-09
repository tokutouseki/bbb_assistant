#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：根据分类结果移动追忆目录中的文件到相应的目录
使用方法：直接运行此脚本
"""

import os
import json
import shutil

TARGET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土\追忆"
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
CLASSIFICATION_FILE = r"d:\TokusCode\bbb_assistant\backend\data\追忆文件分类结果.txt"

def parse_classification_file(file_path):
    classifications = {}
    current_category = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('分类:'):
            current_category = line.replace('分类:', '').strip()
            classifications[current_category] = []
        elif line.startswith('文件:') and current_category:
            file_name = line.replace('文件:', '').strip()
            classifications[current_category].append(file_name)
        
        i += 1
    
    return classifications

def main():
    print("开始根据分类结果移动文件...")
    print("=" * 80)
    
    classifications = parse_classification_file(CLASSIFICATION_FILE)
    
    moved_count = 0
    kept_count = 0
    skipped_count = 0
    error_count = 0
    
    for category, files in classifications.items():
        if category == "往世乐土\\追忆":
            print(f"\n跳过分类: {category}")
            print(f"文件数量: {len(files)} (保留在原位置)")
            print("-" * 80)
            kept_count += len(files)
            continue
        
        print(f"\n处理分类: {category}")
        print(f"文件数量: {len(files)}")
        print("-" * 80)
        
        target_dir = os.path.join(DATA_ROOT, category)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            print(f"创建目录: {target_dir}")
        
        for file_name in files:
            source_json = os.path.join(TARGET_DIR, file_name)
            source_txt = os.path.join(TARGET_DIR, file_name.replace('.json', '.txt'))
            
            target_json = os.path.join(target_dir, file_name)
            target_txt = os.path.join(target_dir, file_name.replace('.json', '.txt'))
            
            try:
                if os.path.exists(source_json):
                    shutil.move(source_json, target_json)
                    
                    if os.path.exists(source_txt):
                        shutil.move(source_txt, target_txt)
                    
                    print(f"  ✓ 移动: {file_name}")
                    moved_count += 1
                else:
                    print(f"  ✗ 跳过: {file_name} (源文件不存在)")
                    skipped_count += 1
            except Exception as e:
                print(f"  ✗ 错误: {file_name} - {e}")
                error_count += 1
    
    print("\n" + "=" * 80)
    print("移动完成！")
    print(f"成功移动: {moved_count} 个文件")
    print(f"保留在原位置: {kept_count} 个文件")
    print(f"跳过: {skipped_count} 个文件")
    print(f"错误: {error_count} 个文件")

if __name__ == "__main__":
    main()
