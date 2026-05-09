#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：找出女武神目录中未找到匹配标题格式的文件
使用方法：直接运行此脚本，会输出需要手动调整的文件列表
"""

import os
import json
import re

# 女武神目录路径
VALKYRIE_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\女武神"
# 结果保存文件路径
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\需要手动调整的女武神文件.txt"

# 主函数
def main():
    print("开始查找未找到匹配标题格式的文件...")
    print("=" * 80)
    
    # 统计信息
    unmatched_files = []
    
    # 遍历女武神目录下的所有JSON文件
    for file_name in sorted(os.listdir(VALKYRIE_DIR)):
        if file_name.endswith('.json'):
            file_path = os.path.join(VALKYRIE_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                title = data.get('title', '')
                url = data.get('url', '')
                main_content = data.get('main_content', '')
                
                # 提取"-圣芙蕾雅档案馆-"前面的内容
                # 尝试两种格式：
                # 1. "xxx-圣芙蕾雅档案馆-崩坏3WIKI"
                # 2. "米哈游官方社区_xxx-圣芙蕾雅档案馆-崩坏3WIKI"
                match = re.search(r'^(.+?)-圣芙蕾雅档案馆-', title)
                if match:
                    new_name = match.group(1).strip()
                else:
                    # 尝试第二种格式
                    match = re.search(r'^米哈游官方社区_(.+?)-圣芙蕾雅档案馆-', title)
                    if match:
                        new_name = match.group(1).strip()
                    else:
                        # 未找到匹配的标题格式
                        unmatched_files.append({
                            'file_name': file_name,
                            'title': title,
                            'url': url,
                            'main_content': main_content[:100] if main_content else ''
                        })
                        print(f"未匹配: {file_name}")
                        print(f"  Title: {title}")
                        print(f"  URL: {url}")
                        print()
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 保存结果到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("需要手动调整的女武神文件列表\n")
        f.write("=" * 80 + "\n\n")
        
        for i, file_info in enumerate(unmatched_files, 1):
            f.write(f"{i}. 文件: {file_info['file_name']}\n")
            f.write(f"   Title: {file_info['title']}\n")
            f.write(f"   URL: {file_info['url']}\n")
            f.write(f"   Main Content: {file_info['main_content']}\n")
            f.write("-" * 80 + "\n\n")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print(f"查找完成！")
    print(f"未找到匹配的文件: {len(unmatched_files)} 个")
    print(f"详细信息已保存到: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
