"""
声音资源管理器
统一管理角色声音参考音频、文本和元数据
支持多角色、多语音资源的管理
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class VoiceStatus(Enum):
    """语音状态枚举"""
    AVAILABLE = "available"      # 可用，有参考音频
    UNAVAILABLE = "unavailable"  # 不可用，无参考音频
    PENDING = "pending"          # 待收集音频资源


@dataclass
class VoiceResource:
    """语音资源数据类"""
    id: str                     # 语音ID（如elysia, kiana）
    name: str                   # 角色名称（中文）
    description: str            # 角色描述
    gender: str                 # 性别（female/male）
    age_group: str              # 年龄组（young/adult/elder）
    source: str                 # 来源（honkai_impact_3等）
    available: bool             # 是否可用
    reference_audio_path: Optional[str] = None    # 参考音频路径
    reference_text: Optional[str] = None          # 参考文本
    voice_characteristics: Optional[Dict[str, Any]] = None  # 声音特性
    format_info: Optional[Dict[str, Any]] = None  # 格式信息
    created_at: Optional[str] = None              # 创建时间
    updated_at: Optional[str] = None              # 更新时间
    notes: Optional[str] = None                   # 备注
    license: Optional[str] = None                 # 许可证信息
    priority: int = 0                             # 优先级（用于排序）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceResource':
        """从字典创建实例"""
        return cls(**data)


class VoiceResourceManager:
    """语音资源管理器"""
    
    def __init__(self, resources_dir: Optional[str] = None):
        """
        初始化语音资源管理器
        
        Args:
            resources_dir: 语音资源目录路径，如果为None则使用默认路径
        """
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
        
        if resources_dir is None:
            self.resources_dir = os.path.join(project_root, "voice_resources")
        else:
            self.resources_dir = resources_dir
        
        # 确保资源目录存在
        os.makedirs(self.resources_dir, exist_ok=True)
        
        # 加载语音资源
        self.voices: Dict[str, VoiceResource] = {}
        self._load_resources()
        
        logger.info(f"语音资源管理器初始化完成，目录: {self.resources_dir}")
    
    def _load_resources(self) -> None:
        """加载所有语音资源"""
        if not os.path.exists(self.resources_dir):
            logger.warning(f"语音资源目录不存在: {self.resources_dir}")
            return
        
        # 遍历每个角色目录
        for voice_id in os.listdir(self.resources_dir):
            voice_dir = os.path.join(self.resources_dir, voice_id)
            if not os.path.isdir(voice_dir):
                continue
            
            # 加载metadata.json
            metadata_path = os.path.join(voice_dir, "metadata.json")
            if not os.path.exists(metadata_path):
                logger.warning(f"角色 {voice_id} 缺少metadata.json")
                continue
            
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # 构建参考音频和文本路径
                ref_files = metadata.get("reference_files", {})
                ref_audio = ref_files.get("audio")
                ref_text = ref_files.get("text")
                
                audio_path = os.path.join(voice_dir, ref_audio) if ref_audio else None
                text_path = os.path.join(voice_dir, ref_text) if ref_text else None
                
                # 如果音频文件不存在，设为None
                if audio_path and not os.path.exists(audio_path):
                    logger.warning(f"参考音频文件不存在: {audio_path}")
                    audio_path = None
                
                # 读取参考文本
                text_content = None
                if text_path and os.path.exists(text_path):
                    try:
                        with open(text_path, 'r', encoding='utf-8') as tf:
                            text_content = tf.read().strip()
                    except Exception as e:
                        logger.error(f"读取参考文本失败 {text_path}: {e}")
                
                # 创建VoiceResource实例
                voice = VoiceResource(
                    id=voice_id,
                    name=metadata.get("name", voice_id),
                    description=metadata.get("description", ""),
                    gender=metadata.get("gender", "unknown"),
                    age_group=metadata.get("age_group", "unknown"),
                    source=metadata.get("source", "unknown"),
                    available=metadata.get("available", False),
                    reference_audio_path=audio_path,
                    reference_text=text_content,
                    voice_characteristics=metadata.get("voice_characteristics"),
                    format_info=metadata.get("format_info"),
                    created_at=metadata.get("created_at"),
                    updated_at=metadata.get("updated_at"),
                    notes=metadata.get("notes"),
                    license=metadata.get("license"),
                    priority=metadata.get("priority", 0)
                )
                
                self.voices[voice_id] = voice
                logger.debug(f"加载语音资源: {voice_id} ({voice.name})")
                
            except Exception as e:
                logger.error(f"加载语音资源 {voice_id} 失败: {e}")
    
    def get_voice(self, voice_id: str) -> Optional[VoiceResource]:
        """
        获取指定语音资源
        
        Args:
            voice_id: 语音ID
            
        Returns:
            语音资源对象，如果不存在则返回None
        """
        return self.voices.get(voice_id)
    
    def get_available_voices(self) -> List[VoiceResource]:
        """
        获取所有可用的语音资源
        
        Returns:
            可用的语音资源列表（按优先级排序）
        """
        available_voices = [v for v in self.voices.values() if v.available]
        return sorted(available_voices, key=lambda x: x.priority, reverse=True)
    
    def get_voice_ids(self) -> List[str]:
        """
        获取所有语音ID
        
        Returns:
            语音ID列表
        """
        return list(self.voices.keys())
    
    def get_voice_by_name(self, name: str) -> Optional[VoiceResource]:
        """
        根据角色名称获取语音资源
        
        Args:
            name: 角色名称
            
        Returns:
            语音资源对象，如果不存在则返回None
        """
        for voice in self.voices.values():
            if voice.name == name:
                return voice
        return None
    
    def is_voice_available(self, voice_id: str) -> bool:
        """
        检查语音是否可用（有参考音频）
        
        Args:
            voice_id: 语音ID
            
        Returns:
            是否可用
        """
        voice = self.get_voice(voice_id)
        return voice is not None and voice.available and voice.reference_audio_path is not None
    
    def get_voice_reference_audio(self, voice_id: str) -> Optional[str]:
        """
        获取语音的参考音频路径
        
        Args:
            voice_id: 语音ID
            
        Returns:
            参考音频路径，如果不存在则返回None
        """
        voice = self.get_voice(voice_id)
        if voice and voice.available:
            return voice.reference_audio_path
        return None
    
    def get_voice_reference_text(self, voice_id: str) -> Optional[str]:
        """
        获取语音的参考文本
        
        Args:
            voice_id: 语音ID
            
        Returns:
            参考文本，如果不存在则返回None
        """
        voice = self.get_voice(voice_id)
        if voice and voice.available:
            return voice.reference_text
        return None
    
    def add_voice_resource(self, voice: VoiceResource) -> bool:
        """
        添加语音资源
        
        Args:
            voice: 语音资源对象
            
        Returns:
            是否成功
        """
        try:
            # 创建角色目录
            voice_dir = os.path.join(self.resources_dir, voice.id)
            os.makedirs(voice_dir, exist_ok=True)
            
            # 保存参考音频（如果有）
            if voice.reference_audio_path:
                import shutil
                ref_audio_dest = os.path.join(voice_dir, "reference.wav")
                shutil.copy2(voice.reference_audio_path, ref_audio_dest)
                voice.reference_audio_path = ref_audio_dest
            
            # 保存参考文本（如果有）
            if voice.reference_text:
                ref_text_path = os.path.join(voice_dir, "reference.txt")
                with open(ref_text_path, 'w', encoding='utf-8') as f:
                    f.write(voice.reference_text)
            
            # 保存metadata.json
            metadata_path = os.path.join(voice_dir, "metadata.json")
            metadata = voice.to_dict()
            
            # 更新reference_files字段
            metadata["reference_files"] = {
                "audio": "reference.wav" if voice.reference_audio_path else None,
                "text": "reference.txt" if voice.reference_text else None
            }
            
            # 移除不需要保存到文件的字段
            metadata.pop("reference_audio_path", None)
            metadata.pop("reference_text", None)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 重新加载资源
            self._load_resources()
            
            logger.info(f"添加语音资源成功: {voice.id} ({voice.name})")
            return True
            
        except Exception as e:
            logger.error(f"添加语音资源失败 {voice.id}: {e}")
            return False
    
    def update_voice_resource(self, voice_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新语音资源
        
        Args:
            voice_id: 语音ID
            updates: 更新字段
            
        Returns:
            是否成功
        """
        voice = self.get_voice(voice_id)
        if not voice:
            logger.error(f"语音资源不存在: {voice_id}")
            return False
        
        try:
            # 更新字段
            for key, value in updates.items():
                if hasattr(voice, key):
                    setattr(voice, key, value)
            
            # 更新metadata.json
            voice_dir = os.path.join(self.resources_dir, voice_id)
            metadata_path = os.path.join(voice_dir, "metadata.json")
            
            metadata = voice.to_dict()
            
            # 更新reference_files字段
            metadata["reference_files"] = {
                "audio": "reference.wav" if voice.reference_audio_path else None,
                "text": "reference.txt" if voice.reference_text else None
            }
            
            # 移除不需要保存到文件的字段
            metadata.pop("reference_audio_path", None)
            metadata.pop("reference_text", None)
            
            # 更新更新时间
            from datetime import datetime
            metadata["updated_at"] = datetime.now().strftime("%Y-%m-%d")
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 重新加载资源
            self._load_resources()
            
            logger.info(f"更新语音资源成功: {voice_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新语音资源失败 {voice_id}: {e}")
            return False
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """
        列出所有语音资源
        
        Returns:
            语音资源信息列表
        """
        voices_list = []
        for voice_id, voice in self.voices.items():
            voice_info = {
                "id": voice.id,
                "name": voice.name,
                "available": voice.available,
                "gender": voice.gender,
                "age_group": voice.age_group,
                "source": voice.source,
                "priority": voice.priority,
                "has_reference_audio": voice.reference_audio_path is not None,
                "has_reference_text": voice.reference_text is not None,
                "notes": voice.notes
            }
            voices_list.append(voice_info)
        
        return sorted(voices_list, key=lambda x: x["priority"], reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取语音资源统计信息
        
        Returns:
            统计信息字典
        """
        total = len(self.voices)
        available = sum(1 for v in self.voices.values() if v.available)
        with_audio = sum(1 for v in self.voices.values() if v.reference_audio_path)
        with_text = sum(1 for v in self.voices.values() if v.reference_text)
        
        # 按性别统计
        gender_stats = {}
        for voice in self.voices.values():
            gender = voice.gender
            gender_stats[gender] = gender_stats.get(gender, 0) + 1
        
        # 按来源统计
        source_stats = {}
        for voice in self.voices.values():
            source = voice.source
            source_stats[source] = source_stats.get(source, 0) + 1
        
        return {
            "total_voices": total,
            "available_voices": available,
            "unavailable_voices": total - available,
            "voices_with_audio": with_audio,
            "voices_with_text": with_text,
            "gender_distribution": gender_stats,
            "source_distribution": source_stats,
            "resources_dir": self.resources_dir
        }
    
    def export_to_json(self, output_path: str) -> bool:
        """
        导出所有语音资源到JSON文件
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            voices_data = []
            for voice in self.voices.values():
                voice_data = voice.to_dict()
                voices_data.append(voice_data)
            
            export_data = {
                "version": "1.0.0",
                "exported_at": self._get_current_time(),
                "total_voices": len(voices_data),
                "voices": voices_data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"导出语音资源到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出语音资源失败: {e}")
            return False
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 全局语音资源管理器实例
_voice_resource_manager: Optional[VoiceResourceManager] = None


def get_voice_resource_manager(resources_dir: Optional[str] = None) -> VoiceResourceManager:
    """
    获取全局语音资源管理器实例（单例模式）
    
    Args:
        resources_dir: 语音资源目录路径
        
    Returns:
        语音资源管理器实例
    """
    global _voice_resource_manager
    if _voice_resource_manager is None:
        _voice_resource_manager = VoiceResourceManager(resources_dir)
    return _voice_resource_manager


def list_available_voices() -> List[Dict[str, Any]]:
    """
    列出所有可用的语音（便捷函数）
    
    Returns:
        可用语音信息列表
    """
    manager = get_voice_resource_manager()
    return [voice.to_dict() for voice in manager.get_available_voices()]


def get_voice_reference_info(voice_id: str) -> Optional[Tuple[str, str]]:
    """
    获取语音的参考音频路径和文本（便捷函数）
    
    Args:
        voice_id: 语音ID
        
    Returns:
        (音频路径, 文本) 元组，如果不存则返回None
    """
    manager = get_voice_resource_manager()
    voice = manager.get_voice(voice_id)
    if voice and voice.available:
        return voice.reference_audio_path, voice.reference_text
    return None


if __name__ == "__main__":
    # 测试语音资源管理器
    logging.basicConfig(level=logging.INFO)
    
    manager = get_voice_resource_manager()
    
    print("=" * 60)
    print("语音资源管理器测试")
    print("=" * 60)
    
    # 列出所有语音
    print(f"📋 总语音数量: {len(manager.voices)}")
    print("\n📁 语音列表:")
    for voice_info in manager.list_voices():
        status = "✅ 可用" if voice_info["available"] else "❌ 不可用"
        print(f"  - {voice_info['id']} ({voice_info['name']}): {status}")
    
    # 获取统计信息
    stats = manager.get_statistics()
    print(f"\n📊 统计信息:")
    print(f"  可用语音: {stats['available_voices']}/{stats['total_voices']}")
    print(f"  有参考音频: {stats['voices_with_audio']}")
    print(f"  有参考文本: {stats['voices_with_text']}")
    
    # 测试爱莉希雅语音
    print(f"\n🧪 测试爱莉希雅语音资源:")
    elysia_voice = manager.get_voice("elysia")
    if elysia_voice:
        print(f"  名称: {elysia_voice.name}")
        print(f"  描述: {elysia_voice.description}")
        print(f"  可用: {elysia_voice.available}")
        print(f"  音频路径: {elysia_voice.reference_audio_path}")
        print(f"  音频存在: {os.path.exists(elysia_voice.reference_audio_path) if elysia_voice.reference_audio_path else 'N/A'}")
        print(f"  参考文本: {elysia_voice.reference_text[:50]}...")
    else:
        print("  错误: 爱莉希雅语音资源未找到")
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)