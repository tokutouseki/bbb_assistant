#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色管理器 — 加载/缓存角色人格描述，供子 Agent 动态注入系统 prompt。

角色文件存储在 skills/characters/{name}/SKILL.md，切换角色无需重建 Agent。
支持通过中文名（tts_voice 字段）或英文名（name 字段）查找角色目录。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class CharacterManager:
    """角色人格管理器（单例）"""

    _instance = None

    def __init__(self, skills_dir: str = None):
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        else:
            self.skills_dir = Path(__file__).parent.parent.parent.parent.parent / "skills" / "characters"
        self._cache: Dict[str, str] = {}
        self._name_map: Optional[Dict[str, str]] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CharacterManager()
        return cls._instance

    def _build_name_map(self) -> Dict[str, str]:
        """扫描所有 SKILL.md，构建 中文名/英文名 → 目录名 的映射。"""
        if self._name_map is not None:
            return self._name_map
        self._name_map = {}
        if not self.skills_dir.exists():
            return self._name_map
        for entry in self.skills_dir.iterdir():
            if not entry.is_dir():
                continue
            skill_path = entry / "SKILL.md"
            if not skill_path.exists():
                continue
            dir_name = entry.name
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line == "---":
                            continue
                        if line.startswith("name:"):
                            name_val = line.split("name:", 1)[1].strip()
                            if name_val and name_val != dir_name:
                                self._name_map[name_val] = dir_name
                        elif line.startswith("tts_voice:"):
                            voice_val = line.split("tts_voice:", 1)[1].strip()
                            if voice_val and voice_val != dir_name:
                                self._name_map[voice_val] = dir_name
                        elif not line:
                            pass
                        elif line == "---":
                            break
            except Exception as e:
                logger.warning(f"扫描角色 '{dir_name}' 的 SKILL.md 时出错: {e}")
        return self._name_map

    def _resolve_name(self, name: str) -> str:
        """将角色名（中文或英文）解析为目录名。"""
        name_map = self._build_name_map()
        return name_map.get(name, name)

    def get_personality(self, name: str) -> str:
        """读取角色人格描述。支持中文名（如"爱莉希雅"）或目录名（如"elysia"）。"""
        dir_name = self._resolve_name(name)
        if dir_name in self._cache:
            return self._cache[dir_name]

        skill_path = self.skills_dir / dir_name / "SKILL.md"
        if not skill_path.exists():
            logger.warning(f"角色 '{name}' (目录: {dir_name}) 的 SKILL.md 不存在: {skill_path}")
            return self._fallback_personality(name)

        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()

            body = self._extract_body(content)
            self._cache[dir_name] = body
            return body
        except Exception as e:
            logger.error(f"读取角色 '{name}' 失败: {e}")
            return self._fallback_personality(name)

    def _extract_body(self, content: str) -> str:
        """提取 YAML frontmatter 之后的 Markdown body。"""
        lines = content.split("\n")
        if lines and lines[0].strip() == "---":
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_idx = i
                    break
            if end_idx is not None:
                return "\n".join(lines[end_idx + 1:]).strip()
        return content.strip()

    def list_characters(self) -> List[Dict[str, str]]:
        """列出所有可用角色，返回中文名用于前端展示。"""
        characters = []
        if not self.skills_dir.exists():
            return characters

        for entry in sorted(self.skills_dir.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                try:
                    with open(entry / "SKILL.md", "r", encoding="utf-8") as f:
                        first_lines = "".join(f.readline() for _ in range(10))
                    display_name = entry.name
                    desc = ""
                    for line in first_lines.split("\n"):
                        if line.startswith("name:"):
                            display_name = line.split("name:", 1)[1].strip()
                        elif line.startswith("description:"):
                            desc = line.split("description:", 1)[1].strip().strip('"')
                    characters.append({"name": display_name, "description": desc or display_name})
                except Exception:
                    characters.append({"name": entry.name, "description": entry.name})

        return characters

    def get_tts_voice(self, character_name: str) -> str:
        """读取角色的默认 TTS 音色。支持中文名或目录名。"""
        dir_name = self._resolve_name(character_name)
        skill_path = self.skills_dir / dir_name / "SKILL.md"
        if not skill_path.exists():
            return character_name

        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            for line in content.split("\n"):
                if line.startswith("tts_voice:"):
                    return line.split("tts_voice:", 1)[1].strip()
        except Exception:
            pass
        return character_name

    def _fallback_personality(self, name: str) -> str:
        return f"""你是{name}，来自崩坏3的角色。请以{name}的身份、语气和风格与用户对话。
保持角色的一致性，用第一人称回复。"""

    def clear_cache(self):
        """清除缓存，强制下次重新读取。"""
        self._cache.clear()
        self._name_map = None


def get_character_manager() -> CharacterManager:
    """获取 CharacterManager 单例。"""
    return CharacterManager.get_instance()
