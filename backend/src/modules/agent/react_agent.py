import logging
import os
import queue
from threading import Lock
from typing import Any, Dict, List, Optional

import cv2
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.llms import LLM
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from src.config.settings import get_settings
from src.config.runtime_settings import get_runtime_settings
from src.config.cancel_signal import is_cancelled
from src.modules.llm.llm_router import TaskType, get_llm_router
from src.modules.rag import RAGConfig, RAGEngine, SearchMode
from src.modules.vision.yolo_model_manager import YOLOModelManager
from src.modules.skill.skill_manager import get_skill_manager
from .react_formatter import ReActFormatter

logger = logging.getLogger(__name__)


class RouterLLM(LLM):
    """将现有 LLMRouter 适配为 LangChain LLM。"""

    @property
    def _llm_type(self) -> str:
        return "bbb_router_llm"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager=None, **kwargs: Any) -> str:
        request_id = getattr(self, '_current_request_id', None)
        if request_id and is_cancelled(request_id):
            raise RuntimeError("CancelledError: 请求已被用户取消")

        router = get_llm_router()
        runtime = get_runtime_settings()

        PROVIDER_MAP = {
            "deepseek": "deepseek-api-default",
            "lmstudio": "lm-studio-default",
            "ollama": "ollama-default",
        }
        RUNTIME_MAP = {"deepseek": "api", "lmstudio": "lmstudio", "ollama": "ollama"}

        router_kwargs = {}
        if runtime.get("llm_provider"):
            router_kwargs["preferred_runtime"] = RUNTIME_MAP.get(runtime["llm_provider"], "auto")
            router_kwargs["user_preference"] = PROVIDER_MAP.get(runtime["llm_provider"], runtime["llm_provider"])
        if runtime.get("llm_model"):
            router_kwargs["model_override"] = runtime["llm_model"]
        if runtime.get("llm_temperature") is not None:
            router_kwargs["temperature"] = runtime["llm_temperature"]
        if runtime.get("llm_max_tokens") is not None:
            router_kwargs["max_tokens"] = runtime["llm_max_tokens"]
        if runtime.get("llm_api_key"):
            router_kwargs["api_key"] = runtime["llm_api_key"]

        result = router.route_request(
            messages=[
                {
                    "role": "system",
                    "content": "你是崩坏3助手，请严格遵循 ReAct 格式并按需调用工具。",
                },
                {"role": "user", "content": prompt},
            ],
            task_type=TaskType.GAME_GUIDE.value,
            stream=False,
            **router_kwargs,
        )
        if isinstance(result, dict):
            if "content" in result:
                return result["content"]
            if "error" in result:
                return f"发生错误: {result['error']}"
        return str(result)


class QueueStreamingHandler(BaseCallbackHandler):
    """将 Agent 每一步事件放入线程安全队列，供 SSE 端点消费。"""

    def __init__(self, event_queue: queue.Queue, agent_ref: Any = None):
        self.event_queue = event_queue
        self.agent_ref = agent_ref
        self._last_action = None

    def _check_cancel(self):
        if self.agent_ref is None:
            return
        request_id = getattr(self.agent_ref, '_request_id', None)
        if request_id and is_cancelled(request_id):
            raise RuntimeError("CancelledError: 请求已被用户取消")

    def on_agent_action(self, action, **kwargs):
        self._check_cancel()
        tool_name = getattr(action, 'tool', '')
        self._last_action = tool_name
        self.event_queue.put({
            "type": "step",
            "thought": getattr(action, 'log', ''),
            "action": tool_name,
            "action_input": str(getattr(action, 'tool_input', '')),
            "timestamp": __import__('time').time(),
        })

    def on_tool_end(self, output, **kwargs):
        output_str = str(output)
        ts = __import__('time').time()
        if self._last_action == 'todo_write':
            try:
                import json as _json
                data = _json.loads(output_str)
                self.event_queue.put({
                    "type": "todo",
                    "tasks": data.get("tasks", []),
                    "timestamp": ts,
                })
            except Exception:
                self.event_queue.put({
                    "type": "observation",
                    "observation": output_str,
                    "timestamp": ts,
                })
        else:
            self.event_queue.put({
                "type": "observation",
                "observation": output_str,
                "timestamp": ts,
            })

    def on_agent_finish(self, finish, **kwargs):
        self.event_queue.put({
            "type": "finish",
            "output": finish.return_values.get("output", str(finish)),
            "timestamp": __import__('time').time(),
        })

    def on_tool_error(self, error, **kwargs):
        self.event_queue.put({
            "type": "error",
            "message": str(error),
            "timestamp": __import__('time').time(),
        })


class ReActGameAgent:
    """LangChain ReAct Agent，接入 RAG + YOLO + 基础工具，支持多轮对话记忆。"""

    def __init__(self):
        self.settings = get_settings()
        self.rag_engine = RAGEngine(
            RAGConfig(
                data_path=self.settings.rag_data_path,
                index_path=self.settings.rag_index_path,
                chroma_persist_directory=self.settings.chroma_persist_directory,
                chroma_collection=self.settings.chroma_collection,
                embedding_model=self.settings.embedding_model,
                embedding_model_path=self.settings.embedding_model_path,
                embedding_device=self.settings.embedding_device,
                embedding_offline_mode=self.settings.embedding_offline_mode,
                default_top_k=self.settings.rag_default_top_k,
                default_mode=SearchMode(self.settings.rag_default_mode),
                context_max_length=self.settings.rag_context_max_length,
            )
        )
        self.yolo_manager = YOLOModelManager.get_instance()
        self._rag_lock = Lock()
        # 在初始化时预热RAG引擎，避免后续的asyncio问题
        self._warm_up_rag()
        self._formatter = ReActFormatter()
        # 初始化对话记忆
        self._memory = self._build_memory()
        # 加载并缓存用户偏好（嵌入系统 prompt）
        self._cached_preferences = self._load_user_preferences()
        self._agent = self._build_agent()
    
    def _build_memory(self):
        """构建对话记忆组件"""
        from langchain_classic.memory.buffer import ConversationBufferMemory

        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=2000
        )

    def clear_context(self) -> Dict[str, Any]:
        """清除对话上下文，重置记忆和 agent 状态。用于用户手动刷新上下文或任务切换时。"""
        import os
        result = {
            "success": True,
            "memory_cleared": True,
            "checkpoint_deleted": False,
            "agent_rebuilt": True,
        }

        # 1. 重置对话记忆
        self._memory.clear()
        self._memory = self._build_memory()

        # 2. 删除任务检查点文件（如果存在）
        checkpoint_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "outputs", "task_checkpoint.json"
        )
        checkpoint_path = os.path.normpath(checkpoint_path)
        if os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                result["checkpoint_deleted"] = True
                logger.info("已删除任务检查点文件")
            except OSError as e:
                logger.warning(f"删除检查点文件失败: {e}")

        # 3. 重新加载偏好（允许热更新）
        self._cached_preferences = self._load_user_preferences()

        # 4. 重建 agent（确保 tool 绑定使用新的 memory，偏好嵌入系统 prompt）
        self._agent = self._build_agent()

        logger.info("Agent 上下文已清除")
        return result

    def _load_user_preferences(self) -> str:
        """读取用户偏好设置文件，返回注入到 prompt 的上下文字符串。"""
        import os
        prefs_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "user_preferences.md"
        )
        prefs_path = os.path.normpath(prefs_path)
        try:
            if os.path.exists(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.info("已加载用户偏好设置")
                return f"""[系统上下文 - 用户偏好设置]
以下是用户的偏好设置，请在执行任务时遵守这些偏好：

{content}

---
请在回复和执行任务时考虑以上用户偏好设置。"""
        except Exception as e:
            logger.warning(f"读取用户偏好设置失败: {e}")
        return ""

    def _warm_up_rag(self) -> None:
        """在初始化时同步预热RAG引擎"""
        import asyncio
        try:
            # 尝试获取现有loop，如果存在则使用它，否则创建新的
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经有loop在运行，我们在新线程中初始化
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.rag_engine.initialize())
                    future.result()
            else:
                asyncio.run(self.rag_engine.initialize())
        except RuntimeError:
            asyncio.run(self.rag_engine.initialize())

    def initialize_rag_sync(self) -> None:
        """同步初始化RAG引擎（用于在ReAct Agent运行前预初始化）"""
        if self.rag_engine.is_initialized:
            return
        with self._rag_lock:
            if self.rag_engine.is_initialized:
                return
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.run_until_complete(self.rag_engine.initialize())
                else:
                    asyncio.run(self.rag_engine.initialize())
            except RuntimeError:
                asyncio.run(self.rag_engine.initialize())

    def _ensure_rag_initialized(self) -> None:
        if self.rag_engine.is_initialized:
            return
        with self._rag_lock:
            if self.rag_engine.is_initialized:
                return
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.rag_engine.initialize())
                else:
                    asyncio.run(self.rag_engine.initialize())
            except RuntimeError:
                import asyncio
                asyncio.run(self.rag_engine.initialize())

    def _build_agent(self) -> AgentExecutor:
        @tool
        def rag_search(query: str) -> str:
            """查询本地 RAG 知识库，返回游戏相关知识摘要。"""
            self._ensure_rag_initialized()
            import concurrent.futures
            import asyncio
            
            def run_async_search():
                return asyncio.run(self.rag_engine.search(query=query, mode=SearchMode.HYBRID, top_k=5))
            
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_search)
                    results = future.result()
            except Exception as e:
                logger.error(f"RAG搜索失败: {e}")
                return f"RAG搜索失败: {str(e)}"
            
            if not results:
                return "未检索到相关知识。"
            lines = []
            for r in results[:5]:
                lines.append(f"{r.name}: {r.content[:200]}")
            return "\n".join(lines)

        @tool
        def list_skills(_: str = "") -> str:
            """列出所有可用的技能，每个技能包含使用说明和触发词。在不确定如何完成某个任务时，可以调用此工具查看可用技能。"""
            skill_manager = get_skill_manager()
            return skill_manager.get_skill_summary()

        @tool
        def view_skill(skill_name: str = "") -> str:
            """查看指定技能的详细使用说明。参数: skill_name - 技能名称（先调用list_skills查看可用技能）。技能包含详细的操作步骤和说明，帮助您完成特定任务。"""
            if not skill_name or skill_name.strip() == "":
                return "❌ 请提供技能名称，先调用list_skills查看可用技能。"
            
            skill_manager = get_skill_manager()
            skill = skill_manager.get_skill(skill_name.strip())
            
            if not skill:
                available_skills = ", ".join(skill_manager.list_skills())
                return f"❌ 未找到技能 '{skill_name}'。可用技能: {available_skills}"
            
            return f"📖 技能: {skill['name']}\n\n描述: {skill['description']}\n\n使用说明:\n{skill['content']}"

        @tool
        def yolo_list_models(_: str = "") -> str:
            """列出所有可用的YOLO模型（包括检测模型和分类模型）以及当前已加载的模型。在使用任何YOLO工具前调用此工具查看可用模型。"""
            available = self.yolo_manager.list_available_models()
            loaded = self.yolo_manager.list_loaded_models()
            
            # 按类型分组可用模型
            classification_models = []
            detect_models = []
            
            for model in available:
                model_name = model["name"]
                if "cls" in model_name.lower():
                    classification_models.append(model_name)
                elif "det" in model_name.lower():
                    detect_models.append(model_name)
            
            # 格式化输出
            lines = []
            lines.append("=== 已加载模型 ===")
            if loaded:
                for model in loaded:
                    lines.append(f"✓ {model['name']} (设备: {model['device']})")
            else:
                lines.append("无")
            
            lines.append("\n=== 可用分类模型 ===")
            if classification_models:
                for model in classification_models:
                    lines.append(f"• {model}")
            else:
                lines.append("无")
            
            lines.append("\n=== 可用检测模型 ===")
            if detect_models:
                for model in detect_models:
                    lines.append(f"• {model}")
            else:
                lines.append("无")
            
            return "\n".join(lines)

        @tool
        def yolo_load_model(model_name: str) -> str:
            """加载指定的YOLO模型到内存（优先加载到GPU）。参数: model_name - 模型名称，必须是可用模型列表中的名称（先调用yolo_list_models查看）。检测模型用于识别游戏UI元素，分类模型用于识别游戏场景。"""
            try:
                import json
                import torch
                
                # 解析可能的JSON格式输入
                if model_name.startswith("{"):
                    try:
                        parsed = json.loads(model_name)
                        model_name = parsed.get("model_name", model_name)
                    except json.JSONDecodeError:
                        pass
                
                # 使用 CPU 运行模型（避免 CUDA 兼容性问题）
                target_device = "cpu"
                logger.info(f"使用设备: {target_device}")
                
                result = self.yolo_manager.load_model(model_name=model_name, device=target_device)
                
                if result.get("success"):
                    model_info = result.get("model", {})
                    message = result.get("message", "模型加载成功")
                    model_name = model_info.get("name", model_name)
                    device = model_info.get("device", target_device)
                    
                    return f"✅ {message}\n\n模型信息:\n• 名称: {model_name}\n• 设备: {device}"
                else:
                    error_msg = result.get("message", "加载失败")
                    return f"❌ 模型加载失败: {error_msg}"
                    
            except Exception as e:
                logger.error(f"加载模型失败: {e}")
                return f"❌ 模型加载失败: {str(e)}"

        @tool
        def yolo_unload_model(model_name: str) -> str:
            """卸载指定的YOLO模型以释放GPU/CPU内存。参数: model_name - 要卸载的模型名称（先调用yolo_list_models查看已加载模型）。当需要释放显存加载其他模型时使用此工具。"""
            try:
                import json

                # 解析可能的JSON格式输入
                if model_name.startswith("{"):
                    try:
                        parsed = json.loads(model_name)
                        model_name = parsed.get("model_name", model_name)
                    except json.JSONDecodeError:
                        pass

                result = self.yolo_manager.unload_model(model_name=model_name.strip())

                if result.get("success"):
                    return f"✅ {result.get('message', '模型已卸载')}"
                else:
                    error_msg = result.get("message", "卸载失败")
                    return f"❌ 卸载失败: {error_msg}"

            except Exception as e:
                logger.error(f"卸载模型失败: {e}")
                return f"❌ 卸载模型失败: {str(e)}"

        @tool
        def yolo_detect_image(model_name: str = "") -> str:
            """对当前屏幕截图进行YOLO目标检测，识别游戏中的UI元素（如按钮、菜单等）。参数: model_name - 已加载的检测模型名称（必须先调用yolo_load_model加载）。适用于检测attack_ui、club、home、mission等场景的UI元素。"""
            try:
                from src.modules.vision.screen_capture import ScreenCapture
                import json
                import os
                
                # 获取已加载的模型列表
                loaded_models = self.yolo_manager.list_loaded_models()
                loaded_names = {m["name"] for m in loaded_models}
                
                # 检查模型名称是否指定
                if not model_name or model_name.strip() == "":
                    return f"❌ 请指定要使用的模型名称。当前已加载的模型: {', '.join(loaded_names) if loaded_names else '无'}"
                
                input_str = model_name.strip()
                
                # 尝试解析JSON格式
                try:
                    parsed = json.loads(input_str)
                    if isinstance(parsed, dict) and "model_name" in parsed:
                        model_name = parsed["model_name"]
                    elif isinstance(parsed, str):
                        model_name = parsed
                    else:
                        model_name = input_str
                except (json.JSONDecodeError, ValueError):
                    model_name = input_str
                
                # 检查模型是否已加载
                if model_name not in loaded_names:
                    return f"❌ 模型 '{model_name}' 未加载。请先使用 yolo_load_model 加载模型，或使用以下已加载的模型: {', '.join(loaded_names) if loaded_names else '无'}"
                
                # 加载检测标签中文映射
                label_mapping = {}
                mapping_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                    "data", "models", "detect", "detect_mapping.json"
                )
                try:
                    if os.path.exists(mapping_path):
                        with open(mapping_path, 'r', encoding='utf-8') as f:
                            all_mappings = json.load(f)
                            label_mapping = all_mappings.get(model_name, {})
                except Exception as e:
                    logger.warning(f"加载检测标签映射文件失败: {e}")
                
                # 捕获屏幕截图
                screen_capture = ScreenCapture()
                image = screen_capture.capture()
                
                if image is None or image.size == 0:
                    return "屏幕捕获失败"
                
                # 进行检测
                result = self.yolo_manager.detect(
                    image=image, 
                    model_name=model_name, 
                    confidence_threshold=0.5
                )
                
                if not result or not result.get("detections"):
                    return "未检测到任何目标"
                
                # 格式化结果
                detections = result["detections"]
                
                # 按标签分组统计（用英文标签统计以保持一致性
                label_counts = {}
                for detection in detections:
                    label = detection.get("label", detection.get("class", "未知"))
                    label_counts[label] = label_counts.get(label, 0) + 1
                
                # 生成详细结果
                lines = []
                lines.append(f"检测到 {len(detections)} 个目标，共 {len(label_counts)} 种类别:")
                lines.append("")
                
                # 按置信度排序并显示完整信息
                sorted_detections = sorted(detections, key=lambda x: -x.get("confidence", 0))
                
                for idx, detection in enumerate(sorted_detections, 1):
                    label = detection.get("label", detection.get("class", "未知"))
                    label_cn = label_mapping.get(label, label)
                    confidence = detection.get("confidence", 0)
                    bbox = detection.get("bbox", [])
                    
                    # 使用 -- 分隔中英文标签
                    if label_cn != label:
                        display_label = f"{label}--{label_cn}"
                    else:
                        display_label = label
                    
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        lines.append(f"{idx}. {display_label}")
                        lines.append(f"   ├─ 置信度: {confidence:.4f}")
                        lines.append(f"   └─ 位置: ({int(x1)}, {int(y1)}) - ({int(x2)}, {int(y2)})")
                    else:
                        lines.append(f"{idx}. {display_label}: {confidence:.4f}")
                
                # 添加标签统计（使用英文标签
                lines.append("")
                lines.append("标签统计:")
                for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
                    lines.append(f"  • {label}: {count} 个")
                
                return "\n".join(lines)
                
            except Exception as e:
                logger.error(f"YOLO检测失败: {e}")
                return f"YOLO检测失败: {str(e)}"

        @tool
        def yolo_classify_image(model_name: str = "") -> str:
            """对当前屏幕截图进行YOLO图像分类，识别当前游戏场景。参数: model_name - 已加载的分类模型名称（必须先调用yolo_load_model加载）。推荐使用yolo11n_scene_cls模型进行崩坏3场景分类，可识别home、combat、gacha、shop、story等34个游戏场景。"""
            try:
                from src.modules.vision.screen_capture import ScreenCapture
                import json
                import os
                
                loaded_models = self.yolo_manager.list_loaded_models()
                loaded_names = {m["name"] for m in loaded_models}
                
                if not model_name or model_name.strip() == "":
                    return f"❌ 请指定要使用的模型名称。当前已加载的模型: {', '.join(loaded_names) if loaded_names else '无'}"
                
                input_str = model_name.strip()
                
                try:
                    parsed = json.loads(input_str)
                    if isinstance(parsed, dict) and "model_name" in parsed:
                        model_name = parsed["model_name"]
                    elif isinstance(parsed, str):
                        model_name = parsed
                    else:
                        model_name = input_str
                except (json.JSONDecodeError, ValueError):
                    model_name = input_str
                
                if model_name not in loaded_names:
                    return f"❌ 模型 '{model_name}' 未加载。请先使用 yolo_load_model 加载模型，或使用以下已加载的模型: {', '.join(loaded_names) if loaded_names else '无'}"
                
                screen_capture = ScreenCapture()
                image = screen_capture.capture()
                
                if image is None or image.size == 0:
                    return "屏幕捕获失败"
                
                result = self.yolo_manager.classify(
                    image=image, 
                    model_name=model_name
                )
                
                if not result or not result.get("predictions"):
                    return "分类失败，未获取到预测结果"
                
                # 加载场景名称映射（如果是场景分类模型）
                is_scene_model = 'scene_cls' in model_name.lower()
                scene_mapping = {}
                if is_scene_model:
                    mapping_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                        "data", "models", "classification", "scene_mapping.json"
                    )
                    try:
                        with open(mapping_path, 'r', encoding='utf-8') as f:
                            scene_mapping = json.load(f)
                    except Exception as e:
                        logger.warning(f"加载场景映射文件失败: {e}")
                
                predictions = result["predictions"]
                
                lines = []
                lines.append(f"分类结果 (模型: {model_name}):")
                if is_scene_model:
                    lines.append("(崩坏3场景分类模型)")
                lines.append("")
                
                for idx, pred in enumerate(predictions, 1):
                    top1 = pred.get("top1", {})
                    top5 = pred.get("top5", [])
                    
                    label = top1.get('label', '未知')
                    
                    # 如果是场景分类模型，显示英文名称（返回给agent）和中文名称（显示给用户）
                    if is_scene_model and label != '未知':
                        cn_label = scene_mapping.get('cn', {}).get(label, label)
                        label = f"{label} ({cn_label})"
                    
                    lines.append(f"📊 预测 #{idx}:")
                    lines.append(f"   └─ Top1: {label} (置信度: {top1.get('confidence', 0):.4f})")
                    
                    if top5:
                        lines.append("")
                        lines.append("   Top5 预测:")
                        for i, item in enumerate(top5, 1):
                            item_label = item.get('label', '未知')
                            if is_scene_model and item_label != '未知':
                                item_cn_label = scene_mapping.get('cn', {}).get(item_label, item_label)
                                item_label = f"{item_label} ({item_cn_label})"
                            lines.append(f"     {i}. {item_label}: {item.get('confidence', 0):.4f}")
                
                # 如果是场景分类模型，添加推荐装载检测模型的提示
                if is_scene_model and predictions:
                    top1_label = predictions[0].get("top1", {}).get('label', '')
                    scene_to_det_model = {
                        "bridge": "yolo11n_bridge_ui_det",
                        "home": "yolo11n_home_ui_det",
                        "mission": "yolo11n_mission_ui_det",
                        "club": "yolo11n_club_ui_det",
                        "attack": "yolo11n_attack_ui_det",
                    }
                    if top1_label in scene_to_det_model:
                        det_model = scene_to_det_model[top1_label]
                        lines.append("")
                        lines.append(f"💡 推荐：当前场景为 {top1_label}，可使用 yolo_load_model 装载 {det_model} 进行UI元素检测")
                
                return "\n".join(lines)
                
            except Exception as e:
                logger.error(f"YOLO分类失败: {e}")
                return f"YOLO分类失败: {str(e)}"

        @tool
        def get_runtime_status(_: str = "") -> str:
            """获取当前 LLM 运行时优先级与状态。"""
            return (
                f"runtime={self.settings.llm_runtime}, "
                f"priority=api>lmstudio/ollama>local, "
                f"local_model={self.settings.llm_local_model_path}"
            )

        @tool
        def focus_bh3_window(_: str = "") -> str:
            """将焦点转到崩坏3游戏窗口。在进行游戏操作前使用此工具确保窗口处于活动状态。"""
            try:
                from src.modules.vision.window_focus import focus_bh3_window, is_admin
                
                if not is_admin():
                    return "⚠️ 当前程序未以管理员身份运行，可能无法正确聚焦游戏窗口。建议以管理员身份重新运行程序。"
                
                success, message = focus_bh3_window()
                if success:
                    return f"✅ {message}"
                else:
                    return f"❌ {message}，请检查游戏是否已启动"
            except ImportError as e:
                return f"❌ 无法导入窗口聚焦模块: {str(e)}"
            except Exception as e:
                return f"❌ 聚焦窗口时发生错误: {str(e)}"

        @tool
        def click_coordinates(coords: str = "") -> str:
            """点击屏幕上的指定坐标。参数: coords - 坐标字符串，格式为"x,y"，例如："500,300"。建议先使用yolo_detect_image获取目标位置。"""
            try:
                import win32api
                import win32con
                import time
                
                if not coords or coords.strip() == "":
                    return "❌ 请提供坐标参数，格式为: x,y"
                
                # 解析坐标
                coords = coords.strip()
                try:
                    # 处理可能的JSON格式
                    if coords.startswith("{"):
                        import json
                        data = json.loads(coords)
                        x = data.get("x", data.get("X", 0))
                        y = data.get("y", data.get("Y", 0))
                    elif "," in coords:
                        x_str, y_str = coords.split(",", 1)
                        x = int(float(x_str.strip()))
                        y = int(float(y_str.strip()))
                    else:
                        return f"❌ 无效的坐标格式: {coords}，请使用 x,y 格式"
                except Exception as e:
                    return f"❌ 坐标解析失败: {str(e)}"
                
                # 移动鼠标到目标位置
                win32api.SetCursorPos((x, y))
                time.sleep(0.1)
                
                # 模拟鼠标左键点击
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                time.sleep(0.1)
                
                return f"✅ 已点击坐标 ({x}, {y})"
                
            except ImportError:
                return "❌ 需要安装 pywin32: pip install pywin32"
            except Exception as e:
                return f"❌ 点击失败: {str(e)}"

        @tool
        def ocr_recognize(region: str = "") -> str:
            """对指定区域进行OCR文字识别。参数: region - 识别区域，格式为"x1,y1,x2,y2"（左上角和右下角坐标），如"100,100,500,500"。留空则默认识别全屏。"""
            try:
                from src.modules.vision.screen_capture import ScreenCapture
                from src.modules.vision.ocr_processor import OCRProcessor
                
                screen_capture = ScreenCapture()
                image = screen_capture.capture()
                
                if image is None or image.size == 0:
                    return "❌ 屏幕捕获失败"
                
                # 解析区域参数
                x1, y1, x2, y2 = None, None, None, None
                if region and region.strip():
                    try:
                        parts = region.strip().split(',')
                        if len(parts) == 4:
                            x1, y1, x2, y2 = map(int, parts)
                        else:
                            return f"❌ 无效的区域格式，请使用 'x1,y1,x2,y2' 格式，例如 '100,100,500,500'"
                    except ValueError:
                        return f"❌ 区域坐标必须是整数，格式: x1,y1,x2,y2"
                
                # 裁剪图像到指定区域
                if x1 is not None:
                    image = image[y1:y2, x1:x2]
                
                # 执行OCR识别
                ocr = OCRProcessor()
                results = ocr.process(image)
                
                if not results:
                    return "未识别到文字"
                
                lines = []
                lines.append("📝 OCR识别结果:")
                lines.append("")
                
                # 统计识别到的文字
                text_count = 0
                for idx, result in enumerate(results, 1):
                    if result.text.strip():
                        text_count += 1
                        lines.append(f"区域 #{idx}:")
                        lines.append(f"   文字: {result.text}")
                        lines.append(f"   置信度: {result.confidence:.2f}")
                        if result.bbox:
                            # 计算实际坐标（如果有区域裁剪）
                            bbox_x1 = result.bbox[0] + (x1 or 0)
                            bbox_y1 = result.bbox[1] + (y1 or 0)
                            bbox_x2 = result.bbox[2] + (x1 or 0)
                            bbox_y2 = result.bbox[3] + (y1 or 0)
                            lines.append(f"   位置: ({int(bbox_x1)}, {int(bbox_y1)}) - ({int(bbox_x2)}, {int(bbox_y2)})")
                        lines.append("")
                
                lines.append(f"📊 共识别到 {text_count} 个文本区域")
                
                return "\n".join(lines)
                
            except ImportError as e:
                return f"❌ 无法导入OCR模块: {str(e)}"
            except Exception as e:
                return f"❌ OCR识别失败: {str(e)}"

        @tool
        def tts_qwen3(text: str = "") -> str:
            """使用Qwen3-TTS引擎将文本转为语音（声音设计模式，无需参考音频）。参数: text - 要合成语音的文本内容。支持多种声音风格（爱莉希雅、琪亚娜、雷电芽衣、布洛妮娅、温柔女声、可爱萝莉等），默认使用爱莉希雅预设音色。生成后返回音频文件路径，你必须在下一步调用 play_audio 工具播放生成的音频文件！"""
            if not text or text.strip() == "":
                return "❌ 请提供要合成语音的文本内容。"
            try:
                from src.utils.model_manager import get_qwen3_tts_model
                tts = get_qwen3_tts_model(device="cuda:0")
                result = tts.generate(
                    text=text.strip(),
                    voice_style="爱莉希雅",
                    language="Chinese"
                )
                filepath = tts.save_to_file(result)
                duration = len(result.audio_data) / result.sample_rate
                return (
                    f"✅ Qwen3-TTS 语音生成成功！\n"
                    f"- 文本: {text.strip()}\n"
                    f"- 声音风格: 爱莉希雅\n"
                    f"- 采样率: {result.sample_rate} Hz\n"
                    f"- 时长: {duration:.1f}s\n"
                    f"- 文件: {filepath}\n\n"
                    f"⚠️ 请在下一步调用 play_audio 工具播放此文件: {filepath}"
                )
            except Exception as e:
                return f"❌ Qwen3-TTS 语音生成失败: {str(e)}"

        @tool
        def tts_voxcpm(text: str = "") -> str:
            """使用VoxCPM引擎通过参考音频克隆爱莉希雅声音生成语音。参数: text - 要合成语音的文本内容。基于爱莉希雅参考音频进行声音克隆，生成后返回音频文件路径，你必须在下一步调用 play_audio 工具播放生成的音频文件！"""
            if not text or text.strip() == "":
                return "❌ 请提供要合成语音的文本内容。"
            try:
                from src.utils.model_manager import get_tts_model
                tts = get_tts_model(device="cuda:0")
                result = tts.generate(
                    text=text.strip(),
                    voice_id="elysia",
                    save_result=True
                )
                filepath = tts.save_to_file(result)
                duration = len(result.audio_data) / result.sample_rate
                return (
                    f"✅ VoxCPM 语音克隆成功！\n"
                    f"- 文本: {text.strip()}\n"
                    f"- 角色: 爱莉希雅(elysia)\n"
                    f"- 采样率: {result.sample_rate} Hz\n"
                    f"- 时长: {duration:.1f}s\n"
                    f"- 文件: {filepath}\n\n"
                    f"⚠️ 请在下一步调用 play_audio 工具播放此文件: {filepath}"
                )
            except Exception as e:
                return f"❌ VoxCPM 语音克隆失败: {str(e)}"

        @tool
        def play_audio(filepath: str = "") -> str:
            """播放指定路径的音频文件（WAV格式）。参数: filepath - 音频文件的完整路径。通常在 tts_qwen3 或 tts_voxcpm 生成音频后调用此工具来播放。"""
            if not filepath or filepath.strip() == "":
                return "❌ 请提供要播放的音频文件路径。"
            try:
                from src.modules.audio.audio_player import get_audio_player
                player = get_audio_player()
                success = player.play_audio(filepath.strip())
                if success:
                    return f"✅ 音频播放成功: {filepath}"
                else:
                    return f"❌ 音频播放失败: {filepath}"
            except Exception as e:
                return f"❌ 音频播放异常: {str(e)}"

        @tool
        def todo_write(tasks_json: str = "") -> str:
            """创建和更新任务计划列表。当任务需要3步以上时，必须先用此工具创建TODO计划，然后每完成一步更新状态。

参数为 JSON 字符串，格式:
  {"tasks": [{"id": "1", "status": "pending", "content": "任务描述"}, ...]}

status 可选: pending, in_progress, completed

使用方式:
- 首次: 列出全部任务的完整 JSON，全部初始为 pending
- 开始某任务: 只发该任务 status: "in_progress"
- 完成某任务: 只发该任务 status: "completed"
- 一次可更新多个任务状态

返回当前完整的 TODO 列表状态。"""
            import json as _json
            try:
                data = _json.loads(tasks_json) if tasks_json and tasks_json.strip() else {"tasks": []}
                tasks = data.get("tasks", [])
                if not hasattr(self, '_todo_list'):
                    self._todo_list = []
                for t in tasks:
                    tid = t.get("id", "")
                    existing = next((x for x in self._todo_list if x.get("id") == tid), None)
                    if existing:
                        if "status" in t:
                            existing["status"] = t["status"]
                        if "content" in t:
                            existing["content"] = t["content"]
                    else:
                        self._todo_list.append({
                            "id": tid,
                            "status": t.get("status", "pending"),
                            "content": t.get("content", ""),
                        })
                result = {"tasks": self._todo_list}
                return _json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return _json.dumps({"error": str(e), "tasks": getattr(self, '_todo_list', [])}, ensure_ascii=False)

        @tool
        def web_search(query: str = "") -> str:
            """联网搜索最新信息。参数: query - 搜索关键词。当本地RAG知识库无法回答或需要最新资讯时使用。支持崩坏3相关的最新攻略、活动、角色信息等。"""
            if not query or query.strip() == "":
                return "❌ 请提供搜索关键词"
            try:
                from src.modules.web_search.web_searcher import WebSearcher, SearchEngine
                searcher = WebSearcher(engine=SearchEngine.BING_CHINA, max_results=5, enable_content_fetch=True)
                results = searcher.search(query.strip())
                if not results:
                    return "未找到相关搜索结果"
                lines = [f"搜索: {query.strip()}", ""]
                for i, r in enumerate(results, 1):
                    lines.append(f"{i}. {r.title}")
                    lines.append(f"   {r.snippet[:200]}")
                    if r.content:
                        lines.append(f"   详情: {r.content[:300]}")
                    lines.append(f"   来源: {r.url}")
                    lines.append("")
                return "\n".join(lines)
            except ImportError:
                return "❌ 联网搜索模块未安装"
            except Exception as e:
                return f"❌ 搜索失败: {str(e)}"

        tools = [rag_search, list_skills, view_skill, yolo_list_models, yolo_load_model, yolo_unload_model, yolo_detect_image, yolo_classify_image, ocr_recognize, get_runtime_status, focus_bh3_window, click_coordinates, tts_qwen3, tts_voxcpm, play_audio, todo_write, web_search]
        llm = RouterLLM()
        self._llm = llm

        # 嵌入用户偏好到系统 prompt
        prefs_section = ""
        if self._cached_preferences:
            prefs_section = f"""

【用户偏好设置 - 必须遵守】
{self._cached_preferences}"""

        prompt = PromptTemplate.from_template(
            f"""你是一个严格遵循 ReAct 范式的崩坏3游戏助手。

【任务规划】
- 当任务预计需要3步以上（含）才能完成时，必须先用 todo_write 创建计划
- 创建计划时，列出所有子任务，每个子任务初始 status 为 "pending"
- 开始执行某任务时，更新其 status 为 "in_progress"
- 完成某任务时，更新其 status 为 "completed"
- 完成所有任务后，给出最终回复

【知识获取策略】
- 游戏基础设定/攻略 → 优先用 rag_search 查本地知识库（速度快）
- 最新资讯/活动/版本更新 → 用 web_search 联网搜索（信息新）
- 两者结果冲突时，以联网搜索结果为准

【游戏背景知识】
- bridge（舰桥界面）是崩坏3的主界面/首页
- 从舰桥可以导航到各个功能界面（家园、任务、补给等）
- home（家园界面）是日常活动聚集地
- mission（任务界面）包含主线、支线、日常等任务
- gacha（补给界面）是抽卡界面
- club（舰团界面）是社团相关功能

【绝对规则 - 必须遵守】
**规则1**: 输出只能是两种格式之一，绝对不能混合！
**规则2**: 如果调用工具，就只输出 Thought + Action + Action Input，不要有 Final Answer
**规则3**: 如果直接回答，就只输出 Thought + Final Answer，不要有 Action
**规则4**: 每次只输出一个Thought + Action + Action Input，然后停止，等待系统返回Observation
**规则5**: 绝对不要自己生成Observation或工具结果！工具结果由系统自动返回
**规则6**: 绝对不要在Action Input后面输出日志、时间戳或任何额外内容
{prefs_section}

【对话历史】
{{chat_history}}

【可用工具】
{{tools}}

【工具名称列表】
{{tool_names}}

【格式选择】
--- 选择A: 需要调用工具 ---
Thought: [你的思考]
Action: [工具名称]
Action Input: [工具输入内容]
（然后停止，等待系统返回Observation）

--- 选择B: 直接回答用户 ---
Thought: 我已经得到最终答案
Final Answer: [你的中文回答]

【示例】
调用工具示例：
Question: 我现在在哪里？
Thought: 用户想知道当前所在界面，需要调用场景分类工具识别当前游戏场景
Action: yolo_load_model
Action Input: yolo11n_scene_cls

直接回答示例：
Question: 你好
Thought: 我已经得到最终答案
Final Answer: 你好！我是崩坏3助手。

TTS语音合成必须的两步流程：
Question: 用爱莉希雅的声音说你好
Thought: 用户想要用爱莉希雅声音说"你好"，我需要先调用 tts_qwen3 生成语音
Action: tts_qwen3
Action Input: 你好
（等待Observation返回文件路径，然后进行第二步）
Thought: 语音已生成，现在需要播放
Action: play_audio
Action Input: [上一步返回的文件路径]

【开始】
Question: {{input}}
{{agent_scratchpad}}"""
        )

        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=1000,
            max_execution_time=5400,
            return_intermediate_steps=True,
            memory=self._memory,
        )

    def run(self, user_input: str, max_retries: int = 2, request_id: str = "") -> Dict[str, Any]:
        self._request_id = request_id

        # 检查是否有匹配的技能
        skill_manager = get_skill_manager()
        matched_skill = skill_manager.find_matching_skill(user_input)

        if matched_skill:
            skill_name = matched_skill['name']
            user_input = f"""用户请求: {user_input}

已匹配到技能「{skill_name}」，请按以下步骤执行：
1. 使用 view_skill 工具查看该技能的详细操作说明
2. 根据技能说明中的步骤，依次调用相应的工具完成任务
3. 完成后请总结执行过程和结果"""

        result = self._run_with_retry(user_input, max_retries)
        
        # 根据结果播放相应的音频
        try:
            from src.modules.audio.audio_player import get_audio_player
            
            player = get_audio_player()
            errors = result.get("errors", [])
            
            if errors or result.get("loop_detected"):
                # 任务出错，播放错误提示音
                player.play_error()
            else:
                # 任务正常完成，播放成功提示音
                player.play_success()
        except Exception as e:
            logger.warning(f"音频播放失败: {str(e)}")
        
        return result

    def run_streaming(self, user_input: str, request_id: str, event_queue: queue.Queue, max_retries: int = 2) -> Dict[str, Any]:
        """流式运行 Agent，每一步通过 event_queue 实时推送。"""
        self._request_id = request_id

        skill_manager = get_skill_manager()
        matched_skill = skill_manager.find_matching_skill(user_input)

        if matched_skill:
            skill_name = matched_skill['name']
            user_input = f"""用户请求: {user_input}

已匹配到技能「{skill_name}」，请按以下步骤执行：
1. 使用 view_skill 工具查看该技能的详细操作说明
2. 根据技能说明中的步骤，依次调用相应的工具完成任务
3. 完成后请总结执行过程和结果"""

        handler = QueueStreamingHandler(event_queue, agent_ref=self)
        try:
            result = self._run_with_retry(user_input, max_retries, callbacks=[handler])
        except Exception as e:
            error_msg = str(e)
            if "CancelledError" in error_msg:
                event_queue.put({"type": "cancelled"})
            else:
                event_queue.put({"type": "error", "message": error_msg})
            raise

        errors = result.get("errors", [])
        if errors or result.get("loop_detected"):
            event_queue.put({"type": "warning", "message": "\\n".join(errors) if errors else "检测到循环调用"})

        # 根据结果播放相应的音频
        try:
            from src.modules.audio.audio_player import get_audio_player

            player = get_audio_player()
            if errors or result.get("loop_detected"):
                player.play_error()
            else:
                player.play_success()
        except Exception as e:
            logger.warning(f"音频播放失败: {str(e)}")

        return result

    def _is_phased_skill(self, skill_name: str) -> bool:
        """检查技能是否定义了阶段"""
        if not skill_name:
            return False
        skill_manager = get_skill_manager()
        phases = skill_manager.get_skill_phases(skill_name)
        return len(phases) > 0

    def _build_phase_prompt(self, phase_name: str, phase_content: str, phase_index: int,
                            total_phases: int, checkpoint_summary: str,
                            original_request: str = "") -> str:
        """为单个阶段构建隔离的 prompt。只包含本阶段的指令和检查点上下文。"""
        checkpoint_block = ""
        if checkpoint_summary:
            checkpoint_block = f"""[上一阶段完成后的状态]
{checkpoint_summary}
"""

        original_block = ""
        if original_request:
            original_block = f"""\n[用户原始请求]
{original_request}
"""

        return f"""[任务阶段 {phase_index + 1}/{total_phases}]
请执行以下阶段：{phase_name}
{original_block}

{checkpoint_block}
[阶段操作说明]
{phase_content}

---
完成本阶段后，请确保已按说明写入检查点到 outputs/task_checkpoint.json。"""

    def _read_checkpoint_summary(self) -> str:
        """读取检查点文件，返回简要上下文摘要供下一阶段使用。"""
        import os
        checkpoint_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "outputs", "task_checkpoint.json"
        )
        checkpoint_path = os.path.normpath(checkpoint_path)
        try:
            if os.path.exists(checkpoint_path):
                import json
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                lines = []
                lines.append(f"已完成阶段: {', '.join(cp.get('completed_phases', []))}")
                lines.append(f"当前场景: {cp.get('scene', 'unknown')}")
                lines.append(f"状态: {cp.get('context_summary', '')}")
                if cp.get("key_data"):
                    lines.append(f"关键数据: {json.dumps(cp.get('key_data', {}), ensure_ascii=False)}")
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"读取检查点失败: {e}")
        return ""

    def _get_checkpoint_phase(self, skill_name: str) -> int:
        """检查是否存在任务断点，返回应从第几个阶段开始（0-indexed）。
        如果没有断点或断点属于其他技能，返回 0。
        """
        import os, json
        checkpoint_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "outputs", "task_checkpoint.json"
        )
        checkpoint_path = os.path.normpath(checkpoint_path)
        try:
            if os.path.exists(checkpoint_path):
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                if cp.get("skill") == skill_name:
                    phase = cp.get("current_phase", 0)
                    logger.info(f"检测到断点: skill={skill_name}, phase={phase}")
                    return phase
        except Exception as e:
            logger.warning(f"读取断点失败: {e}")
        return 0

    def run_phased(self, skill_name: str, user_input: str, request_id: str = "",
                   max_retries: int = 2) -> Dict[str, Any]:
        """分阶段执行（非流式）— 每个阶段在干净的上下文中独立运行。"""
        skill_manager = get_skill_manager()
        phases = skill_manager.get_skill_phases(skill_name)

        if not phases:
            return {"output": "", "errors": ["未定义阶段"], "steps": []}

        # 检查断点，确定起始阶段
        start_phase = self._get_checkpoint_phase(skill_name)
        if start_phase > 0:
            logger.info(f"从阶段 {start_phase + 1}/{len(phases)} 恢复: {skill_name}")

        all_steps = []
        checkpoint_summary = self._read_checkpoint_summary() if start_phase > 0 else ""

        for i in range(start_phase, len(phases)):
            phase_name = phases[i]
            phase_content = skill_manager.extract_phase_content(skill_name, phase_name)
            if not phase_content:
                return {"output": "", "errors": [f"未找到阶段: {phase_name}"], "steps": all_steps}

            phase_prompt = self._build_phase_prompt(
                phase_name, phase_content, i, len(phases), checkpoint_summary,
                original_request=user_input
            )

            self.clear_context()
            result = self._run_with_retry(phase_prompt, max_retries)
            all_steps.extend(result.get("steps", []))

            errors = result.get("errors", [])
            if errors or result.get("loop_detected"):
                return {"output": result.get("output", ""), "errors": errors, "steps": all_steps}

            checkpoint_summary = self._read_checkpoint_summary()

        return {
            "output": f"任务「{skill_name}」全部 {len(phases)} 个阶段已完成",
            "steps": all_steps,
            "errors": [],
        }

    def run_phased_streaming(self, skill_name: str, user_input: str, request_id: str,
                              event_queue: queue.Queue, max_retries: int = 2) -> Dict[str, Any]:
        """分阶段流式执行 — 每个阶段在干净的上下文中独立运行，通过检查点文件交接状态。"""
        skill_manager = get_skill_manager()
        phases = skill_manager.get_skill_phases(skill_name)

        if not phases:
            event_queue.put({"type": "error", "message": f"技能 {skill_name} 未定义阶段"})
            return {"output": "", "errors": ["未定义阶段"], "steps": []}

        # 检查断点，确定起始阶段
        start_phase = self._get_checkpoint_phase(skill_name)
        if start_phase > 0:
            logger.info(f"从阶段 {start_phase + 1}/{len(phases)} 恢复: {skill_name}")
            event_queue.put({
                "type": "phase_resume",
                "phase_index": start_phase,
                "phase_name": phases[start_phase],
                "total_phases": len(phases),
            })

        logger.info(f"开始分阶段执行: {skill_name}, 共 {len(phases)} 个阶段")

        all_steps = []
        checkpoint_summary = self._read_checkpoint_summary() if start_phase > 0 else ""

        for i in range(start_phase, len(phases)):
            phase_name = phases[i]
            # 发送阶段开始事件
            event_queue.put({
                "type": "phase_start",
                "phase_index": i,
                "phase_name": phase_name,
                "total_phases": len(phases),
            })

            # 提取阶段内容
            phase_content = skill_manager.extract_phase_content(skill_name, phase_name)
            if not phase_content:
                error_msg = f"未找到阶段内容: {phase_name}"
                logger.error(error_msg)
                event_queue.put({"type": "error", "message": error_msg})
                return {"output": "", "errors": [error_msg], "steps": all_steps}

            # 构建阶段 prompt（只包含本阶段指令 + 检查点摘要）
            phase_prompt = self._build_phase_prompt(
                phase_name, phase_content, i, len(phases), checkpoint_summary,
                original_request=user_input
            )

            # 清除上一阶段的上下文，为每个阶段提供干净的对话记忆
            self.clear_context()

            # 执行阶段
            handler = QueueStreamingHandler(event_queue, agent_ref=self)
            try:
                result = self._run_with_retry(phase_prompt, max_retries, callbacks=[handler])
            except Exception as e:
                error_msg = str(e)
                if "CancelledError" in error_msg:
                    event_queue.put({"type": "cancelled"})
                else:
                    event_queue.put({"type": "error", "message": error_msg})
                raise

            # 收集步骤
            all_steps.extend(result.get("steps", []))

            # 检查错误
            errors = result.get("errors", [])
            if errors or result.get("loop_detected"):
                event_queue.put({
                    "type": "warning",
                    "message": "\n".join(errors) if errors else "检测到循环调用"
                })

            # 发送阶段完成事件
            event_queue.put({
                "type": "phase_complete",
                "phase_index": i,
                "phase_name": phase_name,
                "output": result.get("output", ""),
            })

            # 读取检查点供下一阶段使用
            checkpoint_summary = self._read_checkpoint_summary()

        logger.info(f"分阶段执行完成: {skill_name}")
        return {
            "output": f"任务「{skill_name}」全部 {len(phases)} 个阶段已完成",
            "steps": all_steps,
            "errors": [],
        }

    def _run_with_retry(self, user_input: str, max_retries: int, callbacks: Optional[List] = None) -> Dict[str, Any]:
        retry_count = 0
        last_errors = []
        tool_call_history = []
        
        while retry_count <= max_retries:
            if hasattr(self, '_llm'):
                self._llm._current_request_id = self._request_id
            invoke_config = {"callbacks": callbacks} if callbacks else None
            result = self._agent.invoke({"input": user_input}, config=invoke_config)
            steps = []
            
            has_parsing_error = False
            has_valid_action = False
            current_tool_chain = []
            
            for action, observation in result.get("intermediate_steps", []):
                action_tool = action.tool if hasattr(action, "tool") else ""
                action_input = str(action.tool_input) if hasattr(action, "tool_input") else ""
                action_log = action.log if hasattr(action, "log") else ""
                
                if action_tool == "_Exception":
                    has_parsing_error = True
                    action_log = f"解析错误: {action_input}"
                elif action_tool and action_tool != "_Exception":
                    has_valid_action = True
                    current_tool_chain.append(action_tool)
                
                steps.append(
                    {
                        "thought": action_log,
                        "action": action_tool,
                        "action_input": action_input,
                        "observation": str(observation),
                    }
                )
            
            # 检测循环调用（同一工具连续执行超过3次）
            if current_tool_chain:
                tool_call_history.extend(current_tool_chain)
                
                # 检查是否有工具连续调用超过3次
                consecutive_count = 1
                for i in range(1, len(tool_call_history)):
                    if tool_call_history[i] == tool_call_history[i-1]:
                        consecutive_count += 1
                        if consecutive_count >= 3:
                            logger.warning(f"检测到工具 {tool_call_history[i]} 连续调用 {consecutive_count} 次，已达到限制")
                            # 返回当前结果，不再继续
                            raw_output = result.get("output", "")
                            clean_answer = self._formatter.extract_clean_answer(raw_output)
                            return {
                                "output": clean_answer,
                                "formatted_output": raw_output,
                                "steps": steps,
                                "raw": result,
                                "retry_count": retry_count,
                                "errors": [f"工具 {tool_call_history[i]} 连续调用超过3次，已自动终止循环"],
                                "loop_detected": True
                            }
                    else:
                        consecutive_count = 1
            
            raw_output = result.get("output", "")
            
            is_valid, errors = self._formatter.validate(raw_output)
            
            if not has_parsing_error and is_valid:
                clean_answer = self._formatter.extract_clean_answer(raw_output)
                formatted_output = self._formatter.correct(raw_output)
                
                return {
                    "output": clean_answer,
                    "formatted_output": formatted_output,
                    "steps": steps,
                    "raw": result,
                    "retry_count": retry_count,
                    "errors": []
                }
            
            last_errors = errors
            
            if retry_count < max_retries:
                if self._request_id and is_cancelled(self._request_id):
                    raise RuntimeError("CancelledError: 请求已被用户取消")
                if has_valid_action:
                    logger.warning(f"工具执行成功但格式验证失败，跳过重试")
                    break
                logger.warning(f"第 {retry_count + 1} 次尝试失败，错误: {errors}")
                retry_count += 1
                user_input = f"修正格式错误并重新回答：{user_input}\n\n错误原因：{errors}"
            else:
                break
        
        clean_answer = self._formatter.extract_clean_answer(raw_output)
        formatted_output = self._formatter.correct(raw_output)
        
        return {
            "output": clean_answer,
            "formatted_output": formatted_output,
            "steps": steps,
            "raw": result,
            "retry_count": retry_count,
            "errors": last_errors
        }


_react_agent_singleton: Optional[ReActGameAgent] = None
_react_agent_lock = Lock()


def get_react_agent() -> ReActGameAgent:
    global _react_agent_singleton
    if _react_agent_singleton is None:
        with _react_agent_lock:
            if _react_agent_singleton is None:
                _react_agent_singleton = ReActGameAgent()
    return _react_agent_singleton
