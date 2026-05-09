# -*- coding: utf-8 -*-
"""
FunASR YueXiaShiYue音频批量识别验证脚本
记录详细时间统计
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import glob

print("="*70)
print("FunASR YueXiaShiYue 音频批量识别验证")
print("="*70)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"显卡: {torch.cuda.get_device_name(0)}")
print()

# 导入模块
total_import_time = time.time()
from src.modules.audio import create_asr_processor
import_time = time.time() - total_import_time
print(f"模块导入时间: {import_time:.3f}s")
print()

# 音频目录
AUDIO_DIR = r"d:\TokusCode\bbb_assistant\YueXiaShiYue"
OUTPUT_DIR = r"d:\TokusCode\bbb_assistant\outputs\asr_validation"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 获取音频文件
audio_files = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.wav")))
print(f"找到 {len(audio_files)} 个音频文件")
print()

# 创建处理器
print("加载ASR模型...")
model_load_start = time.time()
processor = create_asr_processor(
    mode="sensevoice",
    device="cuda:0" if torch.cuda.is_available() else "cpu",
    enable_punc=False,
)
model_load_time = time.time() - model_load_start
print(f"模型加载时间: {model_load_time:.3f}s")
print()

# 批量识别
print("="*70)
print("开始批量识别...")
print("="*70)

results = []
total_process_time = 0
total_audio_duration = 0

import soundfile as sf

overall_start = time.time()

for i, audio_path in enumerate(audio_files, 1):
    filename = os.path.basename(audio_path)
    
    # 获取音频时长
    try:
        audio_data, sr = sf.read(audio_path)
        audio_duration = len(audio_data) / sr
        total_audio_duration += audio_duration
    except:
        audio_duration = 0
    
    # 识别
    file_start = time.time()
    try:
        result = processor.transcribe_file(audio_path)
        file_time = time.time() - file_start
        total_process_time += file_time
        
        results.append({
            "file": filename,
            "text": result.text,
            "emotion": result.emotion,
            "language": result.language,
            "duration": round(audio_duration, 3),
            "process_time": round(file_time, 3),
            "rtf": round(file_time / audio_duration, 4) if audio_duration > 0 else 0,
        })
        
        rtf = file_time / audio_duration if audio_duration > 0 else 0
        print(f"[{i:2d}/{len(audio_files)}] {filename[:25]:25s} | {audio_duration:.2f}s | {file_time:.3f}s | RTF:{rtf:.3f}")
        print(f"         文本: {result.text}")
        if result.emotion:
            print(f"         情感: {result.emotion}")
        
    except Exception as e:
        file_time = time.time() - file_start
        results.append({
            "file": filename,
            "text": f"[错误: {str(e)}]",
            "emotion": None,
            "duration": round(audio_duration, 3),
            "process_time": round(file_time, 3),
        })
        print(f"[{i:2d}/{len(audio_files)}] {filename} - 错误: {e}")

overall_time = time.time() - overall_start

# 统计
print()
print("="*70)
print("识别完成! 统计信息:")
print("="*70)
print(f"总文件数: {len(audio_files)}")
print(f"总音频时长: {total_audio_duration:.2f}s ({total_audio_duration/60:.2f}分钟)")
print(f"总处理时间: {total_process_time:.3f}s ({total_process_time/60:.2f}分钟)")
print(f"总耗时(含模型加载): {overall_time + model_load_time:.3f}s")
print(f"平均每文件: {total_process_time/len(audio_files):.3f}s")
print(f"平均RTF: {total_process_time/total_audio_duration:.4f}")
print(f"实时倍速: {total_audio_duration/total_process_time:.1f}x")
print()

# 保存结果
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
json_file = os.path.join(OUTPUT_DIR, f"validation_{timestamp}.json")
txt_file = os.path.join(OUTPUT_DIR, f"validation_{timestamp}.txt")

report = {
    "timestamp": timestamp,
    "audio_dir": AUDIO_DIR,
    "total_files": len(audio_files),
    "total_audio_duration": round(total_audio_duration, 3),
    "total_process_time": round(total_process_time, 3),
    "model_load_time": round(model_load_time, 3),
    "import_time": round(import_time, 3),
    "avg_rtf": round(total_process_time/total_audio_duration, 4) if total_audio_duration > 0 else 0,
    "realtime_factor": round(total_audio_duration/total_process_time, 2) if total_process_time > 0 else 0,
    "results": results,
}

with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

with open(txt_file, 'w', encoding='utf-8') as f:
    f.write("FunASR YueXiaShiYue 音频批量识别验证报告\n")
    f.write("="*70 + "\n")
    f.write(f"时间: {timestamp}\n")
    f.write(f"音频目录: {AUDIO_DIR}\n")
    f.write(f"总文件数: {len(audio_files)}\n")
    f.write(f"总音频时长: {total_audio_duration:.2f}s\n")
    f.write(f"总处理时间: {total_process_time:.3f}s\n")
    f.write(f"平均RTF: {total_process_time/total_audio_duration:.4f}\n")
    f.write(f"实时倍速: {total_audio_duration/total_process_time:.1f}x\n")
    f.write("="*70 + "\n\n")
    
    for r in results:
        f.write(f"文件: {r['file']}\n")
        f.write(f"文本: {r['text']}\n")
        if r.get('emotion'):
            f.write(f"情感: {r['emotion']}\n")
        f.write(f"时长: {r['duration']}s | 处理: {r['process_time']}s | RTF: {r['rtf']}\n")
        f.write("-"*50 + "\n")

print(f"结果已保存:")
print(f"  JSON: {json_file}")
print(f"  TXT:  {txt_file}")
print()
print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
