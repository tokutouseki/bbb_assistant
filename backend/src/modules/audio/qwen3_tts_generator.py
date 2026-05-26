#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-TTS 语音生成器 (Base 模型)

使用 Qwen3-TTS-12Hz-1.7B-Base 进行 ICL 语音克隆（从 3 秒参考音频克隆声音）。
支持 10 种语言，高质量、自然流畅的语音输出。

使用方法：
  from src.modules.audio.qwen3_tts_generator import Qwen3TTSGenerator

  tts = Qwen3TTSGenerator(device="cuda:0")
  result = tts.generate_with_reference(
      text="你好，这是Qwen3-TTS生成的语音",
      reference_audio="ref.wav",
      ref_text="参考音频的文本"
  )
"""

import os
import json as _json
import logging
import time
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 角色名 → 声音风格描述（供 generate() 快速指定角色用）
CHARACTER_VOICE_STYLES = {
    "爱莉希雅": "温柔甜美的少女声音，带有粉色气息，语调轻柔",
    "琪亚娜": "活泼开朗的少女声音，充满活力和正义感",
    "雷电芽衣": "温柔端庄的女性声音，带有成熟气质",
    "布洛妮娅": "冷静沉稳的少女声音，语速稍慢，带有机械感",
}


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
    """Qwen3-TTS 语音生成器 (Base 模型，ICL 语音克隆)"""

    SUPPORTED_LANGUAGES = [
        "Chinese", "English", "Japanese", "Korean",
        "German", "French", "Russian", "Portuguese",
        "Spanish", "Italian"
    ]

    def __init__(self, model_path: str = None, device: str = "cuda:0",
                 output_dir: str = None, dtype: str = "bfloat16"):
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

    def _get_default_model_path(self) -> str:
        env_path = os.environ.get("QWEN3_TTS_MODEL_PATH")
        if env_path:
            normalized_path = self._normalize_model_path(env_path)
            if os.path.exists(normalized_path):
                logger.info(f"从环境变量获取模型路径: {normalized_path}")
                return normalized_path

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

        possible_paths = [
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS" / "models" / "Qwen" / "Qwen3-TTS-12Hz-1___7B-Base",
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS" / "models" / "Qwen" / "Qwen3-TTS-12Hz-1.7B-Base",
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS" / "models" / "Qwen3-TTS-12Hz-1.7B-Base",
            Path(__file__).parent.parent.parent.parent.parent / "Qwen3-TTS",
            Path.home() / ".cache" / "huggingface" / "hub" / "models--Qwen--Qwen3-TTS-12Hz-1.7B-Base",
        ]

        for path in possible_paths:
            normalized_path = self._normalize_model_path(str(path))
            if os.path.exists(normalized_path):
                logger.info(f"找到模型路径: {normalized_path}")
                return normalized_path

        logger.warning("未找到本地模型，将尝试从HuggingFace下载")
        return "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

    def _normalize_model_path(self, model_path: str) -> str:
        base = Path(model_path)
        if (base / "config.json").exists():
            return str(base)

        candidates = [
            base / "models" / "Qwen" / "Qwen3-TTS-12Hz-1___7B-Base",
            base / "models" / "Qwen" / "Qwen3-TTS-12Hz-1.7B-Base",
            base / "models" / "Qwen3-TTS-12Hz-1.7B-Base",
            base / "Qwen3-TTS-12Hz-1___7B-Base",
            base / "Qwen3-TTS-12Hz-1.7B-Base",
        ]
        for candidate in candidates:
            if (candidate / "config.json").exists():
                logger.info(f"从目录自动解析Qwen3-TTS模型路径: {candidate}")
                return str(candidate)
        return str(base)

    def _initialize(self):
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
                logger.warning("qwen_tts包未安装")
                logger.info("安装方法: pip install qwen-tts")

        except Exception as e:
            logger.error(f"模型初始化失败: {e}")

    def generate(self, text: str, voice_style: str = "爱莉希雅",
                 language: str = "Chinese", speed: float = None,
                 custom_description: str = None) -> Qwen3TTSResult:
        """生成语音，内部使用 ICL 语音克隆。

        voice_style 可以是 CHARACTER_VOICE_STYLES 中的角色名，
        也可以是 reference_audio 索引中的角色名。"""
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"不支持的语言 '{language}'，使用默认 'Chinese'")
            language = "Chinese"

        ref_audio, ref_text = self._resolve_character_ref(voice_style)
        return self.generate_with_reference(
            text=text,
            reference_audio=ref_audio,
            language=language,
            ref_text=ref_text,
        )

    def generate_with_reference(self, text: str, reference_audio: str,
                               language: str = "Chinese", ref_text: str = None) -> Qwen3TTSResult:
        """使用参考音频进行 ICL 语音克隆。

        Args:
            text: 要合成的文本
            reference_audio: 参考音频路径
            language: 语言
            ref_text: 参考音频对应的文本（可选，提供则质量更好）
        """
        start_time = time.time()

        if not self.initialized:
            raise RuntimeError("Qwen3-TTS 模型未初始化")

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

        processing_time = time.time() - start_time
        logger.info(f"语音克隆完成，耗时: {processing_time:.2f}s")

        return Qwen3TTSResult(
            audio_data=audio_data,
            sample_rate=sr,
            text=text,
            voice_style="cloned",
            processing_time=processing_time,
            language=language
        )

    def _resolve_character_ref(self, character_name: str) -> Tuple[str, str]:
        """将角色名解析为 (audio_path, ref_text)。"""
        try:
            index_path = os.path.join(
                os.path.dirname(__file__), "reference_audio", "index.json"
            )
            with open(index_path, "r", encoding="utf-8") as f:
                index = _json.load(f)

            if character_name in index:
                entry = index[character_name]
                return entry["audio_path"], entry.get("ref_text", "")

            for name, entry in index.items():
                if character_name in name or name in character_name:
                    return entry["audio_path"], entry.get("ref_text", "")

            first = next(iter(index.values()))
            return first["audio_path"], first.get("ref_text", "")
        except Exception:
            raise RuntimeError(f"找不到角色 '{character_name}' 的参考音频")

    def save_to_file(self, result: Qwen3TTSResult, filepath: str = None) -> str:
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
        return self.SUPPORTED_LANGUAGES.copy()

    def get_voice_styles(self) -> Dict[str, str]:
        """返回可用角色列表（从 reference_audio 索引加载）。"""
        try:
            index_path = os.path.join(
                os.path.dirname(__file__), "reference_audio", "index.json"
            )
            with open(index_path, "r", encoding="utf-8") as f:
                index = _json.load(f)

            styles = {}
            for name in index:
                desc = CHARACTER_VOICE_STYLES.get(name, f"{name}的声音")
                styles[name] = desc
            return styles
        except Exception:
            return CHARACTER_VOICE_STYLES.copy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Testing Qwen3-TTS generator (Base model, voice clone)...")

    tts = Qwen3TTSGenerator(device="cuda:0")

    print(f"Supported languages: {tts.get_supported_languages()}")
    print(f"Available characters: {list(tts.get_voice_styles().keys())[:10]}...")

    result = tts.generate_with_reference(
        text="舰长你好，测试语音克隆。",
        reference_audio=tts._resolve_character_ref("爱莉希雅")[0],
        language="Chinese",
        ref_text="愿时光永驻此刻",
    )

    print(f"Success! duration={len(result.audio_data)/result.sample_rate:.2f}s, "
          f"time={result.processing_time:.2f}s")

    output_path = tts.save_to_file(result)
    print(f"Saved: {output_path}")
