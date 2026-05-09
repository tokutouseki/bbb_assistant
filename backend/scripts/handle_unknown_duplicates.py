#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：处理未知分类目录中带_1后缀的重复文件
使用方法：直接运行此脚本
逻辑：
1. 找到所有带_1后缀的文件
2. 检查是否存在对应的无后缀文件
3. 比对txt文件内容：
   - 如果相同，删除_1后缀的文件
   - 如果不同，保留两个文件
"""

import os
import filecmp

UNKNOWN_DIR = r"d:\TokusCode\bbb_assistant\backend\data\未知分类"

def main():
    print("开始处理未知分类目录中的重复文件...")
    print("=" * 80)
    
    deleted_count = 0
    kept_count = 0
    no_pair_count = 0
    
    json_files = [f for f in os.listdir(UNKNOWN_DIR) if f.endswith('.json')]
    
    for json_file in sorted(json_files):
        if json_file.endswith('_1.json'):
            base_name = json_file[:-7]
            base_json = f"{base_name}.json"
            base_txt = f"{base_name}.txt"
            suffix_json = json_file
            suffix_txt = json_file.replace('.json', '.txt')
            
            base_json_path = os.path.join(UNKNOWN_DIR, base_json)
            base_txt_path = os.path.join(UNKNOWN_DIR, base_txt)
            suffix_json_path = os.path.join(UNKNOWN_DIR, suffix_json)
            suffix_txt_path = os.path.join(UNKNOWN_DIR, suffix_txt)
            
            if os.path.exists(base_json_path):
                print(f"\n处理: {base_name}")
                print(f"  文件1: {base_json}")
                print(f"  文件2: {suffix_json}")
                
                if os.path.exists(base_txt_path) and os.path.exists(suffix_txt_path):
                    if filecmp.cmp(base_txt_path, suffix_txt_path, shallow=False):
                        print(f"  txt内容相同，删除重复文件: {suffix_json}")
                        os.remove(suffix_json_path)
                        os.remove(suffix_txt_path)
                        deleted_count += 1
                    else:
                        print(f"  txt内容不同，保留两个文件")
                        kept_count += 1
                else:
                    print(f"  txt文件不完整，保留两个文件")
                    kept_count += 1
            else:
                print(f"\n跳过: {suffix_json} (无对应的基础文件)")
                no_pair_count += 1
    
    print("\n" + "=" * 80)
    print(f"处理完成！")
    print(f"删除重复文件: {deleted_count} 个")
    print(f"保留不同文件: {kept_count} 个")
    print(f"无配对文件: {no_pair_count} 个")

if __name__ == "__main__":
    main()
