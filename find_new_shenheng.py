"""
==========================================
查找新增圣痕脚本
功能：对比shenheng_photo.txt和现有JSON文件，找出新增的圣痕
使用方法：python find_new_shenheng.py
==========================================
"""

import os
import re
import json
from collections import defaultdict

def find_new_shenheng():
    base_dir = r'd:\TokusCode\bbb_assistant\data\图鉴\圣痕'
    html_file = r'd:\TokusCode\bbb_assistant\shenheng_photo.txt'
    
    existing_json = set()
    for file in os.listdir(base_dir):
        if file.endswith('.json'):
            name = file[:-5]
            existing_json.add(name)
    
    print(f"现有JSON文件数量: {len(existing_json)}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'href="/bh3/wiki/content/(\d+)/detail[^"]*"[^>]*>.*?class="collection-avatar__title"[^>]*>([^<]+)</div>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    shenheng_in_html = {}
    for shenheng_id, name in matches:
        name = name.strip()
        if name:
            shenheng_in_html[name] = shenheng_id
    
    print(f"HTML中的圣痕数量: {len(shenheng_in_html)}")
    
    new_shenheng = []
    for name, shenheng_id in shenheng_in_html.items():
        if name not in existing_json:
            new_shenheng.append({
                'name': name,
                'id': shenheng_id,
                'url': f'https://bh3.mihoyo.com/bh3/wiki/content/{shenheng_id}/detail'
            })
    
    print(f"\n新增圣痕数量: {len(new_shenheng)}")
    
    if new_shenheng:
        print("\n" + "=" * 60)
        print("新增圣痕列表:")
        print("=" * 60)
        for item in new_shenheng[:20]:
            print(f"  - {item['name']} (ID: {item['id']})")
        if len(new_shenheng) > 20:
            print(f"  ... 还有 {len(new_shenheng) - 20} 个")
    
    report_path = os.path.join(base_dir, 'new_shenheng_list.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(new_shenheng, f, ensure_ascii=False, indent=2)
    
    print(f"\n新增圣痕列表已保存到: {report_path}")
    
    return new_shenheng

if __name__ == '__main__':
    find_new_shenheng()
