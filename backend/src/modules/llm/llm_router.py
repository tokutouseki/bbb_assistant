"""
LLM路由器 - 智能模型选择和切换
根据任务类型、复杂度、成本等因素选择最合适的模型
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass, field

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型枚举"""
    DEEPSEEK_V3_API = "deepseek_v3_api"  # DeepSeek V3 云端API
    LM_STUDIO = "lm_studio"             # LM Studio本地服务
    LOCAL_GGUF = "local_gguf"           # 本地GGUF模型（直接加载）
    OLLAMA = "ollama"                   # Ollama本地服务


class TaskType(Enum):
    """任务类型枚举"""
    CASUAL_CHAT = "casual_chat"         # 日常聊天
    GAME_GUIDE = "game_guide"           # 游戏攻略查询
    COMPLEX_REASONING = "complex_reasoning"  # 复杂推理
    CODE_GENERATION = "code_generation" # 代码生成
    TRANSLATION = "translation"         # 翻译
    SUMMARIZATION = "summarization"     # 摘要生成
    EMOTIONAL_SUPPORT = "emotional_support"  # 情感支持


class ModelPriority(Enum):
    """模型优先级"""
    HIGH = "high"      # 高性能，高成本
    MEDIUM = "medium"  # 平衡性能与成本
    LOW = "low"        # 低成本，可能性能较低


@dataclass
class ModelInfo:
    """模型信息"""
    model_type: ModelType
    model_id: str
    display_name: str
    priority: ModelPriority
    capabilities: List[TaskType]
    cost_per_token: float = 0.0  # 每token成本（美元）
    max_tokens: int = 4096
    supports_streaming: bool = True
    requires_api_key: bool = False
    requires_internet: bool = False
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskContext:
    """任务上下文"""
    task_type: TaskType
    message_length: int = 0
    requires_streaming: bool = False
    requires_low_latency: bool = False
    budget_limit: Optional[float] = None  # 成本预算限制
    internet_available: bool = True
    user_preference: Optional[str] = None  # 用户偏好


class LLMRouter:
    """LLM路由器，负责智能模型选择"""
    
    def __init__(self):
        self.models: Dict[str, ModelInfo] = {}
        self.model_clients: Dict[str, Any] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.settings = get_settings()
        self.preferred_runtime = (self.settings.llm_runtime or "auto").lower()
        self._initialize_default_models()
        logger.info("LLM路由器初始化完成")
    
    def _initialize_default_models(self):
        """初始化默认模型配置"""
        all_capabilities = [
            TaskType.CASUAL_CHAT,
            TaskType.GAME_GUIDE,
            TaskType.COMPLEX_REASONING,
            TaskType.CODE_GENERATION,
            TaskType.TRANSLATION,
            TaskType.SUMMARIZATION,
            TaskType.EMOTIONAL_SUPPORT,
        ]

        # 1) API模型（最高优先级）
        if self.settings.deepseek_api_key:
            self.register_model(
                model_info=ModelInfo(
                    model_type=ModelType.DEEPSEEK_V3_API,
                    model_id="deepseek-api-default",
                    display_name=f"DeepSeek API ({self.settings.llm_model})",
                    priority=ModelPriority.HIGH,
                    capabilities=all_capabilities,
                    cost_per_token=0.000002,
                    max_tokens=max(self.settings.llm_max_tokens, 4096),
                    supports_streaming=True,
                    requires_api_key=True,
                    requires_internet=True,
                    config={
                        "api_key": self.settings.deepseek_api_key,
                        "base_url": self.settings.deepseek_base_url,
                        "model": self.settings.llm_model,
                        "timeout": 60,
                    },
                )
            )

        # 2) LM Studio / Ollama
        self.register_model(
            model_info=ModelInfo(
                model_type=ModelType.LM_STUDIO,
                model_id="lm-studio-default",
                display_name="Qwen (LM Studio)",
                priority=ModelPriority.MEDIUM,
                capabilities=all_capabilities,
                cost_per_token=0.0,
                max_tokens=4096,
                supports_streaming=True,
                requires_api_key=False,
                requires_internet=False,
                config={
                    "base_url": self.settings.lm_studio_base_url,
                    "model": self.settings.lm_studio_model,
                    "timeout": 120,
                },
            )
        )
        self.register_model(
            model_info=ModelInfo(
                model_type=ModelType.OLLAMA,
                model_id="ollama-default",
                display_name=f"Ollama ({self.settings.ollama_model})",
                priority=ModelPriority.MEDIUM,
                capabilities=all_capabilities,
                cost_per_token=0.0,
                max_tokens=4096,
                supports_streaming=True,
                requires_api_key=False,
                requires_internet=False,
                config={
                    "base_url": self.settings.ollama_base_url,
                    "model": self.settings.ollama_model,
                    "timeout": 120,
                },
            )
        )

        # 3) 本地GGUF（最后兜底）
        local_model_path = self._resolve_local_model_path()
        if local_model_path:
            self.register_model(
                model_info=ModelInfo(
                    model_type=ModelType.LOCAL_GGUF,
                    model_id="local-gguf-default",
                    display_name=f"Local GGUF ({os.path.basename(local_model_path)})",
                    priority=ModelPriority.LOW,
                    capabilities=all_capabilities,
                    cost_per_token=0.0,
                    max_tokens=self.settings.llm_local_context_length,
                    supports_streaming=True,
                    requires_api_key=False,
                    requires_internet=False,
                    config={
                        "model_path": local_model_path,
                        "mmproj_path": self.settings.llm_local_mmproj_path,
                        "context_length": self.settings.llm_local_context_length,
                        "temperature": self.settings.llm_temperature,
                        "gpu_layers": self.settings.llm_local_gpu_layers,
                        "n_threads": self.settings.llm_local_threads,
                        "verbose": False,
                    },
                )
            )
            logger.info(f"已注册本地GGUF模型: {local_model_path}")
        else:
            logger.warning("未发现本地GGUF模型，local模式下将无法直接推理")
        
        # LM Studio DeepSeek R1模型 (备用方案，已禁用，专注于Qwen模型)
        # self.register_model(
        #     model_info=ModelInfo(
        #         model_type=ModelType.LM_STUDIO,
        #         model_id="lm-studio-deepseek-r1",
        #         display_name="DeepSeek R1 (LM Studio)",
        #         priority=ModelPriority.MEDIUM,
        #         capabilities=[
        #             TaskType.CASUAL_CHAT,
        #             TaskType.GAME_GUIDE,
        #             TaskType.COMPLEX_REASONING,
        #             TaskType.CODE_GENERATION,
        #             TaskType.TRANSLATION,
        #             TaskType.SUMMARIZATION,
        #             TaskType.EMOTIONAL_SUPPORT
        #         ],
        #         cost_per_token=0.0,  # 本地运行，无直接成本
        #         max_tokens=4096,
        #         supports_streaming=True,
        #         requires_api_key=False,
        #         requires_internet=False,  # LM Studio是本地服务
        #         config={
        #             "base_url": "http://192.168.104.210:1234",  # 用户提供的地址
        #             "model": "deepseek/deepseek-r1-0528-qwen3-8b",  # 已加载的模型
        #             "timeout": 120  # LM Studio可能需要更长时间
        #         }
        #     )
        # )
        
    def _resolve_local_model_path(self) -> Optional[str]:
        """解析本地GGUF模型路径：显式路径优先，否则目录自动发现。"""
        explicit_path = self.settings.llm_local_model_path
        if explicit_path and os.path.exists(explicit_path):
            return explicit_path

        models_dir = self.settings.llm_local_models_dir
        if not os.path.isabs(models_dir):
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            models_dir = os.path.join(backend_root, models_dir)

        if not os.path.exists(models_dir):
            return None

        gguf_files: List[str] = []
        for root, _, files in os.walk(models_dir):
            for file in files:
                if file.lower().endswith(".gguf"):
                    gguf_files.append(os.path.join(root, file))

        if not gguf_files:
            return None

        gguf_files.sort(key=lambda p: os.path.getsize(p), reverse=True)
        return gguf_files[0]
    
    def register_model(self, model_info: ModelInfo):
        """
        注册模型
        
        Args:
            model_info: 模型信息
        """
        self.models[model_info.model_id] = model_info
        logger.info(f"注册模型: {model_info.display_name} ({model_info.model_id})")
    
    def register_model_client(self, model_id: str, client: Any):
        """
        注册模型客户端
        
        Args:
            model_id: 模型ID
            client: 模型客户端实例
        """
        self.model_clients[model_id] = client
        logger.info(f"注册模型客户端: {model_id}")
    
    def select_model(
        self,
        task_context: TaskContext,
        available_models: Optional[List[str]] = None
    ) -> Optional[ModelInfo]:
        """
        选择最适合的模型
        
        Args:
            task_context: 任务上下文
            available_models: 可用的模型ID列表，如果为None则使用所有注册的模型
            
        Returns:
            选中的模型信息，如果没有合适的模型则返回None
        """
        if available_models is None:
            available_models = list(self.models.keys())
        
        # 过滤可用的模型
        candidate_models = []
        for model_id in available_models:
            if model_id in self.models:
                model = self.models[model_id]
                
                # 检查模型是否支持当前任务类型
                if task_context.task_type not in model.capabilities:
                    continue
                
                # 检查网络要求
                if model.requires_internet and not task_context.internet_available:
                    continue
                
                # 检查流式支持要求
                if task_context.requires_streaming and not model.supports_streaming:
                    continue
                
                # 检查预算限制
                if task_context.budget_limit is not None:
                    estimated_cost = self._estimate_cost(model, task_context)
                    if estimated_cost > task_context.budget_limit:
                        continue
                
                candidate_models.append(model)
        
        if not candidate_models:
            logger.warning(f"没有找到适合任务类型 {task_context.task_type} 的模型")
            return None
        
        # 根据优先级和任务类型选择模型
        selected_model = self._rank_and_select_model(candidate_models, task_context)
        
        logger.info(f"选择模型: {selected_model.display_name} ({selected_model.model_id}) "
                   f"用于任务类型: {task_context.task_type}")
        
        return selected_model
    
    def _rank_and_select_model(
        self,
        candidate_models: List[ModelInfo],
        task_context: TaskContext
    ) -> ModelInfo:
        """
        对候选模型进行排名并选择
        
        Args:
            candidate_models: 候选模型列表
            task_context: 任务上下文
            
        Returns:
            选中的模型
        """
        # 计算每个模型的得分
        model_scores = []
        for model in candidate_models:
            score = 0.0
            
            # 1. 优先级权重
            priority_weights = {
                ModelPriority.HIGH: 10.0,
                ModelPriority.MEDIUM: 7.0,
                ModelPriority.LOW: 4.0
            }
            score += priority_weights.get(model.priority, 5.0)
            
            # 2. 成本考虑（成本越低越好）
            if model.cost_per_token > 0:
                # 将成本转换为得分（成本越低得分越高）
                cost_score = 10.0 / (1.0 + model.cost_per_token * 1000000)  # 每百万token的成本
                score += cost_score
            
            # 3. 延迟考虑
            if task_context.requires_low_latency:
                # 本地模型通常延迟更低
                if model.model_type == ModelType.LOCAL_GGUF:
                    score += 5.0
                elif not model.requires_internet:
                    score += 3.0
            
            # 4. 用户偏好
            if task_context.user_preference and task_context.user_preference == model.model_id:
                score += 8.0

            # 4.5 运行时偏好
            if self.preferred_runtime == "api" and model.model_type == ModelType.DEEPSEEK_V3_API:
                score += 20.0
            elif self.preferred_runtime == "lmstudio" and model.model_type == ModelType.LM_STUDIO:
                score += 20.0
            elif self.preferred_runtime == "ollama" and model.model_type == ModelType.OLLAMA:
                score += 20.0
            elif self.preferred_runtime == "local" and model.model_type == ModelType.LOCAL_GGUF:
                score += 20.0
            elif self.preferred_runtime == "auto":
                # 自动模式：API > LM Studio/Ollama > Local
                if model.model_type == ModelType.DEEPSEEK_V3_API:
                    score += 15.0
                elif model.model_type in [ModelType.LM_STUDIO, ModelType.OLLAMA]:
                    score += 10.0
                elif model.model_type == ModelType.LOCAL_GGUF:
                    score += 5.0
            
            # 5. 任务类型适配
            # 复杂推理任务优先选择高性能模型
            if task_context.task_type == TaskType.COMPLEX_REASONING:
                if model.model_type == ModelType.DEEPSEEK_V3_API:
                    score += 6.0
            # 日常聊天可以使用本地模型节省成本
            elif task_context.task_type == TaskType.CASUAL_CHAT:
                if model.model_type == ModelType.LOCAL_GGUF:
                    score += 4.0
            
            model_scores.append((model, score))
        
        # 按得分排序
        model_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 记录选择过程（用于调试和分析）
        selection_log = {
            "task_type": task_context.task_type.value,
            "timestamp": time.time(),
            "candidates": [
                {
                    "model_id": model.model_id,
                    "score": score,
                    "priority": model.priority.value
                }
                for model, score in model_scores
            ]
        }
        self.task_history.append(selection_log)
        
        # 返回得分最高的模型
        return model_scores[0][0]
    
    def _estimate_cost(self, model: ModelInfo, task_context: TaskContext) -> float:
        """
        估算任务成本
        
        Args:
            model: 模型信息
            task_context: 任务上下文
            
        Returns:
            估算的成本（美元）
        """
        # 简单估算：假设平均每个中文字符 = 0.5 token
        estimated_tokens = task_context.message_length * 0.5
        
        # 加上响应token的估算（假设响应与输入等长）
        estimated_total_tokens = estimated_tokens * 2
        
        cost = estimated_total_tokens * model.cost_per_token
        
        return cost
    
    def route_request(
        self,
        messages: List[Dict[str, str]],
        task_type: Union[TaskType, str],
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        路由请求到合适的模型
        
        Args:
            messages: 消息列表
            task_type: 任务类型
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            模型响应
        """
        start_time = time.time()
        
        # 转换任务类型
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                # 默认使用日常聊天
                task_type = TaskType.CASUAL_CHAT
                logger.warning(f"未知的任务类型: {task_type}，使用默认类型: CASUAL_CHAT")
        
        # 构建任务上下文
        total_message_length = sum(len(msg.get("content", "")) for msg in messages)
        
        task_context = TaskContext(
            task_type=task_type,
            message_length=total_message_length,
            requires_streaming=stream,
            requires_low_latency=kwargs.get("low_latency", False),
            budget_limit=kwargs.get("budget_limit"),
            internet_available=kwargs.get("internet_available", True),
            user_preference=kwargs.get("user_preference")
        )
        
        # 选择模型
        selected_model = self.select_model(task_context)
        
        if not selected_model:
            return {
                "error": "没有可用的模型处理此请求",
                "suggestions": ["请检查网络连接", "确认已配置API密钥", "尝试使用不同的任务类型"]
            }
        
        # 获取模型客户端
        client = self.model_clients.get(selected_model.model_id)
        if not client:
            # 如果客户端未注册，尝试创建
            client = self._create_model_client(selected_model)
            if client:
                self.register_model_client(selected_model.model_id, client)
        
        if not client:
            if kwargs.get("fallback", True):
                return self._try_fallback_model(
                    original_model_id=selected_model.model_id,
                    messages=messages,
                    task_context=task_context,
                    stream=stream,
                    **kwargs
                )
            return {
                "error": f"模型客户端未就绪: {selected_model.display_name}",
                "model_id": selected_model.model_id
            }
        
        try:
            # 调用模型
            response = self._call_model_client(
                client=client,
                model_info=selected_model,
                messages=messages,
                stream=stream,
                **kwargs
            )
            
            # 记录成功请求
            request_log = {
                "timestamp": time.time(),
                "model_id": selected_model.model_id,
                "task_type": task_type.value,
                "message_count": len(messages),
                "processing_time": time.time() - start_time,
                "success": True
            }
            self.task_history.append(request_log)
            
            # 添加模型信息到响应
            if isinstance(response, dict):
                response["model_info"] = {
                    "id": selected_model.model_id,
                    "name": selected_model.display_name,
                    "type": selected_model.model_type.value
                }
            
            return response
            
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            
            # 记录失败请求
            error_log = {
                "timestamp": time.time(),
                "model_id": selected_model.model_id,
                "task_type": task_type.value,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "success": False
            }
            self.task_history.append(error_log)
            
            # 尝试使用备用模型
            if kwargs.get("fallback", True):
                return self._try_fallback_model(
                    original_model_id=selected_model.model_id,
                    messages=messages,
                    task_context=task_context,
                    stream=stream,
                    **kwargs
                )
            
            return {
                "error": f"模型调用失败: {str(e)}",
                "model_id": selected_model.model_id
            }
    
    def _create_model_client(self, model_info: ModelInfo) -> Optional[Any]:
        """
        创建模型客户端
        
        Args:
            model_info: 模型信息
            
        Returns:
            模型客户端实例，如果创建失败则返回None
        """
        try:
            if model_info.model_type == ModelType.DEEPSEEK_V3_API:
                from .deepseek_client import create_deepseek_client
                
                api_key = model_info.config.get("api_key")
                if not api_key:
                    # 尝试从环境变量获取
                    import os
                    api_key = os.environ.get("DEEPSEEK_API_KEY")
                
                client = create_deepseek_client(
                    api_key=api_key,
                    config=model_info.config
                )
                return client
                
            elif model_info.model_type == ModelType.LM_STUDIO:
                from .lm_studio_client import create_lm_studio_client
                
                client = create_lm_studio_client(
                    base_url=model_info.config.get("base_url"),
                    model=model_info.config.get("model"),
                    config=model_info.config
                )
                
                # 测试连接
                if not client.test_connection():
                    logger.error(f"LM Studio连接失败: {model_info.config.get('base_url')}")
                    return None
                
                return client
                
            elif model_info.model_type == ModelType.LOCAL_GGUF:
                from .local_model_client import create_local_model_client
                
                model_path = model_info.config.get("model_path")
                if not model_path:
                    logger.error(f"本地模型路径未配置: {model_info.model_id}")
                    return None
                
                # 从配置中移除已显式传递的参数
                config_copy = model_info.config.copy()
                config_copy.pop("model_path", None)
                config_copy.pop("model_name", None)
                
                client = create_local_model_client(
                    model_path=model_path,
                    model_name=model_info.display_name,
                    **config_copy
                )
                
                # 尝试加载模型
                if not client.load_model():
                    logger.error(f"本地模型加载失败: {model_path}")
                    return None
                
                return client
            elif model_info.model_type == ModelType.OLLAMA:
                from .ollama_client import create_ollama_client

                client = create_ollama_client(
                    base_url=model_info.config.get("base_url"),
                    model=model_info.config.get("model"),
                    config=model_info.config
                )
                if not client.test_connection():
                    logger.error(f"Ollama连接失败: {model_info.config.get('base_url')}")
                    return None
                return client
                
            else:
                logger.error(f"不支持的模型类型: {model_info.model_type}")
                return None
                
        except Exception as e:
            logger.error(f"创建模型客户端失败: {e}")
            return None
    
    def _call_model_client(
        self,
        client: Any,
        model_info: ModelInfo,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        调用模型客户端
        
        Args:
            client: 模型客户端实例
            model_info: 模型信息
            messages: 消息列表
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            模型响应
        """
        # 根据模型类型调用不同的方法
        if model_info.model_type == ModelType.DEEPSEEK_V3_API:
            return client.chat_completion(
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens"),
                stream=stream,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
        elif model_info.model_type == ModelType.LM_STUDIO:
            return client.chat_completion(
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens"),
                stream=stream,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
        elif model_info.model_type == ModelType.LOCAL_GGUF:
            return client.chat_completion(
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 512),
                stream=stream,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
        elif model_info.model_type == ModelType.OLLAMA:
            return client.chat_completion(
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens"),
                stream=stream,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
        else:
            raise ValueError(f"不支持的模型类型: {model_info.model_type}")
    
    def _try_fallback_model(
        self,
        original_model_id: str,
        messages: List[Dict[str, str]],
        task_context: TaskContext,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        尝试使用备用模型
        
        Args:
            original_model_id: 原始模型ID
            messages: 消息列表
            task_context: 任务上下文
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            备用模型响应或错误信息
        """
        logger.info(f"尝试使用备用模型，原始模型: {original_model_id}")
        
        # 排除原始模型
        available_models = [mid for mid in self.models.keys() if mid != original_model_id]
        
        # 重新选择模型
        selected_model = self.select_model(task_context, available_models)
        
        if not selected_model:
            return {
                "error": "备用模型不可用",
                "original_error": "模型调用失败",
                "suggestion": "请检查网络连接和模型配置"
            }
        
        # 获取备用模型客户端
        client = self.model_clients.get(selected_model.model_id)
        if not client:
            client = self._create_model_client(selected_model)
            if client:
                self.register_model_client(selected_model.model_id, client)
        
        if not client:
            return {
                "error": "备用模型客户端创建失败",
                "fallback_model_id": selected_model.model_id
            }
        
        try:
            response = self._call_model_client(
                client=client,
                model_info=selected_model,
                messages=messages,
                stream=stream,
                **kwargs
            )
            
            # 添加备用模型标记
            if isinstance(response, dict):
                response["is_fallback"] = True
                response["original_model_id"] = original_model_id
                response["fallback_model_id"] = selected_model.model_id
            
            logger.info(f"备用模型调用成功: {selected_model.display_name}")
            return response
            
        except Exception as e:
            logger.error(f"备用模型调用失败: {e}")
            return {
                "error": "所有模型调用均失败",
                "original_error": "模型调用失败",
                "fallback_error": str(e),
                "suggestion": "请检查系统配置并重试"
            }
    
    def get_model_stats(self) -> Dict[str, Any]:
        """
        获取模型使用统计
        
        Returns:
            统计信息
        """
        stats = {
            "total_models": len(self.models),
            "total_requests": len(self.task_history),
            "successful_requests": sum(1 for log in self.task_history if log.get("success", False)),
            "failed_requests": sum(1 for log in self.task_history if not log.get("success", True)),
            "model_usage": {},
            "task_type_distribution": {}
        }
        
        # 统计模型使用情况
        for log in self.task_history:
            model_id = log.get("model_id")
            task_type = log.get("task_type")
            
            if model_id:
                if model_id not in stats["model_usage"]:
                    stats["model_usage"][model_id] = 0
                stats["model_usage"][model_id] += 1
            
            if task_type:
                if task_type not in stats["task_type_distribution"]:
                    stats["task_type_distribution"][task_type] = 0
                stats["task_type_distribution"][task_type] += 1
        
        return stats
    
    def clear_history(self):
        """清空请求历史"""
        self.task_history.clear()
        logger.info("请求历史已清空")


# 全局路由器实例
_global_router = None

def get_llm_router() -> LLMRouter:
    """
    获取全局LLM路由器实例
    
    Returns:
        LLMRouter实例
    """
    global _global_router
    if _global_router is None:
        _global_router = LLMRouter()
    return _global_router