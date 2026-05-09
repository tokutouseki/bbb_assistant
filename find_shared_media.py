#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
找出共享media文件的JSON文件
"""

import os
from pathlib import Path
from collections import defaultdict

data_dir = Path(r'd:\TokusCode\bbb_assistant\data')
achievements_dir = data_dir / '第二部探索指南' / '成就'
media_dir = achievements_dir / 'media'

# 收集所有JSON文件
json_files = list(achievements_dir.glob('*.json'))

# 收集所有media文件（排除JSON和TXT）
media_files = []
if media_dir.exists():
    media_files = [f for f in media_dir.iterdir() if f.is_file() and f.suffix.lower() not in ['.json', '.txt']]

print('='*80)
print('【共享media文件分析】')
print('='*80)
print(f'JSON文件数量: {len(json_files)}')
print(f'media文件数量: {len(media_files)}')

# 分析哪些JSON文件共享media
media_to_jsons = defaultdict(list)
for jf in json_files:
    base_name = jf.stem
    # 查找以base_name开头的media文件
    for mf in media_files:
        if mf.stem.startswith(base_name):
            media_to_jsons[mf.name].append(jf.name)

# 找出被多个JSON共享的media
shared_media = {k: v for k, v in media_to_jsons.items() if len(v) > 1}
print(f'\n共享media文件: {len(shared_media)} 个')

if shared_media:
    print('\n' + '='*80)
    print('【共享media的JSON文件】')
    print('='*80)
    for media, jsons in shared_media.items():
        print(f'\n{media} 对应 {len(jsons)} 个JSON文件:')
        for jf in jsons:
            print(f'  - {jf}')

# 验证所有JSON都有对应media
missing_media = []
for jf in json_files:
    has_media = False
    base_name = jf.stem
    for mf in media_files:
        if mf.stem.startswith(base_name):
            has_media = True
            break
    if not has_media:
        missing_media.append(jf.name)

print('\n' + '='*80)
print('【验证结果】')
print('='*80)
print(f'✅ 有对应media的JSON: {len(json_files) - len(missing_media)} 个')
print(f'❌ 缺少media的JSON: {len(missing_media)} 个')

if missing_media:
    print('\n缺少media的JSON文件:')
    for f in missing_media:
        print(f'  - {f}')
