#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：收集武器目录中所有JSON文件的URL，并通过面包屑导航进行分类
使用方法：直接运行此脚本
"""

import os
import json
import time
import asyncio
from playwright.async_api import async_playwright

WEAPON_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\武器"
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
URL_FILE = r"d:\TokusCode\bbb_assistant\backend\data\武器文件URL列表.txt"
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\武器文件分类结果.txt"

async def get_breadcrumb_info(page, url, retry_count=3):
    for attempt in range(retry_count):
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await page.wait_for_selector('nav.detail__breadcrumb', timeout=15000)
            breadcrumb_items = await page.locator('nav.detail__breadcrumb li').all_text_contents()
            breadcrumb_list = [item.strip() for item in breadcrumb_items if item.strip()]
            return breadcrumb_list
        except Exception as e:
            if attempt < retry_count - 1:
                await asyncio.sleep(2)
    return []

async def main():
    print("开始收集武器目录中的URL并进行分类...")
    print("=" * 80)
    
    json_files = [f for f in os.listdir(WEAPON_DIR) if f.endswith('.json')]
    total_files = len(json_files)
    print(f"共有 {total_files} 个JSON文件需要处理")
    
    url_list = []
    
    for file_name in sorted(json_files):
        file_path = os.path.join(WEAPON_DIR, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            url = data.get('url', '')
            title = data.get('title', '')
            if url:
                url_list.append({'file_name': file_name, 'url': url, 'title': title})
        except Exception as e:
            print(f"读取文件 {file_name} 时出错: {e}")
    
    with open(URL_FILE, 'w', encoding='utf-8') as f:
        f.write("武器目录文件URL列表\n")
        f.write("=" * 80 + "\n\n")
        for item in url_list:
            f.write(f"文件: {item['file_name']}\n")
            f.write(f"URL: {item['url']}\n")
            f.write(f"标题: {item['title']}\n\n")
    
    print(f"URL列表已保存到: {URL_FILE}")
    print(f"共有 {len(url_list)} 个有效URL")
    
    print("\n开始获取面包屑导航进行分类...")
    print("=" * 80)
    
    categories = {}
    failed_files = []
    
    async with async_playwright() as p:
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        file_count = 0
        for item in url_list:
            file_count += 1
            file_name = item['file_name']
            url = item['url']
            
            print(f"\n[{file_count}/{len(url_list)}] 处理: {file_name}")
            
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
                'title': item['title']
            })
            
            print(f"  分类: {category_path}")
            
            if category_path == "未知分类":
                failed_files.append(file_name)
            
            time.sleep(0.15)
        
        await browser.close()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("武器文件分类结果\n")
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
