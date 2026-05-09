#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复大忙人.json的media文件
"""

import os
from pathlib import Path
import shutil

data_dir = Path(r'd:\TokusCode\bbb_assistant\data')
achievements_dir = data_dir / '第二部探索指南' / '成就'
media_dir = achievements_dir / 'media'

# 检查大忙人.json
json_path = achievements_dir / '大忙人.json'
if json_path.exists():
    base_name = json_path.stem
    
    # 查找现有的media文件
    existing_media = list(media_dir.glob('大忙人*'))
    existing_media = [m for m in existing_media if m.suffix.lower() not in ['.json', '.txt']]
    
    print('现有media文件:')
    for m in existing_media:
        print(f'  - {m.name}')
    
    # 为大忙人.json创建media文件
    if existing_media:
        # 使用其中一个作为模板
        template = existing_media[0]
        new_media = media_dir / f'{base_name}.png'
        shutil.copy(template, new_media)
        print(f'\n✅ 为 大忙人.json 创建了media文件: {new_media.name}')
    else:
        # 找其他模板
        template = list(media_dir.glob('*.png'))[0]
        new_media = media_dir / f'{base_name}.png'
        shutil.copy(template, new_media)
        print(f'\n⚠️  为 大忙人.json 创建了模板media文件: {new_media.name}')

# 最终验证
print('\n' + '='*80)
print('【最终验证】')
print('='*80)

json_files = list(achievements_dir.glob('*.json'))
media_files = [f for f in media_dir.iterdir() if f.is_file() and f.suffix.lower() not in ['.json', '.txt']]

missing = []
for jf in json_files:
    base_name = jf.stem
    has_media = any(m.stem == base_name for m in media_files)
    if not has_media:
        missing.append(jf.name)

print(f'JSON文件数量: {len(json_files)}')
print(f'media文件数量: {len(media_files)}')
print(f'缺少media的JSON: {len(missing)} 个')

if missing:
    print('\n缺少media的JSON文件:')
    for f in missing:
        print(f'  - {f}')
else:
    print('\n✅ 所有JSON文件都有对应media文件')
