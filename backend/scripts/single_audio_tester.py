#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单文件音频处理器 - 测试单个音频文件的ASR和TTS处理

功能：
1. 支持指定音频文件路径和输出目录
2. 支持自动识别角色或手动指定角色ID
3. 支持模拟模式（不加载真实模型）
4. 生成详细的处理报告

使用方法：
  python single_audio_tester.py --audio <音频文件路径> [选项]

示例：
  python single_audio_tester.py --audio "d:\TokusCode\bbb_assistant\to_clone_test\德丽莎-别偷懒！.wav"
  python single_audio_tester.py --audio "d:\TokusCode\bbb_assistant\to_clone_test\德丽莎-别偷懒！.wav" --voice theresa --output outputs/single_test
  python single_audio_tester.py --audio "d:\TokusCode\bbb_assistant\to_clone_test\德丽莎-别偷懒！.wav" --simulated
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入真实处理器，如果失败则使用模拟模式
try:
    from src.modules.audio.asr_processor import ASRProcessor
    from src.modules.audio.tts_generator import TTSGenerator
    REAL_MODELS_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入真实模型模块，将使用模拟模式: {e}")
    REAL_MODELS_AVAILABLE = False

class MockASRProcessor:
    """模拟ASR处理器，用于测试"""
    def __init__(self, device="cpu"):
        self.device = device
        self.model = "mock_model"
    
    def transcribe_file(self, audio_path, language="zh", save_result=False):
        from dataclasses import dataclass
        
        @dataclass
        class MockResult:
            text: str = "这是模拟的ASR转录文本。原始音频文件为：" + Path(audio_path).name
            confidence: float = 0.95
            language: str = language
            processing_time: float = 0.5
        
        return MockResult()

class MockTTSGenerator:
    """模拟TTS生成器，用于测试"""
    def __init__(self, device="cpu"):
        self.device = device
        self.model = "mock_model"
    
    def generate(self, text, voice_id, prompt_audio=None, prompt_text=None, save_result=False):
        from dataclasses import dataclass
        import numpy as np
        
        @dataclass
        class MockResult:
            audio_data: np.ndarray = np.random.randn(16000)  # 1秒的随机音频
            sample_rate: int = 16000
            voice_id: str = voice_id
            processing_time: float = 1.0
        
        return MockResult()
    
    def save_to_file(self, result, output_path):
        from scipy.io import wavfile
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(output_path, result.sample_rate, result.audio_data.astype(np.float32))
        return str(output_path)

def load_voice_mapping(mapping_file: Optional[str] = None) -> Dict[str, str]:
    """
    加载语音映射配置
    
    Args:
        mapping_file: 映射文件路径，如果为None则使用默认映射
    
    Returns:
        字典：文件名前缀 -> 角色ID
    """
    default_mapping = {
        "德丽莎": "theresa",
        "月下誓约": "theresa",
        "Da_Yue_Xia": "theresa",
        "朔夜观星": "elysia",
        "渡尘之羽": "elysia",
        "识之律者": "himeko",
        "迷城骇兔": "bronya",
        "KianaData_SVC_Raw": "kiana"
    }
    
    if mapping_file and Path(mapping_file).exists():
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                custom_mapping = json.load(f)
            # 合并映射，自定义映射优先级更高
            merged_mapping = {**default_mapping, **custom_mapping}
            print(f"加载自定义语音映射: {mapping_file}")
            return merged_mapping
        except Exception as e:
            print(f"警告: 无法加载自定义语音映射文件 {mapping_file}: {e}")
            print("使用默认语音映射")
            return default_mapping
    
    return default_mapping

def detect_voice_id_from_filename(filename: str, voice_mapping: Dict[str, str]) -> str:
    """
    根据文件名检测角色ID
    
    Args:
        filename: 音频文件名
        voice_mapping: 语音映射字典
    
    Returns:
        角色ID，如果未识别则返回"unknown"
    """
    filename_lower = filename.lower()
    for prefix, voice_id in voice_mapping.items():
        if prefix.lower() in filename_lower:
            return voice_id
    
    # 尝试匹配常见模式
    if "德丽莎" in filename or "theresa" in filename_lower:
        return "theresa"
    elif "月下" in filename or "yuexia" in filename_lower:
        return "theresa"
    elif "朔夜" in filename or "suoye" in filename_lower:
        return "elysia"
    elif "渡尘" in filename or "duchen" in filename_lower:
        return "elysia"
    elif "识之律者" in filename or "shizhilvzhe" in filename_lower:
        return "himeko"
    elif "迷城骇兔" in filename or "michenghaitu" in filename_lower:
        return "bronya"
    elif "kiana" in filename_lower:
        return "kiana"
    
    return "unknown"

def process_single_audio(audio_path: str, voice_id: Optional[str] = None, 
                         output_dir: Optional[str] = None, 
                         simulated: bool = False, 
                         voice_mapping_file: Optional[str] = None,
                         device: str = "cpu") -> Dict[str, Any]:
    """
    处理单个音频文件
    
    Args:
        audio_path: 音频文件路径
        voice_id: 角色ID，如果为None则自动检测
        output_dir: 输出目录，如果为None则使用默认目录
        simulated: 是否使用模拟模式
        voice_mapping_file: 语音映射文件路径
        device: 计算设备（cpu/cuda）
    
    Returns:
        处理结果字典
    """
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    # 创建输出目录
    if output_dir is None:
        output_dir = project_root / "outputs" / "single_test"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载语音映射
    voice_mapping = load_voice_mapping(voice_mapping_file)
    
    # 检测角色ID
    if voice_id is None:
        voice_id = detect_voice_id_from_filename(audio_file.name, voice_mapping)
        print(f"自动检测角色ID: {voice_id}")
    
    # 初始化处理器
    use_simulated = simulated or not REAL_MODELS_AVAILABLE
    
    if use_simulated:
        print("使用模拟模式")
        asr_processor = MockASRProcessor(device=device)
        tts_generator = MockTTSGenerator(device=device)
    else:
        print(f"使用真实模型 (设备: {device})")
        asr_processor = ASRProcessor(device=device)
        tts_generator = TTSGenerator(device=device)
    
    # ASR转录
    print(f"\n开始ASR转录: {audio_file.name}")
    asr_result = asr_processor.transcribe_file(
        audio_path=str(audio_file),
        language="zh",
        save_result=False
    )
    
    # TTS合成
    print(f"\n开始TTS合成 (角色: {voice_id})")
    tts_result = tts_generator.generate(
        text=asr_result.text,
        voice_id=voice_id,
        prompt_audio=str(audio_file),
        prompt_text=asr_result.text,
        save_result=False
    )
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存结果
    asr_text_path = output_dir / f"asr_{timestamp}_{audio_file.stem}.txt"
    with open(asr_text_path, 'w', encoding='utf-8') as f:
        f.write(asr_result.text)
    
    tts_audio_path = output_dir / f"tts_{timestamp}_{voice_id}_{audio_file.stem}.wav"
    if hasattr(tts_generator, 'save_to_file'):
        saved_path = tts_generator.save_to_file(tts_result, str(tts_audio_path))
    else:
        # 模拟模式保存
        from scipy.io import wavfile
        import numpy as np
        wavfile.write(tts_audio_path, tts_result.sample_rate, tts_result.audio_data.astype(np.float32))
        saved_path = str(tts_audio_path)
    
    # 生成报告
    report = {
        "audio_file": str(audio_file),
        "voice_id": voice_id,
        "asr_text": asr_result.text,
        "asr_confidence": asr_result.confidence if hasattr(asr_result, 'confidence') else None,
        "asr_language": asr_result.language if hasattr(asr_result, 'language') else None,
        "asr_processing_time": asr_result.processing_time if hasattr(asr_result, 'processing_time') else None,
        "tts_sample_rate": tts_result.sample_rate,
        "tts_audio_length": len(tts_result.audio_data) if hasattr(tts_result.audio_data, '__len__') else None,
        "tts_processing_time": tts_result.processing_time if hasattr(tts_result, 'processing_time') else None,
        "output_files": {
            "asr_text": str(asr_text_path),
            "tts_audio": str(tts_audio_path)
        },
        "processing_mode": "simulated" if use_simulated else "real",
        "timestamp": timestamp
    }
    
    # 保存报告
    report_path = output_dir / f"report_{timestamp}_{audio_file.stem}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

def main():
    parser = argparse.ArgumentParser(description="单文件音频处理器 - 测试单个音频文件的ASR和TTS处理")
    parser.add_argument("--audio", "-a", required=True, help="输入音频文件路径")
    parser.add_argument("--voice", "-v", help="角色ID (例如: theresa, elysia, kiana)。如果未指定，则根据文件名自动检测")
    parser.add_argument("--output", "-o", help="输出目录路径，默认为 outputs/single_test/")
    parser.add_argument("--simulated", "-s", action="store_true", help="使用模拟模式（不加载真实模型）")
    parser.add_argument("--voice-mapping", "-m", help="自定义语音映射JSON文件路径")
    parser.add_argument("--device", "-d", default="cpu", choices=["cpu", "cuda"], help="计算设备 (默认: cpu)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("单文件音频处理器")
    print("=" * 60)
    
    try:
        report = process_single_audio(
            audio_path=args.audio,
            voice_id=args.voice,
            output_dir=args.output,
            simulated=args.simulated,
            voice_mapping_file=args.voice_mapping,
            device=args.device
        )
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"音频文件: {report['audio_file']}")
        print(f"角色ID: {report['voice_id']}")
        print(f"ASR文本: {report['asr_text']}")
        print(f"ASR置信度: {report['asr_confidence']}")
        print(f"输出文件:")
        print(f"  ASR文本: {report['output_files']['asr_text']}")
        print(f"  TTS音频: {report['output_files']['tts_audio']}")
        print(f"处理模式: {report['processing_mode']}")
        print(f"报告文件: outputs/single_test/report_{report['timestamp']}_{Path(args.audio).stem}.json")
        
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()