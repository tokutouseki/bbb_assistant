import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..modules.llm.llm_router import get_llm_router
from ..modules.llm.llm_router import TaskType
from ..modules.tool_integration import LLMToolIntegration
from ..modules.rag import RAGEngine, RAGConfig, SearchMode
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务，集成LLM、RAG、记忆管理和工具集成"""
    
    def __init__(self, enable_tools: bool = True, enable_rag: bool = True):
        self.llm_client = None
        self.rag_engine = None
        self.memory_manager = None
        self.enable_tools = enable_tools
        self.enable_rag = enable_rag
        self.tool_integration = None
        self._initialize_components()
        logger.info("聊天服务初始化完成")
    
    def _initialize_components(self):
        """初始化组件"""
        try:
            # 初始化LLM路由器
            self.llm_router = get_llm_router()
            logger.info("LLM路由器初始化完成")
            
            # 初始化工具集成
            if self.enable_tools:
                try:
                    self.tool_integration = LLMToolIntegration(
                        enable_search=True,
                        enable_crawler=True,
                        enable_audio=False
                    )
                    logger.info("工具集成初始化完成")
                except Exception as e:
                    logger.warning(f"工具集成初始化失败: {e}")
                    self.tool_integration = None
            
            # 初始化RAG引擎
            if self.enable_rag:
                try:
                    settings = get_settings()
                    if settings.rag_enabled:
                        self.rag_config = RAGConfig(
                            data_path=settings.rag_data_path,
                            index_path=settings.rag_index_path,
                            chroma_persist_directory=settings.chroma_persist_directory,
                            chroma_collection=settings.chroma_collection,
                            embedding_model=settings.embedding_model,
                            embedding_device=settings.embedding_device,
                            default_top_k=settings.rag_default_top_k,
                            default_mode=SearchMode(settings.rag_default_mode),
                            context_max_length=settings.rag_context_max_length
                        )
                        self.rag_engine = RAGEngine(self.rag_config)
                        logger.info("RAG引擎配置完成（将在首次使用时初始化）")
                    else:
                        logger.info("RAG功能已禁用")
                except Exception as e:
                    logger.warning(f"RAG引擎配置失败: {e}")
                    self.rag_engine = None
            else:
                logger.info("RAG功能未启用")
            
            # TODO: 初始化记忆管理器
            self.memory_manager = None
            
            logger.info("聊天组件初始化完成")
        except Exception as e:
            logger.error(f"聊天组件初始化失败: {e}")
            raise
    
    async def _ensure_rag_initialized(self):
        """确保RAG引擎已初始化"""
        if self.rag_engine and not self.rag_engine.is_initialized:
            try:
                await self.rag_engine.initialize()
                logger.info("RAG引擎初始化完成")
            except Exception as e:
                logger.error(f"RAG引擎初始化失败: {e}")
                self.rag_engine = None
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                       game_scene: Optional[str] = None,
                       use_rag: bool = True,
                       rag_mode: Optional[str] = None,
                       stream: bool = False) -> Dict[str, Any]:
        """
        聊天补全
        
        Args:
            messages: 消息历史
            game_scene: 当前游戏场景
            use_rag: 是否使用RAG
            rag_mode: RAG模式 (fast/precise/hybrid)
            stream: 是否流式输出
            
        Returns:
            聊天响应
        """
        start_time = time.time()
        
        try:
            # 1. 如果有RAG，检索相关知识
            context = ""
            rag_results = []
            if use_rag and self.rag_engine is not None:
                await self._ensure_rag_initialized()
                last_user_message = self._get_last_user_message(messages)
                if last_user_message and self.rag_engine:
                    try:
                        mode = SearchMode(rag_mode) if rag_mode else None
                        rag_results = await self.rag_engine.search(
                            query=last_user_message,
                            mode=mode
                        )
                        context = self.rag_engine._retriever.format_results_for_context(
                            rag_results,
                            self.rag_config.context_max_length if self.rag_config else 2000
                        )
                        logger.info(f"RAG检索到 {len(rag_results)} 条相关知识")
                    except Exception as e:
                        logger.warning(f"RAG检索失败: {e}")
            
            # 2. 如果有记忆，检索相关记忆
            memory_context = ""
            if self.memory_manager is not None:
                memory_context = self.memory_manager.retrieve_relevant_memories(messages)
            
            # 3. 构建包含系统提示的消息列表
            llm_messages = self._build_llm_messages(messages, context, memory_context, game_scene)
            
            # 4. 根据游戏场景确定任务类型
            task_type = self._determine_task_type(messages, game_scene)
            
            # 5. 调用LLM路由器
            llm_result = self.llm_router.route_request(
                messages=llm_messages,
                task_type=task_type,
                stream=stream
            )
            
            # 6. 提取响应内容
            if isinstance(llm_result, dict) and "error" in llm_result:
                llm_response = llm_result.get("error", "抱歉，处理您的请求时出现了问题。")
            elif isinstance(llm_result, dict) and "content" in llm_result:
                llm_response = llm_result["content"]
            else:
                llm_response = str(llm_result) if llm_result else "抱歉，无法生成响应。"
            
            # 7. 使用工具增强响应（如果需要）
            tool_steps = []
            if self.tool_integration and self._should_use_tools(messages):
                try:
                    last_user_message = self._get_last_user_message(messages)
                    if last_user_message:
                        tool_result = self.tool_integration.enhance_response_with_tools(
                            user_message=last_user_message,
                            llm_response=llm_response,
                            max_tool_calls=2
                        )
                        llm_response = tool_result.get("response", llm_response)
                        tool_steps = tool_result.get("tool_steps", [])
                        logger.info("已使用工具增强响应")
                except Exception as e:
                    logger.warning(f"工具增强响应失败: {e}")
            
            # 8. 保存对话记忆
            if self.memory_manager is not None:
                self.memory_manager.store_conversation(messages, llm_response)
            
            processing_time = time.time() - start_time
            
            return {
                "response": llm_response,
                "context_used": bool(context),
                "rag_results_count": len(rag_results),
                "memory_used": bool(memory_context),
                "tools_used": self.tool_integration is not None and self._should_use_tools(messages),
                "tool_steps": tool_steps,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "llm_result": llm_result if isinstance(llm_result, dict) else {"response": llm_result}
            }
            
        except Exception as e:
            logger.error(f"聊天补全失败: {e}")
            return {
                "response": "抱歉，处理您的请求时出现了问题。",
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _get_last_user_message(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """获取最后一条用户消息"""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return None
    
    def _build_llm_messages(self, messages: List[Dict[str, str]], context: str, 
                           memory_context: str, game_scene: Optional[str]) -> List[Dict[str, str]]:
        """
        构建LLM消息列表
        
        Args:
            messages: 原始消息列表
            context: RAG检索的游戏知识上下文
            memory_context: 记忆上下文
            game_scene: 游戏场景
            
        Returns:
            LLM消息列表，包含系统提示和上下文
        """
        llm_messages = []
        
        # 构建系统提示
        system_prompt = """你是一个崩坏3游戏的AI陪伴助手，专门帮助玩家更好地体验游戏。
你的角色是游戏内的伙伴，能够理解游戏场景、提供游戏建议、解答问题，并与玩家进行自然对话。
请使用中文进行对话，语气友好、专业，符合游戏角色的性格特点。"""
        
        if game_scene:
            system_prompt += f"\n当前游戏场景: {game_scene}"
        
        # 添加游戏知识上下文到系统提示
        if context:
            system_prompt += f"\n相关游戏知识: {context}"
        
        # 添加记忆上下文到系统提示
        if memory_context:
            system_prompt += f"\n对话记忆: {memory_context}"
        
        # 添加系统消息
        llm_messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 添加对话历史（保持原始格式）
        for msg in messages:
            # 确保消息格式正确
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["system", "user", "assistant"]:
                llm_messages.append({
                    "role": role,
                    "content": content
                })
            else:
                # 未知角色，默认为用户
                llm_messages.append({
                    "role": "user",
                    "content": content
                })
        
        return llm_messages
    
    def _determine_task_type(self, messages: List[Dict[str, str]], game_scene: Optional[str]) -> str:
        """
        根据消息内容和游戏场景确定任务类型
        
        Args:
            messages: 消息列表
            game_scene: 游戏场景
            
        Returns:
            任务类型字符串
        """
        # 获取最后一条用户消息
        last_user_message = self._get_last_user_message(messages)
        if not last_user_message:
            return TaskType.CASUAL_CHAT.value
        
        last_message_lower = last_user_message.lower()
        
        # 检查是否包含游戏攻略关键词
        game_guide_keywords = ["攻略", "怎么打", "怎么过", "怎么玩", "技巧", "战术", "配装", "培养", "升级"]
        if any(keyword in last_message_lower for keyword in game_guide_keywords):
            return TaskType.GAME_GUIDE.value
        
        # 检查是否包含复杂推理关键词
        reasoning_keywords = ["为什么", "原因", "分析", "解释", "原理", "机制", "计算", "策略", "对比"]
        if any(keyword in last_message_lower for keyword in reasoning_keywords):
            return TaskType.COMPLEX_REASONING.value
        
        # 检查是否包含情感支持关键词
        emotional_keywords = ["心情", "难过", "开心", "生气", "失望", "鼓励", "安慰", "支持", "陪伴"]
        if any(keyword in last_message_lower for keyword in emotional_keywords):
            return TaskType.EMOTIONAL_SUPPORT.value
        
        # 检查是否包含代码相关
        code_keywords = ["代码", "编程", "脚本", "api", "接口", "实现", "算法", "函数"]
        if any(keyword in last_message_lower for keyword in code_keywords):
            return TaskType.CODE_GENERATION.value
        
        # 默认根据游戏场景判断
        if game_scene:
            # 如果在战斗场景，可能是攻略需求
            if any(scene in game_scene.lower() for scene in ["战斗", "boss", "关卡", "副本"]):
                return TaskType.GAME_GUIDE.value
        
        # 默认日常聊天
        return TaskType.CASUAL_CHAT.value
    
    def _should_use_tools(self, messages: List[Dict[str, str]]) -> bool:
        """
        判断是否应该使用工具
        
        Args:
            messages: 消息列表
            
        Returns:
            是否应该使用工具
        """
        if not self.tool_integration:
            return False
        
        last_user_message = self._get_last_user_message(messages)
        if not last_user_message:
            return False
        
        # 使用工具集成的建议逻辑
        suggested_tools = self.tool_integration.should_use_tool(last_user_message)
        return len(suggested_tools) > 0
    
    

    async def stream_chat_completion(self, messages: List[Dict[str, str]], 
                              game_scene: Optional[str] = None,
                              use_rag: bool = True,
                              rag_mode: Optional[str] = None):
        """
        流式聊天补全
        
        Args:
            messages: 消息历史
            game_scene: 游戏场景
            use_rag: 是否使用RAG
            rag_mode: RAG模式 (fast/precise/hybrid)
            
        Yields:
            流式响应块
        """
        try:
            # 1. 如果有RAG，检索相关知识
            context = ""
            if use_rag and self.rag_engine is not None:
                await self._ensure_rag_initialized()
                last_user_message = self._get_last_user_message(messages)
                if last_user_message and self.rag_engine:
                    try:
                        mode = SearchMode(rag_mode) if rag_mode else None
                        rag_results = await self.rag_engine.search(
                            query=last_user_message,
                            mode=mode
                        )
                        context = self.rag_engine._retriever.format_results_for_context(
                            rag_results,
                            self.rag_config.context_max_length if self.rag_config else 2000
                        )
                    except Exception as e:
                        logger.warning(f"RAG检索失败: {e}")
            
            # 2. 如果有记忆，检索相关记忆
            memory_context = ""
            if self.memory_manager is not None:
                memory_context = self.memory_manager.retrieve_relevant_memories(messages)
            
            # 3. 构建包含系统提示的消息列表
            llm_messages = self._build_llm_messages(messages, context, memory_context, game_scene)
            
            # 4. 根据游戏场景确定任务类型
            task_type = self._determine_task_type(messages, game_scene)
            
            # 5. 调用LLM路由器（流式模式）
            llm_result = self.llm_router.route_request(
                messages=llm_messages,
                task_type=task_type,
                stream=True
            )
            
            # 6. 处理流式响应
            if isinstance(llm_result, dict) and "stream_generator" in llm_result:
                for chunk in llm_result["stream_generator"]:
                    yield chunk
            elif hasattr(llm_result, "__next__") or hasattr(llm_result, "__iter__"):
                for chunk in llm_result:
                    yield {
                        "chunk": chunk,
                        "is_final": False
                    }
                yield {
                    "chunk": "",
                    "is_final": True
                }
            elif isinstance(llm_result, dict) and "content" in llm_result:
                words = llm_result["content"].split()
                for i, word in enumerate(words):
                    yield {
                        "chunk": word + (" " if i < len(words) - 1 else ""),
                        "is_final": i == len(words) - 1
                    }
                    time.sleep(0.05)
            else:
                error_msg = str(llm_result) if llm_result else "无法生成流式响应"
                yield {
                    "chunk": error_msg,
                    "is_final": True
                }
                
        except Exception as e:
            logger.error(f"流式聊天补全失败: {e}")
            yield {
                "chunk": f"抱歉，流式响应失败: {str(e)}",
                "is_final": True
            }
    
    def get_conversation_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            user_id: 用户ID
            limit: 限制条数
            
        Returns:
            对话历史
        """
        # TODO: 从数据库获取对话历史
        return []
    
    def clear_conversation_history(self, user_id: str) -> bool:
        """
        清空对话历史
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        # TODO: 清空数据库中的对话历史
        logger.info(f"清空用户 {user_id} 的对话历史")
        return True
    
    def analyze_conversation_sentiment(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        分析对话情感
        
        Args:
            messages: 消息历史
            
        Returns:
            情感分析结果
        """
        # 简单的情感分析（模拟）
        positive_keywords = ["好", "喜欢", "开心", "谢谢", "帮助", "棒", "厉害"]
        negative_keywords = ["不好", "讨厌", "生气", "问题", "困难", "麻烦", "失望"]
        
        content = " ".join([msg.get("content", "") for msg in messages])
        
        positive_count = sum(content.count(keyword) for keyword in positive_keywords)
        negative_count = sum(content.count(keyword) for keyword in negative_keywords)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "positive_score": positive_count,
            "negative_score": negative_count,
            "neutral_score": len(messages) - positive_count - negative_count
        }