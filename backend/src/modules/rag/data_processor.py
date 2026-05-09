"""
数据处理器
=========
处理知识库数据：
- 加载JSON/TXT数据文件
- 解析数据结构
- 生成文档和向量
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

from .index_manager import IndexDocument
from .vector_store import VectorDocument

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDocument:
    """知识库文档"""
    id: str
    name: str
    content: str
    category: str
    subcategory: Optional[str]
    source_file: str
    metadata: Dict[str, Any]
    aliases: List[str]


class DataProcessor:
    """
    数据处理器
    
    处理知识库数据文件，生成索引文档和向量文档
    """
    
    CATEGORY_MAP = {
        "图鉴": {
            "女武神": "valkyrie",
            "圣痕": "stigmata",
            "武器": "weapon",
            "材料": "material",
            "敌人": "enemy",
            "人偶": "elf",
            "协同者": "collaborator",
            "宿舍名册": "dormitory"
        },
        "档案": {
            "故事": "story",
            "角色": "character",
            "动画短片": "animation",
            "官方漫画": "comic",
            "游戏PV": "pv",
            "壁纸": "wallpaper",
            "主题曲-音乐": "music",
            "美术档案": "art",
            "角色PV": "character_pv",
            "服装视频": "costume",
            "内容合集": "collection",
            "视频集锦": "video"
        },
        "第二部探索指南": {
            "成就": "achievement",
            "收藏品": "collectible",
            "关卡机制": "mechanism",
            "洛星博物纪": "museum",
            "地图点位": "map_point",
            "星之环": "star_ring",
            "道具": "item",
            "相册和CG": "album",
            "系统玩法": "system"
        },
        "往世乐土": {
            "乐土角色": "erosion_character",
            "物品": "item",
            "事件": "event",
            "追忆": "memory",
            "通用刻印": "signet"
        },
        "后崩坏书2专章": {
            "文件": "file",
            "怪物": "monster",
            "成就": "achievement",
            "大地图点位": "map_point",
            "角色": "character",
            "月之环系统": "moon_ring"
        },
        "主线故事": {},
        "世界观": {},
        "主线章节资料": {
            "地图点位": "map_point",
            "成就": "achievement",
            "道具": "item"
        },
        "新手入门": {
            "术语一览": "glossary"
        }
    }
    
    def __init__(
        self,
        data_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.data_path = Path(data_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self._processed_count = 0
        self._error_count = 0
    
    async def scan_data_directory(self) -> Dict[str, Any]:
        """
        扫描数据目录结构
        
        Returns:
            目录结构信息
        """
        structure = {
            "total_files": 0,
            "json_files": 0,
            "txt_files": 0,
            "categories": {}
        }
        
        if not self.data_path.exists():
            logger.warning(f"数据目录不存在: {self.data_path}")
            return structure
        
        for category_dir in self.data_path.iterdir():
            if not category_dir.is_dir():
                continue
            
            cat_name = category_dir.name
            structure["categories"][cat_name] = {
                "subcategories": {},
                "files": 0
            }
            
            for subcategory_dir in category_dir.iterdir():
                if subcategory_dir.is_dir():
                    subcat_name = subcategory_dir.name
                    json_count = len(list(subcategory_dir.glob("*.json")))
                    txt_count = len(list(subcategory_dir.glob("*.txt")))
                    
                    structure["categories"][cat_name]["subcategories"][subcat_name] = {
                        "json": json_count,
                        "txt": txt_count
                    }
                    structure["categories"][cat_name]["files"] += json_count + txt_count
                    structure["json_files"] += json_count
                    structure["txt_files"] += txt_count
                    structure["total_files"] += json_count + txt_count
        
        return structure
    
    def _generate_doc_id(self, name: str, category: str, subcategory: Optional[str] = None) -> str:
        """生成文档ID"""
        key = f"{category}/{subcategory}/{name}" if subcategory else f"{category}/{name}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载JSON文件失败 {file_path}: {e}")
            return None
    
    def _load_txt_file(self, file_path: Path) -> Optional[str]:
        """加载TXT文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载TXT文件失败 {file_path}: {e}")
            return None
    
    def _parse_json_data(
        self,
        data: Dict[str, Any],
        name: str,
        category: str,
        subcategory: Optional[str],
        source_file: str
    ) -> KnowledgeDocument:
        """解析JSON数据"""
        content_parts = []
        
        if "name" in data:
            doc_name = data["name"]
        else:
            doc_name = name
        
        for key, value in data.items():
            if key in ["name", "id"]:
                continue
            
            if isinstance(value, str):
                content_parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                if all(isinstance(v, str) for v in value):
                    content_parts.append(f"{key}: {', '.join(value)}")
                else:
                    content_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            elif isinstance(value, dict):
                content_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                content_parts.append(f"{key}: {str(value)}")
        
        content = "\n".join(content_parts)
        
        aliases = []
        if "别名" in data:
            aliases = data["别名"] if isinstance(data["别名"], list) else [data["别名"]]
        elif "alias" in data:
            aliases = data["alias"] if isinstance(data["alias"], list) else [data["alias"]]
        
        metadata = {k: v for k, v in data.items() if k not in ["name", "content", "别名", "alias"]}
        
        return KnowledgeDocument(
            id=self._generate_doc_id(doc_name, category, subcategory),
            name=doc_name,
            content=content,
            category=category,
            subcategory=subcategory,
            source_file=source_file,
            metadata=metadata,
            aliases=aliases
        )
    
    def _parse_txt_data(
        self,
        content: str,
        name: str,
        category: str,
        subcategory: Optional[str],
        source_file: str
    ) -> KnowledgeDocument:
        """解析TXT数据"""
        lines = content.strip().split("\n")
        
        doc_name = name
        aliases = []
        metadata = {}
        
        for line in lines[:10]:
            if line.startswith("名称:") or line.startswith("名字:"):
                doc_name = line.split(":", 1)[1].strip()
            elif line.startswith("别名:"):
                aliases = [a.strip() for a in line.split(":", 1)[1].split(",")]
        
        return KnowledgeDocument(
            id=self._generate_doc_id(doc_name, category, subcategory),
            name=doc_name,
            content=content,
            category=category,
            subcategory=subcategory,
            source_file=source_file,
            metadata=metadata,
            aliases=aliases
        )
    
    async def load_all_documents(self) -> AsyncIterator[KnowledgeDocument]:
        """
        加载所有文档
        
        Yields:
            知识库文档
        """
        if not self.data_path.exists():
            logger.error(f"数据目录不存在: {self.data_path}")
            return
        
        for category_dir in self.data_path.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            
            for subcategory_dir in category_dir.iterdir():
                if not subcategory_dir.is_dir():
                    continue
                
                subcategory = subcategory_dir.name
                
                json_files = list(subcategory_dir.glob("*.json"))
                for json_file in json_files:
                    data = self._load_json_file(json_file)
                    if data:
                        name = json_file.stem
                        doc = self._parse_json_data(
                            data, name, category, subcategory, str(json_file)
                        )
                        self._processed_count += 1
                        yield doc
                
                txt_files = list(subcategory_dir.glob("*.txt"))
                for txt_file in txt_files:
                    content = self._load_txt_file(txt_file)
                    if content:
                        name = txt_file.stem
                        doc = self._parse_txt_data(
                            content, name, category, subcategory, str(txt_file)
                        )
                        self._processed_count += 1
                        yield doc
        
        logger.info(f"文档加载完成，共处理 {self._processed_count} 个文件")
    
    async def load_documents_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None
    ) -> AsyncIterator[KnowledgeDocument]:
        """按分类加载文档"""
        category_dir = self.data_path / category
        if not category_dir.exists():
            logger.warning(f"分类目录不存在: {category}")
            return
        
        if subcategory:
            subcategory_dir = category_dir / subcategory
            if not subcategory_dir.exists():
                logger.warning(f"子分类目录不存在: {subcategory}")
                return
            
            async for doc in self._load_from_directory(subcategory_dir, category, subcategory):
                yield doc
        else:
            for subcat_dir in category_dir.iterdir():
                if subcat_dir.is_dir():
                    async for doc in self._load_from_directory(subcat_dir, category, subcat_dir.name):
                        yield doc
    
    async def _load_from_directory(
        self,
        directory: Path,
        category: str,
        subcategory: str
    ) -> AsyncIterator[KnowledgeDocument]:
        """从目录加载文档"""
        for json_file in directory.glob("*.json"):
            data = self._load_json_file(json_file)
            if data:
                name = json_file.stem
                doc = self._parse_json_data(
                    data, name, category, subcategory, str(json_file)
                )
                yield doc
        
        for txt_file in directory.glob("*.txt"):
            content = self._load_txt_file(txt_file)
            if content:
                name = txt_file.stem
                doc = self._parse_txt_data(
                    content, name, category, subcategory, str(txt_file)
                )
                yield doc
    
    def to_index_document(self, doc: KnowledgeDocument) -> IndexDocument:
        """转换为索引文档"""
        return IndexDocument(
            id=doc.id,
            name=doc.name,
            content=doc.content,
            category=doc.category,
            subcategory=doc.subcategory,
            keywords=[],
            metadata=doc.metadata,
            aliases=doc.aliases
        )
    
    def to_vector_document(self, doc: KnowledgeDocument, vector: List[float]) -> VectorDocument:
        """转换为向量文档"""
        return VectorDocument(
            id=doc.id,
            vector=vector,
            content=doc.content,
            metadata={
                "name": doc.name,
                "category": doc.category,
                "subcategory": doc.subcategory,
                "source_file": doc.source_file,
                **doc.metadata
            }
        )
    
    def chunk_content(self, content: str, chunk_size: Optional[int] = None) -> List[str]:
        """
        将内容分块
        
        Args:
            content: 原始内容
            chunk_size: 块大小
            
        Returns:
            内容块列表
        """
        size = chunk_size or self.chunk_size
        
        if len(content) <= size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + size
            
            if end < len(content):
                break_point = content.rfind("\n", start, end)
                if break_point > start:
                    end = break_point
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap if end < len(content) else end
        
        return chunks
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return {
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "data_path": str(self.data_path)
        }
