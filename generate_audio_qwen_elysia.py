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
    print("使用Qwen3-TTS（爱莉希雅预设音色）")
    print("=" * 60)
    
    # 初始化Qwen3-TTS生成器
    print("\n1. 初始化Qwen3-TTS生成器...")
    tts = Qwen3TTSGenerator(
        device="cuda:0",
        output_dir=os.path.join(project_root, "outputs", "qwen3_tts_elysia")
    )
    
    print("\n2. 可用预设音色:")
    voice_styles = tts.get_voice_styles()
    for idx, (style_id, description) in enumerate(voice_styles.items(), 1):
        print(f"   {idx}. {style_id}: {description}")
    
    print("\n" + "=" * 60)
    print("使用爱莉希雅预设音色生成音频")
    print("=" * 60)
    
    # 使用爱莉希雅预设音色生成"出错了"
    print("\n3. 生成『出错了』（爱莉希雅音色）...")
    result1 = tts.generate(
        text="出错了",
        voice_style="爱莉希雅",
        language="Chinese"
    )
    output_path1 = tts.save_to_file(result1)
    print(f"   处理时间: {result1.processing_time:.2f}s")
    print(f"   音频已保存: {output_path1}")
    
    # 使用爱莉希雅预设音色生成"舰长，任务完成"
    print("\n4. 生成『舰长，任务完成』（爱莉希雅音色）...")
    result2 = tts.generate(
        text="舰长，任务完成",
        voice_style="爱莉希雅",
        language="Chinese"
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
    print(f"\n说明: 当前Qwen3-TTS使用的是VoiceDesign版本，通过自然语言描述生成爱莉希雅风格的声音。")

if __name__ == "__main__":
    main()