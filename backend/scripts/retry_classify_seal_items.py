#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：重试获取未知分类文件的面包屑导航信息
使用方法：直接运行此脚本
注意：需要安装playwright和chromium浏览器
"""

import os
import json
import time
import asyncio
from playwright.async_api import async_playwright

TARGET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土\物品"
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\物品文件分类结果.txt"

UNKNOWN_FILES = [
    "「决意」.json",
    "「故乡」.json",
    "「纪念」.json",
    "一梦方醒.json",
    "丘壑，易陷难填.json",
    "九命难转.json",
    "五彩斑斓的黑.json",
    "其将背负.json",
    "其将舍弃.json",
    "其将铭记.json",
    "十色浸染的灰.json",
    "善恶明证.json",
    "坠入往昔的流光.json",
]

async def get_breadcrumb_info(page, url):
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_selector('nav.detail__breadcrumb', timeout=15000)
        breadcrumb_items = await page.locator('nav.detail__breadcrumb li').all_text_contents()
        breadcrumb_list = [item.strip() for item in breadcrumb_items if item.strip()]
        return breadcrumb_list
    except Exception as e:
        print(f"  获取面包屑导航失败: {e}")
        return []

async def main():
    print("开始重试获取未知分类文件的分类信息...")
    print("=" * 80)
    
    categories = {}
    results = []
    
    async with async_playwright() as p:
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        file_count = 0
        total_files = len(UNKNOWN_FILES)
        
        for file_name in UNKNOWN_FILES:
            file_count += 1
            file_path = os.path.join(TARGET_DIR, file_name)
            
            if not os.path.exists(file_path):
                print(f"[{file_count}/{total_files}] 跳过: {file_name} (文件不存在)")
                continue
            
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
                    
                    time.sleep(1)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
        
        await browser.close()
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write("\n\n重试分类结果\n")
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
    print("重试分类统计：")
    for category_path, files in sorted(categories.items()):
        print(f"  {category_path}: {len(files)} 个文件")
    
    print("\n" + "=" * 80)
    print(f"分类信息已追加到: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
