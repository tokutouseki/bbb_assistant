"""
技能管理器模块 - 用于加载和管理技能
支持从skills目录加载SKILL.md文件
"""

import os
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SkillManager:
    """技能管理器类"""
    
    def __init__(self):
        self.skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "skills"
        )
        self.skills: Dict[str, dict] = {}
        self.load_all_skills()
    
    def load_all_skills(self):
        """加载所有技能"""
        if not os.path.exists(self.skills_dir):
            logger.warning(f"技能目录不存在: {self.skills_dir}")
            return
        
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                self.load_skill(skill_name)
    
    def load_skill(self, skill_name: str) -> Optional[dict]:
        """加载单个技能"""
        skill_file = os.path.join(self.skills_dir, skill_name, "SKILL.md")
        
        if not os.path.exists(skill_file):
            logger.debug(f"跳过非技能目录: {skill_name}")
            return None
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析YAML frontmatter
            frontmatter, body = self._parse_frontmatter(content)
            
            # 解析 phases（逗号分隔的阶段名称列表）
            phases_raw = frontmatter.get("phases", "")
            phases = [p.strip() for p in phases_raw.split(",") if p.strip()] if phases_raw else []

            skill = {
                "name": frontmatter.get("name", skill_name),
                "description": frontmatter.get("description", ""),
                "content": body,
                "phases": phases,
                "trigger_words": self._extract_trigger_words(frontmatter.get("description", ""), body)
            }
            
            self.skills[skill_name] = skill
            logger.info(f"已加载技能: {skill_name}")
            return skill
            
        except Exception as e:
            logger.error(f"加载技能失败 {skill_name}: {str(e)}")
            return None
    
    def _parse_frontmatter(self, content: str) -> tuple:
        """解析YAML frontmatter"""
        frontmatter_pattern = r'^---\n(.*?)\n---\n'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_str = match.group(1)
            body = content[match.end():]

            # 简单解析YAML
            frontmatter = {}
            for line in frontmatter_str.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"').strip("'")

            return frontmatter, body

        return {}, content

    def get_skill_phases(self, skill_name: str) -> list:
        """获取技能的阶段列表。
        从已解析的 skill 的 phases 字段获取，如果没有 phases 定义则返回空列表。
        """
        skill = self.skills.get(skill_name, {})
        phases_raw = skill.get("phases", "")
        if not phases_raw:
            # 也尝试从原始 frontmatter 重新读取
            skill_file = os.path.join(self.skills_dir, skill_name, "SKILL.md")
            if os.path.exists(skill_file):
                with open(skill_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                frontmatter, _ = self._parse_frontmatter(content)
                phases_raw = frontmatter.get("phases", "")

        if not phases_raw:
            return []

        # phases 是逗号分隔的阶段名称列表
        return [p.strip() for p in phases_raw.split(",") if p.strip()]

    def extract_phase_content(self, skill_name: str, phase_name: str) -> Optional[str]:
        """从技能 markdown 中提取指定阶段的文本内容。
        查找 ### {phase_name} 标题，提取到下一个同级标题之间的所有内容。
        """
        skill = self.skills.get(skill_name, {})
        body = skill.get("content", "")
        if not body:
            skill_file = os.path.join(self.skills_dir, skill_name, "SKILL.md")
            if os.path.exists(skill_file):
                with open(skill_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                _, body = self._parse_frontmatter(content)

        if not body:
            return None

        # 查找 ### {phase_name} 标题
        escaped = re.escape(phase_name)
        phase_pattern = rf'###\s+{escaped}\s*\n(.*?)(?=\n###\s|\Z)'
        match = re.search(phase_pattern, body, re.DOTALL)

        if match:
            return match.group(1).strip()
        return None
    
    def _extract_trigger_words(self, description: str, body: str = "") -> List[str]:
        """从描述和正文中提取触发词，兼容多种引号类型"""
        # 支持: “...” "..."
        pattern = r'[“”"]([^“”"]+)[“”"]'
        words = []
        for text in (description, body):
            matches = re.findall(pattern, text)
            words.extend(m.strip() for m in matches if m.strip())
        return words
    def get_skill(self, skill_name: str) -> Optional[dict]:
        """获取指定技能"""
        return self.skills.get(skill_name)
    
    def list_skills(self) -> List[str]:
        """列出所有可用技能"""
        return list(self.skills.keys())
    
    def find_matching_skill(self, query: str) -> Optional[dict]:
        """根据查询找到匹配的技能"""
        query_lower = query.lower()
        
        for skill_name, skill in self.skills.items():
            # 检查触发词
            for trigger in skill.get("trigger_words", []):
                if trigger.lower() in query_lower:
                    return skill
            
            # 检查技能名称
            if skill_name.lower() in query_lower:
                return skill
        
        return None
    
    def get_skill_summary(self) -> str:
        """获取所有技能的摘要"""
        if not self.skills:
            return "没有可用的技能"
        
        lines = ["可用技能列表:"]
        for skill_name, skill in self.skills.items():
            lines.append(f"- {skill_name}: {skill.get('description', '')[:50]}...")
        
        return "\n".join(lines)
    
    def suggest_skill(self, query: str) -> Optional[str]:
        """根据用户查询建议合适的技能"""
        skill = self.find_matching_skill(query)
        if skill:
            return f"检测到您可能需要使用「{skill['name']}」技能。\n\n描述: {skill['description']}\n\n是否需要查看详细使用说明？"
        return None

# 创建单例
_skill_manager_instance = None

def get_skill_manager() -> SkillManager:
    """获取技能管理器单例"""
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager()
    return _skill_manager_instance