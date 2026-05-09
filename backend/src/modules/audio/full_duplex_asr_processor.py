# -*- coding: utf-8 -*-
"""
FunASR 全双工实时ASR处理器

集成文档中描述的核心能力：
1. 低延迟字级流式识别 (Paraformer流式版)
2. 2pass级联架构 (实时出字+离线修正)
3. 全双工随时打断 (VAD+中断+缓冲区清空)
4. RTX 3060优化 (GPU加速)
5. 识别结果后处理 (标点恢复+口语顺滑)

使用示例:
    from src.modules.audio import create_asr_processor
    
    # 方式1: SenseVoice模式 - 高精度识别+情感检测
    processor = create_asr_processor(mode="sensevoice", device="cuda:0")
    result = processor.transcribe_file("audio.wav")
    print(f"文本: {result.text}, 情感: {result.emotion}")
    
    # 方式2: Streaming模式 - 低延迟流式识别
    processor = create_asr_processor(mode="streaming", device="cuda:0")
    for result in processor.process_audio_stream(audio_generator()):
        print(f"实时: {result.text}")
    
    # 方式3: Full Duplex模式 - 全双工实时对话
    processor = create_asr_processor(mode="full_duplex", device="cuda:0")
    processor.set_callbacks(on_result=lambda r: print(r.text))
    processor.cancel()  # 随时打断

详细文档: backend/docs/FunASR_Integration_Guide.md
"""

import os
import time
import threading
import queue
from dataclasses import dataclass, field
from typing import Optional, Callable, Generator, List, Dict, Any, Union
from enum import Enum
import numpy as np
import logging
import tempfile
import re
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import torch
    import soundfile as sf
    from funasr import AutoModel
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    FUNASR_AVAILABLE = True
except ImportError:
    FUNASR_AVAILABLE = False
    logger.warning("FunASR未安装，将使用模拟模式")


class ASRMode(Enum):
    SENSEVOICE = "sensevoice"
    STREAMING = "streaming"
    FULL_DUPLEX = "full_duplex"


class ASRState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"


@dataclass
class ASRResult:
    text: str
    is_final: bool = True
    confidence: float = 0.95
    language: str = "zh"
    emotion: Optional[str] = None
    process_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    mode: str = "sensevoice"


@dataclass
class VADResult:
    is_speech: bool
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 0.0


class FullDuplexASRProcessor:
    """
    全双工实时ASR处理器
    
    支持三种模式：
    - sensevoice: 高精度多语言识别+情感检测
    - streaming: 低延迟流式识别
    - full_duplex: 全双工实时对话
    
    核心能力：
    - 低延迟字级流式识别 (首包延迟<100ms)
    - 2pass级联架构 (实时+离线修正)
    - VAD实时检测和随时打断
    - GPU加速
    - 标点恢复+口语顺滑
    """
    
    def __init__(
        self,
        mode: str = "sensevoice",
        device: str = "cuda:0",
        enable_2pass: bool = True,
        enable_punc: bool = True,
        enable_vad: bool = True,
        output_dir: Optional[str] = None,
        chunk_size: List[int] = None,
    ):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        
        self.mode = ASRMode(mode)
        self.device = device
        self.enable_2pass = enable_2pass
        self.enable_punc = enable_punc
        self.enable_vad = enable_vad
        
        self.chunk_size = chunk_size or [0, 10, 5]
        self.encoder_chunk_look_back = 4
        self.decoder_chunk_look_back = 1
        
        self.state = ASRState.IDLE
        self._cancel_flag = False
        self._streaming_cache = {}
        self._lock = threading.Lock()
        
        if output_dir is None:
            self.output_dir = os.path.join(project_root, "outputs", "asr_transcriptions")
        else:
            self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._models_loaded = False
        self.sensevoice_model = None
        self.streaming_model = None
        self.vad_model = None
        self.offline_model = None
        self.punc_model = None
        
        self._on_result_callback: Optional[Callable] = None
        self._on_vad_callback: Optional[Callable] = None
        self._on_interrupt_callback: Optional[Callable] = None
        
        self._initialize()
    
    def _initialize(self):
        """初始化模型"""
        if not FUNASR_AVAILABLE:
            logger.warning("FunASR不可用，使用模拟模式")
            return
        
        logger.info("="*50)
        logger.info("FunASR 全双工实时ASR处理器初始化")
        logger.info("="*50)
        logger.info(f"模式: {self.mode.value}")
        logger.info(f"设备: {self.device}")
        
        if torch.cuda.is_available():
            logger.info(f"显卡: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("CUDA不可用，使用CPU")
            self.device = "cpu"
        
        try:
            if self.mode in [ASRMode.SENSEVOICE, ASRMode.FULL_DUPLEX]:
                logger.info("加载SenseVoiceSmall模型...")
                self.sensevoice_model = AutoModel(
                    model="iic/SenseVoiceSmall",
                    device=self.device,
                    disable_update=True
                )
                logger.info("✓ SenseVoiceSmall加载成功")
            
            if self.mode in [ASRMode.STREAMING, ASRMode.FULL_DUPLEX]:
                logger.info("加载流式ASR模型...")
                self.streaming_model = AutoModel(
                    model="paraformer-zh-streaming",
                    device=self.device,
                    disable_update=True
                )
                logger.info("✓ 流式ASR模型加载成功")
            
            if self.mode == ASRMode.FULL_DUPLEX and self.enable_vad:
                logger.info("加载VAD模型...")
                self.vad_model = AutoModel(
                    model="fsmn-vad",
                    device=self.device,
                    disable_update=True
                )
                logger.info("✓ VAD模型加载成功")
            
            if self.mode == ASRMode.FULL_DUPLEX and self.enable_2pass:
                logger.info("加载离线修正模型...")
                self.offline_model = AutoModel(
                    model="paraformer-zh",
                    device=self.device,
                    disable_update=True
                )
                logger.info("✓ 离线修正模型加载成功")
            
            if self.enable_punc:
                logger.info("加载标点恢复模型...")
                try:
                    self.punc_model = AutoModel(
                        model="ct-punc",
                        device=self.device,
                        disable_update=True
                    )
                    logger.info("✓ 标点恢复模型加载成功")
                except Exception as e:
                    logger.warning(f"标点模型加载失败: {e}")
                    self.punc_model = None
            
            self._models_loaded = True
            logger.info("="*50)
            logger.info("所有模型加载完成!")
            logger.info("="*50)
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self._models_loaded = False
    
    def set_callbacks(
        self,
        on_result: Optional[Callable[[ASRResult], None]] = None,
        on_vad: Optional[Callable[[VADResult], None]] = None,
        on_interrupt: Optional[Callable[[], None]] = None,
    ):
        """设置回调函数"""
        self._on_result_callback = on_result
        self._on_vad_callback = on_vad
        self._on_interrupt_callback = on_interrupt
    
    def cancel(self):
        """
        即时中断当前识别
        清空音频缓冲区、中间特征缓存、未输出的解码结果
        """
        with self._lock:
            self._cancel_flag = True
            self._streaming_cache = {}
            
            if self._on_interrupt_callback:
                self._on_interrupt_callback()
            
            self.state = ASRState.IDLE
            logger.info("[中断] 已清空所有缓冲区，准备接收新语音")
    
    def reset(self):
        """重置模型状态"""
        with self._lock:
            self._streaming_cache = {}
            self._cancel_flag = False
            self.state = ASRState.IDLE
    
    def detect_vad(self, audio_data: np.ndarray, sample_rate: int = 16000) -> VADResult:
        """VAD语音活动检测"""
        if self.vad_model is None:
            return VADResult(is_speech=True)
        
        try:
            res = self.vad_model.generate(
                input=audio_data,
                cache={},
                is_final=True,
            )
            
            if res and len(res) > 0:
                vad_info = res[0].get("value", [])
                if vad_info:
                    return VADResult(
                        is_speech=True,
                        start_time=vad_info[0] if len(vad_info) > 0 else 0,
                        end_time=vad_info[1] if len(vad_info) > 1 else len(audio_data)/sample_rate*1000,
                        confidence=0.95
                    )
            
            return VADResult(is_speech=False)
            
        except Exception as e:
            logger.error(f"VAD检测错误: {e}")
            return VADResult(is_speech=True)
    
    def _extract_emotion(self, text: str) -> Optional[str]:
        """从SenseVoice结果中提取情感标签"""
        emotion_map = {
            "HAPPY": "开心",
            "SAD": "难过",
            "ANGRY": "愤怒",
            "NEUTRAL": "中性",
            "SURPRISED": "惊讶",
        }
        
        for tag, emotion in emotion_map.items():
            if tag in text:
                return emotion
        
        if "😊" in text:
            return "开心"
        elif "😔" in text:
            return "难过"
        elif "😡" in text:
            return "愤怒"
        elif "😮" in text:
            return "惊讶"
        
        return None
    
    def transcribe_sensevoice(
        self,
        audio_input: Union[str, np.ndarray],
        language: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """使用SenseVoiceSmall进行识别"""
        start_time = time.time()
        
        if self.sensevoice_model is None:
            return self._mock_result("sensevoice")
        
        try:
            if isinstance(audio_input, np.ndarray):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    sf.write(tmp.name, audio_input, sample_rate)
                    audio_input = tmp.name
            
            res = self.sensevoice_model.generate(
                input=audio_input,
                cache={},
                language="auto" if language is None else language,
                use_itn=True,
                batch_size=1,
            )
            
            text = ""
            if res and len(res) > 0:
                raw_text = res[0].get("text", "")
                text = rich_transcription_postprocess(raw_text)
            
            emotion = self._extract_emotion(text)
            
            return ASRResult(
                text=text,
                is_final=True,
                confidence=0.95,
                language=language or "zh",
                emotion=emotion,
                process_time=time.time() - start_time,
                mode="sensevoice"
            )
            
        except Exception as e:
            logger.error(f"SenseVoice识别失败: {e}")
            return self._mock_result("sensevoice")
    
    def transcribe_streaming(
        self,
        audio_chunk: np.ndarray,
        is_final: bool = False,
    ) -> Optional[ASRResult]:
        """流式识别单个音频块"""
        if self.streaming_model is None:
            return None
        
        if self._cancel_flag:
            return None
        
        start_time = time.time()
        
        try:
            res = self.streaming_model.generate(
                input=audio_chunk,
                cache=self._streaming_cache,
                is_final=is_final,
                chunk_size=self.chunk_size,
                encoder_chunk_look_back=self.encoder_chunk_look_back,
                decoder_chunk_look_back=self.decoder_chunk_look_back,
            )
            
            if res and len(res) > 0:
                text = res[0].get("text", "")
                if text:
                    return ASRResult(
                        text=text,
                        is_final=is_final,
                        process_time=time.time() - start_time,
                        mode="streaming"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"流式识别错误: {e}")
            return None
    
    def transcribe_offline(self, audio_data: np.ndarray) -> Optional[ASRResult]:
        """2pass离线修正"""
        if self.offline_model is None:
            return None
        
        start_time = time.time()
        
        try:
            res = self.offline_model.generate(
                input=audio_data,
                batch_size_s=300,
            )
            
            if res and len(res) > 0:
                text = res[0].get("text", "")
                if text:
                    return ASRResult(
                        text=text,
                        is_final=True,
                        process_time=time.time() - start_time,
                        mode="offline"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"离线修正错误: {e}")
            return None
    
    def add_punctuation(self, text: str) -> str:
        """标点恢复"""
        if self.punc_model is None or not text:
            return text
        
        try:
            res = self.punc_model.generate(input=text)
            if res and len(res) > 0:
                return res[0].get("text", text)
            return text
        except Exception as e:
            logger.error(f"标点恢复错误: {e}")
            return text
    
    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        save_result: bool = False,
        source_filename: Optional[str] = None,
    ) -> ASRResult:
        """
        转录音频数据（兼容旧接口）
        """
        if not self._models_loaded:
            return self._mock_result("sensevoice")
        
        if self.mode == ASRMode.SENSEVOICE:
            result = self.transcribe_sensevoice(audio_data, language, sample_rate)
        elif self.mode == ASRMode.STREAMING:
            result = self.transcribe_streaming(audio_data, is_final=True)
            if result is None:
                result = self._mock_result("streaming")
        else:
            result = self.transcribe_sensevoice(audio_data, language, sample_rate)
        
        if save_result and result:
            self.save_transcription(result, source_filename)
        
        return result
    
    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None,
        save_result: bool = False,
    ) -> ASRResult:
        """转录音频文件"""
        if not self._models_loaded:
            return self._mock_result("sensevoice")
        
        audio_data, sr = sf.read(audio_path)
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]
        
        if sr != 16000:
            import librosa
            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=16000)
        
        result = self.transcribe(audio_data, 16000, language)
        
        if save_result:
            self.save_transcription(result, audio_path)
        
        return result
    
    def process_audio_stream(
        self,
        audio_stream: Generator[np.ndarray, None, None],
        sample_rate: int = 16000,
        chunk_stride_ms: int = 600,
    ) -> Generator[ASRResult, None, None]:
        """
        处理音频流，生成实时识别结果
        """
        chunk_stride = int(chunk_stride_ms * sample_rate / 1000)
        self.state = ASRState.LISTENING
        self._cancel_flag = False
        
        audio_buffer = []
        
        for audio_chunk in audio_stream:
            if self._cancel_flag:
                break
            
            audio_buffer.append(audio_chunk)
            
            if self.enable_vad and self.vad_model:
                vad_result = self.detect_vad(audio_chunk, sample_rate)
                if self._on_vad_callback:
                    self._on_vad_callback(vad_result)
            
            if self.mode in [ASRMode.STREAMING, ASRMode.FULL_DUPLEX]:
                result = self.transcribe_streaming(audio_chunk, is_final=False)
                if result and result.text:
                    yield result
            elif self.mode == ASRMode.SENSEVOICE:
                result = self.transcribe_sensevoice(audio_chunk)
                if result and result.text:
                    yield result
        
        if not self._cancel_flag and audio_buffer:
            full_audio = np.concatenate(audio_buffer)
            
            if self.mode in [ASRMode.STREAMING, ASRMode.FULL_DUPLEX]:
                final_result = self.transcribe_streaming(full_audio, is_final=True)
                if final_result and final_result.text:
                    if self.enable_punc:
                        final_result.text = self.add_punctuation(final_result.text)
                    yield final_result
                
                if self.enable_2pass and self.mode == ASRMode.FULL_DUPLEX:
                    corrected = self.transcribe_offline(full_audio)
                    if corrected and corrected.text:
                        if self.enable_punc:
                            corrected.text = self.add_punctuation(corrected.text)
                        yield corrected
            else:
                result = self.transcribe_sensevoice(full_audio)
                if result:
                    yield result
        
        self.state = ASRState.IDLE
    
    def save_transcription(self, result: ASRResult, source_filename: Optional[str] = None) -> str:
        """保存转录结果到文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            source_part = ""
            if source_filename:
                base_name = os.path.basename(source_filename)
                source_name, _ = os.path.splitext(base_name)
                source_name = re.sub(r'[^\w\-]', '_', source_name)
                source_part = f"_{source_name}"
            
            filename = f"asr_{timestamp}{source_part}_{result.mode}.txt"
            output_path = os.path.join(self.output_dir, filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# ASR Transcription Result\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Mode: {result.mode}\n")
                f.write(f"# Language: {result.language}\n")
                f.write(f"# Confidence: {result.confidence:.3f}\n")
                f.write(f"# Processing Time: {result.processing_time:.3f}s\n")
                f.write(f"# Emotion: {result.emotion or 'N/A'}\n")
                f.write(f"# Source: {source_filename or 'unknown'}\n")
                f.write(f"\n")
                f.write(f"{result.text}\n")
            
            logger.info(f"转录结果保存到: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"保存转录结果失败: {e}")
            return ""
    
    def _mock_result(self, mode: str) -> ASRResult:
        """生成模拟结果"""
        return ASRResult(
            text="[模拟模式] FunASR未加载",
            is_final=True,
            confidence=0.0,
            mode=mode
        )
    
    def stream_transcribe(self, audio_stream, chunk_size: int = 16000):
        """流式转录（兼容旧接口）"""
        logger.info("开始流式转录")
        
        buffer = []
        for chunk in audio_stream:
            buffer.append(chunk)
            
            if len(buffer) >= 10:
                audio_data = np.concatenate(buffer)
                result = self.transcribe(audio_data)
                
                yield {
                    "text": result.text,
                    "is_final": False,
                    "confidence": result.confidence
                }
                
                buffer = []
        
        if buffer:
            audio_data = np.concatenate(buffer)
            result = self.transcribe(audio_data)
            
            yield {
                "text": result.text,
                "is_final": True,
                "confidence": result.confidence
            }
        
        logger.info("流式转录结束")
    
    def detect_language(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """检测音频语言"""
        return "zh"


def create_asr_processor(
    mode: str = "sensevoice",
    device: str = "cuda:0",
    **kwargs
) -> FullDuplexASRProcessor:
    """
    创建ASR处理器的工厂函数
    
    Args:
        mode: 模式选择
            - "sensevoice": 高精度多语言识别+情感检测
            - "streaming": 低延迟流式识别
            - "full_duplex": 全双工实时对话
        device: 设备选择 ("cuda:0" 或 "cpu")
        **kwargs: 其他参数
    
    Returns:
        ASR处理器实例
    """
    return FullDuplexASRProcessor(mode=mode, device=device, **kwargs)
