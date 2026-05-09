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
from modules.audio.tts_generator import TTSGenerator

def main():
    print("=" * 60)
    print("TTS语音合成测试")
    print("=" * 60)
    
    # 初始化Qwen3-TTS生成器（不传入model_path，使用环境变量配置）
    print("\n1. 初始化Qwen3-TTS生成器...")
    qwen3_tts = Qwen3TTSGenerator(
        device="cuda:0",
        output_dir=os.path.join(project_root, "outputs", "qwen3_tts")
    )
    
    print("\n2. Qwen3-TTS可用音色列表:")
    voice_styles = qwen3_tts.get_voice_styles()
    for idx, (style_id, description) in enumerate(voice_styles.items(), 1):
        print(f"   {idx}. {style_id}: {description}")
    
    # 初始化VoxCPM生成器（不传入model_path，使用环境变量配置）
    print("\n3. 初始化VoxCPM生成器...")
    voxcpm_tts = TTSGenerator(
        device="cuda:0",
        output_dir=os.path.join(project_root, "outputs", "tts_audio")
    )
    
    print("\n4. VoxCPM可用音色列表:")
    voxcpm_voices = voxcpm_tts.list_available_voices()
    for idx, voice in enumerate(voxcpm_voices["voices"], 1):
        ref_status = "✓" if voice.get("has_reference") else "✗"
        print(f"   {idx}. {voice['id']} ({voice['name']}): {voice['description']} [{ref_status} 有参考音频]")
    
    print("\n" + "=" * 60)
    print("生成音频文件")
    print("=" * 60)
    
    # 生成"出错了"音频（使用爱莉希雅音色）
    print("\n5. 生成『出错了』音频...")
    result1 = qwen3_tts.generate(
        text="出错了",
        voice_style="爱莉希雅",
        language="Chinese"
    )
    output_path1 = qwen3_tts.save_to_file(result1)
    print(f"   音频已保存: {output_path1}")
    
    # 生成"舰长，任务完成"音频（使用爱莉希雅音色）
    print("\n6. 生成『舰长，任务完成』音频...")
    result2 = qwen3_tts.generate(
        text="舰长，任务完成",
        voice_style="爱莉希雅",
        language="Chinese"
    )
    output_path2 = qwen3_tts.save_to_file(result2)
    print(f"   音频已保存: {output_path2}")
    
    # 额外生成月下誓约风格的音频（使用自定义描述）
    print("\n7. 生成月下誓约风格的音频...")
    result3 = qwen3_tts.generate(
        text="舰长，任务完成",
        custom_description="月下誓约风格，温柔神秘的少女声音，带有月光般清冷的气息，语调轻柔舒缓，梦幻般的感觉",
        language="Chinese"
    )
    output_path3 = qwen3_tts.save_to_file(result3)
    print(f"   音频已保存: {output_path3}")
    
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)
    print(f"\n生成的音频文件:")
    print(f"1. 出错了 (爱莉希雅): {output_path1}")
    print(f"2. 舰长，任务完成 (爱莉希雅): {output_path2}")
    print(f"3. 舰长，任务完成 (月下誓约风格): {output_path3}")
    
    print(f"\n环境变量配置:")
    print(f"  QWEN3_TTS_MODEL_PATH: {os.environ.get('QWEN3_TTS_MODEL_PATH', '未设置')}")
    print(f"  VOXCPM_MODEL_PATH: {os.environ.get('VOXCPM_MODEL_PATH', '未设置')}")

if __name__ == "__main__":
    main()