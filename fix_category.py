"""
JSON文件Category修正脚本
========================
功能说明：
根据JSON文件所在的目录路径，自动修正category_main和category_sub字段

目录结构映射规则：
- data/图鉴/xxx/ -> category_main: 图鉴, category_sub: xxx
- data/往世乐土/xxx/ -> category_main: 往世乐土, category_sub: xxx
- data/档案/xxx/ -> category_main: 档案, category_sub: xxx
- data/第二部探索指南/xxx/ -> category_main: 第二部探索指南, category_sub: xxx
- 等等...

使用方法：
    python fix_category.py [--data-dir DATA_DIR] [--dry-run]

参数说明：
    --data-dir: JSON文件所在目录，默认为脚本所在目录的data文件夹
    --dry-run: 仅显示将要修改的内容，不实际修改文件

作者：AI Assistant
创建时间：2024
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class CategoryFixer:
    """Category字段修正器"""
    
    def __init__(self, data_dir: str, dry_run: bool = False):
        self.data_dir = Path(data_dir)
        self.dry_run = dry_run
        self.stats = {
            'total_files': 0,
            'modified_files': 0,
            'skipped_files': 0,
            'error_files': 0
        }
        self.changes: List[Dict] = []
    
    def _get_category_from_path(self, json_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        根据JSON文件路径获取正确的category_main和category_sub
        
        目录结构：
        data/
          - 图鉴/
            - 人偶/
            - 协同者/
            - 圣痕/
            - 女武神/
            - 敌人/
            - 材料/
            - 武器/
          - 往世乐土/
            - 物品/
          - 档案/
            - 动画短片/
            - 壁纸/
            - 角色/
            - 角色PV/
            - 美术档案/
            - 主线故事/
            - 世界观/
            - 主线章节资料/
            - 后崩坏书/
            - 后崩坏书2专章/
          - 第二部探索指南/
            - 道具/
            - 收藏品/
            - 地图/
            - 角色/
            - 敌人/
        """
        try:
            relative_path = json_path.relative_to(self.data_dir)
            parts = list(relative_path.parts[:-1])  # 排除文件名
            
            if len(parts) >= 2:
                category_main = parts[0]
                category_sub = parts[1]
                return category_main, category_sub
            elif len(parts) == 1:
                category_main = parts[0]
                return category_main, None
            else:
                return None, None
        except ValueError:
            return None, None
    
    def _fix_json_file(self, json_path: Path) -> bool:
        """
        修正单个JSON文件的category字段
        返回：是否进行了修改
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            correct_main, correct_sub = self._get_category_from_path(json_path)
            
            if correct_main is None:
                self.stats['skipped_files'] += 1
                return False
            
            current_main = data.get('category_main')
            current_sub = data.get('category_sub')
            
            needs_update = False
            changes = {
                'file': str(json_path.relative_to(self.data_dir)),
                'old_main': current_main,
                'new_main': correct_main,
                'old_sub': current_sub,
                'new_sub': correct_sub
            }
            
            if current_main != correct_main:
                needs_update = True
            
            if correct_sub is not None and current_sub != correct_sub:
                needs_update = True
            
            if correct_sub is None and current_sub is not None:
                needs_update = True
            
            if needs_update:
                if not self.dry_run:
                    data['category_main'] = correct_main
                    data['category_sub'] = correct_sub
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.changes.append(changes)
                self.stats['modified_files'] += 1
                return True
            else:
                self.stats['skipped_files'] += 1
                return False
                
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {json_path} - {e}")
            self.stats['error_files'] += 1
            return False
        except IOError as e:
            print(f"文件读写错误: {json_path} - {e}")
            self.stats['error_files'] += 1
            return False
        except Exception as e:
            print(f"处理文件时发生错误: {json_path} - {e}")
            self.stats['error_files'] += 1
            return False
    
    def fix_all(self):
        """修正所有JSON文件"""
        print("=" * 60)
        print("JSON文件Category修正任务开始")
        print(f"数据目录: {self.data_dir}")
        print(f"模式: {'预览模式（不实际修改）' if self.dry_run else '执行模式'}")
        print("=" * 60)
        
        if not self.data_dir.exists():
            print(f"错误：数据目录不存在: {self.data_dir}")
            return
        
        json_files = list(self.data_dir.rglob('*.json'))
        json_files = [f for f in json_files if 'logs' not in f.parts]
        self.stats['total_files'] = len(json_files)
        
        print(f"发现 {len(json_files)} 个JSON文件")
        print()
        
        for json_file in json_files:
            self._fix_json_file(json_file)
        
        self._print_report()
    
    def _print_report(self):
        """打印修正报告"""
        print()
        print("=" * 60)
        print("修正任务完成报告")
        print("=" * 60)
        print(f"总文件数: {self.stats['total_files']}")
        print(f"已修改文件: {self.stats['modified_files']}")
        print(f"跳过文件（无需修改）: {self.stats['skipped_files']}")
        print(f"错误文件: {self.stats['error_files']}")
        print("=" * 60)
        
        if self.changes:
            print()
            print("修改详情:")
            print("-" * 60)
            
            for change in self.changes[:50]:  # 只显示前50条
                print(f"文件: {change['file']}")
                print(f"  category_main: '{change['old_main']}' -> '{change['new_main']}'")
                print(f"  category_sub: '{change['old_sub']}' -> '{change['new_sub']}'")
                print()
            
            if len(self.changes) > 50:
                print(f"... 还有 {len(self.changes) - 50} 个文件被修改")
        
        if self.dry_run and self.changes:
            print()
            print("这是预览模式，以上文件尚未实际修改。")
            print("如需执行修改，请去掉 --dry-run 参数重新运行。")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='JSON文件Category修正脚本 - 根据目录路径修正category_main和category_sub字段',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fix_category.py
  python fix_category.py --data-dir "d:\\TokusCode\\bbb_assistant\\data"
  python fix_category.py --dry-run
        """
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='JSON文件所在目录（默认为脚本所在目录的data文件夹）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示将要修改的内容，不实际修改文件'
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = script_dir / 'data'
    
    fixer = CategoryFixer(
        data_dir=str(data_dir),
        dry_run=args.dry_run
    )
    
    fixer.fix_all()


if __name__ == '__main__':
    main()
