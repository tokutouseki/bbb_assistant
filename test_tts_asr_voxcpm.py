import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, "backend", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

sys.path.insert(0, os.path.join(project_root, "backend", "src"))

TTS_OUTPUT_DIR = os.path.join(project_root, "outputs", "test_tts_asr_voxcpm")
os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)

TARGET_TEXT = "大家好呀，我是爱莉希雅~ 今天也要和我一起，开开心心地度过每一刻哦！"


def main():
    print("=" * 70)
    print("  VoxCPM 爱莉希雅参考音频 → 生成音频 → ASR 识别 联动测试")
    print("=" * 70)

    # ===================== Step 1: TTS 生成 =====================
    print("\n[Step 1] 初始化 VoxCPM TTS 生成器...")
    from modules.audio.tts_generator import TTSGenerator

    tts = TTSGenerator(
        device="cuda:0",
        output_dir=TTS_OUTPUT_DIR
    )

    model_ok = tts.model is not None
    print(f"  模型初始化: {'成功' if model_ok else '模拟模式'}")

    voice = tts.voice_manager.get_voice("elysia") if tts.voice_manager else None
    if voice and voice.available:
        print(f"  参考音频: {voice.reference_audio_path}")
        print(f"  参考文本: {voice.reference_text[:50]}...")
    else:
        print(f"  参考音频: {tts.default_prompt_audio}")

    print(f"\n[Step 2] 使用爱莉希雅参考音频生成语音 (VoxCPM)...")
    print(f"  目标文本: {TARGET_TEXT}")

    t_start = time.time()
    tts_result = tts.generate(
        text=TARGET_TEXT,
        voice_id="elysia",
        save_result=True
    )
    tts_time = time.time() - t_start

    audio_path = tts.save_to_file(tts_result)

    print(f"  TTS 耗时: {tts_time:.2f}s")
    print(f"  采样率: {tts_result.sample_rate} Hz")
    audio_duration = len(tts_result.audio_data) / tts_result.sample_rate
    print(f"  音频长度: {len(tts_result.audio_data)} samples ({audio_duration:.2f}s)")
    print(f"  音频文件: {audio_path}")

    # ===================== Step 2: ASR 识别 =====================
    print(f"\n[Step 3] 初始化 ASR 处理器 (SenseVoiceSmall)...")
    from modules.audio.asr_processor import ASRProcessor
    from config.settings import get_settings

    settings = get_settings()
    asr_model_path = settings.asr_model_path

    asr = ASRProcessor(
        model_path=asr_model_path,
        device="cuda:0",
        output_dir=os.path.join(project_root, "outputs", "asr_transcriptions")
    )

    asr_ok = asr.model is not None
    print(f"  模型加载: {'成功' if asr_ok else '模拟模式'}")

    print(f"\n[Step 4] 对生成的音频执行 ASR 识别...")
    asr_start = time.time()
    asr_result = asr.transcribe_file(audio_path, language="zh", save_result=True)
    asr_time = time.time() - asr_start

    # ===================== Step 3: 结果汇总 =====================
    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)
    print(f"""
  ┌─────────────────────────────────────────────────────────────┐
  │  TTS 引擎       : VoxCPM-0.5B (爱莉希雅参考音频克隆)         │
  │  TTS 采样率     : {tts_result.sample_rate} Hz                                        │
  │  TTS 耗时       : {tts_time:.2f}s                                           │
  │  TTS 音频文件   : {audio_path}
  │  ASR 引擎       : SenseVoiceSmall ({'真实模型' if asr_ok else '模拟模式'})           │
  │  ASR 耗时       : {asr_time:.2f}s                                           │
  └─────────────────────────────────────────────────────────────┘
""")
    print(f"  📝 原始输入文字:")
    print(f"     「{TARGET_TEXT}」")
    print(f"")
    print(f"  🎧 ASR 识别结果:")
    print(f"     「{asr_result.text}」")
    print(f"")
    print(f"  📊 识别置信度: {asr_result.confidence:.2%}")
    print("=" * 70)

    return audio_path, asr_result.text


if __name__ == "__main__":
    main()
