#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：通过访问URL获取面包屑导航信息，将敌人目录中的文件分类整理
使用方法：直接运行此脚本，会自动访问URL并获取分类信息
"""

import os
import json
import requests
from bs4 import BeautifulSoup
import time

# 敌人目录路径
ENEMIES_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\敌人"
# 数据根目录
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
# 结果保存文件路径
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\敌人文件分类信息.txt"

# 获取面包屑导航信息
def get_breadcrumb_info(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找面包屑导航
        breadcrumb_nav = soup.find('nav', class_='detail__breadcrumb')
        
        if breadcrumb_nav:
            # 获取所有面包屑项
            items = breadcrumb_nav.find_all('li')
            breadcrumb_list = []
            for item in items:
                text = item.get_text(strip=True)
                if text:
                    breadcrumb_list.append(text)
            
            return breadcrumb_list
        else:
            return []
    except Exception as e:
        print(f"获取面包屑导航失败: {e}")
        return []

# 主函数
def main():
    print("开始获取敌人文件的分类信息...")
    print("=" * 80)
    
    # 结果列表
    results = []
    
    # 遍历敌人目录下的所有JSON文件
    for file_name in os.listdir(ENEMIES_DIR):
        if file_name.endswith('.json'):
            file_path = os.path.join(ENEMIES_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                url = data.get('url', '')
                title = data.get('title', '')
                
                if url:
                    # 获取面包屑导航信息
                    breadcrumb = get_breadcrumb_info(url)
                    
                    results.append({
                        'file_name': file_name,
                        'url': url,
                        'title': title,
                        'breadcrumb': breadcrumb
                    })
                    
                    print(f"处理: {file_name}")
                    print(f"  面包屑: {' -> '.join(breadcrumb)}")
                    
                    # 延迟，避免请求过快
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 保存结果到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("敌人文件分类信息\n")
        f.write("=" * 80 + "\n\n")
        
        for result in results:
            f.write(f"文件: {result['file_name']}\n")
            f.write(f"URL: {result['url']}\n")
            f.write(f"标题: {result['title']}\n")
            f.write(f"面包屑: {' -> '.join(result['breadcrumb'])}\n")
            f.write("-" * 80 + "\n\n")
    
    print("\n" + "=" * 80)
    print(f"分类信息已保存到: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
