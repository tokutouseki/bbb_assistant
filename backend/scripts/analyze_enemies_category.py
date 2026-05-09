#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：根据json文件中的category_main和category_sub字段，将敌人目录中的文件分类整理
使用方法：直接运行此脚本，会输出分类信息供确认
"""

import os
import json

# 敌人目录路径
ENEMIES_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\敌人"
# 结果保存文件路径
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\敌人文件分类信息.txt"

# 主函数
def main():
    print("开始分析敌人目录中的文件分类...")
    print("=" * 80)
    
    # 分类统计
    categories = {}
    
    # 遍历敌人目录下的所有JSON文件
    for file_name in os.listdir(ENEMIES_DIR):
        if file_name.endswith('.json'):
            file_path = os.path.join(ENEMIES_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                category_main = data.get('category_main', '未知')
                category_sub = data.get('category_sub', '未知')
                url = data.get('url', '')
                title = data.get('title', '')
                
                # 构建分类键
                category_key = f"{category_main}\\{category_sub}"
                
                # 添加到分类统计
                if category_key not in categories:
                    categories[category_key] = []
                
                categories[category_key].append({
                    'file_name': file_name,
                    'url': url,
                    'title': title
                })
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 保存结果到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("敌人文件分类信息\n")
        f.write("=" * 80 + "\n\n")
        
        for category_key, files in sorted(categories.items()):
            f.write(f"分类: {category_key}\n")
            f.write(f"文件数量: {len(files)}\n")
            f.write("-" * 80 + "\n")
            
            for file_info in files:
                f.write(f"  文件: {file_info['file_name']}\n")
                f.write(f"  URL: {file_info['url']}\n")
                f.write(f"  标题: {file_info['title']}\n")
                f.write("\n")
            
            f.write("=" * 80 + "\n\n")
    
    # 输出统计信息
    print("\n分类统计：")
    for category_key, files in sorted(categories.items()):
        print(f"  {category_key}: {len(files)} 个文件")
    
    print("\n" + "=" * 80)
    print(f"分类信息已保存到: {OUTPUT_FILE}")
    print("\n请查看分类信息，确认是否需要进行文件移动。")

if __name__ == "__main__":
    main()
