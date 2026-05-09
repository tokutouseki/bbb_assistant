from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import importlib.util

import requests

from ..config.settings import get_settings
from ..modules.agent.react_agent import get_react_agent

router = APIRouter()

class ChatMessage(BaseModel):
    role: str = Field(..., description="角色: user, assistant, system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[float] = Field(None, description="时间戳")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="对话历史")
    game_scene: Optional[str] = Field(None, description="当前游戏场景")
    use_rag: bool = Field(default=True, description="是否使用RAG知识库")
    stream: bool = Field(default=False, description="是否流式输出")
    show_thinking: bool = Field(default=True, description="是否显示思考过程")

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
    
    # 使用ReAct Agent处理
    try:
        agent = get_react_agent()
        result = agent.run(last_user_message)
        
        # 将ReAct步骤转换为tool_steps格式
        tool_steps = []
        thinking_steps = []
        for step in result.get("steps", []):
            tool_steps.append({
                "tool": step.get("action", ""),
                "input": last_user_message,
                "start_time": "",
                "end_time": "",
                "result": bool(step.get("observation", "")),
                "output": step.get("observation", ""),
                "thought": step.get("thought", "")
            })
            
            # 构建思考步骤格式（用于前端显示）
            if request.show_thinking:
                thinking_steps.append({
                    "thought": step.get("thought", ""),
                    "action": step.get("action", ""),
                    "action_input": step.get("action_input", ""),
                    "observation": step.get("observation", "")
                })
        
        # 构建响应
        response = ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=result.get("output", "无法生成响应"),
                timestamp=time.time()
            ),
            sources=None,
            processing_time=time.time() - start_time,
            tool_steps=tool_steps,
            thinking_steps=thinking_steps if request.show_thinking else None
        )
        return response
        
    except Exception as e:
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=f"ReAct Agent执行失败: {str(e)}",
                timestamp=time.time()
            ),
            processing_time=time.time() - start_time,
            tool_steps=[],
            thinking_steps=[]
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