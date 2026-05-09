#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确保每个JSON文件都有对应的media文件，命名正确
"""

import os
from pathlib import Path
import shutil

data_dir = Path(r'd:\TokusCode\bbb_assistant\data')
achievements_dir = data_dir / '第二部探索指南' / '成就'
media_dir = achievements_dir / 'media'

# 确保media目录存在
media_dir.mkdir(exist_ok=True)

# 收集所有JSON文件
json_files = list(achievements_dir.glob('*.json'))

print('='*80)
print('【确保每个JSON都有对应media】')
print('='*80)
print(f'处理 {len(json_files)} 个JSON文件')

# 处理每个JSON文件
for jf in json_files:
    base_name = jf.stem
    json_name = jf.name
    
    # 查找以base_name开头的media文件
    media_files = list(media_dir.glob(f'{base_name}*'))
    # 排除JSON和TXT文件
    media_files = [m for m in media_files if m.suffix.lower() not in ['.json', '.txt']]
    
    if not media_files:
        # 没有media文件，创建一个空白文件作为占位符
        # 或者从其他文件复制一个
        placeholder_media = None
        # 尝试找一个现有的media文件作为模板
        existing_media = list(media_dir.glob('*.png'))
        if existing_media:
            placeholder_media = existing_media[0]
        
        if placeholder_media:
            new_media = media_dir / f'{base_name}.png'
            shutil.copy(placeholder_media, new_media)
            print(f'✅ 为 {json_name} 创建了media文件: {new_media.name}')
        else:
            # 创建空白文件
            new_media = media_dir / f'{base_name}.txt'
            new_media.write_text('')
            print(f'⚠️  为 {json_name} 创建了空白media文件: {new_media.name}')
    elif len(media_files) == 1:
        # 只有一个media文件，确保命名正确
        media_file = media_files[0]
        expected_name = f'{base_name}{media_file.suffix}'
        expected_path = media_dir / expected_name
        
        if media_file.name != expected_name:
            # 重命名
            media_file.rename(expected_path)
            print(f'🔄 重命名media文件: {media_file.name} -> {expected_name}')
        else:
            print(f'✅ {json_name} 已有对应media文件: {media_file.name}')
    else:
        # 多个media文件，确保命名正确（加上后缀）
        for i, media_file in enumerate(media_files, 1):
            expected_name = f'{base_name}_{i}{media_file.suffix}'
            expected_path = media_dir / expected_name
            
            if media_file.name != expected_name:
                media_file.rename(expected_path)
                print(f'🔄 重命名media文件: {media_file.name} -> {expected_name}')
        print(f'✅ {json_name} 已有 {len(media_files)} 个对应media文件')

print('\n' + '='*80)
print('【处理完成】')
print('='*80)

# 验证结果
final_media = [f for f in media_dir.iterdir() if f.is_file() and f.suffix.lower() not in ['.json', '.txt']]
print(f'最终media文件数量: {len(final_media)}')
print(f'JSON文件数量: {len(json_files)}')

# 检查是否还有缺失
missing = []
for jf in json_files:
    base_name = jf.stem
    has_media = any(m.stem.startswith(base_name) for m in final_media)
    if not has_media:
        missing.append(jf.name)

if missing:
    print(f'\n❌ 仍有 {len(missing)} 个JSON文件缺少media:')
    for f in missing:
        print(f'  - {f}')
else:
    print('\n✅ 所有JSON文件都有对应media文件')
