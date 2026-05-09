import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 设置 ONNX Runtime 日志级别，减少警告
import os
os.environ['ORT_LOGGING_LEVEL'] = '3'  # ERROR级别

logger = logging.getLogger(__name__)


@dataclass
class YOLOManagedModel:
    name: str
    path: str
    device: str
    model: Any


class YOLOModelManager:
    """管理 YOLO 模型的装载、卸载和并行推理。"""

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, models_root: Optional[str] = None):
        backend_root = Path(__file__).resolve().parents[3]
        self.models_root = Path(models_root) if models_root else backend_root / "data" / "models"
        self._models: Dict[str, YOLOManagedModel] = {}
        self._lock = threading.RLock()
        self._stats = {
            "load_count": 0,
            "unload_count": 0,
            "detect_calls": 0,
            "parallel_detect_calls": 0,
        }

    @classmethod
    def get_instance(cls) -> "YOLOModelManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = YOLOModelManager()
        return cls._instance

    def list_available_models(self) -> List[Dict[str, str]]:
        if not self.models_root.exists():
            return []

        candidates = list(self.models_root.rglob("*.pt")) + list(self.models_root.rglob("*.onnx"))
        results: List[Dict[str, str]] = []
        for path in candidates:
            results.append(
                {
                    "name": path.stem,
                    "path": str(path),
                    "format": path.suffix.lower().lstrip("."),
                }
            )
        return sorted(results, key=lambda x: x["name"])

    def load_model(self, model_name: Optional[str] = None, model_path: Optional[str] = None, device: str = "cpu") -> Dict[str, Any]:
        from ultralytics import YOLO
        import torch

        resolved_path = self._resolve_model_path(model_name=model_name, model_path=model_path)
        model_key = self._model_key(model_name, resolved_path)

        with self._lock:
            if model_key in self._models:
                loaded = self._models[model_key]
                return {"success": True, "message": "模型已加载", "model": self._to_model_info(loaded)}

            # 根据模型名称判断任务类型
            task = None
            if model_name and 'cls' in model_name.lower():
                task = 'classify'
            elif model_name and 'det' in model_name.lower():
                task = 'detect'
            
            yolo_model = YOLO(str(resolved_path), task=task)
            
            # 对于 PyTorch 模型 (.pt) 才调用 .to()，ONNX 模型不需要
            # ONNX 模型在 predict 时通过 device 参数指定设备
            if resolved_path.suffix.lower() == '.pt':
                try:
                    if device.startswith('cuda') and torch.cuda.is_available():
                        yolo_model.to(device)
                        logger.info(f"PyTorch 模型已加载到GPU: {device}")
                    elif device == 'cpu':
                        yolo_model.to('cpu')
                        logger.info(f"PyTorch 模型已加载到CPU")
                    else:
                        yolo_model.to(device)
                        logger.info(f"PyTorch 模型已加载到设备: {device}")
                except Exception as e:
                    logger.warning(f"移动 PyTorch 模型到 {device} 失败，回退到CPU: {e}")
                    device = 'cpu'
            elif resolved_path.suffix.lower() == '.onnx':
                # ONNX 模型不需要调用 .to()，在 predict 时传递 device 参数即可
                logger.info(f"ONNX 模型已加载，设备将在推理时指定: {device}")
            else:
                logger.info(f"模型已加载: {device}")
            
            managed = YOLOManagedModel(
                name=model_key,
                path=str(resolved_path),
                device=device,
                model=yolo_model,
            )
            self._models[model_key] = managed
            self._stats["load_count"] += 1
            logger.info("YOLO模型加载成功: %s (%s)", managed.path, device)
            return {"success": True, "message": "模型加载成功", "model": self._to_model_info(managed)}

    def unload_model(self, model_name: str) -> Dict[str, Any]:
        with self._lock:
            managed = self._models.pop(model_name, None)
            if not managed:
                return {"success": False, "message": f"模型未加载: {model_name}"}
            self._stats["unload_count"] += 1
            return {"success": True, "message": f"模型已卸载: {model_name}"}

    def list_loaded_models(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._to_model_info(m) for m in self._models.values()]

    def detect(
        self,
        image: np.ndarray,
        model_name: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        save_images: bool = True,
    ) -> Dict[str, Any]:
        import json
        import os
        from PIL import Image, ImageDraw, ImageFont
        import time
        
        with self._lock:
            managed = self._models.get(model_name)
        if not managed:
            raise ValueError(f"模型未加载: {model_name}")

        # 加载检测标签中文映射
        mapping_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', '..', 'data', 'models', 'detect', 'detect_mapping.json'
        )
        mapping_path = os.path.normpath(mapping_path)
        
        label_mapping = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    all_mappings = json.load(f)
                    label_mapping = all_mappings.get(model_name, {})
            except Exception as e:
                pass
        
        # 保存原始图片
        timestamp = int(time.time() * 1000)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        original_dir = os.path.join(project_root, 'yolo_output', 'original')
        process_dir = os.path.join(project_root, 'yolo_output', 'process')
        
        os.makedirs(original_dir, exist_ok=True)
        os.makedirs(process_dir, exist_ok=True)
        
        original_path = None
        if save_images:
            try:
                img_pil = Image.fromarray(image)
                original_path = os.path.join(original_dir, f"{model_name}_{timestamp}.png")
                img_pil.save(original_path)
                logger.info(f"原始图片已保存: {original_path}")
            except Exception as e:
                logger.warning(f"保存原始图片失败: {e}")

        # 尝试用指定设备，如果失败则回退到 CPU
        try:
            results = managed.model.predict(
                image,
                conf=confidence_threshold,
                iou=iou_threshold,
                device=managed.device,
                verbose=False,
            )
        except Exception as e:
            logger.warning(f"用设备 {managed.device} 推理失败，回退到 CPU: {e}")
            results = managed.model.predict(
                image,
                conf=confidence_threshold,
                iou_threshold=iou_threshold,
                device='cpu',
                verbose=False,
            )

        detections = []
        for result in results:
            boxes = result.boxes
            names = result.names if hasattr(result, "names") else {}
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                label = names.get(cls_id, f"class_{cls_id}")
                label_cn = label_mapping.get(label, label)
                
                detections.append(
                    {
                        "label": label,
                        "label_cn": label_cn,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "class_id": cls_id,
                    }
                )
        
        # 保存识别后的图片（带识别框）
        process_path = None
        if save_images:
            try:
                img_pil = Image.fromarray(image).convert("RGB")
                draw = ImageDraw.Draw(img_pil)
                
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except:
                    font = ImageFont.load_default()
                
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    label = det["label_cn"]
                    conf = det["confidence"]
                    
                    draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
                    text = f"{label} {conf:.2f}"
                    
                    text_bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    draw.rectangle([x1, y1 - text_height - 4, x1 + text_width + 4, y1], fill="red")
                    draw.text((x1 + 2, y1 - text_height - 2), text, fill="white", font=font)
                
                process_path = os.path.join(process_dir, f"{model_name}_{timestamp}_detected.png")
                img_pil.save(process_path)
                logger.info(f"识别后图片已保存: {process_path}")
            except Exception as e:
                logger.warning(f"保存识别后图片失败: {e}")

        self._stats["detect_calls"] += 1
        return {
            "model": model_name, 
            "detections": detections,
            "original_image_path": original_path,
            "processed_image_path": process_path
        }

    def classify(
        self,
        image: np.ndarray,
        model_name: str,
    ) -> Dict[str, Any]:
        """
        使用分类模型进行图像分类
        
        Args:
            image: 输入图像（numpy数组，格式为HWC，RGB）
            model_name: 已加载的分类模型名称
        
        Returns:
            Dict: 分类结果，包含top1和top5预测
        """
        import json
        import os
        
        with self._lock:
            managed = self._models.get(model_name)
        if not managed:
            raise ValueError(f"模型未加载: {model_name}")

        # 加载场景分类中文映射
        mapping_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', '..', 'data', 'models', 'classification', 'scene_mapping.json'
        )
        mapping_path = os.path.normpath(mapping_path)
        
        label_mapping = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    all_mappings = json.load(f)
                    label_mapping = all_mappings.get('cn', {})
            except Exception as e:
                pass

        # 确保图像格式正确
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")
        
        # 确保图像是HWC格式（高度，宽度，通道）
        if len(image.shape) == 2:
            # 灰度图像转换为RGB
            image = np.stack([image] * 3, axis=-1)
        elif len(image.shape) == 3 and image.shape[2] == 1:
            # 单通道图像转换为RGB
            image = np.repeat(image, 3, axis=2)
        elif len(image.shape) != 3:
            raise ValueError(f"图像形状不正确: {image.shape}")

        # 尝试用指定设备，如果失败则回退到 CPU
        try:
            results = managed.model.predict(
                image,
                device=managed.device,
                verbose=False,
            )
        except Exception as e:
            logger.warning(f"用设备 {managed.device} 推理失败，回退到 CPU: {e}")
            results = managed.model.predict(
                image,
                device='cpu',
                verbose=False,
            )

        predictions = []
        for result in results:
            names = result.names if hasattr(result, "names") else {}
            
            if hasattr(result, "probs") and result.probs is not None:
                # 获取Top1结果
                top1_idx = result.probs.top1
                top1_conf = float(result.probs.top1conf.cpu().numpy()) if hasattr(result.probs, 'top1conf') else None
                top1_name = names.get(top1_idx, f"class_{top1_idx}")
                top1_name_cn = label_mapping.get(top1_name, top1_name)
                
                # 获取Top5结果
                top5_indices = result.probs.top5 if hasattr(result.probs, 'top5') else []
                top5_confs = result.probs.top5conf.cpu().numpy().tolist() if hasattr(result.probs, 'top5conf') else []
                
                top5 = []
                for i, idx in enumerate(top5_indices):
                    conf = top5_confs[i] if i < len(top5_confs) else None
                    label = names.get(idx, f"class_{idx}")
                    label_cn = label_mapping.get(label, label)
                    top5.append({
                        "class_id": int(idx),
                        "label": label,
                        "label_cn": label_cn,
                        "confidence": float(conf) if conf else None
                    })
                
                predictions.append({
                    "top1": {
                        "class_id": int(top1_idx),
                        "label": top1_name,
                        "label_cn": top1_name_cn,
                        "confidence": top1_conf
                    },
                    "top5": top5,
                    "names": names
                })

        self._stats["detect_calls"] += 1
        return {"model": model_name, "predictions": predictions}

    def parallel_detect(
        self,
        image: np.ndarray,
        model_names: List[str],
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        max_workers: int = 4,
    ) -> Dict[str, Any]:
        if not model_names:
            return {"success": False, "message": "model_names 不能为空", "results": []}

        self._stats["parallel_detect_calls"] += 1
        results: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    self.detect,
                    image=image,
                    model_name=model_name,
                    confidence_threshold=confidence_threshold,
                    iou_threshold=iou_threshold,
                ): model_name
                for model_name in model_names
            }
            for future in as_completed(future_map):
                model_name = future_map[future]
                try:
                    results.append({"model": model_name, "success": True, **future.result()})
                except Exception as exc:
                    results.append({"model": model_name, "success": False, "error": str(exc)})

        return {"success": True, "results": results}

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                **self._stats,
                "loaded_models": len(self._models),
                "models_root": str(self.models_root),
            }

    def _resolve_model_path(self, model_name: Optional[str], model_path: Optional[str]) -> Path:
        if model_path:
            path = Path(model_path)
            if not path.is_absolute():
                path = self.models_root / model_path
            if not path.exists():
                raise FileNotFoundError(f"模型文件不存在: {path}")
            return path

        if model_name:
            for candidate in self.list_available_models():
                if candidate["name"] == model_name:
                    return Path(candidate["path"])
            raise FileNotFoundError(f"未找到模型: {model_name}")

        raise ValueError("必须提供 model_name 或 model_path")

    def _model_key(self, model_name: Optional[str], resolved_path: Path) -> str:
        return model_name or resolved_path.stem

    def _to_model_info(self, model: YOLOManagedModel) -> Dict[str, Any]:
        return {"name": model.name, "path": model.path, "device": model.device}
