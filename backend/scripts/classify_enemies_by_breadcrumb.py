#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：使用playwright访问URL并获取面包屑导航信息，按照分类整理文件
使用方法：直接运行此脚本
注意：需要安装playwright和chromium浏览器
"""

import os
import json
import time
import asyncio
from playwright.async_api import async_playwright

# 敌人目录路径
ENEMIES_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\敌人"
# 数据根目录
DATA_ROOT = r"d:\TokusCode\bbb_assistant\backend\data"
# 结果保存文件路径
OUTPUT_FILE = r"d:\TokusCode\bbb_assistant\backend\data\敌人文件分类结果.txt"

# 获取面包屑导航信息
async def get_breadcrumb_info(page, url):
    try:
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # 等待面包屑导航加载
        await page.wait_for_selector('nav.detail__breadcrumb', timeout=10000)
        
        # 获取所有面包屑项
        breadcrumb_items = await page.locator('nav.detail__breadcrumb li').all_text_contents()
        
        # 清理面包屑项
        breadcrumb_list = [item.strip() for item in breadcrumb_items if item.strip()]
        
        return breadcrumb_list
    except Exception as e:
        print(f"  获取面包屑导航失败: {e}")
        return []

# 主函数
async def main():
    print("开始获取敌人文件的分类信息...")
    print("=" * 80)
    
    # 分类统计
    categories = {}
    results = []
    
    async with async_playwright() as p:
        # 启动浏览器
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 遍历敌人目录下的所有JSON文件
        file_count = 0
        for file_name in sorted(os.listdir(ENEMIES_DIR)):
            if file_name.endswith('.json'):
                file_count += 1
                file_path = os.path.join(ENEMIES_DIR, file_name)
                
                try:
                    # 读取json文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    url = data.get('url', '')
                    title = data.get('title', '')
                    
                    if url:
                        print(f"[{file_count}/155] 处理: {file_name}")
                        
                        # 获取面包屑导航信息
                        breadcrumb = await get_breadcrumb_info(page, url)
                        
                        # 构建分类路径
                        if len(breadcrumb) >= 3:
                            category_path = "\\".join(breadcrumb[1:])  # 跳过"首页"
                        else:
                            category_path = "未知分类"
                        
                        # 添加到分类统计
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
                        
                        # 延迟，避免请求过快
                        time.sleep(0.5)
                    
                except Exception as e:
                    print(f"处理文件 {file_name} 时出错: {e}")
        
        # 关闭浏览器
        await browser.close()
    
    # 保存结果到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("敌人文件分类结果\n")
        f.write("=" * 80 + "\n\n")
        
        # 按分类输出
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
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print("分类统计：")
    for category_path, files in sorted(categories.items()):
        print(f"  {category_path}: {len(files)} 个文件")
    
    print("\n" + "=" * 80)
    print(f"分类信息已保存到: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
