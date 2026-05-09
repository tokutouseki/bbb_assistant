import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging
import time

from .screen_capture import ScreenCapture
from .yolo_detector import YOLODetector
from .ocr_processor import OCRProcessor

logger = logging.getLogger(__name__)

class SceneAnalyzer:
    """游戏场景分析器，整合视觉分析功能"""
    
    def __init__(self, use_gpu: bool = False):
        self.screen_capture = ScreenCapture()
        self.yolo_detector = YOLODetector(device="cuda" if use_gpu else "cpu")
        self.ocr_processor = OCRProcessor()
        
        # 加载模型
        self.yolo_detector.load_model()
        
        logger.info("场景分析器初始化完成")
    
    def analyze_current_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        分析当前屏幕场景
        
        Args:
            region: 可选的分析区域
            
        Returns:
            场景分析结果
        """
        start_time = time.time()
        
        # 1. 捕获屏幕
        logger.info("捕获屏幕...")
        screenshot = self.screen_capture.capture(region)
        capture_time = time.time()
        
        # 2. 目标检测
        logger.info("执行目标检测...")
        detections = self.yolo_detector.detect(screenshot)
        detection_time = time.time()
        
        # 3. OCR文字识别
        logger.info("执行OCR文字识别...")
        ocr_results = self.ocr_processor.process(screenshot)
        ocr_time = time.time()
        
        # 4. 场景分类
        logger.info("分析场景类型...")
        scene_type = self._classify_scene(detections, ocr_results)
        
        # 5. 提取游戏状态信息
        game_state = self._extract_game_state(detections, ocr_results)
        
        total_time = time.time() - start_time
        
        result = {
            "scene_type": scene_type,
            "detections": [
                {
                    "label": d.label,
                    "confidence": d.confidence,
                    "bbox": d.bbox,
                    "class_id": d.class_id
                } for d in detections
            ],
            "ocr_results": [
                {
                    "text": r.text,
                    "confidence": r.confidence,
                    "bbox": r.bbox
                } for r in ocr_results
            ],
            "game_state": game_state,
            "timing": {
                "capture": capture_time - start_time,
                "detection": detection_time - capture_time,
                "ocr": ocr_time - detection_time,
                "total": total_time
            },
            "screenshot_size": {
                "height": screenshot.shape[0],
                "width": screenshot.shape[1],
                "channels": screenshot.shape[2] if len(screenshot.shape) > 2 else 1
            }
        }
        
        logger.info(f"场景分析完成: {scene_type}, 总耗时: {total_time:.3f}s")
        return result
    
    def _classify_scene(self, detections, ocr_results) -> str:
        """基于检测和OCR结果分类场景"""
        # 统计检测结果
        detection_labels = [d.label for d in detections]
        character_count = detection_labels.count("character")
        enemy_count = detection_labels.count("enemy")
        ui_count = detection_labels.count("ui_element")
        
        # 分析OCR结果
        ocr_texts = [r.text.lower() for r in ocr_results]
        
        # 判断场景类型
        if character_count > 0 and enemy_count > 0:
            return "battle"
        elif any("menu" in text or "设置" in text or "选项" in text for text in ocr_texts):
            return "menu"
        elif any("dialog" in text or "对话" in text or "剧情" in text for text in ocr_texts):
            return "dialog"
        elif any("map" in text or "地图" in text or "世界" in text for text in ocr_texts):
            return "map"
        elif ui_count > 3:
            return "ui_heavy"
        elif character_count > 0:
            return "character_focused"
        else:
            return "unknown"
    
    def _extract_game_state(self, detections, ocr_results) -> Dict[str, Any]:
        """从检测和OCR结果中提取游戏状态信息"""
        game_state = {
            "player_health": None,
            "enemy_count": 0,
            "character_count": 0,
            "dialog_active": False,
            "menu_open": False
        }
        
        # 统计检测结果
        for detection in detections:
            if detection.label == "character":
                game_state["character_count"] += 1
            elif detection.label == "enemy":
                game_state["enemy_count"] += 1
        
        # 从OCR结果中提取信息
        for ocr_result in ocr_results:
            text = ocr_result.text.lower()
            
            # 提取HP信息
            if "hp" in text or "生命" in text or "血量" in text:
                import re
                match = re.search(r"(\d+)\s*/\s*(\d+)", text)
                if match:
                    game_state["player_health"] = f"{match.group(1)}/{match.group(2)}"
            
            # 判断对话状态
            if ":" in text or "：" in text or "对话" in text or "选择" in text:
                game_state["dialog_active"] = True
            
            # 判断菜单状态
            if "menu" in text or "设置" in text or "选项" in text or "退出" in text:
                game_state["menu_open"] = True
        
        return game_state
    
    def monitor_game_scene(self, interval: float = 2.0, duration: Optional[float] = None):
        """
        监控游戏场景变化
        
        Args:
            interval: 监控间隔（秒）
            duration: 总监控时长（秒），None表示无限
            
        Yields:
            每次分析的结果
        """
        import time
        
        start_time = time.time()
        iteration = 0
        
        logger.info(f"开始游戏场景监控，间隔: {interval}s")
        
        while True:
            if duration and (time.time() - start_time) > duration:
                logger.info("监控时长达到，停止监控")
                break
            
            iteration += 1
            logger.info(f"监控迭代 #{iteration}")
            
            try:
                result = self.analyze_current_screen()
                result["iteration"] = iteration
                result["timestamp"] = time.time()
                
                yield result
                
            except Exception as e:
                logger.error(f"监控迭代 #{iteration} 失败: {e}")
                yield {
                    "error": str(e),
                    "iteration": iteration,
                    "timestamp": time.time()
                }
            
            # 等待下次迭代
            time.sleep(interval)
    
    def analyze_specific_game_state(self, state_type: str) -> Dict[str, Any]:
        """
        分析特定游戏状态
        
        Args:
            state_type: 状态类型（battle, dialog, menu等）
            
        Returns:
            特定状态的分析结果
        """
        analysis = self.analyze_current_screen()
        
        if state_type == "battle":
            return self._analyze_battle_state(analysis)
        elif state_type == "dialog":
            return self._analyze_dialog_state(analysis)
        elif state_type == "menu":
            return self._analyze_menu_state(analysis)
        else:
            return {"error": f"未知状态类型: {state_type}"}
    
    def _analyze_battle_state(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析战斗状态"""
        return {
            "type": "battle",
            "enemy_count": analysis["game_state"]["enemy_count"],
            "character_count": analysis["game_state"]["character_count"],
            "player_health": analysis["game_state"]["player_health"],
            "threat_level": "high" if analysis["game_state"]["enemy_count"] > 3 else "medium",
            "recommended_action": "使用技能攻击敌人" if analysis["game_state"]["enemy_count"] > 0 else "寻找敌人"
        }
    
    def _analyze_dialog_state(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析对话状态"""
        dialog_texts = [r["text"] for r in analysis["ocr_results"] if len(r["text"]) > 5]
        
        return {
            "type": "dialog",
            "dialog_active": True,
            "text_samples": dialog_texts[:3],  # 取前3个文本作为样本
            "recommended_action": "阅读对话并做出选择"
        }
    
    def _analyze_menu_state(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析菜单状态"""
        menu_items = [r["text"] for r in analysis["ocr_results"] 
                     if any(keyword in r["text"].lower() for keyword in ["设置", "选项", "退出", "保存", "加载"])]
        
        return {
            "type": "menu",
            "menu_items": menu_items,
            "recommended_action": "根据需要进行设置调整"
        }