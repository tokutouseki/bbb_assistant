#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：找出女武神目录中重复的文件并删除
使用方法：直接运行此脚本
"""

import os
import json
import re

# 女武神目录路径
VALKYRIE_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\女武神"

# 主函数
def main():
    print("开始查找重复的文件...")
    print("=" * 80)
    
    # 统计信息
    file_mapping = {}  # 新文件名 -> 原文件名列表
    duplicate_files = []  # 重复的文件列表
    
    # 遍历女武神目录下的所有JSON文件
    for file_name in sorted(os.listdir(VALKYRIE_DIR)):
        if file_name.endswith('.json'):
            file_path = os.path.join(VALKYRIE_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                title = data.get('title', '')
                
                # 提取"-圣芙蕾雅档案馆-"前面的内容
                match = re.search(r'^(.+?)-圣芙蕾雅档案馆-', title)
                if match:
                    new_name = match.group(1).strip()
                else:
                    # 尝试第二种格式
                    match = re.search(r'^米哈游官方社区_(.+?)-圣芙蕾雅档案馆-', title)
                    if match:
                        new_name = match.group(1).strip()
                    else:
                        continue
                
                # 检查新文件名是否已存在
                new_json_path = os.path.join(VALKYRIE_DIR, f"{new_name}.json")
                
                if new_json_path != file_path:
                    # 这是一个需要重命名的文件
                    if new_name not in file_mapping:
                        file_mapping[new_name] = [file_name]
                    else:
                        file_mapping[new_name].append(file_name)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 找出重复的文件
    for new_name, files in file_mapping.items():
        if len(files) > 1:
            print(f"\n重复文件: {new_name}.json")
            print(f"  文件列表:")
            for file in files:
                print(f"    - {file}")
            duplicate_files.extend(files)
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print(f"找到 {len(duplicate_files)} 个重复文件")
    
    # 询问是否删除
    if duplicate_files:
        response = input("\n是否删除这些重复文件？(y/n): ")
        if response.lower() == 'y':
            for file_name in duplicate_files:
                file_path = os.path.join(VALKYRIE_DIR, file_name)
                txt_path = file_path.replace('.json', '.txt')
                
                try:
                    # 删除json文件
                    os.remove(file_path)
                    
                    # 删除txt文件
                    if os.path.exists(txt_path):
                        os.remove(txt_path)
                    
                    print(f"删除: {file_name}")
                except Exception as e:
                    print(f"删除 {file_name} 时出错: {e}")
            
            print("\n删除完成！")
        else:
            print("取消删除")

if __name__ == "__main__":
    main()
