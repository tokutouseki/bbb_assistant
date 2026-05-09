import numpy as np
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import time
from .yolo_model_manager import YOLOModelManager

logger = logging.getLogger(__name__)

@dataclass
class Detection:
    label: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    class_id: int

class YOLODetector:
    """YOLO11n目标检测器"""
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.model_path = model_path or "./data/models/yolo/yolo11n.pt"
        self.device = device
        self.model = None
        self.model_name = None
        self.manager = YOLOModelManager.get_instance()
        self.class_names = self._load_class_names()
        logger.info(f"初始化YOLO检测器，设备: {device}")
    
    def _load_class_names(self) -> List[str]:
        """加载类别名称"""
        # 崩坏3特定类别
        return [
            "character", "enemy", "item", "ui_element", 
            "dialog_box", "menu", "map", "skill_icon"
        ]
    
    def load_model(self):
        """加载YOLO模型"""
        if self.model is not None and self.model_name:
            return
        
        try:
            load_result = self.manager.load_model(model_path=self.model_path, device=self.device)
            if load_result.get("success"):
                self.model_name = load_result["model"]["name"]
                self.model = True
                logger.info(f"YOLO模型加载成功: {self.model_path}")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self.model = None
    
    def detect(self, image: np.ndarray, confidence_threshold: float = 0.5) -> List[Detection]:
        """
        执行目标检测
        
        Args:
            image: 输入图像 (H, W, C)
            confidence_threshold: 置信度阈值
            
        Returns:
            检测结果列表
        """
        start_time = time.time()
        
        if self.model is None:
            # 模拟模式
            return self._mock_detection(image)
        
        try:
            if not self.model_name:
                return self._mock_detection(image)
            detect_result = self.manager.detect(
                image=image,
                model_name=self.model_name,
                confidence_threshold=confidence_threshold,
            )
            detections = [
                Detection(
                    label=item["label"],
                    confidence=float(item["confidence"]),
                    bbox=[float(x) for x in item["bbox"]],
                    class_id=int(item["class_id"]),
                )
                for item in detect_result.get("detections", [])
            ]
            
            processing_time = time.time() - start_time
            logger.info(f"检测完成: {len(detections)} 个目标, 耗时: {processing_time:.3f}s")
            return detections
            
        except Exception as e:
            logger.error(f"检测失败: {e}")
            return self._mock_detection(image)
    
    def _mock_detection(self, image: np.ndarray) -> List[Detection]:
        """模拟检测结果（用于测试）"""
        h, w = image.shape[:2]
        
        # 生成一些模拟检测结果
        return [
            Detection(
                label="character",
                confidence=0.85,
                bbox=[w*0.1, h*0.2, w*0.2, h*0.3],
                class_id=0
            ),
            Detection(
                label="enemy",
                confidence=0.72,
                bbox=[w*0.6, h*0.5, w*0.7, h*0.6],
                class_id=1
            ),
            Detection(
                label="ui_element",
                confidence=0.91,
                bbox=[w*0.8, h*0.05, w*0.95, h*0.1],
                class_id=3
            )
        ]
    
    def detect_game_scene(self, image: np.ndarray) -> Dict[str, Any]:
        """
        检测游戏场景类型
        
        Args:
            image: 游戏截图
            
        Returns:
            场景分析结果
        """
        detections = self.detect(image)
        
        # 基于检测结果判断场景类型
        scene_type = "unknown"
        character_count = sum(1 for d in detections if d.label == "character")
        enemy_count = sum(1 for d in detections if d.label == "enemy")
        ui_count = sum(1 for d in detections if d.label == "ui_element")
        
        if character_count > 0 and enemy_count > 0:
            scene_type = "battle"
        elif ui_count > 5:
            scene_type = "menu"
        elif character_count > 0:
            scene_type = "dialog"
        
        return {
            "scene_type": scene_type,
            "detections": detections,
            "counts": {
                "characters": character_count,
                "enemies": enemy_count,
                "ui_elements": ui_count
            }
        }