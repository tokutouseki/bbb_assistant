# -*- coding: utf-8 -*-
"""
FunASR 快速测试脚本
测试三种ASR模式的基本功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from src.modules.audio import create_asr_processor, ASRMode

def test_sensevoice():
    """测试SenseVoice模式"""
    print("\n" + "="*60)
    print("测试1: SenseVoice模式 - 高精度识别+情感检测")
    print("="*60)
    
    processor = create_asr_processor(
        mode="sensevoice",
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        enable_punc=False,
    )
    
    test_audio = r"d:\TokusCode\bbb_assistant\SenseVoiceSmall\example\zh.mp3"
    
    if os.path.exists(test_audio):
        result = processor.transcribe_file(test_audio)
        print(f"识别结果: {result.text}")
        print(f"情感: {result.emotion}")
        print(f"语言: {result.language}")
        print(f"处理时间: {result.processing_time:.3f}s")
    else:
        print(f"测试文件不存在: {test_audio}")
    
    return processor


def test_streaming():
    """测试Streaming模式"""
    print("\n" + "="*60)
    print("测试2: Streaming模式 - 低延迟流式识别")
    print("="*60)
    
    processor = create_asr_processor(
        mode="streaming",
        device="cuda:0" if torch.cuda.is_available() else "cpu",
    )
    
    import soundfile as sf
    test_audio = r"d:\TokusCode\bbb_assistant\SenseVoiceSmall\example\zh.mp3"
    
    if os.path.exists(test_audio):
        audio_data, sample_rate = sf.read(test_audio)
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]
        
        chunk_size = int(0.6 * sample_rate)
        
        def audio_gen():
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i+chunk_size]
        
        results = list(processor.process_audio_stream(audio_gen(), sample_rate))
        print(f"收到 {len(results)} 个识别结果")
        for i, r in enumerate(results[-3:], 1):
            print(f"结果{i}: {r.text}")
    else:
        print(f"测试文件不存在: {test_audio}")
    
    return processor


def test_full_duplex():
    """测试Full Duplex模式"""
    print("\n" + "="*60)
    print("测试3: Full Duplex模式 - 全双工实时对话")
    print("="*60)
    
    processor = create_asr_processor(
        mode="full_duplex",
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        enable_2pass=True,
        enable_vad=True,
        enable_punc=False,
    )
    
    results_received = []
    
    def on_result(result):
        status = "最终" if result.is_final else "实时"
        results_received.append(result)
        print(f"[{status}] {result.text}")
    
    def on_vad(vad):
        if vad.is_speech:
            print("[VAD] 检测到语音")
    
    processor.set_callbacks(on_result=on_result, on_vad=on_vad)
    
    import soundfile as sf
    test_audio = r"d:\TokusCode\bbb_assistant\SenseVoiceSmall\example\zh.mp3"
    
    if os.path.exists(test_audio):
        audio_data, sample_rate = sf.read(test_audio)
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]
        
        chunk_size = int(0.6 * sample_rate)
        
        def audio_gen():
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i+chunk_size]
        
        list(processor.process_audio_stream(audio_gen(), sample_rate))
        print(f"共收到 {len(results_received)} 个结果")
    else:
        print(f"测试文件不存在: {test_audio}")
    
    return processor


def main():
    print("="*60)
    print("FunASR 全双工实时ASR系统测试")
    print("="*60)
    print(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"显卡: {torch.cuda.get_device_name(0)}")
    
    try:
        test_sensevoice()
    except Exception as e:
        print(f"SenseVoice测试失败: {e}")
    
    try:
        test_streaming()
    except Exception as e:
        print(f"Streaming测试失败: {e}")
    
    try:
        test_full_duplex()
    except Exception as e:
        print(f"Full Duplex测试失败: {e}")
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)


if __name__ == "__main__":
    main()
