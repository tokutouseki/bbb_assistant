# -*- coding: utf-8 -*-
"""
批量音频识别脚本
使用FunASR识别指定文件夹中的所有音频文件
"""

import os
import glob
import time
import json
from datetime import datetime
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import torch

AUDIO_DIR = r"d:\TokusCode\bbb_assistant\YueXiaShiYue"
OUTPUT_DIR = r"d:\TokusCode\bbb_assistant\outputs\asr_results"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("="*60)
print("FunASR 批量音频识别")
print("="*60)
print(f"音频目录: {AUDIO_DIR}")
print(f"输出目录: {OUTPUT_DIR}")
print(f"CUDA可用: {torch.cuda.is_available()}")
print(f"显卡: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
print()

print("正在加载SenseVoiceSmall模型...")
model = AutoModel(
    model='iic/SenseVoiceSmall',
    device='cuda:0' if torch.cuda.is_available() else 'cpu',
    disable_update=True
)
print("模型加载成功!")
print()

audio_extensions = ['*.wav', '*.mp3', '*.flac', '*.ogg', '*.m4a']
audio_files = []
for ext in audio_extensions:
    audio_files.extend(glob.glob(os.path.join(AUDIO_DIR, ext)))
    audio_files.extend(glob.glob(os.path.join(AUDIO_DIR, '**', ext), recursive=True))

audio_files = sorted(set(audio_files))

print(f"找到 {len(audio_files)} 个音频文件")
print()

results = []
total_time = 0

for i, audio_path in enumerate(audio_files, 1):
    filename = os.path.basename(audio_path)
    print(f"[{i}/{len(audio_files)}] 识别: {filename}")
    
    try:
        start_time = time.time()
        
        res = model.generate(
            input=audio_path,
            cache={},
            language='auto',
            use_itn=True,
        )
        
        text = rich_transcription_postprocess(res[0]['text']) if res else ""
        process_time = time.time() - start_time
        total_time += process_time
        
        result = {
            "file": filename,
            "path": audio_path,
            "text": text,
            "process_time": round(process_time, 3)
        }
        results.append(result)
        
        print(f"    结果: {text}")
        print(f"    耗时: {process_time:.3f}秒")
        
    except Exception as e:
        print(f"    错误: {e}")
        results.append({
            "file": filename,
            "path": audio_path,
            "text": f"[错误: {str(e)}]",
            "process_time": 0
        })

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(OUTPUT_DIR, f"asr_results_{timestamp}.json")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "audio_dir": AUDIO_DIR,
        "total_files": len(audio_files),
        "total_time": round(total_time, 3),
        "timestamp": timestamp,
        "results": results
    }, f, ensure_ascii=False, indent=2)

txt_file = os.path.join(OUTPUT_DIR, f"asr_results_{timestamp}.txt")
with open(txt_file, 'w', encoding='utf-8') as f:
    f.write(f"FunASR 批量音频识别结果\n")
    f.write(f"{'='*60}\n")
    f.write(f"音频目录: {AUDIO_DIR}\n")
    f.write(f"识别时间: {timestamp}\n")
    f.write(f"文件数量: {len(audio_files)}\n")
    f.write(f"总耗时: {total_time:.3f}秒\n")
    f.write(f"{'='*60}\n\n")
    
    for r in results:
        f.write(f"文件: {r['file']}\n")
        f.write(f"文本: {r['text']}\n")
        f.write(f"耗时: {r['process_time']}秒\n")
        f.write(f"{'-'*40}\n")

print()
print("="*60)
print("识别完成!")
print("="*60)
print(f"总文件数: {len(audio_files)}")
print(f"总耗时: {total_time:.3f}秒")
print(f"平均耗时: {total_time/len(audio_files):.3f}秒/文件")
print(f"结果已保存到:")
print(f"  - {output_file}")
print(f"  - {txt_file}")
