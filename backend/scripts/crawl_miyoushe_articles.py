#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
米游社文章爬虫脚本
用于爬取米游社崩坏3社区的文章内容
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

SELECTOR = ".mhy-article-page__main"
CONTENT_SELECTOR = ".mhy-img-text-article__content"
TITLE_SELECTOR = ".mhy-article-page__title h1"
TIME_SELECTOR = ".mhy-article-page-updatetime"
COLLECTION_SELECTOR = ".mhy-article-page-collection-info a"


def sanitize_filename(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', name).strip()


def extract_media_resources(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    resources = []
    seen_urls = set()
    
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and src not in seen_urls and not src.startswith('data:'):
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
    
    return resources


async def crawl_miyoushe_article(page, url: str) -> Optional[Dict[str, Any]]:
    print(f"正在爬取: {url}")
    
    try:
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)
        
        try:
            await page.wait_for_selector(SELECTOR, timeout=30000)
        except:
            print(f"  [警告] 未找到主要内容选择器")
            return None
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        title_element = soup.select_one(TITLE_SELECTOR)
        title = title_element.get_text(strip=True) if title_element else "未知标题"
        
        content_element = soup.select_one(CONTENT_SELECTOR)
        if content_element:
            main_content = content_element.get_text(separator='\n', strip=True)
            html_content = str(content_element)
        else:
            main_content = ""
            html_content = None
        
        if not main_content:
            print(f"  [跳过] 内容为空")
            return None
        
        time_element = soup.select_one(TIME_SELECTOR)
        publish_time = ""
        edit_time = ""
        if time_element:
            time_text = time_element.get_text(strip=True)
            time_match = re.search(r'文章发表[：:]\s*(\d{4}-\d{2}-\d{2})', time_text)
            if time_match:
                publish_time = time_match.group(1)
            edit_match = re.search(r'最后编辑[：:]\s*(\d{4}-\d{2}-\d{2})', time_text)
            if edit_match:
                edit_time = edit_match.group(1)
        
        collection_element = soup.select_one(COLLECTION_SELECTOR)
        collection_name = collection_element.get_text(strip=True) if collection_element else ""
        
        media_resources = extract_media_resources(soup, url)
        
        data = {
            "url": url,
            "title": title,
            "main_content": main_content,
            "html_content": html_content,
            "publish_time": publish_time,
            "edit_time": edit_time,
            "collection": collection_name,
            "media_resources": media_resources,
            "metadata": {
                "content_length": len(main_content),
                "media_count": len(media_resources),
                "extraction_time": time.time()
            },
            "extracted_at": time.time()
        }
        
        print(f"  [成功] 标题: {title}, 字数: {len(main_content)}, 媒体数: {len(media_resources)}")
        return data
        
    except Exception as e:
        print(f"  [错误] 爬取失败: {e}")
        return None


def save_result(data: Dict[str, Any], output_dir: Path, category_main: str = "", category_sub: str = ""):
    title = sanitize_filename(data["title"])
    filename_base = title
    
    json_data = {
        "url": data["url"],
        "title": data["title"],
        "content_id": None,
        "main_content": data["main_content"],
        "html_content": data["html_content"],
        "category_main": category_main,
        "category_sub": category_sub,
        "media_resources": data["media_resources"],
        "metadata": {
            "publish_time": data.get("publish_time", ""),
            "edit_time": data.get("edit_time", ""),
            "collection": data.get("collection", ""),
            "content_length": data["metadata"]["content_length"],
            "media_count": data["metadata"]["media_count"],
            "extraction_time": data["metadata"]["extraction_time"],
            "selector_used": SELECTOR
        },
        "extracted_at": data["extracted_at"]
    }
    
    json_path = output_dir / f"{filename_base}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    txt_path = output_dir / f"{filename_base}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"标题: {data['title']}\n")
        f.write(f"URL: {data['url']}\n")
        f.write(f"发布时间: {data.get('publish_time', '')}\n")
        f.write(f"编辑时间: {data.get('edit_time', '')}\n")
        f.write(f"合集: {data.get('collection', '')}\n")
        f.write("-" * 50 + "\n\n")
        f.write(data['main_content'])


async def main():
    print("=" * 60)
    print("米游社文章爬虫")
    print("=" * 60)
    
    data_dir = Path(r"d:\TokusCode\bbb_assistant\backend\data")
    
    story_dir = data_dir / "主线故事"
    worldview_dir = data_dir / "世界观"
    
    story_dir.mkdir(parents=True, exist_ok=True)
    worldview_dir.mkdir(parents=True, exist_ok=True)
    
    story_urls = [
        "https://www.miyoushe.com/planet/article/69404343"
    ]
    
    worldview_urls = [
        "https://www.miyoushe.com/bh3/article/69706693",
        "https://www.miyoushe.com/bh3/article/69796186"
    ]
    
    success_count = 0
    fail_count = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("\n--- 爬取主线故事 ---")
            for url in story_urls:
                result = await crawl_miyoushe_article(page, url)
                if result:
                    save_result(result, story_dir, "主线故事", "")
                    success_count += 1
                else:
                    fail_count += 1
                await asyncio.sleep(1)
            
            print("\n--- 爬取世界观 ---")
            for url in worldview_urls:
                result = await crawl_miyoushe_article(page, url)
                if result:
                    save_result(result, worldview_dir, "世界观", "")
                    success_count += 1
                else:
                    fail_count += 1
                await asyncio.sleep(1)
                
        finally:
            await browser.close()
    
    print("\n" + "=" * 60)
    print("爬取完成!")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"主线故事目录: {story_dir}")
    print(f"世界观目录: {worldview_dir}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
