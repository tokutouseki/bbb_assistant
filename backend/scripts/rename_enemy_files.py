#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：将json文件和txt文件的名字修改为title中"-圣芙蕾雅档案馆-"前面的内容
使用方法：直接运行此脚本
"""

import os
import json
import re

# 敌人目录路径
ENEMIES_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\敌人"

# 主函数
def main():
    print("开始修改文件名...")
    print("=" * 80)
    
    # 统计信息
    renamed_files = []
    skipped_files = []
    
    # 遍历敌人目录下的所有JSON文件
    for file_name in os.listdir(ENEMIES_DIR):
        if file_name.endswith('.json'):
            file_path = os.path.join(ENEMIES_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                title = data.get('title', '')
                
                # 提取"-圣芙蕾雅档案馆-"前面的内容
                match = re.search(r'^(.+?)-圣芙蕾雅档案馆-', title)
                if match:
                    new_name = match.group(1).strip()
                    
                    # 检查新文件名是否已存在
                    new_json_path = os.path.join(ENEMIES_DIR, f"{new_name}.json")
                    new_txt_path = os.path.join(ENEMIES_DIR, f"{new_name}.txt")
                    
                    if new_json_path != file_path:
                        # 检查目标文件是否已存在
                        if os.path.exists(new_json_path):
                            print(f"跳过: {file_name} -> {new_name}.json (目标文件已存在)")
                            skipped_files.append(file_name)
                        else:
                            # 重命名json文件
                            os.rename(file_path, new_json_path)
                            
                            # 重命名对应的txt文件
                            old_txt_path = file_path.replace('.json', '.txt')
                            if os.path.exists(old_txt_path):
                                os.rename(old_txt_path, new_txt_path)
                            
                            renamed_files.append((file_name, f"{new_name}.json"))
                            print(f"重命名: {file_name} -> {new_name}.json")
                    else:
                        skipped_files.append(file_name)
                else:
                    print(f"跳过: {file_name} (未找到匹配的标题格式)")
                    skipped_files.append(file_name)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print(f"重命名完成！")
    print(f"成功重命名: {len(renamed_files)} 个文件")
    print(f"跳过: {len(skipped_files)} 个文件")

if __name__ == "__main__":
    main()
