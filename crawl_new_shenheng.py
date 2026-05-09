"""
==========================================
爬取新增圣痕详细信息脚本
功能：爬取新增圣痕的详细信息并保存为JSON
使用方法：python crawl_new_shenheng.py
==========================================
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
import re

def crawl_shenheng_detail(shenheng_id, name):
    """
    爬取圣痕详细信息
    """
    url = f'https://bh3.mihoyo.com/bh3/wiki/content/{shenheng_id}/detail?bbs_presentation_style=no_header'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('title').text if soup.find('title') else f'{name}-圣芙蕾雅档案馆-崩坏3WIKI'
        
        content_selector = soup.select_one('#__layout > div > div.root__content > div.root__scroll-body > div > div.detail.detail--outside-app.fix-comment--out-app-all > div.detail__body.detail__body-contrib-bottom-pc')
        main_content = content_selector.get_text(separator='\t', strip=True) if content_selector else ''
        
        media_resources = []
        images = soup.select('img[src*="mihoyo.com"]')
        for img in images:
            img_url = img.get('src', '')
            if img_url and ('uploadstatic.mihoyo.com' in img_url or 'act-upload.mihoyo.com' in img_url):
                media_resources.append({
                    'url': img_url,
                    'type': 'image',
                    'local_path': f'd:\\TokusCode\\bbb_assistant\\data\\图鉴\\圣痕\\media\\{name}.png',
                    'download_status': 'pending',
                    'error_message': None,
                    'alt_text': img.get('alt', ''),
                    'size_bytes': None,
                    'metadata': {}
                })
        
        shenheng_data = {
            'url': url,
            'title': title,
            'content_id': int(shenheng_id),
            'main_content': main_content,
            'html_content': None,
            'category_main': '图鉴',
            'category_sub': '圣痕',
            'media_resources': media_resources,
            'metadata': {
                'content_length': len(main_content),
                'media_count': len(media_resources),
                'extraction_time': time.time(),
                'selector_used': '#__layout > div > div.root__content > div.root__scroll-body > div > div.detail.detail--outside-app.fix-comment--out-app-all > div.detail__body.detail__body-contrib-bottom-pc'
            },
            'extracted_at': time.time()
        }
        
        return shenheng_data
        
    except Exception as e:
        print(f"爬取失败: {name}, 错误: {e}")
        return None

def main():
    base_dir = r'd:\TokusCode\bbb_assistant\data\图鉴\圣痕'
    new_list_path = os.path.join(base_dir, 'new_shenheng_list.json')
    
    with open(new_list_path, 'r', encoding='utf-8') as f:
        new_shenheng_list = json.load(f)
    
    print(f"需要爬取 {len(new_shenheng_list)} 个新圣痕")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, item in enumerate(new_shenheng_list, 1):
        name = item['name']
        shenheng_id = item['id']
        
        print(f"[{i}/{len(new_shenheng_list)}] 爬取中: {name} (ID: {shenheng_id})")
        
        data = crawl_shenheng_detail(shenheng_id, name)
        
        if data:
            json_path = os.path.join(base_dir, f'{name}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 保存成功: {name}.json")
            success_count += 1
        else:
            print(f"✗ 爬取失败: {name}")
            fail_count += 1
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("爬取完成！")
    print("=" * 60)
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    print("=" * 60)

if __name__ == '__main__':
    main()
