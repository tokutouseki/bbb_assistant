"""
用途：批量更新 data 目录下 JSON 文件的 category_main 和 category_sub 字段
      根据文件所在文件夹路径自动设置分类
运行：python update_categories.py
"""
import os
import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(r"d:\TokusCode\bbb_assistant\backend\data")
STATS_FILE = DATA_DIR / "crawl_stats.json"


def get_categories_from_path(file_path: Path, data_dir: Path) -> tuple:
    """
    根据文件路径提取 category_main 和 category_sub
    
    目录结构示例：
    data/图鉴/女武神/炽翎.json -> category_main=图鉴, category_sub=女武神
    data/第二部探索指南/成就/xxx.json -> category_main=第二部探索指南, category_sub=成就
    """
    try:
        relative_path = file_path.relative_to(data_dir)
        parts = relative_path.parts
        
        if len(parts) >= 3:
            category_main = parts[0]
            category_sub = parts[1]
            return category_main, category_sub
        elif len(parts) == 2:
            return parts[0], ""
        else:
            return "", ""
    except ValueError:
        return "", ""


def update_json_categories():
    """遍历所有 JSON 文件并更新分类字段"""
    stats = {
        "total_processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "categories_distribution": defaultdict(int)
    }
    
    json_files = list(DATA_DIR.rglob("*.json"))
    
    for json_file in json_files:
        if json_file.name == "crawl_stats.json":
            continue
            
        stats["total_processed"] += 1
        
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            category_main, category_sub = get_categories_from_path(json_file, DATA_DIR)
            
            old_main = data.get("category_main", "")
            old_sub = data.get("category_sub", "")
            
            if old_main != category_main or old_sub != category_sub:
                data["category_main"] = category_main
                data["category_sub"] = category_sub
                
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                stats["updated"] += 1
                print(f"Updated: {json_file.name} | {old_main}/{old_sub} -> {category_main}/{category_sub}")
            else:
                stats["skipped"] += 1
            
            category_key = f"{category_main}/{category_sub}" if category_sub else category_main
            stats["categories_distribution"][category_key] += 1
            
        except Exception as e:
            stats["errors"] += 1
            print(f"Error processing {json_file}: {e}")
    
    return stats


def update_crawl_stats(stats: dict):
    """更新 crawl_stats.json 文件"""
    if STATS_FILE.exists():
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            crawl_stats = json.load(f)
    else:
        crawl_stats = {}
    
    crawl_stats["categories_distribution"] = dict(stats["categories_distribution"])
    crawl_stats["category_update_stats"] = {
        "total_processed": stats["total_processed"],
        "updated": stats["updated"],
        "skipped": stats["skipped"],
        "errors": stats["errors"]
    }
    
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(crawl_stats, f, ensure_ascii=False, indent=2)
    
    print(f"\nStats saved to {STATS_FILE}")


def main():
    print("=" * 60)
    print("开始更新 JSON 文件的分类字段...")
    print("=" * 60)
    
    stats = update_json_categories()
    update_crawl_stats(stats)
    
    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"  总文件数: {stats['total_processed']}")
    print(f"  已更新: {stats['updated']}")
    print(f"  无需更新: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
