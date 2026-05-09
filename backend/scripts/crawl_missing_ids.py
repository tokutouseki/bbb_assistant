#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缺失 content_id 爬虫脚本
用于爬取崩坏3百科中缺失的 content_id 对应的页面内容
URL规律: https://baike.mihoyo.com/bh3/wiki/content/{id}/detail?bbs_presentation_style=no_header
保存格式: JSON 和 TXT 两种
"""

import asyncio
import json
import os
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://baike.mihoyo.com/bh3/wiki/content/{id}/detail?bbs_presentation_style=no_header"
OUTPUT_DIR = Path(r"d:\TokusCode\bbb_assistant\backend\data\missing_content_ids")
MISSING_IDS_FILE = Path(r"d:\TokusCode\bbb_assistant\backend\data\missing_content_ids.txt")
SELECTOR = "#__layout > div > div.root__content > div.root__scroll-body > div > div.detail.detail--outside-app.fix-comment--out-app-all > div.detail__body.detail__body-contrib-bottom-pc"


def load_missing_ids() -> List[int]:
    with open(MISSING_IDS_FILE, 'r', encoding='utf-8-sig') as f:
        content = f.read().strip()
        ids = [int(id.strip()) for id in content.split(',') if id.strip()]
        return sorted(ids)


def sanitize_filename(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', name).strip()


def extract_media_resources(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    resources = []
    seen_urls = set()
    
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and src not in seen_urls:
            full_url = urljoin(base_url, src) if not src.startswith('http') else src
            resources.append({
                "url": full_url,
                "type": "image",
                "local_path": None,
                "download_status": "pending",
                "error_message": None,
                "alt_text": img.get('alt', ''),
                "size_bytes": None,
                "metadata": {}
            })
            seen_urls.add(full_url)
    
    for video in soup.find_all('video'):
        src = video.get('src')
        if src and src not in seen_urls:
            full_url = urljoin(base_url, src) if not src.startswith('http') else src
            resources.append({
                "url": full_url,
                "type": "video",
                "local_path": None,
                "download_status": "pending",
                "error_message": None,
                "alt_text": "",
                "size_bytes": None,
                "metadata": {}
            })
            seen_urls.add(full_url)
    
    for source in soup.find_all('source'):
        src = source.get('src')
        if src and src not in seen_urls:
            full_url = urljoin(base_url, src) if not src.startswith('http') else src
            resources.append({
                "url": full_url,
                "type": "video",
                "local_path": None,
                "download_status": "pending",
                "error_message": None,
                "alt_text": "",
                "size_bytes": None,
                "metadata": {}
            })
            seen_urls.add(full_url)
    
    return resources


def extract_category_info(soup: BeautifulSoup) -> tuple:
    category_main = ""
    category_sub = ""
    
    breadcrumb = soup.find('div', class_='breadcrumb') or soup.find('nav', class_='breadcrumb')
    if breadcrumb:
        links = breadcrumb.find_all('a')
        if len(links) >= 2:
            category_main = links[-2].get_text(strip=True) if links[-2] else ""
            category_sub = links[-1].get_text(strip=True) if links[-1] else ""
        elif len(links) == 1:
            category_main = links[0].get_text(strip=True)
    
    return category_main, category_sub


async def crawl_page(page, content_id: int) -> Optional[Dict[str, Any]]:
    url = BASE_URL.format(id=content_id)
    print(f"正在爬取: {url}")
    
    try:
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)
        
        try:
            await page.wait_for_selector(SELECTOR, timeout=30000)
        except:
            print(f"  [警告] content_id={content_id} 未找到主要内容选择器")
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        title_element = soup.find('h1', class_='detail__title')
        if title_element:
            title = title_element.get_text(strip=True)
        else:
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else f"content_{content_id}"
        
        content_element = soup.select_one(SELECTOR)
        if content_element:
            main_content = content_element.get_text(separator='\n', strip=True)
            html_content = str(content_element)
        else:
            main_content = ""
            html_content = None
        
        if not main_content or main_content == "数据加载中":
            print(f"  [跳过] content_id={content_id} 内容为空或加载失败")
            return None
        
        media_resources = extract_media_resources(soup, url)
        category_main, category_sub = extract_category_info(soup)
        
        data = {
            "url": url,
            "title": f"{title}-圣芙蕾雅档案馆-崩坏3WIKI",
            "content_id": content_id,
            "main_content": title,
            "html_content": html_content,
            "category_main": category_main,
            "category_sub": category_sub,
            "media_resources": media_resources,
            "metadata": {
                "content_length": len(main_content),
                "media_count": len(media_resources),
                "extraction_time": time.time(),
                "selector_used": SELECTOR
            },
            "extracted_at": time.time()
        }
        
        print(f"  [成功] content_id={content_id}, 标题: {title}, 媒体数: {len(media_resources)}")
        return data
        
    except Exception as e:
        print(f"  [错误] content_id={content_id} 爬取失败: {e}")
        return None


def save_result(data: Dict[str, Any], output_dir: Path):
    content_id = data["content_id"]
    title = sanitize_filename(data["main_content"]) or f"content_{content_id}"
    
    filename_base = f"{title}"
    
    json_path = output_dir / f"{filename_base}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    txt_path = output_dir / f"{filename_base}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"标题: {data['main_content']}\n")
        f.write(f"URL: {data['url']}\n")
        f.write(f"content_id: {content_id}\n")
        f.write(f"分类: {data['category_main']} / {data['category_sub']}\n")
        f.write("-" * 50 + "\n\n")
        f.write(data.get('main_content', ''))
        if data.get('html_content'):
            f.write("\n\n" + "=" * 50 + "\n")
            f.write("HTML内容:\n")
            f.write("=" * 50 + "\n")
            f.write(data['html_content'])


async def main(test_mode: bool = False, test_limit: int = 5):
    print("=" * 60)
    print("缺失 content_id 爬虫")
    if test_mode:
        print(f"[测试模式] 只爬取前 {test_limit} 个ID")
    print("=" * 60)
    
    missing_ids = load_missing_ids()
    if test_mode:
        missing_ids = missing_ids[:test_limit]
    print(f"共需爬取 {len(missing_ids)} 个缺失ID")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            for i, content_id in enumerate(missing_ids, 1):
                print(f"\n[{i}/{len(missing_ids)}] 处理 content_id={content_id}")
                
                result = await crawl_page(page, content_id)
                
                if result:
                    save_result(result, OUTPUT_DIR)
                    success_count += 1
                else:
                    skip_count += 1
                
                await asyncio.sleep(1)
                
        finally:
            await browser.close()
    
    print("\n" + "=" * 60)
    print("爬取完成!")
    print(f"成功: {success_count}")
    print(f"跳过(无内容): {skip_count}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="爬取缺失的 content_id")
    parser.add_argument("--test", action="store_true", help="测试模式，只爬取前5个ID")
    parser.add_argument("--limit", type=int, default=5, help="测试模式下爬取的ID数量")
    args = parser.parse_args()
    
    asyncio.run(main(test_mode=args.test, test_limit=args.limit))
