#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：处理人偶目录中因目标文件已存在而未重命名的文件
使用方法：直接运行此脚本
逻辑：比对txt文件内容，相同则删除，不同则重命名为_1
"""

import os
import filecmp

PUPPET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\人偶"

def main():
    print("开始处理人偶目录中的重复文件...")
    print("=" * 80)
    
    deleted_count = 0
    renamed_count = 0
    skipped_count = 0
    
    duplicate_pairs = [
        ("晓月镇魂歌_1.json", "晓月镇魂歌.json"),
        ("苍玄之书_1.json", "苍玄之书.json"),
        ("角色资料.json", "西琳.json"),
    ]
    
    for suffix_file, base_file in duplicate_pairs:
        suffix_json = os.path.join(PUPPET_DIR, suffix_file)
        base_json = os.path.join(PUPPET_DIR, base_file)
        suffix_txt = suffix_json.replace('.json', '.txt')
        base_txt = base_json.replace('.json', '.txt')
        
        if not os.path.exists(suffix_json):
            print(f"跳过: {suffix_file} (文件不存在)")
            continue
        
        print(f"\n处理: {suffix_file}")
        print(f"  对比: {base_file}")
        
        if os.path.exists(base_json):
            if os.path.exists(suffix_txt) and os.path.exists(base_txt):
                if filecmp.cmp(suffix_txt, base_txt, shallow=False):
                    print(f"  txt内容相同，删除重复文件")
                    os.remove(suffix_json)
                    os.remove(suffix_txt)
                    deleted_count += 1
                else:
                    print(f"  txt内容不同，保留两个文件")
                    skipped_count += 1
            else:
                print(f"  txt文件不完整，保留两个文件")
                skipped_count += 1
        else:
            print(f"  基础文件不存在，保留")
            skipped_count += 1
    
    print("\n" + "=" * 80)
    print(f"处理完成！")
    print(f"删除重复文件: {deleted_count} 个")
    print(f"保留不同文件: {skipped_count} 个")

if __name__ == "__main__":
    main()
