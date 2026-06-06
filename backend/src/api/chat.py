import asyncio
import json
import os
import queue
import importlib.util
import re as _re
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import requests

from ..config.settings import get_settings
from ..config.runtime_settings import update_runtime_settings
from ..config.cancel_signal import register_request, clear_request, cancel_request
from ..modules.agent.react_agent import (
    get_main_agent, get_sub_agent, get_react_agent,
    get_action_agent, get_companion_agent, AgentRouter,
)

router = APIRouter()

import tempfile
import base64
import logging
logger = logging.getLogger(__name__)


def _transcribe_audios(audios: List[str]) -> str:
    """将 base64 音频列表转写为文本，返回可前置到用户消息的转写结果。"""
    settings = get_settings()
    if not settings.enable_audio or not settings.enable_asr:
        return ""
    try:
        from ..modules.audio.asr_processor import ASRProcessor
        asr = ASRProcessor(
            model_path=settings.asr_model_path,
            device="cuda:0",
        )
        if asr.model is None:
            return ""
    except Exception:
        return ""

    transcriptions = []
    for i, audio_b64 in enumerate(audios):
        try:
            if "," in audio_b64:
                audio_b64 = audio_b64.split(",", 1)[1]
            audio_bytes = base64.b64decode(audio_b64)
            suffix = ".webm"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name
            try:
                result = asr.transcribe_file(tmp_path, language="zh")
                if result.text and not result.text.startswith("这是SenseVoiceSmall"):
                    transcriptions.append(f"[音频{i+1}转写] {result.text}")
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"音频{i+1}转写失败: {e}")

    if transcriptions:
        return "\n".join(transcriptions) + "\n\n"
    return ""


_EMOTION_RE = _re.compile(r'^\s*\[(happy|sad|angry|surprised|shy|serious|teasing|gentle|excited|neutral)\]\s*', _re.IGNORECASE)


def _parse_emotion_tag(text: str) -> tuple:
    """解析文本开头的 [emotion] 标签，返回 (emotion, clean_text)。"""
    match = _EMOTION_RE.match(text)
    if match:
        emotion = match.group(1).lower()
        clean = text[match.end():].strip()
        return emotion, clean
    return None, text


def _trigger_live2d_emotion(emotion: str):
    """异步触发 Live2D 表情切换（fire-and-forget）。"""
    try:
        from ..modules.live2d_control.call_live2d import call_live2d
        call_live2d("set_emotion", emotion=emotion)
    except Exception as e:
        logger.warning(f"Live2D 表情切换失败 [{emotion}]: {e}")


def _generate_tts_background(text: str):
    """在后台线程中生成 TTS 语音并播放（fire-and-forget，不阻塞主流程）。
    仅在用户开启 auto_tts_enabled 设置时才执行。
    """
    try:
        from ..config.runtime_settings import get_runtime_settings
        if not get_runtime_settings().get("auto_tts_enabled", False):
            logger.info("TTS: auto_tts_enabled 未开启，跳过")
            return
    except Exception:
        return

    import threading

    def _run():
        try:
            from ..modules.agent.react_agent import _resolve_ref_audio
            from ..config.runtime_settings import get_runtime_settings
            from ..utils.model_manager import get_qwen3_tts_model
            from ..modules.audio.audio_player import get_audio_player

            runtime = get_runtime_settings()
            char_name = runtime.get("companion_character", "爱莉希雅")

            audio_path, ref_text = _resolve_ref_audio(char_name, "")
            if not audio_path:
                logger.warning(f"TTS: 找不到角色 '{char_name}' 的参考音频，跳过")
                return

            tts = get_qwen3_tts_model(device="cuda:0")
            result = tts.generate_with_reference(
                text=text,
                reference_audio=audio_path,
                language="Chinese",
                ref_text=ref_text if ref_text else None,
            )
            filepath = tts.save_to_file(result)
            logger.info(f"TTS 已生成: {filepath}")

            player = get_audio_player()
            player.play_audio(filepath)
            logger.info(f"TTS 播放完成")
        except Exception as e:
            logger.warning(f"TTS 后台生成失败: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()


class ChatMessage(BaseModel):
    role: str = Field(..., description="角色: user, assistant, system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[float] = Field(None, description="时间戳")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="对话历史")
    request_id: Optional[str] = Field(None, description="请求ID，用于取消")
    game_scene: Optional[str] = Field(None, description="当前游戏场景")
    use_rag: bool = Field(default=True, description="是否使用RAG知识库")
    stream: bool = Field(default=False, description="是否流式输出")
    show_thinking: bool = Field(default=True, description="是否显示思考过程")
    images: Optional[List[str]] = Field(None, description="base64图片列表(data:image/...;base64,...)")
    audios: Optional[List[str]] = Field(None, description="base64音频列表(data:audio/...;base64,...)")
    image_describer_backend: Optional[str] = Field(None, description="图片描述后端优先级: bailian / pixai_tagger / lmstudio")
    bailian_api_key: Optional[str] = Field(None, description="阿里百炼API密钥覆盖")
    llm_provider: Optional[str] = Field(None, description="LLM提供商覆盖: deepseek / lmstudio / ollama")
    llm_model: Optional[str] = Field(None, description="模型名称覆盖")
    llm_api_key: Optional[str] = Field(None, description="API密钥覆盖")
    llm_api_base_url: Optional[str] = Field(None, description="API地址覆盖")
    llm_temperature: Optional[float] = Field(None, description="Temperature覆盖")
    llm_max_tokens: Optional[int] = Field(None, description="Max Token覆盖")

class ChatResponse(BaseModel):
    message: ChatMessage = Field(..., description="助手回复")
    sources: Optional[List[str]] = Field(None, description="参考的知识库来源")
    processing_time: float = Field(..., description="处理耗时（秒）")
    tool_steps: Optional[List[Dict[str, Any]]] = Field(None, description="工具使用的中间过程")
    thinking_steps: Optional[List[Dict[str, Any]]] = Field(None, description="ReAct思考步骤")


class RuntimeStatusResponse(BaseModel):
    runtime_mode: str
    priority_order: List[str]
    selected_runtime: str
    checks: Dict[str, Any]


class ReActAgentRequest(BaseModel):
    input: str = Field(..., description="用户输入")


class ReActAgentResponse(BaseModel):
    output: str = Field(..., description="Agent最终回答")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="ReAct中间轨迹")
    raw: Dict[str, Any] = Field(default_factory=dict, description="Agent原始输出")

@router.post("/", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    聊天补全接口，使用标准ReAct Agent运行
    """
    import time
    start_time = time.time()
    
    # 获取最后一条用户消息
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break
    
    if not last_user_message:
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content="没有收到用户消息",
                timestamp=time.time()
            ),
            processing_time=time.time() - start_time,
            tool_steps=[],
            thinking_steps=[]
        )
    
    # 应用LLM运行时覆盖
    llm_overrides = {
        "llm_provider": request.llm_provider,
        "llm_model": request.llm_model,
        "llm_api_key": request.llm_api_key,
        "llm_api_base_url": request.llm_api_base_url,
        "llm_temperature": request.llm_temperature,
        "llm_max_tokens": request.llm_max_tokens,
        "image_describer_backend": request.image_describer_backend,
        "bailian_api_key": request.bailian_api_key,
    }
    update_runtime_settings(llm_overrides)

    # 自动转写音频
    audios = request.audios or None
    if audios:
        audio_text = _transcribe_audios(audios)
        if audio_text:
            last_user_message = audio_text + last_user_message

    # Router + 3-Agent 编排
    request_id = request.request_id or str(time.time())
    register_request(request_id)
    try:
        images = request.images or None

        # 阶段 0: Router 意图分类
        router = AgentRouter()
        intent_result = await asyncio.to_thread(router.classify, last_user_message)
        intent = intent_result["intent"]
        skill_name = intent_result.get("skill_name")
        logger.info(f"[Router] 意图分类: intent={intent}, skill={skill_name}")

        business_output = ""

        # 阶段 1: 业务 Agent
        if intent == "game":
            from ..modules.skill.skill_manager import get_skill_manager as _get_sm
            _sm = _get_sm()
            _matched = _sm.find_matching_skill(last_user_message)
            _has_phases = _matched and len(_sm.get_skill_phases(_matched["name"])) > 0

            main_agent = get_main_agent()
            if _has_phases:
                main_result = await asyncio.to_thread(
                    main_agent.run_phased, _matched["name"], last_user_message, request_id, 2, images
                )
            else:
                main_result = await asyncio.to_thread(
                    main_agent.run, last_user_message, 2, request_id, images
                )
            business_output = main_result.get("output", "")
            logger.info(f"[MainAgent] 任务报告: {business_output[:500]}")

        elif intent == "action":
            action_agent = get_action_agent()
            action_result = await asyncio.to_thread(
                action_agent.run, last_user_message, 2, request_id, images
            )
            business_output = action_result.get("output", "")
            logger.info(f"[ActionAgent] 操作结果: {business_output[:500]}")

        # 阶段 2: CompanionAgent 角色化回复
        comp_input = f"[用户消息] {last_user_message}\n\n"
        if business_output:
            comp_input += f"[后台操作结果] {business_output}\n\n"
        comp_input += "请以当前角色身份回复用户。"

        comp_agent = get_companion_agent()
        comp_result = await asyncio.to_thread(
            comp_agent.run, comp_input, 1, request_id, None
        )

        raw_output = comp_result.get("output", business_output)
        emotion, clean_output = _parse_emotion_tag(raw_output)
        if emotion:
            _trigger_live2d_emotion(emotion)
        final_output = clean_output
        _generate_tts_background(clean_output)

        tool_steps = []
        thinking_steps = []
        for step in comp_result.get("steps", []):
            tool_steps.append({
                "tool": step.get("action", ""),
                "input": comp_input,
                "start_time": "",
                "end_time": "",
                "result": bool(step.get("observation", "")),
                "output": step.get("observation", ""),
                "thought": step.get("thought", "")
            })
            if request.show_thinking:
                thinking_steps.append({
                    "thought": step.get("thought", ""),
                    "action": step.get("action", ""),
                    "action_input": step.get("action_input", ""),
                    "observation": step.get("observation", "")
                })

        response = ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=final_output,
                timestamp=time.time()
            ),
            sources=None,
            processing_time=time.time() - start_time,
            tool_steps=tool_steps,
            thinking_steps=thinking_steps if request.show_thinking else None
        )
        return response
        
    except Exception as e:
        error_msg = str(e)
        if "CancelledError" in error_msg or "cancelled" in error_msg.lower():
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="请求已被取消",
                    timestamp=time.time()
                ),
                processing_time=time.time() - start_time,
                tool_steps=[],
                thinking_steps=[]
            )
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=f"ReAct Agent执行失败: {error_msg}",
                timestamp=time.time()
            ),
            processing_time=time.time() - start_time,
            tool_steps=[],
            thinking_steps=[]
        )
    finally:
        clear_request(request_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE 流式聊天接口——Agent 每一步实时推送到前端。
    """
    import time

    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break

    if not last_user_message:
        async def empty_generator():
            yield f"data: {json.dumps({'type': 'error', 'message': '没有收到用户消息'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(empty_generator(), media_type="text/event-stream")

    llm_overrides = {
        "llm_provider": request.llm_provider,
        "llm_model": request.llm_model,
        "llm_api_key": request.llm_api_key,
        "llm_api_base_url": request.llm_api_base_url,
        "llm_temperature": request.llm_temperature,
        "llm_max_tokens": request.llm_max_tokens,
        "image_describer_backend": request.image_describer_backend,
        "bailian_api_key": request.bailian_api_key,
    }
    update_runtime_settings(llm_overrides)

    # 自动转写音频
    audios = request.audios or None
    if audios:
        audio_text = _transcribe_audios(audios)
        if audio_text:
            last_user_message = audio_text + last_user_message

    request_id = request.request_id or str(time.time())
    register_request(request_id)
    event_queue = queue.Queue()

    async def generate():
        loop = asyncio.get_event_loop()
        images = request.images or None

        # ====== 阶段 0: Router 意图分类 ======
        router = AgentRouter()
        intent_result = await loop.run_in_executor(None, router.classify, last_user_message)
        intent = intent_result["intent"]
        skill_name = intent_result.get("skill_name")
        logger.info(f"[Router] 意图分类: intent={intent}, skill={skill_name}")

        business_output = ""

        # ====== 阶段 1: 业务 Agent（game / action / chat 跳过） ======
        if intent == "game":
            from ..modules.skill.skill_manager import get_skill_manager
            skill_mgr = get_skill_manager()
            matched = skill_mgr.find_matching_skill(last_user_message)
            has_phases = matched and len(skill_mgr.get_skill_phases(matched["name"])) > 0
            phased_name = matched["name"] if has_phases else None

            def run_main():
                agent = get_main_agent()
                if phased_name:
                    return agent.run_phased(phased_name, last_user_message, request_id, 2, images)
                return agent.run(last_user_message, 2, request_id, images)

            try:
                main_result = await loop.run_in_executor(None, run_main)
                business_output = main_result.get("output", "")
                logger.info(f"[MainAgent] 任务报告: {business_output[:500]}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[MainAgent] 执行失败: {error_msg}")
                if "CancelledError" in error_msg:
                    event_queue.put({"type": "cancelled"})
                else:
                    event_queue.put({"type": "error", "message": f"主Agent执行失败: {error_msg}"})
                clear_request(request_id)
                yield f"data: {json.dumps({'type': 'error', 'message': f'主Agent执行失败: {error_msg}'}, ensure_ascii=False)}\n\n"
                return

        elif intent == "action":
            def run_action():
                agent = get_action_agent()
                return agent.run(last_user_message, 2, request_id, images)

            try:
                action_result = await loop.run_in_executor(None, run_action)
                business_output = action_result.get("output", "")
                logger.info(f"[ActionAgent] 操作结果: {business_output[:500]}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ActionAgent] 执行失败: {error_msg}")
                if "CancelledError" in error_msg:
                    event_queue.put({"type": "cancelled"})
                else:
                    event_queue.put({"type": "error", "message": f"操作Agent执行失败: {error_msg}"})
                clear_request(request_id)
                yield f"data: {json.dumps({'type': 'error', 'message': f'操作Agent执行失败: {error_msg}'}, ensure_ascii=False)}\n\n"
                return

        # else intent == "chat": 无需业务 Agent，business_output 保持为空

        # ====== 阶段 2: CompanionAgent 角色化回复（流式推前端） ======
        comp_input = f"[用户消息] {last_user_message}\n\n"
        if business_output:
            comp_input += f"[后台操作结果] {business_output}\n\n"
        comp_input += "请以当前角色身份回复用户。"

        def run_companion():
            agent = get_companion_agent()
            return agent.run_streaming(comp_input, request_id, event_queue, 1, None)

        future = loop.run_in_executor(None, run_companion)

        while True:
            try:
                event = await loop.run_in_executor(None, event_queue.get, True, 0.1)
            except queue.Empty:
                if future.done():
                    break
                continue

            event_type = event.get("type", "")

            # 解析 [emotion] 标签 → Live2D 表情
            if event_type == "finish":
                raw_output = event.get("output", "")
                emotion, clean_output = _parse_emotion_tag(raw_output)
                if emotion:
                    logger.info(f"[Companion] 情绪标签: {emotion}")
                    _trigger_live2d_emotion(emotion)
                event["output"] = clean_output
                if clean_output.strip():
                    _generate_tts_background(clean_output)

            if event_type in ("finish", "cancelled", "error"):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                break

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        if future.done():
            try:
                await future
            except Exception:
                pass
        else:
            future.cancel()

        clear_request(request_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class CancelRequest(BaseModel):
    request_id: str = Field(..., description="要取消的请求ID")


class ClearContextResponse(BaseModel):
    success: bool
    memory_cleared: bool
    checkpoint_deleted: bool
    agent_rebuilt: bool
    message: str = "上下文已清除"


@router.post("/cancel")
async def cancel_chat(req: CancelRequest):
    """取消正在运行的聊天请求"""
    ok = cancel_request(req.request_id)
    return {"success": ok, "message": "已发送取消信号" if ok else "未找到对应请求"}


@router.post("/clear", response_model=ClearContextResponse)
async def clear_chat_context():
    """清除对话上下文：重置 LLM 记忆、删除任务检查点、重建所有 Agent"""
    results = {
        "main": get_main_agent().clear_context(),
        "action": get_action_agent().clear_context(),
        "companion": get_companion_agent().clear_context(),
    }
    all_ok = all(r["success"] for r in results.values())
    all_mem = all(r["memory_cleared"] for r in results.values())
    all_rebuilt = all(r["agent_rebuilt"] for r in results.values())
    return ClearContextResponse(
        success=all_ok,
        memory_cleared=all_mem,
        checkpoint_deleted=results["main"]["checkpoint_deleted"],
        agent_rebuilt=all_rebuilt,
        message="对话上下文、任务检查点已清除，所有 Agent 已重建"
    )

@router.get("/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 50):
    """
    获取用户的对话历史
    """
    # TODO: 从记忆存储中获取对话历史
    return {"user_id": user_id, "history": []}

@router.delete("/history/{user_id}")
async def clear_chat_history(user_id: str):
    """
    清空用户的对话历史
    """
    # TODO: 清空记忆存储中的对话历史
    return {"message": f"已清空用户 {user_id} 的对话历史"}


@router.get("/runtime-status", response_model=RuntimeStatusResponse)
async def get_runtime_status():
    """调试接口：查看 LLM 运行时可用性与当前优先选择。"""
    settings = get_settings()
    runtime_mode = (settings.llm_runtime or "auto").lower()

    api_available = bool(settings.deepseek_api_key)

    lmstudio_ok = False
    lmstudio_error = None
    try:
        resp = requests.get(f"{settings.lm_studio_base_url.rstrip('/')}/v1/models", timeout=2)
        lmstudio_ok = resp.status_code == 200
        if not lmstudio_ok:
            lmstudio_error = f"status={resp.status_code}"
    except Exception as e:
        lmstudio_error = str(e)

    ollama_ok = False
    ollama_error = None
    try:
        resp = requests.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2)
        ollama_ok = resp.status_code == 200
        if not ollama_ok:
            ollama_error = f"status={resp.status_code}"
    except Exception as e:
        ollama_error = str(e)

    local_model_exists = bool(settings.llm_local_model_path and os.path.exists(settings.llm_local_model_path))
    local_llama_cpp_installed = importlib.util.find_spec("llama_cpp") is not None
    local_available = local_model_exists and local_llama_cpp_installed

    checks = {
        "api": {
            "available": api_available,
            "model": settings.llm_model,
            "base_url": settings.deepseek_base_url,
            "reason": None if api_available else "missing_api_key",
        },
        "lm_studio": {
            "available": lmstudio_ok,
            "base_url": settings.lm_studio_base_url,
            "model": settings.lm_studio_model,
            "reason": lmstudio_error,
        },
        "ollama": {
            "available": ollama_ok,
            "base_url": settings.ollama_base_url,
            "model": settings.ollama_model,
            "reason": ollama_error,
        },
        "local": {
            "available": local_available,
            "model_path": settings.llm_local_model_path,
            "llama_cpp_installed": local_llama_cpp_installed,
            "model_exists": local_model_exists,
            "reason": None if local_available else "missing_model_or_llama_cpp",
        },
    }

    if runtime_mode == "auto":
        order = ["api", "lm_studio", "ollama", "local"]
    elif runtime_mode == "api":
        order = ["api", "lm_studio", "ollama", "local"]
    elif runtime_mode == "lmstudio":
        order = ["lm_studio", "ollama", "local", "api"]
    elif runtime_mode == "ollama":
        order = ["ollama", "lm_studio", "local", "api"]
    elif runtime_mode == "local":
        order = ["local", "lm_studio", "ollama", "api"]
    else:
        order = ["api", "lm_studio", "ollama", "local"]

    selected_runtime = "none"
    for runtime in order:
        if checks[runtime]["available"]:
            selected_runtime = runtime
            break

    return RuntimeStatusResponse(
        runtime_mode=runtime_mode,
        priority_order=order,
        selected_runtime=selected_runtime,
        checks=checks,
    )


@router.post("/react-agent", response_model=ReActAgentResponse)
def run_react_agent(request: ReActAgentRequest):
    """运行 LangChain ReAct Agent（含 RAG + YOLO + 基础工具）。"""
    try:
        agent = get_react_agent()
        result = agent.run(request.input)
        return ReActAgentResponse(
            output=result.get("output", ""),
            steps=result.get("steps", []),
            raw=result.get("raw", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ReAct Agent执行失败: {e}") from e