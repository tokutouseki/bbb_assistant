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


class SettingsResponse(BaseModel):
    success: bool = True
    data: LLMSettings
    config_file: str = ""
    message: str = "ok"


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
