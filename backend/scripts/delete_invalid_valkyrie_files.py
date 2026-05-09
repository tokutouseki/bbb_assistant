#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：删除女武神目录中无效的"米哈游官方社区"文件
使用方法：直接运行此脚本
"""

import os
import json

# 女武神目录路径
VALKYRIE_DIR = r"d:\TokusCode\bbb_assistant\backend\data\图鉴\女武神"

# 主函数
def main():
    print("开始删除无效的'米哈游官方社区'文件...")
    print("=" * 80)
    
    # 统计信息
    deleted_count = 0
    kept_count = 0
    
    # 遍历女武神目录下的所有JSON文件
    for file_name in os.listdir(VALKYRIE_DIR):
        if file_name.startswith('米哈游官方社区') and file_name.endswith('.json'):
            file_path = os.path.join(VALKYRIE_DIR, file_name)
            
            try:
                # 读取json文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                title = data.get('title', '')
                main_content = data.get('main_content', '')
                
                # 检查是否是无效文件
                if '内容不存在' in main_content or title == '圣芙蕾雅档案馆-崩坏3WIKI圣芙蕾雅档案馆-崩坏3WIKI':
                    # 删除json文件
                    os.remove(file_path)
                    
                    # 删除对应的txt文件
                    txt_file_path = file_path.replace('.json', '.txt')
                    if os.path.exists(txt_file_path):
                        os.remove(txt_file_path)
                    
                    deleted_count += 1
                    print(f"删除: {file_name}")
                else:
                    kept_count += 1
                    
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print(f"删除完成！")
    print(f"删除: {deleted_count} 个文件")
    print(f"保留: {kept_count} 个文件")

if __name__ == "__main__":
    main()
