#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：处理追忆目录中的重复文件，比对txt内容决定保留哪个
使用方法：直接运行此脚本
"""

import os
import json
import re

TARGET_DIR = r"d:\TokusCode\bbb_assistant\backend\data\往世乐土\追忆"

DUPLICATE_GROUPS = [
    {
        "title": "蛇主的追忆",
        "files": ["以我之手.json", "蛇主的追忆.json"]
    },
    {
        "title": "觉者的追忆",
        "files": ["崩坏病.json", "觉者的追忆.json"]
    },
    {
        "title": "落樱的追忆",
        "files": ["夜叉.json", "落樱的追忆.json"]
    },
    {
        "title": "歌者的追忆",
        "files": ["《穆娱乐周刊》节选.json", "歌者的追忆.json"]
    },
    {
        "title": "英雄的追忆",
        "files": ["流言：深寒.json", "英雄的追忆.json"]
    }
]

def get_txt_content(json_path):
    txt_path = json_path.replace('.json', '.txt')
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def get_json_content_length(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return len(data.get('main_content', ''))
    except:
        return 0

def main():
    print("开始处理追忆目录中的重复文件...")
    print("=" * 80)
    
    deleted_count = 0
    kept_count = 0
    
    for group in DUPLICATE_GROUPS:
        print(f"\n处理重复组: {group['title']}")
        print("-" * 40)
        
        files_info = []
        for file_name in group['files']:
            file_path = os.path.join(TARGET_DIR, file_name)
            if os.path.exists(file_path):
                txt_content = get_txt_content(file_path)
                json_length = get_json_content_length(file_path)
                files_info.append({
                    'name': file_name,
                    'path': file_path,
                    'txt_length': len(txt_content),
                    'json_length': json_length
                })
                print(f"  文件: {file_name}")
                print(f"    txt长度: {len(txt_content)}")
                print(f"    json内容长度: {json_length}")
        
        if len(files_info) < 2:
            print(f"  只有一个文件存在，跳过")
            continue
        
        files_info.sort(key=lambda x: (x['txt_length'], x['json_length']), reverse=True)
        
        keep_file = files_info[0]
        delete_files = files_info[1:]
        
        print(f"\n  保留: {keep_file['name']} (内容最长)")
        
        for del_file in delete_files:
            json_path = del_file['path']
            txt_path = json_path.replace('.json', '.txt')
            
            try:
                if os.path.exists(json_path):
                    os.remove(json_path)
                    print(f"  删除: {del_file['name']}")
                if os.path.exists(txt_path):
                    os.remove(txt_path)
                    print(f"  删除: {del_file['name'].replace('.json', '.txt')}")
                deleted_count += 1
            except Exception as e:
                print(f"  删除失败: {del_file['name']} - {e}")
        
        kept_count += 1
    
    print("\n" + "=" * 80)
    print(f"处理完成！")
    print(f"保留文件组: {kept_count} 组")
    print(f"删除重复文件: {deleted_count} 个")

if __name__ == "__main__":
    main()
