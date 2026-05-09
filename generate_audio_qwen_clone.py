import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
from dotenv import load_dotenv
project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, "backend", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"已加载环境变量: {env_path}")

# 添加项目路径
sys.path.insert(0, os.path.join(project_root, "backend", "src"))

from modules.audio.qwen3_tts_generator import Qwen3TTSGenerator

def main():
    print("=" * 60)
    print("使用Qwen3-TTS语音克隆（爱莉希雅参考音频）")
    print("=" * 60)
    
    # 爱莉希雅参考音频路径
    reference_audio_path = os.path.join(project_root, "voice_resources", "elysia", "reference.wav")
    
    if not os.path.exists(reference_audio_path):
        print(f"错误：未找到参考音频文件: {reference_audio_path}")
        return
    
    print(f"\n参考音频: {reference_audio_path}")
    
    # 初始化Qwen3-TTS生成器
    print("\n1. 初始化Qwen3-TTS生成器...")
    tts = Qwen3TTSGenerator(
        device="cuda:0",
        output_dir=os.path.join(project_root, "outputs", "qwen3_tts_clone")
    )
    
    print("\n" + "=" * 60)
    print("使用爱莉希雅参考音频进行语音克隆")
    print("=" * 60)
    
    # 读取参考文本
    reference_text_path = os.path.join(project_root, "voice_resources", "elysia", "reference.txt")
    ref_text = ""
    if os.path.exists(reference_text_path):
        with open(reference_text_path, 'r', encoding='utf-8') as f:
            ref_text = f.read().strip()
        print(f"参考文本: {ref_text}")
    
    # 使用语音克隆生成"出错了"
    print("\n2. 生成『出错了』（爱莉希雅语音克隆）...")
    result1 = tts.generate_with_reference(
        text="出错了",
        reference_audio=reference_audio_path,
        language="Chinese",
        ref_text=ref_text
    )
    output_path1 = tts.save_to_file(result1)
    print(f"   处理时间: {result1.processing_time:.2f}s")
    print(f"   音频已保存: {output_path1}")
    
    # 使用语音克隆生成"舰长，任务完成"
    print("\n3. 生成『舰长，任务完成』（爱莉希雅语音克隆）...")
    result2 = tts.generate_with_reference(
        text="舰长，任务完成",
        reference_audio=reference_audio_path,
        language="Chinese",
        ref_text=ref_text
    )
    output_path2 = tts.save_to_file(result2)
    print(f"   处理时间: {result2.processing_time:.2f}s")
    print(f"   音频已保存: {output_path2}")
    
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)
    print(f"\n生成的音频文件:")
    print(f"1. 出错了: {output_path1}")
    print(f"2. 舰长，任务完成: {output_path2}")
    print(f"\n音频信息:")
    print(f"1. 出错了: {len(result1.audio_data)} samples, {result1.sample_rate} Hz")
    print(f"2. 舰长，任务完成: {len(result2.audio_data)} samples, {result2.sample_rate} Hz")

if __name__ == "__main__":
    main()