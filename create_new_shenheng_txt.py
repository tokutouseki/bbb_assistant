"""
==========================================
为新增圣痕生成TXT文件脚本
功能：为新增的圣痕创建对应的TXT文件
使用方法：python create_new_shenheng_txt.py
==========================================
"""

import os
import json
from pathlib import Path

def create_txt_files():
    base_dir = Path(r'd:\TokusCode\bbb_assistant\data\图鉴\圣痕')
    new_list_file = base_dir / 'new_shenheng_list.json'
    
    try:
        with open(new_list_file, 'r', encoding='utf-8') as f:
            new_shenheng_list = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {new_list_file}")
        return
    
    print(f"需要创建 {len(new_shenheng_list)} 个TXT文件")
    print("=" * 60)
    
    for item in new_shenheng_list:
        name = item['name']
        json_file = base_dir / f'{name}.json'
        txt_file = base_dir / f'{name}.txt'
        
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            main_content = data.get('main_content', '')
            
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(main_content)
            
            print(f"✓ 创建成功: {name}.txt")
        else:
            print(f"✗ JSON文件不存在: {json_file}")
    
    print("\n" + "=" * 60)
    print("TXT文件创建完成！")
    print("=" * 60)

if __name__ == '__main__':
    create_txt_files()
