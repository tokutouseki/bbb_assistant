#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
圣痕媒体资源获取脚本
只获取 td.obc-tmpl-character__avatar 结构下的媒体资源
"""

import asyncio
import json
import os
import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError
import aiohttp

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\data")
STIGMATA_DIR = DATA_DIR / "图鉴" / "圣痕"
MEDIA_DIR = STIGMATA_DIR / "media"
MAX_RETRIES = 3
RETRY_DELAY = 2

AVATAR_SELECTOR = "td.obc-tmpl-character__avatar img"
AVATAR_TD_SELECTOR = "td.obc-tmpl-character__avatar"


async def download_image(session: aiohttp.ClientSession, url: str, save_path: Path) -> bool:
    """
    下载图片
    """
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.read()
                with open(save_path, 'wb') as f:
                    f.write(content)
                return True
    except Exception as e:
        print(f"    [下载失败] {url}: {e}")
    return False


async def get_avatar_media(page, url: str) -> List[Dict]:
    """
    获取页面中 td.obc-tmpl-character__avatar 结构下的媒体资源
    """
    media_list = []
    
    for attempt in range(MAX_RETRIES):
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            avatar_tds = soup.select(AVATAR_TD_SELECTOR)
            
            for td in avatar_tds:
                img = td.find('img')
                if img:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        if not src.startswith('http'):
                            src = urljoin(url, src)
                        
                        ext = '.png'
                        if '.jpg' in src or '.jpeg' in src:
                            ext = '.jpg'
                        elif '.gif' in src:
                            ext = '.gif'
                        elif '.webp' in src:
                            ext = '.webp'
                        
                        media_list.append({
                            "url": src,
                            "type": "image",
                            "ext": ext
                        })
            
            return media_list
            
        except (PlaywrightError, Exception) as e:
            if attempt < MAX_RETRIES - 1:
                print(f"    [重试 {attempt + 2}/{MAX_RETRIES}] {e}")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print(f"    [失败] {e}")
                return []
    
    return []


async def process_json_file(page, session: aiohttp.ClientSession, json_path: Path) -> Dict:
    """
    处理单个JSON文件，获取其媒体资源
    """
    result = {
        "file": json_path.name,
        "url": "",
        "media_count": 0,
        "downloaded": 0,
        "failed": 0,
        "error": None
    }
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        url = data.get("url", "")
        result["url"] = url
        
        if not url:
            result["error"] = "URL为空"
            return result
        
        media_list = await get_avatar_media(page, url)
        result["media_count"] = len(media_list)
        
        if not media_list:
            return result
        
        base_name = json_path.stem
        
        for i, media in enumerate(media_list):
            media_url = media["url"]
            ext = media["ext"]
            
            if len(media_list) == 1:
                filename = f"{base_name}{ext}"
            else:
                filename = f"{base_name}_{i+1}{ext}"
            
            save_path = MEDIA_DIR / filename
            
            if save_path.exists():
                print(f"    [跳过] {filename} 已存在")
                continue
            
            success = await download_image(session, media_url, save_path)
            if success:
                result["downloaded"] += 1
                print(f"    [下载] {filename}")
            else:
                result["failed"] += 1
        
        if data.get("media_resources"):
            new_media_resources = []
            for i, media in enumerate(media_list):
                media_url = media["url"]
                ext = media["ext"]
                
                if len(media_list) == 1:
                    filename = f"{base_name}{ext}"
                else:
                    filename = f"{base_name}_{i+1}{ext}"
                
                new_media_resources.append({
                    "url": media_url,
                    "type": "image",
                    "local_path": str(MEDIA_DIR / filename),
                    "download_status": "downloaded" if (MEDIA_DIR / filename).exists() else "failed",
                    "error_message": None,
                    "alt_text": "",
                    "size_bytes": None,
                    "metadata": {}
                })
            
            data["media_resources"] = new_media_resources
            data["metadata"]["media_count"] = len(new_media_resources)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
    except Exception as e:
        result["error"] = str(e)
        print(f"    [错误] {e}")
    
    return result


async def main():
    print("=" * 60)
    print("圣痕媒体资源获取（限定avatar结构）")
    print("=" * 60)
    
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    
    json_files = list(STIGMATA_DIR.glob("*.json"))
    print(f"\n找到 {len(json_files)} 个JSON文件\n")
    
    total_media = 0
    total_downloaded = 0
    total_failed = 0
    total_skipped = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        async with aiohttp.ClientSession() as session:
            try:
                for i, json_path in enumerate(json_files, 1):
                    print(f"[{i}/{len(json_files)}] {json_path.name}")
                    
                    result = await process_json_file(page, session, json_path)
                    
                    total_media += result["media_count"]
                    total_downloaded += result["downloaded"]
                    total_failed += result["failed"]
                    
                    await asyncio.sleep(0.5)
                    
            finally:
                await browser.close()
    
    print("\n" + "=" * 60)
    print("获取完成!")
    print(f"总媒体数: {total_media}")
    print(f"已下载: {total_downloaded}")
    print(f"下载失败: {total_failed}")
    print(f"媒体目录: {MEDIA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
