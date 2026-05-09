#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：处理女武神目录中因目标文件已存在而未重命名的文件
使用方法：直接运行此脚本
"""

import os
import json
import re
import filecmp

# 女武神目录路径
VALKYRIE_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\女武神"

# 主函数
def main():
    print("开始处理未重命名的文件...")
    print("=" * 80)
    
    # 统计信息
    deleted_count = 0
    renamed_count = 0
    skipped_count = 0
    
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
                new_txt_path = os.path.join(VALKYRIE_DIR, f"{new_name}.txt")
                
                if new_json_path != file_path and os.path.exists(new_json_path):
                    # 这是一个需要重命名的文件，但目标文件已存在
                    print(f"\n处理: {file_name}")
                    print(f"  目标文件: {new_name}.json (已存在)")
                    
                    # 比对txt文件内容
                    old_txt_path = file_path.replace('.json', '.txt')
                    
                    if os.path.exists(old_txt_path) and os.path.exists(new_txt_path):
                        # 比对txt文件内容
                        if filecmp.cmp(old_txt_path, new_txt_path, shallow=False):
                            # txt文件内容相同，删除重复文件
                            print(f"  txt文件内容相同，删除重复文件")
                            os.remove(file_path)
                            os.remove(old_txt_path)
                            deleted_count += 1
                        else:
                            # txt文件内容不同，重命名为_1
                            new_json_path_1 = os.path.join(VALKYRIE_DIR, f"{new_name}_1.json")
                            new_txt_path_1 = os.path.join(VALKYRIE_DIR, f"{new_name}_1.txt")
                            
                            # 检查_1文件是否已存在
                            if os.path.exists(new_json_path_1):
                                print(f"  {new_name}_1.json 已存在，跳过")
                                skipped_count += 1
                            else:
                                print(f"  txt文件内容不同，重命名为 {new_name}_1.json")
                                os.rename(file_path, new_json_path_1)
                                os.rename(old_txt_path, new_txt_path_1)
                                renamed_count += 1
                    else:
                        # txt文件不存在，跳过
                        print(f"  txt文件不存在，跳过")
                        skipped_count += 1
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print(f"处理完成！")
    print(f"删除重复文件: {deleted_count} 个")
    print(f"重命名为_1: {renamed_count} 个")
    print(f"跳过: {skipped_count} 个")

if __name__ == "__main__":
    main()
