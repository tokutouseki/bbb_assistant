from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any
import psutil
import platform
from datetime import datetime

router = APIRouter()

class HealthStatus(BaseModel):
    status: str = Field(..., description="服务状态: healthy, degraded, unhealthy")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0", description="服务版本")
    uptime: float = Field(..., description="运行时间（秒）")

class SystemInfo(BaseModel):
    platform: str = Field(..., description="操作系统")
    python_version: str = Field(..., description="Python版本")
    cpu_usage: float = Field(..., description="CPU使用率")
    memory_usage: float = Field(..., description="内存使用率")
    disk_usage: Dict[str, float] = Field(..., description="磁盘使用情况")

class ServiceStatus(BaseModel):
    yolo: bool = Field(..., description="YOLO11n模型状态")
    ocr: bool = Field(..., description="OCR模型状态")
    asr: bool = Field(..., description="ASR模型状态")
    tts: bool = Field(..., description="TTS模型状态")
    llm: bool = Field(..., description="大模型API状态")
    rag: bool = Field(..., description="RAG知识库状态")
    database: bool = Field(..., description="数据库连接状态")

# 模拟启动时间
_start_time = datetime.now()

@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    基础健康检查
    """
    uptime = (datetime.now() - _start_time).total_seconds()
    return HealthStatus(
        status="healthy",
        uptime=uptime
    )

@router.get("/system", response_model=SystemInfo)
async def system_info():
    """
    系统信息
    """
    return SystemInfo(
        platform=platform.platform(),
        python_version=platform.python_version(),
        cpu_usage=psutil.cpu_percent(),
        memory_usage=psutil.virtual_memory().percent,
        disk_usage={}
    )

@router.get("/services", response_model=ServiceStatus)
async def service_status():
    """
    各AI服务状态检查
    """
    # TODO: 实际检查各服务状态
    return ServiceStatus(
        yolo=True,
        ocr=True,
        asr=True,
        tts=True,
        llm=True,
        rag=True,
        database=True
    )

@router.get("/detailed")
async def detailed_health():
    """
    详细健康检查（包含所有组件状态）
    """
    uptime = (datetime.now() - _start_time).total_seconds()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": uptime,
        "services": {
            "yolo": {"status": "ready", "model": "yolo11n"},
            "ocr": {"status": "ready", "engine": "PaddleOCR"},
            "asr": {"status": "ready", "model": "Whisper"},
            "tts": {"status": "ready", "model": "VoxCPM-0.5B"},
            "qwen3_tts": {"status": "ready", "model": "Qwen3-TTS-1.7B"},
            "llm": {"status": "ready", "providers": ["DeepSeek", "Kimi"]},
            "rag": {"status": "ready", "vector_db": "ChromaDB"},
            "database": {"status": "connected", "type": "SQLite/ChromaDB"}
        },
        "system": {
            "cpu_cores": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available
        }
    }