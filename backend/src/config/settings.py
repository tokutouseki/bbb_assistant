"""
崩坏3专属AI陪伴助手 - 配置管理
基于Pydantic Settings管理应用配置
"""

import os
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, RedisDsn, PostgresDsn, HttpUrl


class Settings(BaseSettings):
    """
    应用配置
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 应用基础配置
    app_name: str = "崩坏3专属AI陪伴助手"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", description="运行环境: development, testing, production")
    debug: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=8000, description="服务器监听端口")
    workers: int = Field(default=1, description="工作进程数")
    enable_reload: bool = Field(default=False, description="启用热重载")
    enable_access_log: bool = Field(default=True, description="启用访问日志")
    
    # API配置
    api_prefix: str = Field(default="/api", description="API前缀")
    enable_docs: bool = Field(default=True, description="启用API文档")
    enable_openapi: bool = Field(default=True, description="启用OpenAPI")
    
    # 跨域配置
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
        description="允许的跨域来源"
    )
    
    # 数据库配置
    database_url: str = Field(
        default="sqlite:///./data/bbb_assistant.db",
        description="数据库连接URL"
    )
    database_echo: bool = Field(default=False, description="SQL日志")
    
    # Redis配置
    redis_url: Optional[RedisDsn] = Field(default=None, description="Redis连接URL")
    redis_password: Optional[str] = Field(default=None, description="Redis密码")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: Optional[str] = Field(default="./logs/app.log", description="日志文件路径")
    log_rotation: str = Field(default="10 MB", description="日志轮转大小")
    log_retention: str = Field(default="30 days", description="日志保留时间")
    
    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="加密密钥"
    )
    algorithm: str = Field(default="HS256", description="加密算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间")
    
    # AI模型配置
    load_models_on_startup: bool = Field(default=False, description="启动时加载AI模型")
    model_assets_root: str = Field(default="D:/TokusCode/models", description="外部模型根目录")
    asr_model_path: str = Field(default="D:/TokusCode/models/SenseVoiceSmall", description="ASR模型路径")
    voxcpm_model_path: str = Field(default="D:/TokusCode/models/VoxCPM-0.5B", description="VoxCPM模型路径")
    qwen3_tts_model_path: str = Field(default="D:/TokusCode/models/Qwen3-TTS", description="Qwen3-TTS模型路径")
    ocr_models_dir: str = Field(default="D:/TokusCode/models/OCR", description="OCR模型/缓存目录")
    
    # YOLO11n配置
    yolo_model_path: str = Field(default="./data/models/yolo/yolo11n.pt", description="YOLO11n模型路径")
    yolo_models_root: str = Field(default="./data/models", description="YOLO模型根目录")
    yolo_conf_threshold: float = Field(default=0.5, description="YOLO置信度阈值")
    yolo_iou_threshold: float = Field(default=0.45, description="YOLO IOU阈值")
    
    # OCR配置
    ocr_language: str = Field(default="ch", description="OCR语言: ch, en, jp, etc.")
    ocr_use_gpu: bool = Field(default=True, description="OCR使用GPU")
    
    # 语音识别配置
    asr_model: str = Field(default="base", description="Whisper模型: tiny, base, small, medium, large")
    asr_language: str = Field(default="zh", description="ASR语言")
    
    # 语音合成配置
    tts_model: str = Field(default="tts_models/zh-CN/baker/tacotron2-DDC", description="TTS模型")
    tts_speaker_wav: Optional[str] = Field(default=None, description="语音克隆参考音频")
    
    # 大模型配置
    llm_provider: str = Field(default="deepseek", description="大模型提供商: deepseek, kimi, openai")
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API密钥")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", description="DeepSeek API基础URL")
    kimi_api_key: Optional[str] = Field(default=None, description="Kimi API密钥")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI API基础URL")
    llm_model: str = Field(default="deepseek-chat", description="大模型名称")
    llm_temperature: float = Field(default=0.7, description="大模型温度")
    llm_max_tokens: int = Field(default=2000, description="大模型最大令牌数")
    llm_runtime: str = Field(default="auto", description="LLM运行方式: local, lmstudio, ollama, api, auto")
    llm_local_model_path: Optional[str] = Field(default=None, description="本地GGUF模型文件路径")
    llm_local_mmproj_path: Optional[str] = Field(default=None, description="本地多模态mmproj文件路径")
    llm_local_models_dir: str = Field(default="./models", description="本地GGUF模型目录")
    llm_local_context_length: int = Field(default=4096, description="本地模型上下文长度")
    llm_local_gpu_layers: int = Field(default=0, description="本地模型GPU层数，0表示CPU")
    llm_local_threads: int = Field(default=6, description="本地模型CPU线程数")
    lm_studio_base_url: str = Field(default="http://127.0.0.1:1234", description="LM Studio服务地址")
    lm_studio_model: str = Field(default="qwen3.5-4b", description="LM Studio模型标识")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", description="Ollama服务地址")
    ollama_model: str = Field(default="qwen2.5:7b", description="Ollama模型标识")
    
    # RAG配置
    rag_enabled: bool = Field(default=True, description="启用RAG检索增强")
    rag_data_path: str = Field(default="../data", description="知识库数据路径")
    rag_index_path: str = Field(default="../data/rag_index", description="RAG索引存储路径")
    rag_default_mode: str = Field(default="hybrid", description="默认检索模式: fast, precise, hybrid")
    rag_default_top_k: int = Field(default=5, description="默认返回结果数量")
    rag_context_max_length: int = Field(default=2000, description="上下文最大长度")
    
    # ChromaDB向量数据库配置
    chroma_persist_directory: str = Field(default="../data/chroma_db", description="ChromaDB持久化目录")
    chroma_collection: str = Field(default="bbb_knowledge", description="ChromaDB集合名称")
    
    # 嵌入模型配置
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2", description="嵌入模型名称")
    embedding_model_path: str = Field(default="./paraphrase-multilingual-MiniLM-L12-v2", description="本地嵌入模型路径")
    embedding_device: str = Field(default="cpu", description="嵌入模型运行设备: cpu, cuda")
    embedding_cache_enabled: bool = Field(default=True, description="启用嵌入缓存")
    embedding_offline_mode: bool = Field(default=True, description="嵌入模型离线模式")
    
    # 游戏监控配置
    enable_game_monitor: bool = Field(default=True, description="启用游戏监控")
    game_monitor_interval: float = Field(default=1.0, description="游戏监控间隔(秒)")
    game_window_title: str = Field(default="崩坏3", description="游戏窗口标题")
    
    # 聊天服务配置
    enable_chat_service: bool = Field(default=True, description="启用聊天服务")
    chat_history_limit: int = Field(default=50, description="聊天历史限制")
    
    # 音频处理配置
    enable_audio: bool = Field(default=False, description="启用音频处理功能（ASR/TTS）")
    enable_asr: bool = Field(default=False, description="启用语音识别（SenseVoiceSmall）")
    enable_tts: bool = Field(default=False, description="启用文本转语音（Qwen3-TTS/VoxCPM）")
    
    # 记忆配置
    memory_enabled: bool = Field(default=True, description="启用对话记忆")
    memory_store_path: str = Field(default="./data/memory", description="记忆存储路径")
    memory_retention_days: int = Field(default=30, description="记忆保留天数")
    
    # 文件存储配置
    upload_dir: str = Field(default="./data/uploads", description="文件上传目录")
    max_upload_size: int = Field(default=100 * 1024 * 1024, description="最大上传大小(字节)")
    
    # 静态文件配置
    enable_static_files: bool = Field(default=True, description="启用静态文件服务")
    static_dir: str = Field(default="./static", description="静态文件目录")
    
    # WebSocket配置
    websocket_enabled: bool = Field(default=True, description="启用WebSocket")
    websocket_ping_interval: float = Field(default=30.0, description="WebSocket Ping间隔")
    
    # 性能配置
    request_timeout: int = Field(default=30, description="请求超时时间(秒)")
    max_concurrent_requests: int = Field(default=100, description="最大并发请求数")
    
    # 搜索配置
    default_search_engine: str = Field(default="google", description="默认搜索引擎: google, duckduckgo, miyoushe, honkai_official")
    miyoushe_search_url: str = Field(default="https://www.miyoushe.com/bh3/search?keyword=", description="米游社搜索URL")
    honkai_official_url: str = Field(default="https://bh3.mihoyo.com/main", description="崩坏3官网URL")

    # 图片描述配置
    image_describer_backend: str = Field(default="bailian", description="图片描述后端优先级(bailian/pixai_tagger/lmstudio)")
    bailian_api_key: Optional[str] = Field(default=None, description="阿里百炼API密钥")
    bailian_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", description="阿里百炼兼容OpenAI接口地址")
    bailian_vision_model: str = Field(default="qwen-vl-plus", description="阿里百炼视觉模型: qwen-vl-plus, qwen-vl-max")
    pixai_tagger_model_path: str = Field(default="D:/TokusCode/models/PixAI-Tagger", description="PixAI Tagger模型目录路径")
    
    # Uvicorn日志级别
    uvicorn_log_level: str = Field(default="info", description="Uvicorn日志级别")
    
    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "testing", "production"]
        if v not in allowed:
            raise ValueError(f"环境必须是: {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"日志级别必须是: {allowed}")
        return v.upper()
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v, values):
        if "sqlite" in v and not v.startswith("sqlite:///"):
            # 确保SQLite路径是绝对路径
            db_path = v.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                # 转换为相对于项目根目录的路径
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                v = f"sqlite:///{os.path.join(project_root, db_path)}"
        return v
    
    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        """是否测试环境"""
        return self.environment == "testing"
    
    @property
    def llm_api_key(self) -> Optional[str]:
        """获取当前配置的大模型API密钥"""
        if self.llm_provider == "deepseek":
            return self.deepseek_api_key
        elif self.llm_provider == "kimi":
            return self.kimi_api_key
        elif self.llm_provider == "openai":
            return self.openai_api_key
        return None
    
    @property
    def llm_base_url(self) -> Optional[str]:
        """获取当前配置的大模型基础URL"""
        if self.llm_provider == "deepseek":
            return self.deepseek_base_url
        elif self.llm_provider == "openai" and self.openai_base_url:
            return self.openai_base_url
        return None
    
    def get_game_scenes_config(self) -> Dict[str, Any]:
        """获取游戏场景配置"""
        from .game_scenes import GAME_SCENES
        return GAME_SCENES
    
    def get_characters_config(self) -> Dict[str, Any]:
        """获取角色配置"""
        from .characters import CHARACTERS
        return CHARACTERS


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    获取配置实例（单例模式）
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    重新加载配置
    """
    global _settings
    _settings = Settings()
    return _settings