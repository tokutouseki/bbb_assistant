import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import time
import os

logger = logging.getLogger(__name__)

@dataclass
class OCRResult:
    text: str
    confidence: float
    bbox: Optional[List[float]]  

class OCRProcessor:
    """OCR文字识别处理器，使用RapidOCR"""
    
    def __init__(self, language: str = "ch"):
        self.language = language
        self.rapid_ocr = None
        self._initialize()
    
    def _initialize(self):
        """初始化RapidOCR引擎"""
        try:
            from rapidocr_onnxruntime import RapidOCR
            
            base_model_dir = "D:/TokusCode/models/ocr"
            
            det_model_path = os.path.join(base_model_dir, 'ch_PP-OCRv4_det_infer.onnx')
            rec_model_path = os.path.join(base_model_dir, 'ch_PP-OCRv4_rec_infer.onnx')
            cls_model_path = os.path.join(base_model_dir, 'ch_ppocr_mobile_v2.0_cls_infer.onnx')
            
            if os.path.exists(det_model_path) and os.path.exists(rec_model_path) and os.path.exists(cls_model_path):
                self.rapid_ocr = RapidOCR(
                    det_model_path=det_model_path,
                    rec_model_path=rec_model_path,
                    cls_model_path=cls_model_path,
                    use_angle_cls=True,
                    use_text_det=True,
                    print_verbose=False
                )
                logger.info(f"RapidOCR初始化成功（使用模型: {base_model_dir}）")
            else:
                logger.warning(f"OCR模型文件不存在于 {base_model_dir}，使用默认模型")
                self.rapid_ocr = RapidOCR(use_angle_cls=True, use_text_det=True, print_verbose=False)
                logger.info("RapidOCR初始化成功（使用默认模型）")
                
        except ImportError:
            logger.warning("RapidOCR未安装，使用模拟模式")
            self.rapid_ocr = None
    
    def process(self, image: np.ndarray, language: Optional[str] = None) -> List[OCRResult]:
        """
        执行OCR文字识别
        
        Args:
            image: 输入图像 (H, W, C) RGB格式
            language: 语言代码，默认为初始化时的语言
            
        Returns:
            OCR结果列表
        """
        start_time = time.time()
        
        if self.rapid_ocr is not None:
            results = self._process_rapidocr(image)
        else:
            results = self._mock_ocr(image)
        
        processing_time = time.time() - start_time
        logger.info(f"OCR完成: {len(results)} 个文本, 耗时: {processing_time:.3f}s")
        return results
    
    def _process_rapidocr(self, image: np.ndarray) -> List[OCRResult]:
        """使用RapidOCR处理"""
        try:
            if len(image.shape) == 2:
                image = np.stack([image]*3, axis=-1)
            elif image.shape[2] == 4:
                image = image[:, :, :3]
            
            result, elapse = self.rapid_ocr(image)
            
            ocr_results = []
            if result and len(result) > 0:
                for line in result:
                    box = line[0]
                    text = line[1]
                    confidence = float(line[2])
                    
                    flat_bbox = [coord for point in box for coord in point]
                    ocr_results.append(OCRResult(
                        text=text,
                        confidence=confidence,
                        bbox=flat_bbox
                    ))
            
            return ocr_results
            
        except Exception as e:
            logger.error(f"RapidOCR处理失败: {e}")
            return self._mock_ocr(image)
    
    def _mock_ocr(self, image: np.ndarray) -> List[OCRResult]:
        """模拟OCR结果（用于测试）"""
        h, w = image.shape[:2]
        
        return [
            OCRResult(
                text="崩坏3",
                confidence=0.95,
                bbox=[w*0.05, h*0.05, w*0.15, h*0.05, w*0.15, h*0.1, w*0.05, h*0.1]
            ),
            OCRResult(
                text="HP: 100/100",
                confidence=0.88,
                bbox=[w*0.7, h*0.02, w*0.85, h*0.02, w*0.85, h*0.05, w*0.7, h*0.05]
            ),
            OCRResult(
                text="技能冷却",
                confidence=0.82,
                bbox=[w*0.8, h*0.9, w*0.9, h*0.9, w*0.9, h*0.95, w*0.8, h*0.95]
            )
        ]
    
    def extract_game_info(self, image: np.ndarray) -> Dict[str, Any]:
        """
        从游戏截图中提取关键信息
        
        Args:
            image: 游戏截图
            
        Returns:
            提取的游戏信息
        """
        ocr_results = self.process(image)
        
        hp_value = None
        skill_info = []
        dialog_text = []
        
        for result in ocr_results:
            text = result.text.lower()
            
            if "hp" in text or "生命" in text or "血量" in text:
                hp_value = self._extract_hp_value(result.text)
            
            if "skill" in text or "技能" in text or "冷却" in text:
                skill_info.append(result.text)
            
            if result.bbox:
                x_center = (result.bbox[0] + result.bbox[2] + result.bbox[4] + result.bbox[6]) / 4
                y_center = (result.bbox[1] + result.bbox[3] + result.bbox[5] + result.bbox[7]) / 4
                if 0.3 < x_center/image.shape[1] < 0.7 and 0.4 < y_center/image.shape[0] < 0.6:
                    dialog_text.append(result.text)
        
        return {
            "hp": hp_value,
            "skills": skill_info,
            "dialog": dialog_text,
            "all_texts": [r.text for r in ocr_results]
        }
    
    def _extract_hp_value(self, text: str) -> Optional[str]:
        """从文本中提取HP值"""
        import re
        patterns = [
            r"HP[:：]?\s*(\d+/\d+)",
            r"生命[:：]?\s*(\d+/\d+)",
            r"血量[:：]?\s*(\d+/\d+)",
            r"(\d+)\s*/\s*(\d+)\s*HP"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)}/{match.group(2)}"
                else:
                    return match.group(1)
        
        return None
