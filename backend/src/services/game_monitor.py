import time
import threading
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class GameMonitor:
    """游戏监控服务，监视游戏状态变化"""
    
    def __init__(self, check_interval: float = 2.0):
        self.check_interval = check_interval
        self.monitoring = False
        self.thread: Optional[threading.Thread] = None
        self.callbacks: Dict[str, Callable] = {}
        self.last_game_state: Dict[str, Any] = {}
        logger.info(f"游戏监控服务初始化，检查间隔: {check_interval}s")
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            logger.warning("游戏监控已在运行中")
            return
        
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        logger.info("游戏监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=5.0)
            self.thread = None
        logger.info("游戏监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        iteration = 0
        
        while self.monitoring:
            iteration += 1
            try:
                game_state = self._check_game_state()
                self._process_state_change(game_state)
                self.last_game_state = game_state
                
            except Exception as e:
                logger.error(f"监控迭代 #{iteration} 失败: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_game_state(self) -> Dict[str, Any]:
        """检查游戏状态"""
        # TODO: 实际检查游戏状态
        # 这里模拟状态检查
        
        current_time = datetime.now()
        
        return {
            "timestamp": current_time.isoformat(),
            "game_running": True,  # 模拟游戏运行中
            "game_scene": "battle",  # 模拟场景
            "player_health": 85,
            "enemy_count": 3,
            "in_dialog": False,
            "in_menu": False
        }
    
    def _process_state_change(self, new_state: Dict[str, Any]):
        """处理状态变化"""
        if not self.last_game_state:
            # 第一次检查，不触发变化
            return
        
        # 检查场景变化
        if new_state.get("game_scene") != self.last_game_state.get("game_scene"):
            self._trigger_callback("scene_changed", {
                "old_scene": self.last_game_state.get("game_scene"),
                "new_scene": new_state.get("game_scene")
            })
        
        # 检查玩家健康值变化
        if new_state.get("player_health") != self.last_game_state.get("player_health"):
            self._trigger_callback("health_changed", {
                "old_health": self.last_game_state.get("player_health"),
                "new_health": new_state.get("player_health")
            })
        
        # 检查敌人数量变化
        if new_state.get("enemy_count") != self.last_game_state.get("enemy_count"):
            self._trigger_callback("enemy_count_changed", {
                "old_count": self.last_game_state.get("enemy_count"),
                "new_count": new_state.get("enemy_count")
            })
    
    def _trigger_callback(self, event_type: str, data: Dict[str, Any]):
        """触发回调"""
        if event_type in self.callbacks:
            try:
                self.callbacks[event_type](data)
            except Exception as e:
                logger.error(f"回调执行失败 ({event_type}): {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        注册事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        self.callbacks[event_type] = callback
        logger.info(f"注册回调: {event_type}")
    
    def unregister_callback(self, event_type: str):
        """取消注册回调"""
        if event_type in self.callbacks:
            del self.callbacks[event_type]
            logger.info(f"取消注册回调: {event_type}")
    
    def detect_game_process(self) -> bool:
        """检测游戏进程是否运行"""
        # TODO: 实际检测游戏进程
        # 这里模拟检测
        
        import random
        return random.random() > 0.2  # 80%概率检测到游戏运行
    
    def get_game_window_info(self) -> Optional[Dict[str, Any]]:
        """获取游戏窗口信息"""
        # TODO: 实际获取窗口信息
        
        return {
            "title": "崩坏3",
            "width": 1920,
            "height": 1080,
            "is_foreground": True,
            "is_fullscreen": False
        }
    
    def take_game_screenshot(self) -> Optional[bytes]:
        """获取游戏截图"""
        # TODO: 实际截图
        # 这里返回模拟
        
        logger.info("获取游戏截图")
        return b"simulated_screenshot_data"