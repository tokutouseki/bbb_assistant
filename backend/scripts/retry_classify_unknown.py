#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：重试分类未知分类目录中剩余的文件
使用方法：直接运行此脚本
"""

import os
import json
import time
import asyncio
from playwright.async_api import async_playwright

UNKNOWN_DIR = r"d:\TokusCode\bbb_assistant\backend\data\未知分类"
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\未知分类文件分类结果_重试.txt"

async def get_breadcrumb_info(page, url, retry_count=3):
    for attempt in range(retry_count):
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await page.wait_for_selector('nav.detail__breadcrumb', timeout=15000)
            breadcrumb_items = await page.locator('nav.detail__breadcrumb li').all_text_contents()
            breadcrumb_list = [item.strip() for item in breadcrumb_items if item.strip()]
            return breadcrumb_list
        except Exception as e:
            print(f"  尝试 {attempt + 1}/{retry_count} 失败: {e}")
            if attempt < retry_count - 1:
                await asyncio.sleep(2)
    return []

async def main():
    print("开始重试分类未知分类文件...")
    print("=" * 80)
    
    categories = {}
    results = []
    failed_files = []
    
    json_files = [f for f in os.listdir(UNKNOWN_DIR) if f.endswith('.json')]
    total_files = len(json_files)
    print(f"共有 {total_files} 个JSON文件需要处理")
    
    async with async_playwright() as p:
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        file_count = 0
        for file_name in sorted(json_files):
            file_count += 1
            file_path = os.path.join(UNKNOWN_DIR, file_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                url = data.get('url', '')
                title = data.get('title', '')
                
                if url:
                    print(f"\n[{file_count}/{total_files}] 处理: {file_name}")
                    print(f"  URL: {url}")
                    
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
                    
                    if category_path == "未知分类":
                        failed_files.append(file_name)
                    
                    time.sleep(0.5)
                else:
                    print(f"\n[{file_count}/{total_files}] 跳过: {file_name} (无URL)")
                    failed_files.append(file_name)
                    
            except Exception as e:
                print(f"\n[{file_count}/{total_files}] 处理文件 {file_name} 时出错: {e}")
                failed_files.append(file_name)
        
        await browser.close()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("未知分类文件分类结果(重试)\n")
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
    
    if failed_files:
        print(f"\n未能分类的文件 ({len(failed_files)} 个):")
        for fn in failed_files:
            print(f"  - {fn}")
    
    print("\n" + "=" * 80)
    print(f"分类信息已保存到: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
