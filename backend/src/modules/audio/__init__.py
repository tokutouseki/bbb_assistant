# -*- coding: utf-8 -*-
"""
音频处理模块

提供语音识别(ASR)、语音合成(TTS)、语音克隆等功能。

ASR语音识别:
    from src.modules.audio import create_asr_processor
    
    # SenseVoice模式 - 高精度识别+情感检测
    processor = create_asr_processor(mode="sensevoice", device="cuda:0")
    result = processor.transcribe_file("audio.wav")
    
    # Streaming模式 - 低延迟流式识别
    processor = create_asr_processor(mode="streaming", device="cuda:0")
    
    # Full Duplex模式 - 全双工实时对话
    processor = create_asr_processor(mode="full_duplex", device="cuda:0")

TTS语音合成:
    from src.modules.audio import TTSGenerator, Qwen3TTSGenerator
    
    # VoxCPM语音合成
    tts = TTSGenerator(device="cuda:0")
    audio = tts.generate("你好", reference_audio="ref.wav")
    
    # Qwen3-TTS语音合成 (ICL语音克隆)
    tts = Qwen3TTSGenerator(device="cuda:0")
    audio = tts.generate("你好", voice_style="爱莉希雅")
"""

from .asr_processor import ASRProcessor
from .tts_generator import TTSGenerator
from .qwen3_tts_generator import Qwen3TTSGenerator
from .voice_clone import VoiceClone
from .full_duplex_asr_processor import (
    FullDuplexASRProcessor,
    ASRMode,
    ASRState,
    ASRResult,
    VADResult,
    create_asr_processor,
)

__all__ = [
    "ASRProcessor",
    "TTSGenerator", 
    "Qwen3TTSGenerator", 
    "VoiceClone",
    "FullDuplexASRProcessor",
    "ASRMode",
    "ASRState",
    "ASRResult",
    "VADResult",
    "create_asr_processor",
]
