#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-TTS 语音生成器

使用阿里Qwen3-TTS模型进行高质量语音合成，支持多语言、多情感表达和声音设计。

Qwen3-TTS优势：
- 支持10种语言（中文、英文、日语、韩语等）
- 支持声音设计（用自然语言描述想要的声音风格）
- 支持3秒语音克隆
- 高质量、自然流畅的语音输出
- 可免费商用

使用方法：
  from src.modules.audio.qwen3_tts_generator import Qwen3TTSGenerator
  
  tts = Qwen3TTSGenerator(device="cuda:0")
  result = tts.generate(
      text="你好，这是Qwen3-TTS生成的语音",
      voice_style="温柔女声"
  )
"""

import os
import sys
import logging
import time
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Qwen3TTSResult:
    """Qwen3-TTS生成结果"""
    audio_data: np.ndarray
    sample_rate: int
    text: str
    voice_style: str
    processing_time: float
    language: str = "Chinese"


class Qwen3TTSGenerator:
    """Qwen3-TTS 语音生成器"""
    
    SUPPORTED_LANGUAGES = [
        "Chinese", "English", "Japanese", "Korean",
        "German", "French", "Russian", "Portuguese",
        "Spanish", "Italian"
    ]
    
    DEFAULT_VOICE_STYLES = {
        "温柔女声": "温柔的成年女性声音，语速适中，音调柔和",
        "活力女声": "活泼开朗的年轻女性声音，语速较快，充满活力",
        "沉稳男声": "沉稳的成年男性声音，语速平稳，音调低沉",
        "可爱萝莉": "撒娇稚嫩的萝莉女声，音调偏高且起伏明显",
        "专业客服": "专业的客服女声，语速适中，礼貌亲切",
        "新闻播报": "标准的新闻播报声音，语速平稳，吐字清晰",
        "爱莉希雅": "温柔甜美的少女声音，带有粉色气息，语调轻柔",
        "琪亚娜": "活泼开朗的少女声音，充满活力和正义感",
        "雷电芽衣": "温柔端庄的女性声音，带有成熟气质",
        "布洛妮娅": "冷静沉稳的少女声音，语速稍慢，带有机械感",
    }
    
    def __init__(self, model_path: str = None, device: str = "cuda:0",
                 output_dir: str = None, dtype: str = "bfloat16"):
        """
        初始化Qwen3-TTS生成器
        
        Args:
            model_path: 模型路径，默认使用预设路径
            device: 计算设备 (cpu/cuda:0)
            output_dir: 输出目录
            dtype: 数据类型 (bfloat16/float16/float32)
        """
        self.device = device
        self.dtype = dtype
        
        if model_path:
            self.model_path = self._normalize_model_path(model_path)
        else:
            self.model_path = self._get_default_model_path()
        
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.join(os.getcwd(), "outputs", "qwen3_tts")
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.model = None
        self.initialized = False
        
        try:
            self._initialize()
        except Exception as e:
            logger.error(f"Qwen3-TTS初始化失败: {e}")
            self.initialized = False
    
    def _get_default_model_path(self) -> str:
        """获取默认模型路径"""
        # 1. 首先从环境变量读取
        env_path = os.environ.get("QWEN3_TTS_MODEL_PATH")
        if env_path:
            normalized_path = self._normalize_model_path(env_path)
            if os.path.exists(normalized_path):
                logger.info(f"从环境变量获取模型路径: {normalized_path}")
                return normalized_path
        
        # 2. 从配置文件读取
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "model_cache.yaml")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    qwen3_tts_path = config.get("model_cache", {}).get("qwen3_tts_path")
                    if qwen3_tts_path and os.path.exists(qwen3_tts_path):
                        logger.info(f"从配置文件获取模型路径: {qwen3_tts_path}")
                        return self._normalize_model_path(qwen3_tts_path)
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")
        
        # 3. 尝试项目根目录下的模型
        possible_paths = [
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS" / "models" / "Qwen" / "Qwen3-TTS-12Hz-1___7B-VoiceDesign",
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS" / "models" / "Qwen" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS" / "models" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS",
            Path.home() / ".cache" / "huggingface" / "hub" / "models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        ]
        
        for path in possible_paths:
            normalized_path = self._normalize_model_path(str(path))
            if os.path.exists(normalized_path):
                logger.info(f"找到模型路径: {normalized_path}")
                return normalized_path
        
        logger.warning("未找到本地模型，将尝试从HuggingFace下载")
        return "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"

    def _normalize_model_path(self, model_path: str) -> str:
        """将传入路径规范化为可直接加载的Qwen3-TTS模型目录。"""
        base = Path(model_path)
        if (base / "config.json").exists():
            return str(base)

        candidates = [
            base / "models" / "Qwen" / "Qwen3-TTS-12Hz-1___7B-VoiceDesign",
            base / "models" / "Qwen" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            base / "models" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            base / "Qwen3-TTS-12Hz-1___7B-VoiceDesign",
            base / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        ]
        for candidate in candidates:
            if (candidate / "config.json").exists():
                logger.info(f"从目录自动解析Qwen3-TTS模型路径: {candidate}")
                return str(candidate)
        return str(base)
    
    def _initialize(self):
        """初始化Qwen3-TTS模型"""
        try:
            import torch
            
            logger.info(f"正在加载Qwen3-TTS模型: {self.model_path}")
            logger.info(f"设备: {self.device}, 数据类型: {self.dtype}")
            
            try:
                from qwen_tts import Qwen3TTSModel
                
                dtype_map = {
                    "bfloat16": torch.bfloat16,
                    "float16": torch.float16,
                    "float32": torch.float32
                }
                
                self.model = Qwen3TTSModel.from_pretrained(
                    self.model_path,
                    device_map=self.device,
                    dtype=dtype_map.get(self.dtype, torch.bfloat16)
                )
                
                logger.info("Qwen3-TTS模型加载成功")
                self.initialized = True
                
            except ImportError:
                logger.warning("qwen_tts包未安装，将使用模拟模式")
                logger.info("安装方法: pip install qwen-tts")
                self.initialized = False
                
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            self.initialized = False
    
    def generate(self, text: str, voice_style: str = "温柔女声",
                language: str = "Chinese", speed: float = 1.0,
                custom_description: str = None) -> Qwen3TTSResult:
        """
        生成语音
        
        Args:
            text: 要合成的文本
            voice_style: 预设声音风格名称
            language: 语言（Chinese/English/Japanese等）
            speed: 语速（暂不支持）
            custom_description: 自定义声音描述（优先于voice_style）
        
        Returns:
            Qwen3TTSResult: 生成结果
        """
        start_time = time.time()
        
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"不支持的语言 '{language}'，使用默认 'Chinese'")
            language = "Chinese"
        
        if custom_description:
            description = custom_description
        elif voice_style in self.DEFAULT_VOICE_STYLES:
            description = self.DEFAULT_VOICE_STYLES[voice_style]
        else:
            description = voice_style
        
        if not self.initialized:
            audio_data, sample_rate = self._generate_mock_audio(text)
        else:
            audio_data, sample_rate = self._generate_real_audio(
                text, description, language
            )
        
        processing_time = time.time() - start_time
        
        result = Qwen3TTSResult(
            audio_data=audio_data,
            sample_rate=sample_rate,
            text=text,
            voice_style=voice_style,
            processing_time=processing_time,
            language=language
        )
        
        logger.info(f"语音生成完成，耗时: {processing_time:.2f}s")
        return result
    
    def _generate_mock_audio(self, text: str) -> Tuple[np.ndarray, int]:
        """生成模拟音频（当模型未初始化时）"""
        duration = len(text) * 0.15
        sample_rate = 24000
        samples = int(duration * sample_rate)
        
        t = np.linspace(0, duration, samples, endpoint=False)
        frequency = 440
        audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
        audio_data = audio_data.astype(np.float32)
        
        logger.warning("使用模拟音频模式，请安装qwen_tts以获得真实语音")
        return audio_data, sample_rate
    
    def _generate_real_audio(self, text: str, description: str, 
                            language: str) -> Tuple[np.ndarray, int]:
        """使用真实Qwen3-TTS模型生成音频"""
        try:
            wavs, sr = self.model.generate_voice_design(
                text=text,
                language=language,
                instruct=description
            )
            
            if isinstance(wavs, list) and len(wavs) > 0:
                audio_data = wavs[0]
            else:
                audio_data = np.array(wavs)
            
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            return audio_data, sr
            
        except Exception as e:
            logger.error(f"Qwen3-TTS生成失败: {e}")
            return self._generate_mock_audio(text)
    
    def generate_with_reference(self, text: str, reference_audio: str,
                               language: str = "Chinese", ref_text: str = None) -> Qwen3TTSResult:
        """
        使用参考音频进行语音克隆
        
        Args:
            text: 要合成的文本
            reference_audio: 参考音频路径
            language: 语言
            ref_text: 参考音频对应的文本（用于ICL模式，可选）
        
        Returns:
            Qwen3TTSResult: 生成结果
        """
        start_time = time.time()
        
        if not self.initialized:
            audio_data, sample_rate = self._generate_mock_audio(text)
        else:
            try:
                # 使用正确的API: generate_voice_clone
                wavs, sr = self.model.generate_voice_clone(
                    text=text,
                    language=language,
                    ref_audio=reference_audio,
                    ref_text=ref_text,
                    x_vector_only_mode=False if ref_text else True
                )
                
                if isinstance(wavs, list) and len(wavs) > 0:
                    audio_data = wavs[0]
                else:
                    audio_data = np.array(wavs)
                
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                sample_rate = sr
                logger.info(f"Qwen3-TTS语音克隆成功")
                
            except Exception as e:
                logger.error(f"语音克隆失败: {e}")
                audio_data, sample_rate = self._generate_mock_audio(text)
        
        processing_time = time.time() - start_time
        
        return Qwen3TTSResult(
            audio_data=audio_data,
            sample_rate=sample_rate,
            text=text,
            voice_style="cloned",
            processing_time=processing_time,
            language=language
        )
    
    def save_to_file(self, result: Qwen3TTSResult, filepath: str = None) -> str:
        """
        保存语音结果到文件
        
        Args:
            result: TTS结果
            filepath: 文件路径（可选）
        
        Returns:
            保存的文件路径
        """
        try:
            import soundfile as sf
            
            if filepath is None:
                import hashlib
                import datetime
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                text_hash = hashlib.md5(result.text.encode('utf-8')).hexdigest()[:6]
                filename = f"qwen3_tts_{timestamp}_{result.voice_style}_{text_hash}.wav"
                filepath = os.path.join(self.output_dir, filename)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            sf.write(filepath, result.audio_data, result.sample_rate)
            
            logger.info(f"音频已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存音频失败: {e}")
            return ""
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def get_voice_styles(self) -> Dict[str, str]:
        """获取预设声音风格"""
        return self.DEFAULT_VOICE_STYLES.copy()


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("测试Qwen3-TTS生成器...")
    
    tts = Qwen3TTSGenerator(device="cuda:0")
    
    print(f"支持的语言: {tts.get_supported_languages()}")
    print(f"预设声音风格: {list(tts.get_voice_styles().keys())}")
    
    result = tts.generate(
        text="哥哥，你回来啦，人家等了你好久好久了，要抱抱！",
        voice_style="可爱萝莉",
        language="Chinese"
    )
    
    print(f"生成成功!")
    print(f"音频长度: {len(result.audio_data)} samples")
    print(f"采样率: {result.sample_rate} Hz")
    print(f"处理时间: {result.processing_time:.3f}s")
    
    output_path = tts.save_to_file(result)
    print(f"音频已保存到: {output_path}")
