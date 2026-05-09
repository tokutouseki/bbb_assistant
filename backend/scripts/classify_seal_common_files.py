#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：使用playwright访问URL并获取面包屑导航信息，按照分类整理通用刻印文件
使用方法：直接运行此脚本
注意：需要安装playwright和chromium浏览器
"""

import os
import json
import time
import asyncio
from playwright.async_api import async_playwright

TARGET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土\通用刻印"
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\通用刻印文件分类结果.txt"

async def get_breadcrumb_info(page, url):
    try:
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_selector('nav.detail__breadcrumb', timeout=10000)
        breadcrumb_items = await page.locator('nav.detail__breadcrumb li').all_text_contents()
        breadcrumb_list = [item.strip() for item in breadcrumb_items if item.strip()]
        return breadcrumb_list
    except Exception as e:
        print(f"  获取面包屑导航失败: {e}")
        return []

async def main():
    print("开始获取通用刻印文件的分类信息...")
    print("=" * 80)
    
    categories = {}
    results = []
    
    json_files = [f for f in os.listdir(TARGET_DIR) if f.endswith('.json')]
    total_files = len(json_files)
    
    async with async_playwright() as p:
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        file_count = 0
        for file_name in sorted(json_files):
            file_count += 1
            file_path = os.path.join(TARGET_DIR, file_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                url = data.get('url', '')
                title = data.get('title', '')
                
                if url:
                    print(f"[{file_count}/{total_files}] 处理: {file_name}")
                    
                    breadcrumb = await get_breadcrumb_info(page, url)
                    
                    if len(breadcrumb) >= 3:
                        category_path = "\\".join(breadcrumb[1:])
                    else:
                        category_path = "未知分类"
                    
                    if category_path not in categories:
                        categories[category_path] = []
                    
                    categories[category_path].append({
                        'file_name': file_name,
                        'url': url,
                        'title': title
                    })
                    
                    results.append({
                        'file_name': file_name,
                        'url': url,
                        'title': title,
                        'breadcrumb': breadcrumb,
                        'category_path': category_path
                    })
                    
                    print(f"  分类: {category_path}")
                    print(f"  面包屑: {' -> '.join(breadcrumb)}")
                    
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
        
        await browser.close()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("通用刻印文件分类结果\n")
        f.write("=" * 80 + "\n\n")
        
        for category_path, files in sorted(categories.items()):
            f.write(f"分类: {category_path}\n")
            f.write(f"文件数量: {len(files)}\n")
            f.write("-" * 80 + "\n")
            
            for file_info in files:
                f.write(f"  文件: {file_info['file_name']}\n")
                f.write(f"  URL: {file_info['url']}\n")
                f.write(f"  标题: {file_info['title']}\n")
                f.write("\n")
            
            f.write("=" * 80 + "\n\n")
    
    print("\n" + "=" * 80)
    print("分类统计：")
    for category_path, files in sorted(categories.items()):
        print(f"  {category_path}: {len(files)} 个文件")
    
    print("\n" + "=" * 80)
    print(f"分类信息已保存到: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
