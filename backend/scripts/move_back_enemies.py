#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：将错误移动的"图鉴\敌人"分类的文件移回到敌人目录
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
    print("开始将'图鉴\\敌人'分类的文件移回到敌人目录...")
    print("=" * 80)
    
    # 解析分类结果文件
    classifications = parse_classification_file(CLASSIFICATION_FILE)
    
    # 获取"图鉴\敌人"分类的文件列表
    enemy_files = classifications.get("图鉴\\敌人", [])
    
    print(f"需要移回的文件数量: {len(enemy_files)}")
    print("-" * 80)
    
    # 统计信息
    moved_count = 0
    not_found_count = 0
    error_count = 0
    
    # 确保敌人目录存在
    if not os.path.exists(ENEMIES_DIR):
        os.makedirs(ENEMIES_DIR)
        print(f"创建目录: {ENEMIES_DIR}")
    
    # 移动文件
    for file_name in enemy_files:
        # 在数据根目录下查找文件
        found = False
        for root, dirs, files in os.walk(DATA_ROOT):
            if file_name in files:
                # 找到文件，移动到敌人目录
                source_json = os.path.join(root, file_name)
                source_txt = os.path.join(root, file_name.replace('.json', '.txt'))
                
                target_json = os.path.join(ENEMIES_DIR, file_name)
                target_txt = os.path.join(ENEMIES_DIR, file_name.replace('.json', '.txt'))
                
                try:
                    # 移动json文件
                    shutil.move(source_json, target_json)
                    
                    # 移动txt文件（如果存在）
                    if os.path.exists(source_txt):
                        shutil.move(source_txt, target_txt)
                    
                    print(f"  ✓ 移回: {file_name}")
                    moved_count += 1
                    found = True
                except Exception as e:
                    print(f"  ✗ 错误: {file_name} - {e}")
                    error_count += 1
                break
        
        if not found:
            print(f"  ✗ 未找到: {file_name}")
            not_found_count += 1
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print("移动完成！")
    print(f"成功移回: {moved_count} 个文件")
    print(f"未找到: {not_found_count} 个文件")
    print(f"错误: {error_count} 个文件")

if __name__ == "__main__":
    main()
