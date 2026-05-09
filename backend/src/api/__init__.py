from fastapi import APIRouter

from . import chat, vision, audio, memory, health, rag

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(rag.router, tags=["rag"])