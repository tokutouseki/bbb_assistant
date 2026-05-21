"""
设置管理 API
提供运行时 LLM 配置的读取与修改，持久化到 data/user_settings.json
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from ..config.runtime_settings import (
    get_runtime_settings,
    update_runtime_settings,
    reset_to_defaults,
    get_config_file_path,
    get_config_file_content,
)

router = APIRouter()


class LLMSettings(BaseModel):
    llm_provider: Optional[str] = Field(None, description="deepseek / lmstudio / ollama")
    llm_model: Optional[str] = Field(None, description="模型名称")
    llm_api_key: Optional[str] = Field(None, description="API密钥")
    llm_api_base_url: Optional[str] = Field(None, description="API地址")
    llm_temperature: Optional[float] = Field(None, ge=0, le=2)
    llm_max_tokens: Optional[int] = Field(None, ge=256, le=32768)
    image_describer_backend: Optional[str] = Field(None, description="图片描述后端优先级: bailian / pixai_tagger / lmstudio")
    bailian_api_key: Optional[str] = Field(None, description="阿里百炼API密钥")
    live2d_enabled: Optional[bool] = Field(None, description="启用Live2D看板娘")
    live2d_model_name: Optional[str] = Field(None, description="Live2D模型名称")
    live2d_auto_emotion: Optional[bool] = Field(None, description="根据对话自动切换情绪")
    live2d_window_alpha: Optional[float] = Field(None, ge=0.0, le=1.0, description="窗口透明度")
    live2d_window_width: Optional[int] = Field(None, ge=200, le=2000, description="窗口宽度(像素)")
    live2d_window_height: Optional[int] = Field(None, ge=200, le=2000, description="窗口高度(像素)")
    live2d_window_x: Optional[int] = Field(None, ge=0, description="窗口X坐标")
    live2d_window_y: Optional[int] = Field(None, ge=0, description="窗口Y坐标")


class SettingsResponse(BaseModel):
    success: bool = True
    data: LLMSettings
    config_file: str = ""
    message: str = "ok"


def _propagate_live2d(overrides: dict) -> None:
    """Apply Live2D-related settings to the running Live2D server (if available).

    Only handles model loading here — position/size/alpha are handled in
    real-time by PUT /api/live2d/apply from the frontend debounced calls.
    """
    if "live2d_model_name" not in overrides or not overrides.get("live2d_model_name"):
        return
    try:
        from src.modules.live2d_control.config import LIVE2D_HOST, LIVE2D_PORT, CLIENT_TIMEOUT
        from src.modules.live2d_control.live2d_client import Live2DClient
        client = Live2DClient(host=LIVE2D_HOST, port=LIVE2D_PORT, timeout=CLIENT_TIMEOUT)
        if not client.connect():
            return
        client.send({"action": "load_model", "model_name": overrides["live2d_model_name"]})
        client.close()
    except Exception:
        pass  # Fire-and-forget: server may not be running


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    current = get_runtime_settings()
    return SettingsResponse(
        data=LLMSettings(**{k: v for k, v in current.items()}),
        config_file=get_config_file_path(),
        message="ok"
    )


@router.put("/", response_model=SettingsResponse)
async def put_settings(settings: LLMSettings):
    overrides = settings.model_dump(exclude_none=True)
    update_runtime_settings(overrides)
    _propagate_live2d(overrides)
    current = get_runtime_settings()
    return SettingsResponse(
        data=LLMSettings(**{k: v for k, v in current.items()}),
        config_file=get_config_file_path(),
        message="设置已保存到文件"
    )


@router.post("/reset")
async def reset_settings():
    reset_to_defaults()
    current = get_runtime_settings()
    return SettingsResponse(
        data=LLMSettings(**{k: v for k, v in current.items()}),
        config_file=get_config_file_path(),
        message="已重置为默认设置"
    )
