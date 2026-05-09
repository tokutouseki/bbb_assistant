#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件分类检查和转移固化脚本
通过JSON文件的URL获取正确的分类信息，转移分类错误的文件
确保JSON、TXT和媒体资源文件都正确转移
"""

import asyncio
import json
import shutil
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")
MAX_RETRIES = 3
RETRY_DELAY = 2


class CategoryTransfer:
    def __init__(self, target_dir: Path):
        self.target_dir = target_dir
        self.results = []
        self.failed_urls = []
        self.stats = {
            "total": 0,
            "correct": 0,
            "transferred": 0,
            "failed": 0,
            "media_transferred": 0
        }
    
    async def get_breadcrumb_categories(self, page, url: str) -> Tuple[str, str]:
        """
        访问URL并获取breadcrumb导航中的分类信息
        支持3次重试
        """
        for attempt in range(MAX_RETRIES):
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)
                
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
                else:
                    return "", ""
                    
            except (PlaywrightError, Exception) as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"    [重试 {attempt + 2}/{MAX_RETRIES}] 网络错误: {e}")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    raise e
        
        return "", ""
    
    def find_all_media_files(self, json_filename: str) -> List[Path]:
        """
        查找JSON文件对应的所有媒体文件
        """
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
    
    def transfer_file(self, json_path: Path, correct_main: str, correct_sub: str) -> Dict:
        """
        转移单个JSON文件及其相关文件
        """
        result = {
            "file": json_path.name,
            "original_path": str(json_path.parent),
            "correct_main": correct_main,
            "correct_sub": correct_sub,
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
            
            media_files = self.find_all_media_files(json_path.name)
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
    
    async def check_and_transfer_file(self, page, json_path: Path) -> Dict:
        """
        检查并转移单个文件
        """
        self.stats["total"] += 1
        
        result = {
            "file": json_path.name,
            "original_main": "",
            "original_sub": "",
            "correct_main": "",
            "correct_sub": "",
            "needs_transfer": False,
            "transferred": False,
            "error": None
        }
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result["original_main"] = data.get("category_main", "")
            result["original_sub"] = data.get("category_sub", "")
            
            url = data.get("url", "")
            if not url:
                result["error"] = "URL为空"
                self.stats["failed"] += 1
                return result
            
            print(f"  [{self.stats['total']}] 检查: {json_path.name}")
            
            correct_main, correct_sub = await self.get_breadcrumb_categories(page, url)
            result["correct_main"] = correct_main
            result["correct_sub"] = correct_sub
            
            if not correct_main:
                result["error"] = "无法获取分类"
                self.stats["failed"] += 1
                self.failed_urls.append({"file": json_path.name, "url": url})
                return result
            
            if result["original_main"] != correct_main or result["original_sub"] != correct_sub:
                result["needs_transfer"] = True
                print(f"    [需转移] {result['original_main']}/{result['original_sub']} -> {correct_main}/{correct_sub}")
                
                transfer_result = self.transfer_file(json_path, correct_main, correct_sub)
                result["transferred"] = transfer_result.get("json_transferred", False) or transfer_result.get("txt_transferred", False)
                result["media_transferred"] = transfer_result.get("media_transferred", [])
                result["error"] = transfer_result.get("error")
                
                if result["transferred"]:
                    self.stats["transferred"] += 1
                    self.stats["media_transferred"] += len(result.get("media_transferred", []))
                    print(f"    [已转移] JSON+TXT + {len(result.get('media_transferred', []))}个媒体文件")
            else:
                self.stats["correct"] += 1
                print(f"    [正确] 分类: {correct_main}/{correct_sub}")
            
        except Exception as e:
            result["error"] = str(e)
            self.stats["failed"] += 1
            print(f"    [错误] {e}")
        
        self.results.append(result)
        return result
    
    async def retry_failed(self, page):
        """
        重试失败的URL
        """
        if not self.failed_urls:
            return
        
        print(f"\n重试 {len(self.failed_urls)} 个失败的URL...")
        retry_list = self.failed_urls.copy()
        self.failed_urls.clear()
        
        for item in retry_list:
            json_path = None
            for p in DATA_DIR.rglob(item["file"]):
                if p.is_file():
                    json_path = p
                    break
            
            if json_path:
                await self.check_and_transfer_file(page, json_path)
                await asyncio.sleep(1)
    
    async def run(self, dry_run: bool = False):
        """
        运行检查和转移
        """
        print("=" * 60)
        print(f"检查目录: {self.target_dir}")
        if dry_run:
            print("[预览模式] 只检查不转移")
        print("=" * 60)
        
        json_files = list(self.target_dir.glob("*.json"))
        print(f"\n找到 {len(json_files)} 个JSON文件\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                for json_path in json_files:
                    if dry_run:
                        result = await self.check_and_transfer_file(page, json_path)
                        if result.get("needs_transfer"):
                            print(f"    [预览] 需要转移")
                    else:
                        await self.check_and_transfer_file(page, json_path)
                    
                    await asyncio.sleep(0.5)
                
                if self.failed_urls and not dry_run:
                    await self.retry_failed(page)
                    
            finally:
                await browser.close()
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print(f"总文件数: {self.stats['total']}")
        print(f"分类正确: {self.stats['correct']}")
        print(f"已转移: {self.stats['transferred']}")
        print(f"媒体文件转移: {self.stats['media_transferred']}")
        print(f"失败: {self.stats['failed']}")
        print("=" * 60)
        
        report_path = DATA_DIR / f"transfer_report_{self.target_dir.name}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "target_dir": str(self.target_dir),
                "timestamp": time.time(),
                "dry_run": dry_run,
                "stats": self.stats,
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {report_path}")


async def main(target_dir: str, dry_run: bool = False):
    target_path = Path(target_dir)
    if not target_path.exists():
        print(f"错误: 目录不存在 - {target_path}")
        return
    
    transfer = CategoryTransfer(target_path)
    await transfer.run(dry_run=dry_run)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="检查和转移文件分类")
    parser.add_argument("target_dir", help="目标目录路径")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，只检查不转移")
    args = parser.parse_args()
    
    asyncio.run(main(args.target_dir, args.dry_run))
