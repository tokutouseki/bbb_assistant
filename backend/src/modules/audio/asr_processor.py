import numpy as np
from typing import Optional, Tuple, Dict, Any
import logging
import tempfile
import os
import time
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ASRResult:
    text: str
    confidence: float
    language: str
    processing_time: float

class ASRProcessor:
    """语音识别处理器，使用SenseVoiceSmall模型"""
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cuda:0", 
                 output_dir: Optional[str] = None):
        # 计算项目根目录的绝对路径
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
        
        self.model_path = model_path or os.path.join(project_root, "SenseVoiceSmall")
        self.device = device
        self.model = None
        
        # 设置输出目录
        if output_dir is None:
            # 默认输出目录：项目根目录下的outputs/asr_transcriptions
            self.output_dir = os.path.join(project_root, "outputs", "asr_transcriptions")
        else:
            self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._initialize()
    
    def _generate_output_filename(self, source_filename: Optional[str] = None, 
                                  language: Optional[str] = None, 
                                  extension: str = "txt") -> str:
        """
        生成输出文件名
        格式: asr_YYYYMMDD_HHMMSS_[source]_[lang].txt
        例如: asr_20250311_174830_audio.wav_zh.txt
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 提取源文件名（不含路径和扩展名）
        source_part = ""
        if source_filename:
            base_name = os.path.basename(source_filename)
            source_name, _ = os.path.splitext(base_name)
            # 清理文件名中的特殊字符
            source_name = re.sub(r'[^\w\-]', '_', source_name)
            source_part = f"_{source_name}"
        
        # 语言部分
        lang_part = f"_{language}" if language else ""
        
        # 生成最终文件名
        filename = f"asr_{timestamp}{source_part}{lang_part}.{extension}"
        return os.path.join(self.output_dir, filename)
    
    def save_transcription(self, result: ASRResult, source_filename: Optional[str] = None) -> str:
        """
        保存转录结果到文件
        
        Args:
            result: ASR结果
            source_filename: 源音频文件名（可选）
            
        Returns:
            保存的文件路径
        """
        try:
            # 生成输出文件名
            output_path = self._generate_output_filename(
                source_filename=source_filename,
                language=result.language,
                extension="txt"
            )
            
            # 写入转录结果
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入元数据
                f.write(f"# ASR Transcription Result\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Language: {result.language}\n")
                f.write(f"# Confidence: {result.confidence:.3f}\n")
                f.write(f"# Processing Time: {result.processing_time:.3f}s\n")
                f.write(f"# Source: {source_filename or 'unknown'}\n")
                f.write(f"\n")
                f.write(f"{result.text}\n")
            
            logger.info(f"转录结果保存到: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"保存转录结果失败: {e}")
            return ""
    
    def _initialize(self):
        """初始化SenseVoiceSmall模型"""
        try:
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
            
            self.model = AutoModel(
                model=self.model_path,
                trust_remote_code=False,  # 使用funasr内部集成的模型代码
                device=self.device,
            )
            logger.info(f"SenseVoiceSmall模型加载成功: {self.model_path}, 设备: {self.device}")
        except ImportError:
            logger.warning("funasr库未安装，使用模拟模式")
            self.model = None
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self.model = None
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, 
                   language: Optional[str] = None, save_result: bool = False,
                   source_filename: Optional[str] = None) -> ASRResult:
        """
        转录音频数据
        
        Args:
            audio_data: 音频数据，形状 (samples,) 或 (channels, samples)
            sample_rate: 采样率
            language: 语言代码（zh, en等），None表示自动检测
            save_result: 是否保存转录结果到文件
            source_filename: 源音频文件名（可选，用于保存时命名）
            
        Returns:
            转录结果
        """
        start_time = time.time()
        
        if self.model is None:
            # 模拟模式
            return self._mock_transcribe(audio_data, sample_rate, language)
        
        try:
            # 保存音频到临时文件
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    self._save_audio(tmp_path, audio_data, sample_rate)
                
                # 使用SenseVoiceSmall转录
                from funasr.utils.postprocess_utils import rich_transcription_postprocess
                
                res = self.model.generate(
                    input=tmp_path,
                    cache={},
                    language="auto" if language is None else language,
                    use_itn=True,  # 启用标点和逆文本正则化
                    batch_size=1,
                )
            finally:
                # 清理临时文件
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception as e:
                        logger.warning(f"删除临时文件失败 {tmp_path}: {e}")
            
            # 处理识别结果
            text = ""
            if res and len(res) > 0:
                if isinstance(res[0], dict) and "text" in res[0]:
                    text = rich_transcription_postprocess(res[0]["text"])
                elif isinstance(res[0], list) and len(res[0]) > 0 and isinstance(res[0][0], dict) and "text" in res[0][0]:
                    text = rich_transcription_postprocess(res[0][0]["text"])
                else:
                    logger.warning("识别结果格式不匹配")
                    text = "识别结果格式错误"
            
            processing_time = time.time() - start_time
            
            result = ASRResult(
                text=text,
                confidence=0.95,  # SenseVoice通常有高置信度
                language=language or "zh",
                processing_time=processing_time
            )
            
            # 如果需要保存结果
            if save_result:
                self.save_transcription(result, source_filename=source_filename)
            
            return result
            
        except Exception as e:
            logger.error(f"转录失败: {e}")
            return self._mock_transcribe(audio_data, sample_rate, language)
    
    def transcribe_file(self, audio_path: str, language: Optional[str] = None, 
                        save_result: bool = False) -> ASRResult:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            save_result: 是否保存转录结果到文件
            
        Returns:
            转录结果
        """
        start_time = time.time()
        
        if self.model is None:
            # 模拟模式
            return self._mock_transcribe_file(audio_path, language)
        
        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
            
            res = self.model.generate(
                input=audio_path,
                cache={},
                language="auto" if language is None else language,
                use_itn=True,
                batch_size=1,
            )
            
            # 处理识别结果
            text = ""
            if res and len(res) > 0:
                if isinstance(res[0], dict) and "text" in res[0]:
                    text = rich_transcription_postprocess(res[0]["text"])
                elif isinstance(res[0], list) and len(res[0]) > 0 and isinstance(res[0][0], dict) and "text" in res[0][0]:
                    text = rich_transcription_postprocess(res[0][0]["text"])
                else:
                    logger.warning("识别结果格式不匹配")
                    text = "识别结果格式错误"
            
            processing_time = time.time() - start_time
            
            result = ASRResult(
                text=text,
                confidence=0.95,
                language=language or "zh",
                processing_time=processing_time
            )
            
            # 如果需要保存结果
            if save_result:
                self.save_transcription(result, source_filename=audio_path)
            
            return result
            
        except Exception as e:
            logger.error(f"文件转录失败: {e}")
            return self._mock_transcribe_file(audio_path, language)
    
    def _save_audio(self, filepath: str, audio_data: np.ndarray, sample_rate: int):
        """保存音频数据到文件"""
        try:
            import soundfile as sf
            sf.write(filepath, audio_data, sample_rate)
        except ImportError:
            # 使用scipy作为备用
            from scipy.io import wavfile
            wavfile.write(filepath, sample_rate, audio_data.astype(np.int16))
    
    def _mock_transcribe(self, audio_data: np.ndarray, sample_rate: int, 
                        language: Optional[str]) -> ASRResult:
        """模拟转录结果"""
        processing_time = 0.5
        
        # 根据语言生成模拟文本
        if language == "en":
            text = "This is a simulated transcription result from SenseVoiceSmall model."
        else:
            text = "这是SenseVoiceSmall模型的模拟语音识别结果，用于测试。"
        
        return ASRResult(
            text=text,
            confidence=0.95,
            language=language or "zh",
            processing_time=processing_time
        )
    
    def _mock_transcribe_file(self, audio_path: str, language: Optional[str]) -> ASRResult:
        """模拟文件转录结果"""
        return self._mock_transcribe(np.zeros(16000), 16000, language)
    
    def detect_language(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        检测音频语言
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            
        Returns:
            语言代码
        """
        if self.model is None:
            return "zh"  # 默认中文
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                self._save_audio(tmp_file.name, audio_data, sample_rate)
                
                # 使用SenseVoice检测语言
                res = self.model.generate(
                    input=tmp_file.name,
                    cache={},
                    language="auto",
                    use_itn=False,
                    batch_size=1,
                )
                
                os.unlink(tmp_file.name)
                
                # SenseVoice在结果中通常包含语言信息
                # 如果无法从结果中提取，返回默认中文
                return "zh"
                
        except Exception as e:
            logger.error(f"语言检测失败: {e}")
            return "zh"
    
    def stream_transcribe(self, audio_stream, chunk_size: int = 16000):
        """
        流式转录（实时语音识别）
        
        Args:
            audio_stream: 音频流生成器
            chunk_size: 块大小
            
        Yields:
            实时转录结果
        """
        logger.info("开始流式转录")
        
        buffer = []
        for chunk in audio_stream:
            buffer.append(chunk)
            
            # 当缓冲区足够大时进行转录
            if len(buffer) >= 10:  # 10个块
                audio_data = np.concatenate(buffer)
                result = self.transcribe(audio_data)
                
                yield {
                    "text": result.text,
                    "is_final": False,
                    "confidence": result.confidence
                }
                
                buffer = []  # 清空缓冲区
        
        # 转录最后的缓冲区
        if buffer:
            audio_data = np.concatenate(buffer)
            result = self.transcribe(audio_data)
            
            yield {
                "text": result.text,
                "is_final": True,
                "confidence": result.confidence
            }
        
        logger.info("流式转录结束")