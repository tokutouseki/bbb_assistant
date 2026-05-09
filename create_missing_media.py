#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为缺少media的4个JSON文件创建media文件
"""

import os
from pathlib import Path
import shutil

data_dir = Path(r'd:\TokusCode\bbb_assistant\data')
achievements_dir = data_dir / '第二部探索指南' / '成就'
media_dir = achievements_dir / 'media'

# 需要创建media的JSON文件
missing_jsons = [
    '博古通今 · 二.json',
    '大忙人 · 二.json',
    '寻幽探奇 · 二.json',
    '轶闻 · 二.json'
]

print('='*80)
print('【为缺少media的JSON文件创建media】')
print('='*80)

for json_name in missing_jsons:
    json_path = achievements_dir / json_name
    base_name = json_path.stem
    
    # 查找对应的基础版本media文件
    base_name_no_suffix = base_name.replace(' · 二', '')
    base_media = list(media_dir.glob(f'{base_name_no_suffix}*'))
    base_media = [m for m in base_media if m.suffix.lower() not in ['.json', '.txt']]
    
    if base_media:
        # 复制基础版本的media文件
        base_file = base_media[0]
        new_media = media_dir / f'{base_name}{base_file.suffix}'
        shutil.copy(base_file, new_media)
        print(f'✅ 为 {json_name} 创建了media文件: {new_media.name}')
    else:
        # 尝试找其他media文件作为模板
        template_media = list(media_dir.glob('*.png'))
        if template_media:
            template = template_media[0]
            new_media = media_dir / f'{base_name}.png'
            shutil.copy(template, new_media)
            print(f'⚠️  为 {json_name} 创建了模板media文件: {new_media.name}')
        else:
            print(f'❌ 无法为 {json_name} 创建media文件')

print('\n' + '='*80)
print('【验证结果】')
print('='*80)

# 验证所有JSON都有对应media
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
