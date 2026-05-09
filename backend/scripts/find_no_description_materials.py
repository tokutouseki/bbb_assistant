#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：找出材料目录下没有详细材料描述的JSON文件，并提取其url和main_content保存到txt文件
使用方法：直接运行此脚本，会生成结果文件
"""

import os
import json

# 材料目录路径
MATERIALS_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\材料"
# 结果保存文件路径
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\没有详细描述的材料文件.txt"

# 判断是否为没有详细描述的文件
def is_no_description_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查main_content字段是否存在
        if 'main_content' not in data:
            return True
        
        main_content = data['main_content']
        
        # 检查main_content是否为空或过短
        if not main_content or len(main_content.strip()) == 0:
            return True
        
        # 检查main_content是否只是简单重复文件名或标题
        file_name = os.path.basename(file_path).replace('.json', '')
        if 'title' in data:
            title = data['title']
            # 如果main_content与title相似且长度较短，可能没有详细描述
            if main_content.strip() == title.strip() or len(main_content) < 50:
                return True
        
        # 检查main_content是否包含详细描述关键词
        description_keywords = ['材料描述', '类型', '使用', '获取', '途径']
        has_keywords = any(keyword in main_content for keyword in description_keywords)
        
        # 如果没有关键词且长度较短，可能没有详细描述
        if not has_keywords and len(main_content) < 100:
            return True
        
        return False
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False

# 提取文件的url和main_content
def extract_file_info(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        url = data.get('url', 'N/A')
        main_content = data.get('main_content', 'N/A')
        
        return url, main_content
    except Exception as e:
        print(f"提取文件 {file_path} 信息时出错: {e}")
        return 'N/A', 'N/A'

# 主函数
def main():
    print("开始查找没有详细材料描述的文件...")
    print("=" * 60)
    
    no_description_files = []
    file_infos = []
    
    # 遍历材料目录下的所有JSON文件
    for file_name in os.listdir(MATERIALS_DIR):
        if file_name.endswith('.json'):
            file_path = os.path.join(MATERIALS_DIR, file_name)
            if is_no_description_file(file_path):
                no_description_files.append(file_name)
                url, main_content = extract_file_info(file_path)
                file_infos.append((file_name, url, main_content))
    
    # 保存结果到txt文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("没有详细材料描述的文件列表\n")
        f.write("=" * 80 + "\n\n")
        
        for i, (file_name, url, main_content) in enumerate(file_infos, 1):
            f.write(f"{i}. 文件: {file_name}\n")
            f.write(f"   URL: {url}\n")
            f.write(f"   Main Content: {main_content}\n")
            f.write("-" * 80 + "\n\n")
    
    # 输出结果
    if no_description_files:
        print("找到以下没有详细材料描述的文件：")
        print("-" * 60)
        for file_name in no_description_files:
            print(f"• {file_name}")
        print("-" * 60)
        print(f"总计: {len(no_description_files)} 个文件")
        print(f"结果已保存到: {OUTPUT_FILE}")
    else:
        print("没有找到没有详细材料描述的文件")

if __name__ == "__main__":
    main()
