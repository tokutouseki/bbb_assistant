from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np
import cv2

from src.modules.vision.yolo_model_manager import YOLOModelManager

router = APIRouter()
yolo_manager = YOLOModelManager.get_instance()

class DetectionResult(BaseModel):
    label: str = Field(..., description="检测标签")
    confidence: float = Field(..., description="置信度")
    bbox: List[float] = Field(..., description="边界框 [x1, y1, x2, y2]")
    class_id: int = Field(..., description="类别ID")

class OCRResult(BaseModel):
    text: str = Field(..., description="识别文本")
    confidence: float = Field(..., description="置信度")
    bbox: Optional[List[float]] = Field(None, description="文本区域")

class SceneAnalysis(BaseModel):
    scene_type: str = Field(..., description="场景类型")
    detected_objects: List[DetectionResult] = Field(default_factory=list)
    ocr_results: List[OCRResult] = Field(default_factory=list)
    game_state: Optional[Dict[str, Any]] = Field(None, description="游戏状态推断")


class YOLOModelLoadRequest(BaseModel):
    model_name: Optional[str] = Field(default=None, description="模型名（不含后缀）")
    model_path: Optional[str] = Field(default=None, description="模型路径，支持相对 backend/data/models")
    device: str = Field(default="cpu", description="推理设备，例如 cpu/cuda:0")


class YOLOParallelDetectRequest(BaseModel):
    model_names: List[str] = Field(..., description="并行推理模型列表")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_workers: int = Field(default=4, ge=1, le=16)

@router.post("/capture")
async def capture_screen(region: Optional[str] = None):
    """
    捕获屏幕截图
    - region: 可选区域 "x1,y1,x2,y2"
    """
    # TODO: 实现屏幕捕获
    return {"message": "屏幕捕获功能待实现", "region": region}

@router.post("/detect", response_model=List[DetectionResult])
async def detect_objects(
    image: UploadFile = File(...),
    confidence_threshold: float = 0.5,
    model_name: str = "yolo11n",
    iou_threshold: float = 0.45
):
    """
    使用YOLO11n进行目标检测
    """
    try:
        raw = await image.read()
        np_image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if np_image is None:
            raise ValueError("无法解析图片数据")

        if model_name not in {m["name"] for m in yolo_manager.list_loaded_models()}:
            yolo_manager.load_model(model_name=model_name, device="cpu")

        detect_result = yolo_manager.detect(
            image=np_image,
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )
        return [DetectionResult(**item) for item in detect_result.get("detections", [])]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"目标检测失败: {e}") from e


@router.post("/detect/parallel")
async def detect_objects_parallel(
    request: YOLOParallelDetectRequest,
    image: UploadFile = File(...),
):
    """对同一图像使用多个 YOLO 模型并行检测。"""
    try:
        raw = await image.read()
        np_image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if np_image is None:
            raise ValueError("无法解析图片数据")

        loaded = {m["name"] for m in yolo_manager.list_loaded_models()}
        for model_name in request.model_names:
            if model_name not in loaded:
                yolo_manager.load_model(model_name=model_name, device="cpu")

        return yolo_manager.parallel_detect(
            image=np_image,
            model_names=request.model_names,
            confidence_threshold=request.confidence_threshold,
            iou_threshold=request.iou_threshold,
            max_workers=request.max_workers,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"并行检测失败: {e}") from e


@router.get("/models/available")
async def list_available_yolo_models():
    """列出 backend/data/models 下可发现的 YOLO 模型文件。"""
    return {"models": yolo_manager.list_available_models()}


@router.get("/models/loaded")
async def list_loaded_yolo_models():
    """列出已装载 YOLO 模型。"""
    return {"models": yolo_manager.list_loaded_models(), "stats": yolo_manager.get_stats()}


@router.post("/models/load")
async def load_yolo_model(request: YOLOModelLoadRequest):
    """装载 YOLO 模型到内存。"""
    try:
        return yolo_manager.load_model(
            model_name=request.model_name,
            model_path=request.model_path,
            device=request.device,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"模型加载失败: {e}") from e


@router.post("/models/unload/{model_name}")
async def unload_yolo_model(model_name: str):
    """卸载 YOLO 模型。"""
    result = yolo_manager.unload_model(model_name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

@router.post("/ocr", response_model=List[OCRResult])
async def ocr_processing(
    image: UploadFile = File(...),
    language: str = "ch"
):
    """
    OCR文字识别（支持中英文）
    """
    # TODO: 实现PaddleOCR/EasyOCR
    return [
        OCRResult(
            text="崩坏3",
            confidence=0.95,
            bbox=[50, 60, 200, 80]
        ),
        OCRResult(
            text="HP: 100/100",
            confidence=0.88,
            bbox=[300, 400, 450, 420]
        )
    ]

@router.post("/analyze", response_model=SceneAnalysis)
async def analyze_scene(
    image: UploadFile = File(...)
):
    """
    综合分析游戏场景：目标检测 + OCR + 场景分类
    """
    # TODO: 集成检测和OCR，进行场景分类
    return SceneAnalysis(
        scene_type="battle",
        detected_objects=[
            DetectionResult(
                label="character",
                confidence=0.85,
                bbox=[100, 200, 150, 250],
                class_id=0
            )
        ],
        ocr_results=[
            OCRResult(
                text="Round 3",
                confidence=0.92,
                bbox=[10, 10, 100, 30]
            )
        ],
        game_state={"round": 3, "player_health": 100}
    )

@router.get("/game_scenes")
async def list_game_scenes():
    """
    获取预定义的崩坏3游戏场景列表
    """
    # TODO: 从配置加载游戏场景
    return {
        "scenes": [
            {"id": "battle", "name": "战斗场景", "description": "角色战斗状态"},
            {"id": "dialog", "name": "对话场景", "description": "剧情对话界面"},
            {"id": "menu", "name": "菜单界面", "description": "游戏菜单设置"},
            {"id": "map", "name": "地图界面", "description": "世界地图导航"}
        ]
    }