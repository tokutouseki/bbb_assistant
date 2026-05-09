# FunASR 全双工实时ASR系统集成指南

## 概述

FunASR是阿里达摩院开源的语音识别框架，本项目集成了FunASR 1.3.x版本，支持三种ASR模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `sensevoice` | 高精度多语言识别+情感检测 | 文件转录、情感分析 |
| `streaming` | 低延迟流式识别 | 实时字幕、语音输入 |
| `full_duplex` | 全双工实时对话 | AI对话助手、语音交互 |

## 安装配置

### 1. 安装依赖

```bash
# 安装FunASR
pip install funasr modelscope

# 或从源码安装（获取最新功能）
git clone https://github.com/alibaba-damo-academy/FunASR.git
cd FunASR && pip install -e .
```

### 2. 模型自动下载

首次运行时，模型会自动从ModelScope下载到本地缓存：
- Windows: `C:\Users\{用户名}\.cache\modelscope\hub\models\`
- Linux: `~/.cache/modelscope/hub/models/`

### 3. 验证安装

```python
import funasr
import torch

print(f"FunASR版本: {funasr.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"显卡: {torch.cuda.get_device_name(0)}")
```

## 快速开始

### 方式一：使用工厂函数（推荐）

```python
from src.modules.audio import create_asr_processor

# 创建处理器
processor = create_asr_processor(
    mode="sensevoice",      # 模式: sensevoice/streaming/full_duplex
    device="cuda:0",        # 设备: cuda:0 或 cpu
    enable_2pass=True,      # 启用2pass级联（仅full_duplex模式）
    enable_punc=True,       # 启用标点恢复
    enable_vad=True,        # 启用VAD检测（仅full_duplex模式）
)

# 识别音频文件
result = processor.transcribe_file("audio.wav")
print(f"识别结果: {result.text}")
print(f"情感: {result.emotion}")
print(f"处理时间: {result.processing_time:.3f}s")
```

### 方式二：直接导入类

```python
from src.modules.audio import FullDuplexASRProcessor, ASRMode

# 创建处理器
processor = FullDuplexASRProcessor(
    mode=ASRMode.SENSEVOICE,
    device="cuda:0",
)

# 识别音频
result = processor.transcribe_file("audio.mp3")
print(result.text)
```

## 使用示例

### 1. SenseVoice模式 - 高精度识别

```python
from src.modules.audio import create_asr_processor

# 创建处理器
processor = create_asr_processor(mode="sensevoice", device="cuda:0")

# 识别音频文件
result = processor.transcribe_file("d:/TokusCode/bbb_assistant/YueXiaShiYue/1 (100).wav")

print(f"文本: {result.text}")
print(f"语言: {result.language}")
print(f"情感: {result.emotion}")  # 开心/难过/愤怒/惊讶
print(f"置信度: {result.confidence}")
print(f"耗时: {result.processing_time:.3f}s")
```

**输出示例：**
```
文本: 我想学着做饭给你吃，可每次都失败，做饭好难啊。😔
语言: zh
情感: 难过
置信度: 0.95
耗时: 0.254s
```

### 2. Streaming模式 - 低延迟流式识别

```python
from src.modules.audio import create_asr_processor
import numpy as np
import soundfile as sf

# 创建处理器
processor = create_asr_processor(mode="streaming", device="cuda:0")

# 读取音频
audio_data, sample_rate = sf.read("audio.wav")
chunk_size = int(0.6 * sample_rate)  # 600ms块

# 流式识别
def audio_generator():
    for i in range(0, len(audio_data), chunk_size):
        yield audio_data[i:i+chunk_size]

for result in processor.process_audio_stream(audio_generator(), sample_rate):
    print(f"实时: {result.text}")

print("识别完成!")
```

### 3. Full Duplex模式 - 全双工实时对话

```python
from src.modules.audio import create_asr_processor

# 创建处理器
processor = create_asr_processor(
    mode="full_duplex",
    device="cuda:0",
    enable_2pass=True,
    enable_vad=True,
    enable_punc=True,
)

# 设置回调函数
def on_result(result):
    status = "最终" if result.is_final else "实时"
    print(f"[{status}] {result.text}")

def on_vad(vad_result):
    if vad_result.is_speech:
        print("[VAD] 检测到语音活动")

def on_interrupt():
    print("[中断] 用户打断，已重置状态")

processor.set_callbacks(
    on_result=on_result,
    on_vad=on_vad,
    on_interrupt=on_interrupt,
)

# 流式处理
for result in processor.process_audio_stream(audio_generator()):
    pass  # 结果通过回调处理

# 随时打断
processor.cancel()  # 即时中断，清空缓冲区
```

### 4. 批量识别

```python
from src.modules.audio import create_asr_processor
import glob
import json

# 创建处理器
processor = create_asr_processor(mode="sensevoice", device="cuda:0")

# 批量识别
audio_dir = "d:/TokusCode/bbb_assistant/YueXiaShiYue"
audio_files = glob.glob(f"{audio_dir}/*.wav")

results = []
for i, audio_path in enumerate(audio_files, 1):
    result = processor.transcribe_file(audio_path)
    results.append({
        "file": audio_path,
        "text": result.text,
        "emotion": result.emotion,
    })
    print(f"[{i}/{len(audio_files)}] {result.text}")

# 保存结果
with open("asr_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

## API参考

### FullDuplexASRProcessor

#### 初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mode` | str | "sensevoice" | 模式: sensevoice/streaming/full_duplex |
| `device` | str | "cuda:0" | 设备: cuda:0 或 cpu |
| `enable_2pass` | bool | True | 启用2pass级联（离线修正） |
| `enable_punc` | bool | True | 启用标点恢复 |
| `enable_vad` | bool | True | 启用VAD检测 |
| `output_dir` | str | None | 转录结果输出目录 |
| `chunk_size` | List[int] | [0, 10, 5] | 流式块大小配置 |

#### 主要方法

| 方法 | 说明 |
|------|------|
| `transcribe_file(path)` | 识别音频文件 |
| `transcribe(audio_data, sample_rate)` | 识别音频数据 |
| `process_audio_stream(generator)` | 流式处理音频流 |
| `cancel()` | 即时中断当前识别 |
| `reset()` | 重置模型状态 |
| `set_callbacks(...)` | 设置回调函数 |
| `save_transcription(result, filename)` | 保存转录结果 |

### ASRResult 数据类

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | str | 识别文本 |
| `is_final` | bool | 是否最终结果 |
| `confidence` | float | 置信度 |
| `language` | str | 语言代码 |
| `emotion` | str | 情感标签 |
| `process_time` | float | 处理时间(秒) |
| `mode` | str | 使用的模式 |

## 性能优化

### GPU加速

```python
# 使用CUDA加速
processor = create_asr_processor(device="cuda:0")

# 检查GPU状态
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

### RTX 3060优化建议

1. **使用CUDA 12.x** - 与TensorRT 10.0适配最佳
2. **INT8量化** - 显存占用减半，速度提升30%
3. **ONNX Runtime** - 自动调用CUDA核心并行推理

```python
# 安装ONNX Runtime GPU
pip install onnxruntime-gpu==1.19.2

# 安装TensorRT（可选）
pip install nvidia-tensorrt==10.0.1
```

## 常见问题

### Q: 模型下载慢怎么办？

```python
# 设置国内镜像
import os
os.environ['MODELSCOPE_CACHE'] = 'D:/modelscope_cache'  # 自定义缓存目录
```

### Q: 标点模型加载失败？

标点模型(ct-punc)依赖jieba分词，部分版本可能不兼容。可以禁用标点恢复：

```python
processor = create_asr_processor(mode="sensevoice", enable_punc=False)
```

### Q: 如何处理长音频？

```python
# 使用VAD分割长音频
processor = create_asr_processor(
    mode="full_duplex",
    enable_vad=True,
)

# VAD会自动分割长音频
for result in processor.process_audio_stream(long_audio_generator()):
    print(result.text)
```

## 文件结构

```
backend/src/modules/audio/
├── __init__.py                    # 模块导出
├── asr_processor.py               # 原ASR处理器（兼容旧代码）
├── full_duplex_asr_processor.py   # 全双工实时ASR处理器
├── tts_generator.py               # TTS生成器
├── qwen3_tts_generator.py         # Qwen3-TTS生成器
├── voice_clone.py                 # 语音克隆
└── voice_resource_manager.py      # 声音资源管理器
```

## 相关链接

- [FunASR GitHub](https://github.com/alibaba-damo-academy/FunASR)
- [ModelScope模型库](https://www.modelscope.cn/organization/damo)
- [官方文档](https://alibaba-damo-academy.github.io/FunASR/)

---
*最后更新: 2026-03-14*
