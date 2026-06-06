#!/usr/bin/env python3
"""
崩坏3专属AI陪伴助手 - 后端主入口
基于FastAPI的AI多模态服务，集成YOLO11n游戏场景识别、语音处理、大模型API等
"""

import os
import sys
import asyncio
import signal
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

# 配置标准logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import Settings, get_settings
from src.api import chat, vision, audio, memory, health, rag
from src.api.settings import router as settings_router
from src.api.live2d import router as live2d_router
from src.services.game_monitor import GameMonitor
from src.services.chat_service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    logger.info("崩坏3专属AI陪伴助手后端服务启动中...")
    
    # 启动时初始化
    settings = get_settings()
    
    # 日志已经在文件顶部配置
    logger.info(f"日志配置完成: {settings.log_level}")
    
    logger.info(f"应用配置加载完成: {settings.app_name} v{settings.app_version}")
    logger.info(f"运行环境: {settings.environment}")
    logger.info(f"数据库: {settings.database_url}")
    logger.info(f"API地址: http://{settings.host}:{settings.port}")
    
    # 统一外部模型目录（OCR等组件会读取该缓存目录）
    os.environ["PADDLEOCR_HOME"] = settings.ocr_models_dir
    
    # 初始化AI模型（按需加载）
    if settings.load_models_on_startup:
        logger.info("正在初始化AI模型...")
        await initialize_ai_models(settings)
    
    # 启动后台服务
    if settings.enable_game_monitor:
        logger.info("启动游戏监控服务...")
        game_monitor = GameMonitor()
        app.state.game_monitor = game_monitor
        game_monitor.start_monitoring()
    
    if settings.enable_chat_service:
        logger.info("初始化聊天服务...")
        chat_service = ChatService()
        app.state.chat_service = chat_service

    # 启动 Qwen3-TTS worker 子进程（后台，不阻塞启动）
    if settings.enable_audio:
        import threading
        def _start_tts_worker():
            try:
                from src.modules.audio.call_qwen3_tts import start_worker
                logger.info("正在启动 TTS worker 子进程（后台）...")
                ok = start_worker(quantize=settings.qwen3_tts_quantize)
                if ok:
                    logger.info("TTS worker 子进程启动成功")
                else:
                    logger.warning("TTS worker 子进程启动失败，TTS功能可能不可用")
            except Exception as e:
                logger.warning(f"TTS worker 子进程启动异常: {e}")
        threading.Thread(target=_start_tts_worker, daemon=True).start()

    yield
    
    # 关闭时清理
    logger.info("崩坏3专属AI陪伴助手后端服务关闭中...")
    
    if hasattr(app.state, 'game_monitor'):
        app.state.game_monitor.stop_monitoring()
    
    if hasattr(app.state, 'chat_service'):
        logger.info("聊天服务已清理")

    # 关闭 TTS worker 子进程
    try:
        from src.modules.audio.call_qwen3_tts import stop_worker
        stop_worker()
    except Exception:
        pass
    
    logger.info("服务已安全关闭")


async def initialize_ai_models(settings: Settings):
    """
    初始化AI模型
    按需加载，避免启动时加载所有模型
    """
    from src.modules.utils.config_manager import ConfigManager
    
    config_manager = ConfigManager()
    
    # 预加载配置
    await config_manager.load_configs()
    
    logger.info("AI模型初始化完成（按需加载）")


def create_application() -> FastAPI:
    """
    创建FastAPI应用
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="崩坏3专属AI陪伴助手后端API服务",
        version=settings.app_version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_openapi else None,
        lifespan=lifespan,
    )
    
    # 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 静态文件
    if settings.enable_static_files:
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        if os.path.exists(static_dir):
            app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # 路由（必须在前端静态文件服务之前注册）
    app.include_router(chat.router, prefix="/api/chat", tags=["聊天"])
    app.include_router(vision.router, prefix="/api/vision", tags=["视觉"])
    if settings.enable_audio:
        app.include_router(audio.router, prefix="/api/audio", tags=["音频"])
    else:
        logger.info("音频功能已禁用，跳过 audio API 路由注册")
    app.include_router(memory.router, prefix="/api/memory", tags=["记忆"])
    app.include_router(health.router, prefix="/api/health", tags=["健康检查"])
    app.include_router(rag.router, prefix="/api", tags=["RAG检索"])
    app.include_router(settings_router, prefix="/api/settings", tags=["设置"])
    app.include_router(live2d_router, prefix="/api/live2d", tags=["Live2D"])
    
    # 前端页面静态文件服务（挂载到 /frontend 路径，避免覆盖 API 路由）
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
    if os.path.exists(frontend_dir):
        app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    
    # 根路径重定向到前端
    @app.get("/")
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/frontend")
    
    return app


# 创建应用实例
app = create_application()


def run_api():
    """
    运行API服务器
    """
    settings = get_settings()
    
    # 配置信号处理
    def signal_handler(sig, frame):
        logger.info(f"收到信号 {sig}，正在关闭服务器...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务器
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.enable_reload,
        log_level=settings.uvicorn_log_level,
        access_log=settings.enable_access_log,
    )


def check_admin():
    """
    检查当前进程是否以管理员身份运行，如果不是则尝试自动提权
    """
    import ctypes
    
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    
    if not is_admin:
        print("⚠️ 当前程序未以管理员身份运行")
        print("窗口聚焦等功能需要管理员权限")
        print("正在尝试自动提权...")
        
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            print("请在弹出的UAC提示中选择'是'以继续...")
            time.sleep(2)
        except Exception as e:
            print(f"❌ 自动提权失败: {e}")
            print("请手动右键点击程序并选择'以管理员身份运行'")
        
        print("继续以普通用户身份运行...")
        return False
    
    print("✅ 已以管理员身份运行")
    return True


def main():
    """
    主函数
    """
    print("=" * 60)
    print("崩坏3专属AI陪伴助手 - 后端服务")
    print(f"版本: {get_settings().app_version}")
    print("=" * 60)
    
    # 检查管理员权限
    check_admin()
    
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("错误: 需要Python 3.10或更高版本")
        sys.exit(1)
    
    # 检查依赖
    try:
        import fastapi
        import uvicorn
    except ImportError as e:
        print(f"错误: 缺少依赖 - {e}")
        print("请运行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 运行API服务器
    run_api()


if __name__ == "__main__":
    main()