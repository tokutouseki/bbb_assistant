#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：重命名往世乐土通用刻印目录中的文件，使用方法：直接运行此脚本
"""

import os
import json
import re

SEAL_DIR = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土\通用刻印"
output_file = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土通用刻印文件重命名结果.txt"
no_match_file = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土通用刻印未匹配标题.txt"

def main():
    print("开始重命名往世乐土通用刻印目录中的文件...")
    print("=" * 80)
    
    renamed_count = 0
    skipped_count = 0
    error_count = 0
    no_match_files = []
    
    json_files = [f for f in os.listdir(SEAL_DIR) if f.endswith('.json')]
    total_files = len(json_files)
    print(f"共有 {total_files} 个JSON文件需要处理")
    
    for file_name in sorted(json_files):
        file_path = os.path.join(SEAL_DIR, file_name)
        
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
            
            new_json_path = os.path.join(SEAL_DIR, f"{new_name}.json")
            new_txt_path = os.path.join(SEAL_DIR, f"{new_name}.txt")
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
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("往世乐土通用刻印文件重命名结果\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"成功重命名: {renamed_count} 个\n")
        f.write(f"跳过: {skipped_count} 个\n")
        f.write(f"错误: {error_count} 个\n")
    
    if no_match_files:
        f.write(f"\n未找到匹配的标题格式 ({len(no_match_files)} 个):\n")
        for item in no_match_files:
            f.write(f"  文件: {item['file_name']}\n")
            f.write(f"  标题: {item['title']}\n")
    
    with open(no_match_file, 'w', encoding='utf-8') as f:
        f.write("未找到匹配的标题格式的文件\n")
        f.write("=" * 80 + "\n\n")
        for item in no_match_files:
            f.write(f"文件: {item['file_name']}\n")
            f.write(f"标题: {item['title']}\n\n")
    
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

if __name__ == "__main__":
    main()
