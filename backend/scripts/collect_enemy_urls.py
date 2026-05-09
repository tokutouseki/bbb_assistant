#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：收集敌人目录下所有json文件中的URL，并保存到txt文件中
使用方法：直接运行此脚本
"""

import os
import json

# 敌人目录路径
ENEMIES_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\敌人"
# URL保存文件路径
URL_FILE = r"d:\TokusCode\bbb_assistant\backend\data\敌人文件URL列表.txt"

# 主函数
def main():
    print("开始收集敌人文件的URL...")
    print("=" * 80)
    
    # URL列表
    urls = []
    
    # 遍历敌人目录下的所有JSON文件
    for file_name in sorted(os.listdir(ENEMIES_DIR)):
        if file_name.endswith('.json'):
            file_path = os.path.join(ENEMIES_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                url = data.get('url', '')
                title = data.get('title', '')
                
                if url:
                    urls.append({
                        'file_name': file_name,
                        'url': url,
                        'title': title
                    })
                    print(f"收集: {file_name}")
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 保存URL到文件
    with open(URL_FILE, 'w', encoding='utf-8') as f:
        f.write("敌人文件URL列表\n")
        f.write("=" * 80 + "\n\n")
        
        for url_info in urls:
            f.write(f"文件: {url_info['file_name']}\n")
            f.write(f"URL: {url_info['url']}\n")
            f.write(f"标题: {url_info['title']}\n")
            f.write("-" * 80 + "\n\n")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print(f"URL收集完成！")
    print(f"共收集: {len(urls)} 个URL")
    print(f"已保存到: {URL_FILE}")

if __name__ == "__main__":
    main()
