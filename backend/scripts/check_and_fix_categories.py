#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类检查和修正脚本
用于检查和修正材料目录下文件的分类错误问题
通过Playwright访问URL获取正确的breadcrumb分类
"""

import asyncio
import json
import os
import re
import time
import shutil
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

MATERIALS_DIR = Path(r"d:\TokusCode\bbb_assistant\data\图鉴\材料")
DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")
BREADCRUMB_SELECTOR = "ul.detail__breadcrumb, .breadcrumb, nav.breadcrumb"
BREADCRUMB_ITEM_SELECTOR = "li a, .breadcrumb-item a"


def sanitize_filename(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', name).strip()


async def get_breadcrumb_categories(page, url: str) -> Tuple[str, str]:
    """
    访问URL并获取breadcrumb导航中的分类信息
    返回 (category_main, category_sub)
    """
    try:
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
            return "", ""
        
        items = breadcrumb.select("li a")
        categories = []
        for item in items:
            text = item.get_text(strip=True)
            if text and text != "首页":
                categories.append(text)
        
        if len(categories) >= 2:
            return categories[0], categories[1]
        elif len(categories) == 1:
            return categories[0], ""
        else:
            return "", ""
            
    except Exception as e:
        print(f"    [错误] 获取分类失败: {e}")
        return "", ""


def get_target_directory(category_main: str, category_sub: str) -> Path:
    """
    根据分类获取目标目录路径
    """
    if not category_main:
        return DATA_DIR / "未知分类"
    
    target_dir = DATA_DIR / category_main
    if category_sub:
        target_dir = target_dir / category_sub
    
    return target_dir


async def check_and_fix_file(page, json_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """
    检查并修正单个JSON文件的分类
    """
    result = {
        "file": json_path.name,
        "original_category_main": "",
        "original_category_sub": "",
        "correct_category_main": "",
        "correct_category_sub": "",
        "needs_fix": False,
        "fixed": False,
        "moved": False,
        "error": None
    }
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result["original_category_main"] = data.get("category_main", "")
        result["original_category_sub"] = data.get("category_sub", "")
        
        url = data.get("url", "")
        if not url:
            result["error"] = "URL为空"
            return result
        
        print(f"  检查: {json_path.name}")
        correct_main, correct_sub = await get_breadcrumb_categories(page, url)
        result["correct_category_main"] = correct_main
        result["correct_category_sub"] = correct_sub
        
        if not correct_main:
            result["error"] = "无法获取正确分类"
            return result
        
        if data.get("category_main") != correct_main or data.get("category_sub") != correct_sub:
            result["needs_fix"] = True
            
            if not dry_run:
                data["category_main"] = correct_main
                data["category_sub"] = correct_sub
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                result["fixed"] = True
                
                target_dir = get_target_directory(correct_main, correct_sub)
                target_dir.mkdir(parents=True, exist_ok=True)
                
                txt_path = json_path.with_suffix('.txt')
                
                target_json = target_dir / json_path.name
                target_txt = target_dir / txt_path.name
                
                if json_path.parent != target_dir:
                    shutil.move(str(json_path), str(target_json))
                    if txt_path.exists():
                        shutil.move(str(txt_path), str(target_txt))
                    result["moved"] = True
                    print(f"    [修正] 分类: {correct_main}/{correct_sub}, 已移动到: {target_dir}")
                else:
                    print(f"    [修正] 分类: {correct_main}/{correct_sub}")
            else:
                print(f"    [需修正] 当前: {result['original_category_main']}/{result['original_category_sub']}, 正确: {correct_main}/{correct_sub}")
        else:
            print(f"    [正确] 分类: {correct_main}/{correct_sub}")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"    [错误] {e}")
    
    return result


async def main(dry_run: bool = False, limit: int = 0):
    """
    主函数
    dry_run: True时只检查不修正
    limit: 限制处理的文件数量，0表示不限制
    """
    print("=" * 60)
    print("分类检查和修正脚本")
    if dry_run:
        print("[预览模式] 只检查不修正")
    print("=" * 60)
    
    json_files = list(MATERIALS_DIR.glob("*.json"))
    print(f"\n材料目录下共有 {len(json_files)} 个JSON文件")
    
    if limit > 0:
        json_files = json_files[:limit]
        print(f"限制处理前 {limit} 个文件")
    
    results = []
    need_fix_count = 0
    fixed_count = 0
    moved_count = 0
    error_count = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            for i, json_path in enumerate(json_files, 1):
                print(f"\n[{i}/{len(json_files)}]")
                result = await check_and_fix_file(page, json_path, dry_run)
                results.append(result)
                
                if result["needs_fix"]:
                    need_fix_count += 1
                    if result["fixed"]:
                        fixed_count += 1
                    if result["moved"]:
                        moved_count += 1
                if result["error"]:
                    error_count += 1
                
                await asyncio.sleep(0.5)
                
        finally:
            await browser.close()
    
    print("\n" + "=" * 60)
    print("检查完成!")
    print(f"总文件数: {len(json_files)}")
    print(f"需要修正: {need_fix_count}")
    if not dry_run:
        print(f"已修正: {fixed_count}")
        print(f"已移动: {moved_count}")
    print(f"错误: {error_count}")
    print("=" * 60)
    
    report_path = DATA_DIR / "category_fix_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.time(),
            "dry_run": dry_run,
            "total_files": len(json_files),
            "need_fix_count": need_fix_count,
            "fixed_count": fixed_count,
            "moved_count": moved_count,
            "error_count": error_count,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="检查和修正材料目录下文件的分类")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，只检查不修正")
    parser.add_argument("--limit", type=int, default=0, help="限制处理的文件数量，0表示不限制")
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, limit=args.limit))
