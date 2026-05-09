"""
音频播放模块 - 用于播放提示音
支持在任务完成或出错时自动播放相应的音频文件
"""

import os
import platform
import subprocess
import logging

logger = logging.getLogger(__name__)

class AudioPlayer:
    """音频播放器类"""
    
    def __init__(self):
        self.success_audio = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "outputs", "qwen3_tts", "舰长任务完成.wav"
        )
        self.error_audio = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "outputs", "qwen3_tts", "出错了.wav"
        )
    
    def play_audio(self, audio_path: str):
        """播放指定的音频文件"""
        if not os.path.exists(audio_path):
            logger.warning(f"音频文件不存在: {audio_path}")
            return False
        
        try:
            system = platform.system()
            
            if system == "Windows":
                # 使用 Windows 内置命令播放
                subprocess.run(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()"],
                    check=True,
                    capture_output=True
                )
            elif system == "Linux":
                # 使用 alsa 播放
                subprocess.run(["aplay", audio_path], check=True, capture_output=True)
            elif system == "Darwin":
                # macOS 使用 afplay
                subprocess.run(["afplay", audio_path], check=True, capture_output=True)
            else:
                logger.warning(f"不支持的操作系统: {system}")
                return False
            
            logger.info(f"音频播放成功: {audio_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"音频播放失败: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"音频播放异常: {str(e)}")
            return False
    
    def play_success(self):
        """播放任务完成提示音"""
        return self.play_audio(self.success_audio)
    
    def play_error(self):
        """播放出错提示音"""
        return self.play_audio(self.error_audio)

# 创建单例
_audio_player_instance = None

def get_audio_player():
    """获取音频播放器单例"""
    global _audio_player_instance
    if _audio_player_instance is None:
        _audio_player_instance = AudioPlayer()
    return _audio_player_instance
