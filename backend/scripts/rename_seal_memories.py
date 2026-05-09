#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：将追忆目录中的json文件和txt文件的名字修改为title中"-圣芙蕾雅档案馆-"前面的内容
使用方法：直接运行此脚本
"""

import os
import json
import re

TARGET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土\追忆"

def main():
    print("开始修改追忆目录中的文件名...")
    print("=" * 80)
    
    renamed_files = []
    skipped_files = []
    
    for file_name in os.listdir(TARGET_DIR):
        if file_name.endswith('.json'):
            file_path = os.path.join(TARGET_DIR, file_name)
            
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
                        print(f"跳过: {file_name} (未找到匹配的标题格式)")
                        skipped_files.append(file_name)
                        continue
                
                new_json_path = os.path.join(TARGET_DIR, f"{new_name}.json")
                new_txt_path = os.path.join(TARGET_DIR, f"{new_name}.txt")
                
                if new_json_path != file_path:
                    if os.path.exists(new_json_path):
                        print(f"跳过: {file_name} -> {new_name}.json (目标文件已存在)")
                        skipped_files.append(file_name)
                    else:
                        os.rename(file_path, new_json_path)
                        
                        old_txt_path = file_path.replace('.json', '.txt')
                        if os.path.exists(old_txt_path):
                            os.rename(old_txt_path, new_txt_path)
                        
                        renamed_files.append((file_name, f"{new_name}.json"))
                        print(f"重命名: {file_name} -> {new_name}.json")
                else:
                    skipped_files.append(file_name)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    print("\n" + "=" * 80)
    print(f"重命名完成！")
    print(f"成功重命名: {len(renamed_files)} 个文件")
    print(f"跳过: {len(skipped_files)} 个文件")

if __name__ == "__main__":
    main()
