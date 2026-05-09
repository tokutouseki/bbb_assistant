from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import base64
import tempfile
import time
import numpy as np
import logging
import os

# 导入配置
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 获取配置
settings = get_settings()

# 初始化变量
asr_processor = None
default_tts_generator = None
voxcpm_tts_generator = None

# 仅在启用音频功能时初始化
if settings.enable_audio:
    # 使用相对于项目根目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
    
    if settings.enable_asr:
        try:
            from ..modules.audio.asr_processor import ASRProcessor, ASRResult
            logger.info("正在初始化 ASR 处理器...")
            asr_processor = ASRProcessor(
                model_path=os.path.join(project_root, "SenseVoiceSmall"), 
                device="cuda:0",
                output_dir=os.path.join(project_root, "outputs", "asr_transcriptions")
            )
            logger.info("ASR 处理器初始化完成")
        except Exception as e:
            logger.warning(f"ASR 处理器初始化失败（已禁用）: {e}")
            asr_processor = None
    
    if settings.enable_tts:
        try:
            from ..modules.audio.tts_generator import TTSGenerator, TTSResult
            from ..modules.audio.qwen3_tts_generator import Qwen3TTSGenerator, Qwen3TTSResult
            logger.info("正在初始化 TTS 生成器...")
            default_tts_generator = Qwen3TTSGenerator(
                model_path=os.path.join(project_root, "Qwen3-TTS"), 
                device="cuda:0",
                output_dir=os.path.join(project_root, "outputs", "qwen3_tts")
            )
            voxcpm_tts_generator = TTSGenerator(
                model_path=os.path.join(project_root, "VoxCPM-0.5B"), 
                device="cuda:0",
                output_dir=os.path.join(project_root, "outputs", "tts_audio")
            )
            logger.info("TTS 生成器初始化完成")
        except Exception as e:
            logger.warning(f"TTS 生成器初始化失败（已禁用）: {e}")
            default_tts_generator = None
            voxcpm_tts_generator = None
else:
    logger.info("音频功能已禁用，跳过 ASR/TTS 初始化")

# 获取TTS生成器的函数
def get_tts_generator(tts_engine: str = "qwen3") -> object:
    """获取指定的TTS生成器"""
    if tts_engine == "voxcpm" and voxcpm_tts_generator is not None:
        return voxcpm_tts_generator
    elif default_tts_generator is not None:
        return default_tts_generator
    else:
        return None

class ASRRequest(BaseModel):
    audio_format: str = Field(default="wav", description="音频格式: wav, mp3, flac")
    language: str = Field(default="zh", description="语言代码: zh, en")
    sample_rate: Optional[int] = Field(default=16000, description="采样率")

class ASRResponse(BaseModel):
    text: str = Field(..., description="识别文本")
    confidence: float = Field(..., description="置信度")
    processing_time: float = Field(..., description="处理耗时（秒）")

class TTSRequest(BaseModel):
    text: str = Field(..., description="合成文本")
    voice_id: str = Field(default="温柔女声", description="语音ID或声音风格")
    speed: float = Field(default=1.0, description="语速")
    pitch: float = Field(default=1.0, description="音调")
    tts_engine: str = Field(default="qwen3", description="TTS引擎: qwen3, voxcpm")
    language: str = Field(default="Chinese", description="语言")

class TTSResponse(BaseModel):
    audio_base64: str = Field(..., description="Base64编码的音频数据")
    format: str = Field(default="wav", description="音频格式")
    sample_rate: int = Field(default=24000, description="采样率")
    tts_engine: str = Field(default="qwen3", description="使用的TTS引擎")

class VoiceCloneRequest(BaseModel):
    reference_audio: UploadFile = File(...)
    text: str = Field(..., description="要合成的文本")
    reference_text: Optional[str] = Field(None, description="参考音频对应的文本（可选，如果为空将尝试自动识别）")
    similarity: float = Field(default=0.7, description="语音相似度目标")
    voice_id: str = Field(default="cloned", description="生成的语音ID")

@router.post("/asr", response_model=ASRResponse)
async def speech_recognition(
    audio: UploadFile = File(...),
    request: Optional[ASRRequest] = None
):
    """
    语音识别（ASR）使用SenseVoiceSmall模型
    """
    # 检查 ASR 是否启用
    if not settings.enable_audio or not settings.enable_asr or asr_processor is None:
        raise HTTPException(status_code=503, detail="ASR 功能已禁用")
    
    start_time = time.time()
    
    try:
        # 读取上传的音频文件内容
        audio_content = await audio.read()
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_content)
            tmp_path = tmp_file.name
        
        try:
            # 使用ASR处理器进行识别
            language = request.language if request else "zh"
            result = asr_processor.transcribe_file(tmp_path, language=language)
            
            return ASRResponse(
                text=result.text,
                confidence=result.confidence,
                processing_time=result.processing_time
            )
        finally:
            # 清理临时文件
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        # 如果出错，返回模拟结果
        processing_time = time.time() - start_time
        return ASRResponse(
            text=f"语音识别出错: {str(e)}",
            confidence=0.0,
            processing_time=processing_time
        )

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """
    文本转语音（TTS）使用Qwen3-TTS模型（默认）或VoxCPM模型
    """
    # 检查 TTS 是否启用
    if not settings.enable_audio or not settings.enable_tts or default_tts_generator is None:
        raise HTTPException(status_code=503, detail="TTS 功能已禁用")
    
    start_time = time.time()
    
    try:
        # 获取指定的TTS生成器
        tts_generator = get_tts_generator(request.tts_engine)
        if tts_generator is None:
            raise HTTPException(status_code=503, detail="指定的 TTS 引擎不可用")
        
        # 根据TTS引擎类型生成语音
        if request.tts_engine == "voxcpm":
            # 使用VoxCPM生成语音
            result = tts_generator.generate(
                text=request.text,
                voice_id=request.voice_id,
                speed=request.speed,
                pitch=request.pitch
            )
            
            # 将音频数据转换为base64
            audio_base64 = tts_generator.to_base64(result)
            sample_rate = result.sample_rate
        else:
            # 使用Qwen3-TTS生成语音
            result = tts_generator.generate(
                text=request.text,
                voice_style=request.voice_id,
                language=request.language
            )
            
            # 将音频数据转换为base64
            import io
            import soundfile as sf
            buffer = io.BytesIO()
            sf.write(buffer, result.audio_data, result.sample_rate, format='WAV')
            buffer.seek(0)
            audio_bytes = buffer.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            sample_rate = result.sample_rate
        
        return TTSResponse(
            audio_base64=audio_base64,
            format="wav",
            sample_rate=sample_rate,
            tts_engine=request.tts_engine
        )
        
    except Exception as e:
        # 如果出错，返回模拟音频
        logger.error(f"TTS生成失败: {e}")
        
        # 生成模拟音频作为回退
        sample_rate = 24000
        duration = max(2.0, len(request.text) * 0.1)
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.05
        
        # 转换为base64
        import io
        import soundfile as sf
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)
        audio_bytes = buffer.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return TTSResponse(
            audio_base64=audio_base64,
            format="wav",
            sample_rate=sample_rate,
            tts_engine=request.tts_engine
        )

@router.post("/clone")
async def voice_clone(request: VoiceCloneRequest):
    """
    语音克隆：根据参考音频生成相似语音
    """
    # 检查 TTS 是否启用
    if not settings.enable_audio or not settings.enable_tts or voxcpm_tts_generator is None:
        raise HTTPException(status_code=503, detail="语音克隆功能已禁用")
    
    start_time = time.time()
    
    try:
        # 读取参考音频文件
        audio_content = await request.reference_audio.read()
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_content)
            reference_audio_path = tmp_file.name
        
        try:
            # 如果没有提供参考文本，尝试使用ASR识别
            prompt_text = request.reference_text
            if not prompt_text and asr_processor is not None:
                logger.info("未提供参考文本，尝试使用ASR识别参考音频内容")
                asr_result = asr_processor.transcribe_file(reference_audio_path, language="auto")
                prompt_text = asr_result.text
                logger.info(f"ASR识别到的参考文本: {prompt_text}")
            
            # 使用TTS生成器进行语音克隆
            result = voxcpm_tts_generator.generate(
                text=request.text,
                voice_id=request.voice_id,
                speed=1.0,
                pitch=1.0,
                prompt_audio=reference_audio_path,
                prompt_text=prompt_text
            )
            
            # 将音频数据转换为base64
            audio_base64 = voxcpm_tts_generator.to_base64(result)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "message": "语音克隆成功",
                "voice_id": request.voice_id,
                "similarity": request.similarity,
                "audio_base64": audio_base64,
                "sample_rate": result.sample_rate,
                "processing_time": processing_time
            }
            
        finally:
            # 清理临时文件
            import os
            if os.path.exists(reference_audio_path):
                os.unlink(reference_audio_path)
                
    except Exception as e:
        logger.error(f"语音克隆失败: {e}")
        processing_time = time.time() - start_time
        
        return {
            "success": False,
            "message": f"语音克隆失败: {str(e)}",
            "processing_time": processing_time
        }

@router.get("/voices")
async def list_available_voices(tts_engine: str = Query("qwen3", description="TTS引擎: qwen3, voxcpm")):
    """
    获取可用的语音列表（崩坏3角色语音）
    """
    # 检查 TTS 是否启用
    if not settings.enable_audio or not settings.enable_tts:
        raise HTTPException(status_code=503, detail="TTS 功能已禁用")
    
    try:
        if tts_engine == "voxcpm" and voxcpm_tts_generator is not None:
            # 返回VoxCPM的语音列表
            return voxcpm_tts_generator.list_available_voices()
        elif tts_engine == "qwen3" and default_tts_generator is not None:
            # 返回Qwen3-TTS的声音风格列表
            voice_styles = default_tts_generator.get_voice_styles()
            voices = []
            for style_id, description in voice_styles.items():
                voices.append({
                    "id": style_id,
                    "name": style_id,
                    "description": description
                })
            return {
                "voices": voices,
                "tts_engine": "qwen3",
                "note": "Qwen3-TTS支持通过自然语言描述自定义声音风格"
            }
        else:
            raise HTTPException(status_code=503, detail="指定的 TTS 引擎不可用")
    except Exception as e:
        logger.error(f"获取语音列表失败: {e}")
        # 返回默认列表作为回退
        if tts_engine == "voxcpm":
            return {
                "voices": [
                    {"id": "elysia", "name": "爱莉希雅", "description": "爱莉希雅语音（默认参考音频）"},
                    {"id": "kiana", "name": "琪亚娜", "description": "主角琪亚娜语音"},
                    {"id": "mei", "name": "芽衣", "description": "雷电芽衣语音"},
                    {"id": "bronya", "name": "布洛妮娅", "description": "布洛妮娅语音"},
                    {"id": "seele", "name": "希儿", "description": "希儿语音"},
                    {"id": "default", "name": "默认语音", "description": "通用语音"}
                ],
                "tts_engine": "voxcpm"
            }
        else:
            return {
                "voices": [
                    {"id": "温柔女声", "name": "温柔女声", "description": "温柔的成年女性声音，语速适中，音调柔和"},
                    {"id": "活力女声", "name": "活力女声", "description": "活泼开朗的年轻女性声音，语速较快，充满活力"},
                    {"id": "沉稳男声", "name": "沉稳男声", "description": "沉稳的成年男性声音，语速平稳，音调低沉"},
                    {"id": "可爱萝莉", "name": "可爱萝莉", "description": "撒娇稚嫩的萝莉女声，音调偏高且起伏明显"},
                    {"id": "专业客服", "name": "专业客服", "description": "专业的客服女声，语速适中，礼貌亲切"},
                    {"id": "新闻播报", "name": "新闻播报", "description": "标准的新闻播报声音，语速平稳，吐字清晰"},
                    {"id": "爱莉希雅", "name": "爱莉希雅", "description": "温柔甜美的少女声音，带有粉色气息，语调轻柔"},
                    {"id": "琪亚娜", "name": "琪亚娜", "description": "活泼开朗的少女声音，充满活力和正义感"},
                    {"id": "雷电芽衣", "name": "雷电芽衣", "description": "温柔端庄的女性声音，带有成熟气质"},
                    {"id": "布洛妮娅", "name": "布洛妮娅", "description": "冷静沉稳的少女声音，语速稍慢，带有机械感"}
                ],
                "tts_engine": "qwen3",
                "note": "Qwen3-TTS支持通过自然语言描述自定义声音风格"
            }