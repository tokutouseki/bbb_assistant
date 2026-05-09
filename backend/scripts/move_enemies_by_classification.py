#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：根据分类结果移动敌人目录中的文件到相应的目录（保留图鉴\敌人分类的文件）
使用方法：直接运行此脚本
"""

import os
import json
import shutil

# 敌人目录路径
ENEMIES_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\敌人"
# 数据根目录
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
# 分类结果文件路径
CLASSIFICATION_FILE = r"d:\TokusCode\bbb_assistant\backend\data\敌人文件分类结果.txt"

# 解析分类结果文件
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

# 主函数
def main():
    print("开始根据分类结果移动文件...")
    print("=" * 80)
    
    # 解析分类结果文件
    classifications = parse_classification_file(CLASSIFICATION_FILE)
    
    # 统计信息
    moved_count = 0
    skipped_count = 0
    kept_count = 0
    error_count = 0
    
    # 遍历所有分类
    for category, files in classifications.items():
        # 跳过"图鉴\敌人"分类，这些文件应该保留在原位置
        if category == "图鉴\\敌人":
            print(f"\n跳过分类: {category}")
            print(f"文件数量: {len(files)} (保留在原位置)")
            print("-" * 80)
            kept_count += len(files)
            continue
        
        print(f"\n处理分类: {category}")
        print(f"文件数量: {len(files)}")
        print("-" * 80)
        
        # 构建目标目录路径
        target_dir = os.path.join(DATA_ROOT, category)
        
        # 如果目标目录不存在，则创建
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            print(f"创建目录: {target_dir}")
        
        # 移动文件
        for file_name in files:
            # 源文件路径
            source_json = os.path.join(ENEMIES_DIR, file_name)
            source_txt = os.path.join(ENEMIES_DIR, file_name.replace('.json', '.txt'))
            
            # 目标文件路径
            target_json = os.path.join(target_dir, file_name)
            target_txt = os.path.join(target_dir, file_name.replace('.json', '.txt'))
            
            try:
                # 检查源文件是否存在
                if os.path.exists(source_json):
                    # 移动json文件
                    shutil.move(source_json, target_json)
                    
                    # 移动txt文件（如果存在）
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
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print("移动完成！")
    print(f"成功移动: {moved_count} 个文件")
    print(f"保留在原位置: {kept_count} 个文件")
    print(f"跳过: {skipped_count} 个文件")
    print(f"错误: {error_count} 个文件")

if __name__ == "__main__":
    main()
