#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查特定文件的分类
"""

import asyncio
import json
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")


async def check_file_category(page, json_path: Path):
    """
    检查单个JSON文件的分类
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        url = data.get("url", "")
        current_main = data.get("category_main", "")
        current_sub = data.get("category_sub", "")
        
        if not url:
            print(f"  [跳过] {json_path.name} - URL为空")
            return None
        
        print(f"  检查: {json_path.name}")
        print(f"    当前分类: {current_main}/{current_sub}")
        print(f"    URL: {url}")
        
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        breadcrumb = None
        for ul in soup.find_all('ul'):
            lis = ul.find_all('li', recursive=False)
            has_home = False
            for li in lis:
                a = li.find('a')
                if a and '首页' in a.get_text():
                    has_home = True
                    break
            if has_home and len(lis) >= 2:
                breadcrumb = ul
                break
        
        if not breadcrumb:
            print(f"    [警告] 未找到breadcrumb导航")
            return None
        
        items = breadcrumb.select("li a")
        categories = []
        for item in items:
            text = item.get_text(strip=True)
            if text and text != "首页":
                categories.append(text)
        
        if len(categories) >= 2:
            correct_main, correct_sub = categories[0], categories[1]
        elif len(categories) == 1:
            correct_main, correct_sub = categories[0], ""
        else:
            correct_main, correct_sub = "", ""
        
        print(f"    正确分类: {correct_main}/{correct_sub}")
        
        needs_fix = (current_main != correct_main or current_sub != correct_sub)
        if needs_fix:
            print(f"    [需要修正!]")
        else:
            print(f"    [分类正确]")
        
        return {
            "file": json_path.name,
            "current_main": current_main,
            "current_sub": current_sub,
            "correct_main": correct_main,
            "correct_sub": correct_sub,
            "needs_fix": needs_fix
        }
        
    except Exception as e:
        print(f"    [错误] {e}")
        return None


async def main():
    print("=" * 60)
    print("检查「化物诸相」相关文件的分类")
    print("=" * 60)
    
    materials_dir = DATA_DIR / "图鉴" / "材料"
    
    target_files = [
        materials_dir / "「化物诸相」随机箱：结合.json",
        materials_dir / "「化物诸相」随机箱：器用.json",
        materials_dir / "「化物诸相」随机箱：殉死.json",
        materials_dir / "「化物诸相」自选箱：结合-星蚀.json",
        materials_dir / "「化物诸相」自选箱：结合-罹厄.json",
        materials_dir / "「化物诸相」自选箱：器用-罹厄.json",
        materials_dir / "「化物诸相」自选箱：器用-星蚀.json",
    ]
    
    existing_files = [f for f in target_files if f.exists()]
    print(f"\n找到 {len(existing_files)} 个文件需要检查\n")
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            for i, json_path in enumerate(existing_files, 1):
                print(f"[{i}/{len(existing_files)}]")
                result = await check_file_category(page, json_path)
                if result:
                    results.append(result)
                print()
                await asyncio.sleep(1)
                
        finally:
            await browser.close()
    
    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)
    
    need_fix = [r for r in results if r["needs_fix"]]
    correct = [r for r in results if not r["needs_fix"]]
    
    print(f"\n分类正确: {len(correct)} 个")
    print(f"需要修正: {len(need_fix)} 个")
    
    if need_fix:
        print("\n需要修正的文件:")
        for r in need_fix:
            print(f"  - {r['file']}")
            print(f"    当前: {r['current_main']}/{r['current_sub']}")
            print(f"    正确: {r['correct_main']}/{r['correct_sub']}")


if __name__ == "__main__":
    asyncio.run(main())
