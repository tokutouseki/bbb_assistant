#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型单例管理器

功能：
1. 全局单例管理TTS和ASR模型实例
2. 避免重复加载模型，减少初始化时间
3. 线程安全的模型访问
4. LRU缓存支持多个设备配置

使用方法：
  from src.utils.model_manager import ModelManager
  
  # 获取单例实例
  manager = ModelManager.get_instance()
  
  # 获取TTS模型（首次调用会加载模型）
  tts_model = manager.get_tts_model(device="cuda:0")
  
  # 获取Qwen3-TTS模型
  qwen3_tts_model = manager.get_qwen3_tts_model(device="cuda:0")
  
  # 获取ASR模型
  asr_model = manager.get_asr_model(device="cuda:0")
"""

import threading
import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ModelManager:
    """
    模型单例管理器，全局管理TTS和ASR模型实例
    """
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        """私有构造函数，通过get_instance()获取实例"""
        self._initialized = False
        self._init_lock = threading.Lock()
        
        self.stats = {
            "tts_load_count": 0,
            "qwen3_tts_load_count": 0,
            "asr_load_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        self._setup_modelscope_cache()
        self._pre_import_modules()
        
        logger.info("模型管理器初始化完成")
    
    def _setup_modelscope_cache(self):
        """设置ModelScope缓存路径"""
        import os
        from pathlib import Path
        
        config_path = Path(__file__).parent.parent.parent / "config" / "model_cache.yaml"
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                zipenhancer_path = config.get("model_cache", {}).get("zipenhancer_path")
                if zipenhancer_path:
                    cache_dir = Path(zipenhancer_path).parent.parent.parent
                    os.environ["MODELSCOPE_CACHE"] = str(cache_dir)
                    logger.info(f"设置MODELSCOPE_CACHE: {cache_dir}")
                    os.environ["MODELSCOPE_HOME"] = str(cache_dir)
            except Exception as e:
                logger.warning(f"读取缓存配置失败: {e}")
        else:
            default_cache = Path(__file__).parent.parent.parent.parent / "models"
            os.environ["MODELSCOPE_CACHE"] = str(default_cache)
            logger.info(f"使用默认MODELSCOPE_CACHE: {default_cache}")
    
    def _pre_import_modules(self):
        """预先导入所有需要的模块"""
        try:
            logger.info("预先导入TTS和ASR模块...")
            import src.modules.audio.tts_generator
            logger.info("TTS模块导入完成")
        except ImportError as e:
            logger.warning(f"无法导入TTS模块: {e}")
        
        try:
            import src.modules.audio.qwen3_tts_generator
            logger.info("Qwen3-TTS模块导入完成")
        except ImportError as e:
            logger.warning(f"无法导入Qwen3-TTS模块: {e}")
        
        try:
            import src.modules.audio.asr_processor
            logger.info("ASR模块导入完成")
        except ImportError as e:
            logger.warning(f"无法导入ASR模块: {e}")
    
    @classmethod
    def get_instance(cls):
        """获取模型管理器单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ModelManager()
        return cls._instance
    
    @lru_cache(maxsize=2)
    def get_tts_model(self, device: str = "cuda:0"):
        """获取TTS模型实例 (VoxCPM-0.5B)"""
        logger.info(f"获取TTS模型 (设备: {device})")
        
        try:
            from src.modules.audio.tts_generator import TTSGenerator
            settings = get_settings()
            
            model = TTSGenerator(model_path=settings.voxcpm_model_path, device=device)
            self.stats["tts_load_count"] += 1
            self._warmup_tts_model(model, device)
            
            logger.info(f"TTS模型加载完成 (设备: {device})")
            return model
            
        except ImportError as e:
            logger.error(f"无法导入TTSGenerator: {e}")
            raise
        except Exception as e:
            logger.error(f"加载TTS模型失败: {e}")
            raise
    
    @lru_cache(maxsize=2)
    def get_qwen3_tts_model(self, device: str = "cuda:0"):
        """获取Qwen3-TTS模型实例"""
        logger.info(f"获取Qwen3-TTS模型 (设备: {device})")
        
        try:
            from src.modules.audio.qwen3_tts_generator import Qwen3TTSGenerator
            settings = get_settings()
            
            model = Qwen3TTSGenerator(model_path=settings.qwen3_tts_model_path, device=device)
            self.stats["qwen3_tts_load_count"] += 1
            self._warmup_qwen3_tts_model(model, device)
            
            logger.info(f"Qwen3-TTS模型加载完成 (设备: {device})")
            return model
            
        except ImportError as e:
            logger.error(f"无法导入Qwen3TTSGenerator: {e}")
            raise
        except Exception as e:
            logger.error(f"加载Qwen3-TTS模型失败: {e}")
            raise
    
    @lru_cache(maxsize=2)
    def get_asr_model(self, device: str = "cuda:0"):
        """获取ASR模型实例"""
        logger.info(f"获取ASR模型 (设备: {device})")
        
        try:
            from src.modules.audio.asr_processor import ASRProcessor
            settings = get_settings()
            
            model = ASRProcessor(model_path=settings.asr_model_path, device=device)
            self.stats["asr_load_count"] += 1
            self._warmup_asr_model(model, device)
            
            logger.info(f"ASR模型加载完成 (设备: {device})")
            return model
            
        except ImportError as e:
            logger.error(f"无法导入ASRProcessor: {e}")
            raise
        except Exception as e:
            logger.error(f"加载ASR模型失败: {e}")
            raise
    
    def _warmup_tts_model(self, model, device: str):
        """TTS模型预热"""
        try:
            logger.info("开始TTS模型预热...")
            warmup_text = "模型预热测试"
            warmup_result = model.generate(
                text=warmup_text,
                voice_id="elysia",
                speed=1.0,
                pitch=1.0
            )
            audio_length = len(warmup_result.audio_data) if hasattr(warmup_result, 'audio_data') else 0
            logger.info(f"TTS模型预热完成，生成音频长度: {audio_length}")
        except Exception as e:
            logger.warning(f"TTS模型预热失败: {e}")
    
    def _warmup_qwen3_tts_model(self, model, device: str):
        """Qwen3-TTS模型预热 (使用语音克隆)"""
        try:
            logger.info("开始Qwen3-TTS模型预热...")
            import os as _os
            import json as _json
            index_path = _os.path.join(
                _os.path.dirname(__file__), "..", "modules", "audio", "reference_audio", "index.json"
            )
            with open(index_path, "r", encoding="utf-8") as _f:
                index = _json.load(_f)
            first_entry = next(iter(index.values()))
            ref_audio = first_entry["audio_path"]
            ref_text = first_entry.get("ref_text", "")

            warmup_result = model.generate_with_reference(
                text="模型预热测试",
                reference_audio=ref_audio,
                language="Chinese",
                ref_text=ref_text,
            )
            audio_length = len(warmup_result.audio_data) if hasattr(warmup_result, 'audio_data') else 0
            logger.info(f"Qwen3-TTS模型预热完成，生成音频长度: {audio_length}")
        except Exception as e:
            logger.warning(f"Qwen3-TTS模型预热失败: {e}")
    
    def _warmup_asr_model(self, model, device: str):
        """ASR模型预热"""
        try:
            logger.info("开始ASR模型预热...")
            import numpy as np
            warmup_audio = np.zeros(8000, dtype=np.float32)
            warmup_result = model.transcribe(
                audio_data=warmup_audio,
                sample_rate=16000,
                language="zh"
            )
            logger.info("ASR模型预热完成")
        except Exception as e:
            logger.warning(f"ASR模型预热失败: {e}")
    
    def clear_cache(self):
        """清除所有模型缓存"""
        self.get_tts_model.cache_clear()
        self.get_qwen3_tts_model.cache_clear()
        self.get_asr_model.cache_clear()
        logger.info("模型缓存已清除")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        tts_cache_info = self.get_tts_model.cache_info()
        qwen3_tts_cache_info = self.get_qwen3_tts_model.cache_info()
        asr_cache_info = self.get_asr_model.cache_info()
        
        stats = {
            "tts_load_count": self.stats["tts_load_count"],
            "qwen3_tts_load_count": self.stats["qwen3_tts_load_count"],
            "asr_load_count": self.stats["asr_load_count"],
            "tts_cache_hits": tts_cache_info.hits,
            "tts_cache_misses": tts_cache_info.misses,
            "tts_cache_size": tts_cache_info.currsize,
            "qwen3_tts_cache_hits": qwen3_tts_cache_info.hits,
            "qwen3_tts_cache_misses": qwen3_tts_cache_info.misses,
            "qwen3_tts_cache_size": qwen3_tts_cache_info.currsize,
            "asr_cache_hits": asr_cache_info.hits,
            "asr_cache_misses": asr_cache_info.misses,
            "asr_cache_size": asr_cache_info.currsize,
            "total_cache_hits": tts_cache_info.hits + qwen3_tts_cache_info.hits + asr_cache_info.hits,
            "total_cache_misses": tts_cache_info.misses + qwen3_tts_cache_info.misses + asr_cache_info.misses,
        }
        
        return stats
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        
        logger.info("=" * 60)
        logger.info("模型管理器统计信息")
        logger.info("=" * 60)
        logger.info(f"TTS加载次数: {stats['tts_load_count']}")
        logger.info(f"Qwen3-TTS加载次数: {stats['qwen3_tts_load_count']}")
        logger.info(f"ASR加载次数: {stats['asr_load_count']}")
        logger.info(f"TTS缓存命中: {stats['tts_cache_hits']}, 未命中: {stats['tts_cache_misses']}")
        logger.info(f"Qwen3-TTS缓存命中: {stats['qwen3_tts_cache_hits']}, 未命中: {stats['qwen3_tts_cache_misses']}")
        logger.info(f"ASR缓存命中: {stats['asr_cache_hits']}, 未命中: {stats['asr_cache_misses']}")
        total = stats['total_cache_hits'] + stats['total_cache_misses']
        if total > 0:
            logger.info(f"总缓存命中率: {stats['total_cache_hits']/total*100:.1f}%")
        logger.info("=" * 60)


def get_tts_model(device: str = "cuda:0"):
    """便捷函数：获取TTS模型 (VoxCPM-0.5B)"""
    manager = ModelManager.get_instance()
    return manager.get_tts_model(device)


def get_qwen3_tts_model(device: str = "cuda:0"):
    """便捷函数：获取Qwen3-TTS模型"""
    manager = ModelManager.get_instance()
    return manager.get_qwen3_tts_model(device)


def get_asr_model(device: str = "cuda:0"):
    """便捷函数：获取ASR模型"""
    manager = ModelManager.get_instance()
    return manager.get_asr_model(device)


def clear_model_cache():
    """便捷函数：清除模型缓存"""
    manager = ModelManager.get_instance()
    manager.clear_cache()


def print_model_stats():
    """便捷函数：打印模型统计信息"""
    manager = ModelManager.get_instance()
    manager.print_stats()


if __name__ == "__main__":
    import time
    
    logging.basicConfig(level=logging.INFO)
    
    print("测试模型单例管理器...")
    
    start = time.time()
    tts1 = get_tts_model("cuda:0")
    time1 = time.time() - start
    print(f"第一次获取TTS模型: {time1:.3f}s")
    
    start = time.time()
    tts2 = get_tts_model("cuda:0")
    time2 = time.time() - start
    print(f"第二次获取TTS模型: {time2:.3f}s")
    
    start = time.time()
    qwen3_tts = get_qwen3_tts_model("cuda:0")
    time3 = time.time() - start
    print(f"获取Qwen3-TTS模型: {time3:.3f}s")
    
    start = time.time()
    asr1 = get_asr_model("cuda:0")
    time4 = time.time() - start
    print(f"第一次获取ASR模型: {time4:.3f}s")
    
    print_model_stats()
    
    print("测试完成！")
