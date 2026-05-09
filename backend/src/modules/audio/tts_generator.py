import numpy as np
from typing import Optional, Dict, Any, Tuple
import logging
import base64
import tempfile
import os
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TTSResult:
    audio_data: np.ndarray
    sample_rate: int
    text: str
    voice_id: str
    processing_time: float

class TTSGenerator:
    """语音合成生成器，使用VoxCPM模型，支持语音克隆"""
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cuda:0",
                 output_dir: Optional[str] = None):
        # 计算项目根目录的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
        
        # 优先从环境变量读取模型路径
        env_model_path = os.environ.get("VOXCPM_MODEL_PATH")
        
        if model_path:
            self.model_path = model_path
        elif env_model_path and os.path.exists(env_model_path):
            self.model_path = env_model_path
            logger.info(f"从环境变量获取VoxCPM模型路径: {self.model_path}")
        else:
            self.model_path = os.path.join(project_root, "VoxCPM-0.5B")
        self.device = device
        self.model = None
        
        # 初始化声音资源管理器
        try:
            from .voice_resource_manager import get_voice_resource_manager
            self.voice_manager = get_voice_resource_manager()
            logger.info("声音资源管理器初始化成功")
        except Exception as e:
            logger.error(f"声音资源管理器初始化失败: {e}")
            self.voice_manager = None
        
        # 保留默认值作为后备
        self.default_prompt_audio = os.path.join(project_root, "voice_resources/elysia/reference.wav")
        self.default_prompt_text = "有沉默寡言，却又敏锐细腻的绘画少女。除此之外，还有一位在我们那个时代举世瞩目的大明星呢"
        
        # 设置输出目录
        if output_dir is None:
            # 默认输出目录：项目根目录下的outputs/tts_audio
            self.output_dir = os.path.join(project_root, "outputs", "tts_audio")
        else:
            self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._initialize()
        
    def _get_zipenhancer_path(self) -> str:
        """
        获取zipenhancer模型路径
        
        Returns:
            str: zipenhancer模型路径
        """
        import os
        import yaml
        
        # 1. 从环境变量读取
        env_path = os.environ.get("ZIPENHANCER_MODEL_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
        
        # 2. 从配置文件读取
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "model_cache.yaml")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                zipenhancer_path = config.get("model_cache", {}).get("zipenhancer_path")
                if zipenhancer_path and os.path.exists(zipenhancer_path):
                    return zipenhancer_path
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")
        
        # 3. 从models目录查找
        default_paths = [
            "models/zipenhancer/models/iic/speech_zipenhancer_ans_multiloss_16k_base",
            "models/zipenhancer/iic/speech_zipenhancer_ans_multiloss_16k_base",
            "../models/zipenhancer/models/iic/speech_zipenhancer_ans_multiloss_16k_base",
            "../models/zipenhancer/iic/speech_zipenhancer_ans_multiloss_16k_base"
        ]
        
        for path in default_paths:
            full_path = os.path.abspath(path)
            if os.path.exists(full_path):
                return full_path
        
        return None
    
    def _initialize(self):
        """初始化VoxCPM模型"""
        try:
            from voxcpm import VoxCPM
            
            # 从配置文件读取zipenhancer模型路径
            zipenhancer_path = self._get_zipenhancer_path()
            
            if zipenhancer_path and os.path.exists(zipenhancer_path):
                # 使用本地zipenhancer模型，禁用网络下载
                self.model = VoxCPM.from_pretrained(
                    self.model_path,
                    zipenhancer_model_id=zipenhancer_path,
                    local_files_only=True
                )
                logger.info(f"VoxCPM模型加载成功: {self.model_path}, 设备: {self.device}")
                logger.info(f"使用本地zipenhancer模型: {zipenhancer_path}")
            else:
                # 回退到默认行为
                self.model = VoxCPM.from_pretrained(self.model_path)
                logger.info(f"VoxCPM模型加载成功: {self.model_path}, 设备: {self.device}")
                logger.info("使用默认zipenhancer模型")
                
        except ImportError:
            logger.warning("voxcpm库未安装，使用模拟模式")
            self.model = None
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self.model = None
    
    def _generate_output_filename(self, text: str, voice_id: str = "default", 
                                  emotion: Optional[str] = None) -> str:
        """
        生成输出文件名
        格式: tts_YYYYMMDD_HHMMSS_[voice]_[emotion]_[hash].wav
        例如: tts_20250311_174830_elysia_happy_abc123.wav
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理voice_id中的特殊字符
        voice_clean = re.sub(r'[^\w\-]', '_', voice_id)
        
        # 情感部分
        emotion_part = f"_{emotion}" if emotion else ""
        
        # 生成文本的短哈希（前6位）
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:6]
        
        # 生成最终文件名
        filename = f"tts_{timestamp}_{voice_clean}{emotion_part}_{text_hash}.wav"
        return os.path.join(self.output_dir, filename)
    
    def save_to_file(self, result: TTSResult, filepath: Optional[str] = None) -> str:
        """
        保存语音结果到文件
        
        Args:
            result: TTS结果
            filepath: 文件路径（可选，如果为None则自动生成）
            
        Returns:
            保存的文件路径，如果失败则返回空字符串
        """
        try:
            # 如果未提供文件路径，自动生成
            if filepath is None:
                filepath = self._generate_output_filename(
                    text=result.text,
                    voice_id=result.voice_id
                )
            
            import soundfile as sf
            sf.write(filepath, result.audio_data, result.sample_rate)
            logger.info(f"语音保存到: {filepath}")
            return filepath
        except ImportError:
            try:
                from scipy.io import wavfile
                wavfile.write(filepath, result.sample_rate, result.audio_data)
                logger.info(f"语音保存到: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"保存失败: {e}")
                return ""
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return ""
    
    def generate(self, text: str, voice_id: str = "default", 
                 speed: float = 1.0, pitch: float = 1.0,
                 prompt_audio: Optional[str] = None,
                 prompt_text: Optional[str] = None,
                 save_result: bool = False) -> TTSResult:
        """
        生成语音
        
        Args:
            text: 要合成的文本
            voice_id: 语音ID（用于选择参考音频）
            speed: 语速（1.0为正常） - 注意：VoxCPM不支持直接调整语速
            pitch: 音调（1.0为正常） - 注意：VoxCPM不支持直接调整音调
            prompt_audio: 参考音频路径（可选）
            prompt_text: 参考文本（可选）
            save_result: 是否保存生成的音频到文件
            
        Returns:
            语音合成结果
        """
        import time
        start_time = time.time()
        
        if self.model is None:
            # 模拟模式
            return self._generate_mock(text, voice_id, speed, pitch)
        
        try:
            # 根据voice_id选择参考音频
            if prompt_audio is None:
                # 使用声音资源管理器获取参考音频和文本
                if self.voice_manager:
                    voice_ref = self.voice_manager.get_voice_reference_audio(voice_id)
                    voice_text = self.voice_manager.get_voice_reference_text(voice_id)
                    
                    if voice_ref:
                        prompt_audio = voice_ref
                        prompt_text = voice_text or text  # 如果没有参考文本，使用当前文本
                        logger.info(f"使用语音资源: {voice_id}, 音频: {prompt_audio}")
                    else:
                        # 如果指定角色不可用，使用默认爱莉希雅语音
                        logger.warning(f"语音 {voice_id} 不可用，使用默认语音")
                        prompt_audio = self.default_prompt_audio
                        prompt_text = self.default_prompt_text
                else:
                    # 声音资源管理器不可用，使用默认值
                    if voice_id == "elysia" or voice_id == "default":
                        prompt_audio = self.default_prompt_audio
                        prompt_text = self.default_prompt_text
                    else:
                        # 对于其他角色，尝试使用对应角色的参考音频
                        # 这里可以扩展为角色语音库
                        prompt_audio = self.default_prompt_audio
                        prompt_text = self.default_prompt_text
            
            # 使用VoxCPM生成语音
            wav = self.model.generate(
                text=text,
                prompt_wav_path=prompt_audio,
                prompt_text=prompt_text,
                cfg_value=2.0,
                inference_timesteps=10,
                normalize=True,
                denoise=True,
                retry_badcase=True,
                retry_badcase_max_times=3,
                retry_badcase_ratio_threshold=6.0,
            )
            
            # VoxCPM生成的是16000Hz采样率的音频
            sample_rate = 16000
            
            processing_time = time.time() - start_time
            
            result = TTSResult(
                audio_data=wav.astype(np.float32),
                sample_rate=sample_rate,
                text=text,
                voice_id=voice_id,
                processing_time=processing_time
            )
            
            # 如果需要保存结果
            if save_result:
                self.save_to_file(result)
            
            return result
            
        except Exception as e:
            logger.error(f"语音生成失败: {e}")
            result = self._generate_mock(text, voice_id, speed, pitch)
            
            # 如果需要保存结果
            if save_result:
                self.save_to_file(result)
            
            return result
    

    
    def _generate_mock(self, text: str, voice_id: str, speed: float, pitch: float) -> TTSResult:
        """模拟语音生成（用于测试或模型不可用时）"""
        import time
        start_time = time.time()
        
        # VoxCPM生成的是16000Hz采样率的音频
        sample_rate = 16000
        duration = max(1.0, len(text) * 0.1)  # 最小1秒，根据文本长度估算
        
        # 生成带有调制的音频，使听起来更像语音
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # 基础频率，根据voice_id调整
        base_freq = 220
        if voice_id == "kiana":
            base_freq = 210  # 琪亚娜：稍高的频率
        elif voice_id == "mei":
            base_freq = 200  # 芽衣：稍低的频率
        elif voice_id == "bronya":
            base_freq = 190  # 布洛妮娅：更低的频率
        elif voice_id == "seele":
            base_freq = 205  # 希儿：中等频率
        
        # 应用音调调整
        base_freq *= pitch
        
        # 添加一些频率变化模拟语调和情感
        freq_variation = 15 * np.sin(2 * np.pi * 2 * t / duration)
        freq = base_freq + freq_variation
        
        # 生成音频，应用语速调整
        audio_data = np.sin(2 * np.pi * freq * t * speed) * 0.05
        
        # 添加包络，使开始和结束更平滑
        envelope = np.ones_like(t)
        attack_len = int(0.05 * sample_rate)  # 5% attack
        release_len = int(0.1 * sample_rate)  # 10% release
        
        envelope[:attack_len] = np.linspace(0, 1, attack_len)
        envelope[-release_len:] = np.linspace(1, 0, release_len)
        
        audio_data *= envelope
        
        processing_time = time.time() - start_time
        
        return TTSResult(
            audio_data=audio_data.astype(np.float32),
            sample_rate=sample_rate,
            text=text,
            voice_id=voice_id,
            processing_time=processing_time
        )
    

    
    def to_base64(self, result: TTSResult) -> str:
        """
        将语音结果转换为Base64字符串
        
        Args:
            result: TTS结果
            
        Returns:
            Base64编码的音频数据
        """
        try:
            import soundfile as sf
            import io
            
            buffer = io.BytesIO()
            sf.write(buffer, result.audio_data, result.sample_rate, format='WAV')
            buffer.seek(0)
            
            audio_bytes = buffer.read()
            return base64.b64encode(audio_bytes).decode('utf-8')
            
        except ImportError:
            # 使用wave模块作为备用
            import wave
            import io
            
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(result.sample_rate)
                
                # 转换为16-bit整数
                audio_int16 = (result.audio_data * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            buffer.seek(0)
            audio_bytes = buffer.read()
            return base64.b64encode(audio_bytes).decode('utf-8')
    
    def list_available_voices(self) -> Dict[str, Any]:
        """
        获取可用的语音列表（崩坏3角色语音）
        
        Returns:
            语音列表信息
        """
        return {
            "voices": [
                {
                    "id": "elysia",
                    "name": "爱莉希雅",
                    "description": "爱莉希雅语音（默认参考音频）",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": True
                },
                {
                    "id": "kiana",
                    "name": "琪亚娜·卡斯兰娜",
                    "description": "主角琪亚娜语音，活泼开朗",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": False
                },
                {
                    "id": "mei",
                    "name": "雷电芽衣",
                    "description": "雷电芽衣语音，温柔稳重",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": False
                },
                {
                    "id": "bronya",
                    "name": "布洛妮娅·扎伊切克",
                    "description": "布洛妮娅语音，冷静理性",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": False
                },
                {
                    "id": "seele",
                    "name": "希儿·芙乐艾",
                    "description": "希儿语音，温柔内向",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": False
                },
                {
                    "id": "theresa",
                    "name": "德丽莎·阿波卡利斯",
                    "description": "德丽莎语音，活泼可爱",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": False
                },
                {
                    "id": "fu_hua",
                    "name": "符华",
                    "description": "符华语音，沉稳冷静",
                    "gender": "female",
                    "age_group": "young",
                    "has_reference": False
                },
                {
                    "id": "default",
                    "name": "默认语音",
                    "description": "通用语音（使用爱莉希雅参考音频）",
                    "gender": "neutral",
                    "age_group": "adult",
                    "has_reference": True
                }
            ],
            "note": "当前只有爱莉希雅语音有参考音频。其他角色需要收集游戏内语音片段作为参考音频。"
        }
    
    def generate_with_emotion(self, text: str, voice_id: str, emotion: str = "neutral", 
                             save_result: bool = False) -> TTSResult:
        """
        生成带有情感的语音
        
        Args:
            text: 文本
            voice_id: 语音ID
            emotion: 情感类型 (neutral, happy, sad, angry, surprised)
            save_result: 是否保存生成的音频到文件
            
        Returns:
            语音结果
        """
        # 根据情感调整参数
        # 注意：VoxCPM本身不支持直接调整语速和音调，这些参数主要用于模拟模式
        emotion_params = {
            "neutral": {"speed": 1.0, "pitch": 1.0},
            "happy": {"speed": 1.05, "pitch": 1.05},  # 轻微提高
            "sad": {"speed": 0.95, "pitch": 0.95},   # 轻微降低
            "angry": {"speed": 1.1, "pitch": 1.03},  # 稍快稍高
            "surprised": {"speed": 1.15, "pitch": 1.08}  # 更快更高
        }
        
        params = emotion_params.get(emotion, emotion_params["neutral"])
        
        return self.generate(
            text=text,
            voice_id=voice_id,
            speed=params["speed"],
            pitch=params["pitch"],
            save_result=save_result
        )