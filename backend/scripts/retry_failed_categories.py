#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试失败的文件分类检查
"""

import asyncio
import json
import shutil
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")
MAX_RETRIES = 5
RETRY_DELAY = 3


async def get_breadcrumb_categories(page, url: str) -> Tuple[str, str]:
    for attempt in range(MAX_RETRIES):
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
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
            return "", ""
            
        except (PlaywrightError, Exception) as e:
            if attempt < MAX_RETRIES - 1:
                print(f"    [重试 {attempt + 2}/{MAX_RETRIES}] {e}")
                await asyncio.sleep(RETRY_DELAY)
            else:
                raise e
    
    return "", ""


def find_all_media_files(json_filename: str) -> List[Path]:
    base_name = Path(json_filename).stem
    media_files = []
    
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        for media_path in DATA_DIR.rglob(f"{base_name}{ext}"):
            if media_path.is_file():
                media_files.append(media_path)
        
        pattern = re.compile(rf"^{re.escape(base_name)}_\d+({re.escape(ext)})?$")
        for media_path in DATA_DIR.rglob(f"*{ext}"):
            if media_path.is_file() and pattern.match(media_path.name):
                media_files.append(media_path)
        
        pattern2 = re.compile(rf"^{re.escape(base_name)}_\d+_\d+{re.escape(ext)}$")
        for media_path in DATA_DIR.rglob(f"*{ext}"):
            if media_path.is_file() and pattern2.match(media_path.name):
                media_files.append(media_path)
    
    return list(set(media_files))


def transfer_file(json_path: Path, correct_main: str, correct_sub: str) -> Dict:
    result = {
        "json_transferred": False,
        "txt_transferred": False,
        "media_transferred": [],
        "error": None
    }
    
    try:
        target_dir = DATA_DIR / correct_main
        if correct_sub:
            target_dir = target_dir / correct_sub
        target_dir.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data["category_main"] = correct_main
        data["category_sub"] = correct_sub
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        txt_path = json_path.with_suffix('.txt')
        target_json = target_dir / json_path.name
        target_txt = target_dir / txt_path.name
        
        if json_path.parent != target_dir:
            shutil.move(str(json_path), str(target_json))
            result["json_transferred"] = True
            
            if txt_path.exists():
                shutil.move(str(txt_path), str(target_txt))
                result["txt_transferred"] = True
        
        media_files = find_all_media_files(json_path.name)
        target_media_dir = target_dir / "media"
        target_media_dir.mkdir(parents=True, exist_ok=True)
        
        for media_path in media_files:
            if media_path.parent != target_media_dir:
                target_media = target_media_dir / media_path.name
                if not target_media.exists():
                    shutil.move(str(media_path), str(target_media))
                    result["media_transferred"].append(media_path.name)
    
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def retry_failed():
    print("=" * 60)
    print("重试失败的文件分类检查")
    print("=" * 60)
    
    report_files = list(DATA_DIR.glob("transfer_report_*.json"))
    if not report_files:
        print("未找到报告文件")
        return
    
    all_failed = []
    for report_file in report_files:
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        for result in report.get("results", []):
            if result.get("error") and "Timeout" in str(result.get("error", "")):
                all_failed.append(result["file"])
    
    all_failed = list(set(all_failed))
    
    if not all_failed:
        print("\n没有需要重试的文件")
        return
    
    print(f"\n找到 {len(all_failed)} 个需要重试的文件\n")
    
    success_count = 0
    failed_count = 0
    transferred_count = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            for i, filename in enumerate(all_failed, 1):
                json_path = None
                for p in DATA_DIR.rglob(filename):
                    if p.is_file():
                        json_path = p
                        break
                
                if not json_path:
                    print(f"[{i}/{len(all_failed)}] {filename} - 文件未找到")
                    failed_count += 1
                    continue
                
                print(f"[{i}/{len(all_failed)}] {filename}")
                
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    url = data.get("url", "")
                    if not url:
                        print(f"  [跳过] URL为空")
                        failed_count += 1
                        continue
                    
                    correct_main, correct_sub = await get_breadcrumb_categories(page, url)
                    
                    if not correct_main:
                        print(f"  [失败] 无法获取分类")
                        failed_count += 1
                        continue
                    
                    current_main = data.get("category_main", "")
                    current_sub = data.get("category_sub", "")
                    
                    if current_main != correct_main or current_sub != correct_sub:
                        print(f"  [需转移] {current_main}/{current_sub} -> {correct_main}/{correct_sub}")
                        result = transfer_file(json_path, correct_main, correct_sub)
                        if result.get("json_transferred") or result.get("txt_transferred"):
                            transferred_count += 1
                            print(f"  [已转移] + {len(result.get('media_transferred', []))}个媒体文件")
                        success_count += 1
                    else:
                        print(f"  [正确] {correct_main}/{correct_sub}")
                        success_count += 1
                    
                except Exception as e:
                    print(f"  [错误] {e}")
                    failed_count += 1
                
                await asyncio.sleep(1)
                
        finally:
            await browser.close()
    
    print("\n" + "=" * 60)
    print("重试完成!")
    print(f"成功: {success_count}")
    print(f"已转移: {transferred_count}")
    print(f"失败: {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(retry_failed())
