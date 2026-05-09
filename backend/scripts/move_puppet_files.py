#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：根据分类结果移动人偶目录中的文件到相应的目录
使用方法：直接运行此脚本
"""

import os
import shutil

PUPPET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\人偶"
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
CLASSIFICATION_FILE = r"d:\TokusCode\bbb_assistant\backend\data\人偶文件分类结果.txt"

def parse_classification_file(file_path):
    categories = {}
    current_category = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('分类:'):
                current_category = line.replace('分类:', '').strip()
                categories[current_category] = []
            elif line.startswith('文件:') and current_category:
                file_name = line.replace('文件:', '').strip()
                categories[current_category].append(file_name)
    
    return categories

def main():
    print("开始移动人偶目录中的文件...")
    print("=" * 80)
    
    categories = parse_classification_file(CLASSIFICATION_FILE)
    
    moved_count = 0
    kept_count = 0
    skipped_count = 0
    error_count = 0
    
    for category_path, files in categories.items():
        if category_path == "未知分类":
            print(f"\n跳过分类: {category_path} ({len(files)} 个文件)")
            kept_count += len(files)
            continue
        
        if category_path == "图鉴\\人偶":
            print(f"\n保留分类: {category_path} ({len(files)} 个文件) - 保持在原位置")
            kept_count += len(files)
            continue
        
        print(f"\n处理分类: {category_path} ({len(files)} 个文件)")
        
        for file_name in files:
            try:
                src_json = os.path.join(PUPPET_DIR, file_name)
                src_txt = src_json.replace('.json', '.txt')
                
                if not os.path.exists(src_json):
                    print(f"  ✗ 跳过: {file_name} (源文件不存在)")
                    skipped_count += 1
                    continue
                
                target_dir = os.path.join(DATA_ROOT, category_path)
                
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                    print(f"  创建目录: {target_dir}")
                
                dst_json = os.path.join(target_dir, file_name)
                dst_txt = dst_json.replace('.json', '.txt')
                
                if os.path.exists(dst_json):
                    print(f"  ⚠ 跳过: {file_name} (目标文件已存在)")
                    skipped_count += 1
                    continue
                
                shutil.move(src_json, dst_json)
                if os.path.exists(src_txt):
                    shutil.move(src_txt, dst_txt)
                
                print(f"  ✓ 移动: {file_name} -> {category_path}")
                moved_count += 1
                
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
