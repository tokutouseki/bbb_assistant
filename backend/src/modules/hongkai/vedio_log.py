import cv2
import os
import time
import datetime
import inspect
import psutil
from threading import Thread

class VideoLogger:
    def __init__(self, enabled=False, fps=30, resolution=(640, 360), video_dir='vedio_log'):
        """
        初始化视频日志记录器
        :param enabled: 是否开启视频记录
        :param fps: 视频帧率
        :param resolution: 视频分辨率 (宽, 高)
        :param video_dir: 视频保存目录
        """
        self.enabled = enabled
        self.fps = fps
        self.actual_fps = fps  # 实际使用的帧率，可能会在start()中调整
        self.resolution = resolution
        self.video_dir = video_dir
        self.recording = False
        self.out = None
        self.thread = None
        self.video_file = None
        
        # 确保视频目录存在
        if not os.path.exists(self.video_dir):
            os.makedirs(self.video_dir)
        
        # 清理过期视频文件
        self.clean_old_videos()
    
    def start(self):
        """
        开始视频记录
        """
        if not self.enabled or self.recording:
            return
        
        try:
            # 获取调用文件名
            caller_frame = inspect.stack()[1]
            caller_filename = os.path.basename(caller_frame.filename).split('.')[0]
            
            # 生成视频文件名
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            self.video_file = os.path.join(self.video_dir, f"{caller_filename}_{timestamp}.mp4")
            
            # 创建视频写入对象
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            # 根据实际性能调整帧率（如果目标30fps但实际达不到）
            self.actual_fps = self.fps
            if self.fps >= 25:  # 高帧率目标可能需要调整
                # 经验值：实际帧率通常约为目标帧率的55-60%
                self.actual_fps = int(self.fps * 0.6)
                if self.actual_fps < 10:  # 确保最低帧率
                    self.actual_fps = 10
                print(f"视频录制: 目标帧率{self.fps}fps，使用实际帧率{self.actual_fps}fps以确保正常播放速度")
            self.out = cv2.VideoWriter(self.video_file, fourcc, self.actual_fps, self.resolution)
            
            # 开始录制线程
            self.recording = True
            self.thread = Thread(target=self._record)
            self.thread.daemon = True
            self.thread.start()
            
        except Exception as e:
            print(f"视频记录启动失败: {e}")
            self.recording = False
    
    def stop(self):
        """
        停止视频记录
        """
        if not self.recording:
            return
        
        self.recording = False
        if self.thread:
            self.thread.join(timeout=2)
        
        if self.out:
            self.out.release()
            self.out = None
    
    def _record(self):
        """
        录制视频的内部方法
        """
        import numpy as np
        from PIL import ImageGrab
        import win32api
        
        # 获取屏幕分辨率
        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        
        # 计算缩放比例
        scale_x = self.resolution[0] / screen_width
        scale_y = self.resolution[1] / screen_height
        
        # 计算每帧目标时间（秒）
        target_frame_time = 1.0 / self.actual_fps
        
        while self.recording:
            frame_start = time.time()
            
            try:
                # 捕获全屏
                screen = ImageGrab.grab(bbox=(0, 0, screen_width, screen_height))
                # 调整大小为360p
                screen = screen.resize(self.resolution)
                frame = np.array(screen)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # 获取鼠标位置并绘制
                mouse_x, mouse_y = win32api.GetCursorPos()
                # 转换鼠标位置到调整后的视频分辨率
                video_mouse_x = int(mouse_x * scale_x)
                video_mouse_y = int(mouse_y * scale_y)
                # 绘制鼠标位置（红色圆圈）
                cv2.circle(frame, (video_mouse_x, video_mouse_y), 3, (0, 0, 255), -1)
                # 绘制鼠标十字线
                cv2.line(frame, (video_mouse_x - 6, video_mouse_y), (video_mouse_x + 6, video_mouse_y), (0, 0, 255), 1)
                cv2.line(frame, (video_mouse_x, video_mouse_y - 6), (video_mouse_x, video_mouse_y + 6), (0, 0, 255), 1)
                
                # 写入视频
                if self.out:
                    self.out.write(frame)
                
                # 精确控制帧率
                frame_elapsed = time.time() - frame_start
                sleep_time = target_frame_time - frame_elapsed
                
                if sleep_time > 0.001:  # 只sleep有意义的时间
                    time.sleep(sleep_time)
                # 如果处理时间超过目标时间，立即开始下一帧
                
            except Exception as e:
                print(f"视频录制错误: {e}")
                # 发生错误时短暂暂停
                time.sleep(0.1)
    
    def clean_old_videos(self):
        """
        清理一天前的视频文件
        """
        try:
            now = datetime.datetime.now()
            one_day_ago = now - datetime.timedelta(days=1)
            
            for file in os.listdir(self.video_dir):
                file_path = os.path.join(self.video_dir, file)
                if os.path.isfile(file_path):
                    # 检查文件修改时间
                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if mod_time < one_day_ago:
                        os.remove(file_path)
        except Exception as e:
            print(f"清理过期视频失败: {e}")
    
    def __enter__(self):
        """
        上下文管理器进入方法
        """
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器退出方法
        """
        self.stop()

# 便捷函数
def get_video_logger(enabled=False, fps=30, resolution=(640, 360)):
    """
    获取视频日志记录器实例
    :param enabled: 是否开启视频记录
    :param fps: 视频帧率
    :param resolution: 视频分辨率
    :return: VideoLogger实例
    """
    return VideoLogger(enabled=enabled, fps=fps, resolution=resolution)

# 示例用法
if __name__ == "__main__":
    # 创建视频日志记录器
    logger = get_video_logger(enabled=True)
    
    try:
        print("开始录制视频...")
        logger.start()
        
        # 模拟一些操作
        for i in range(10):
            print(f"执行操作 {i+1}")
            time.sleep(1)
            
    finally:
        print("停止录制视频...")
        logger.stop()
        print("视频录制完成！")
