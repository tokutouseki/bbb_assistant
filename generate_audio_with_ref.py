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

from modules.audio.tts_generator import TTSGenerator

def main():
    print("=" * 60)
    print("使用爱莉希雅参考音频生成语音")
    print("=" * 60)
    
    # 初始化VoxCPM生成器（使用参考音频进行语音克隆）
    print("\n1. 初始化VoxCPM生成器...")
    tts = TTSGenerator(
        device="cuda:0",
        output_dir=os.path.join(project_root, "outputs", "tts_audio")
    )
    
    print("\n2. 可用语音列表:")
    voices = tts.list_available_voices()
    for idx, voice in enumerate(voices["voices"], 1):
        ref_status = "✓" if voice.get("has_reference") else "✗"
        print(f"   {idx}. {voice['id']} ({voice['name']}): {voice['description']} [{ref_status} 有参考音频]")
    
    print("\n" + "=" * 60)
    print("使用爱莉希雅参考音频生成音频")
    print("=" * 60)
    
    # 使用爱莉希雅参考音频生成"出错了"
    print("\n3. 生成『出错了』（爱莉希雅语音克隆）...")
    result1 = tts.generate(
        text="出错了",
        voice_id="elysia",
        save_result=True
    )
    print(f"   处理时间: {result1.processing_time:.2f}s")
    
    # 使用爱莉希雅参考音频生成"舰长，任务完成"
    print("\n4. 生成『舰长，任务完成』（爱莉希雅语音克隆）...")
    result2 = tts.generate(
        text="舰长，任务完成",
        voice_id="elysia",
        save_result=True
    )
    print(f"   处理时间: {result2.processing_time:.2f}s")
    
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)
    print(f"\n生成的音频文件保存在: {tts.output_dir}")
    print(f"\n音频信息:")
    print(f"1. 出错了: {len(result1.audio_data)} samples, {result1.sample_rate} Hz")
    print(f"2. 舰长，任务完成: {len(result2.audio_data)} samples, {result2.sample_rate} Hz")

if __name__ == "__main__":
    main()