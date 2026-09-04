#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话日志记录与导出模块
======================
记录每次对话的完整上下文供 MP（数字海马体）消费：
- 用户消息 + Agent 路由决策
- 业务 Agent 的 ReAct 思考链（thought/action/observation）
- 陪伴 Agent 的角色化回复 + 思考步骤
- 角色人格文件完整内容
- 匹配的技能内容

持久化到 data/conversations/ 目录。

线程安全：所有 _conversations 字典访问由 _data_lock 保护。
"""

import json
import logging
import os
import re
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 存储目录
_STORAGE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "conversations"

# conv_id 安全校验：仅允许字母、数字、连字符、下划线（防止路径遍历）
_VALID_CONV_ID = re.compile(r'^[a-zA-Z0-9_-]+$')


def _safe_serialize(obj: Any) -> Any:
    """递归安全序列化：将不可序列化类型转为字符串，防止 json.dump 崩溃。"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_safe_serialize(v) for v in obj]
    elif isinstance(obj, (datetime,)):
        return obj.isoformat()
    else:
        return str(obj)


@dataclass
class ReActStep:
    """ReAct 思考步骤"""
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""


@dataclass
class RouterDecision:
    """AgentRouter 意图分类结果"""
    intent: str = ""           # "game" / "action" / "chat"
    skill_name: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessAgentResult:
    """业务 Agent（MainGameAgent / ActionAgent）执行结果"""
    agent_type: str = ""       # "main" / "action"
    output: str = ""
    steps: List[ReActStep] = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    skills_matched: List[str] = field(default_factory=list)
    skills_content: Dict[str, str] = field(default_factory=dict)  # 技能名 → SKILL.md 内容
    processing_time_ms: float = 0.0


@dataclass
class CompanionResult:
    """CompanionAgent 角色化回复"""
    emotion: Optional[str] = None     # [happy] / [sad] / ...
    clean_output: str = ""            # 去除 emotion 标签后的纯文本
    raw_output: str = ""              # 含 emotion 标签的原始输出
    thinking_steps: List[ReActStep] = field(default_factory=list)  # Companion 的 ReAct 思考
    triggered_live2d: bool = False
    triggered_tts: bool = False


@dataclass
class ConversationRecord:
    """单次对话的完整记录"""
    conversation_id: str = ""
    timestamp: str = ""               # ISO 8601
    # 用户输入
    user_message: str = ""
    user_images_count: int = 0
    user_audios_count: int = 0
    # 角色人格
    character: Dict[str, str] = field(default_factory=dict)
    # Agent 链路
    router: Optional[RouterDecision] = None
    business_agent: Optional[BusinessAgentResult] = None
    companion: Optional[CompanionResult] = None
    # 元数据
    llm_provider: str = ""
    llm_model: str = ""


class ConversationLogger:
    """对话日志记录器（线程安全，内存 + 磁盘持久化）"""

    _instance: Optional["ConversationLogger"] = None
    _class_lock = threading.Lock()

    def __init__(self):
        self._conversations: Dict[str, ConversationRecord] = {}
        self._data_lock = threading.Lock()  # 保护 _conversations 字典
        self._ensure_storage_dir()

    @classmethod
    def get_instance(cls) -> "ConversationLogger":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ================================================================
    # 存储管理
    # ================================================================

    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        os.makedirs(str(_STORAGE_DIR), exist_ok=True)

    def _save_to_disk(self, record: ConversationRecord):
        """将单条对话保存到磁盘（安全序列化）"""
        try:
            filepath = _STORAGE_DIR / f"{record.conversation_id}.json"
            data = _record_to_dict(record)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"对话已保存: {filepath}")
        except Exception as e:
            logger.error(f"保存对话失败 [{record.conversation_id}]: {e}")

    @staticmethod
    def _validate_conv_id(conv_id: str) -> bool:
        """校验 conv_id 格式，防止路径遍历攻击。"""
        return bool(_VALID_CONV_ID.match(conv_id))

    # ================================================================
    # 记录API（在 chat.py 的各个阶段调用，线程安全）
    # ================================================================

    def start_conversation(
        self,
        user_message: str,
        character_name: str = "爱莉希雅",
        character_personality: str = "",
        images_count: int = 0,
        audios_count: int = 0,
        llm_provider: str = "",
        llm_model: str = "",
    ) -> str:
        """
        开始记录一次对话。
        返回 conversation_id。
        """
        conv_id = uuid.uuid4().hex  # 32 字符完整 UUID，无碰撞风险

        # 读取完整人格文件内容
        personality_content = character_personality
        personality_file = ""
        if not personality_content:
            try:
                from .character.character_manager import get_character_manager
                cm = get_character_manager()
                dir_name = cm._resolve_name(character_name)
                skill_path = cm.skills_dir / dir_name / "SKILL.md"
                if skill_path.exists():
                    personality_file = str(skill_path)
                    with open(skill_path, "r", encoding="utf-8") as f:
                        personality_content = f.read()
            except Exception as e:
                logger.warning(f"读取人格文件失败: {e}")

        record = ConversationRecord(
            conversation_id=conv_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_message=user_message,
            user_images_count=images_count,
            user_audios_count=audios_count,
            character={
                "name": character_name,
                "personality_file": personality_file,
                "personality_content": personality_content,
            },
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        with self._data_lock:
            self._conversations[conv_id] = record
        logger.info(f"[ConversationLogger] 开始记录对话 {conv_id[:12]}..., 角色={character_name}")
        return conv_id

    def record_router(self, conv_id: str, intent: str, skill_name: Optional[str],
                      raw_response: Optional[Dict] = None):
        """记录 AgentRouter 意图分类结果（含完整 LLM 输出）。"""
        with self._data_lock:
            record = self._conversations.get(conv_id)
        if not record:
            return
        record.router = RouterDecision(
            intent=intent,
            skill_name=skill_name,
            raw_response=_safe_serialize(raw_response) if raw_response else {},
        )
        logger.info(f"[ConversationLogger] {conv_id[:12]}: Router → {intent}, skill={skill_name}")

    def record_business_agent(
        self,
        conv_id: str,
        agent_type: str,
        output: str,
        steps: Optional[List[Dict]] = None,
        tools_called: Optional[List[str]] = None,
        skills_matched: Optional[List[str]] = None,
        skills_content: Optional[Dict[str, str]] = None,
        processing_time_ms: float = 0.0,
    ):
        """记录业务 Agent 执行结果（MainGameAgent / ActionAgent）。"""
        with self._data_lock:
            record = self._conversations.get(conv_id)
        if not record:
            return

        react_steps = []
        tool_names = list(tools_called or [])
        for step in (steps or []):
            action_name = step.get("action", "")
            react_steps.append(ReActStep(
                thought=step.get("thought", ""),
                action=action_name,
                action_input=str(step.get("action_input", "")),
                observation=str(step.get("observation", "")),
            ))
            if action_name and action_name not in tool_names:
                tool_names.append(action_name)

        record.business_agent = BusinessAgentResult(
            agent_type=agent_type,
            output=output,
            steps=react_steps,
            tools_called=tool_names,
            skills_matched=list(skills_matched or []),
            skills_content=dict(skills_content or {}),
            processing_time_ms=processing_time_ms,
        )
        logger.info(f"[ConversationLogger] {conv_id[:12]}: BusinessAgent({agent_type}) → "
                     f"{len(react_steps)} steps, tools={tool_names}")

    def record_companion(
        self,
        conv_id: str,
        raw_output: str,
        emotion: Optional[str],
        clean_output: str,
        thinking_steps: Optional[List[Dict]] = None,
        triggered_live2d: bool = False,
        triggered_tts: bool = False,
    ):
        """记录 CompanionAgent 角色化回复（含思考步骤）。"""
        with self._data_lock:
            record = self._conversations.get(conv_id)
        if not record:
            return

        comp_steps = []
        for step in (thinking_steps or []):
            comp_steps.append(ReActStep(
                thought=step.get("thought", ""),
                action=step.get("action", ""),
                action_input=str(step.get("action_input", "")),
                observation=str(step.get("observation", "")),
            ))

        record.companion = CompanionResult(
            emotion=emotion,
            clean_output=clean_output,
            raw_output=raw_output,
            thinking_steps=comp_steps,
            triggered_live2d=triggered_live2d,
            triggered_tts=triggered_tts,
        )
        logger.info(f"[ConversationLogger] {conv_id[:12]}: Companion → emotion={emotion}, "
                     f"reply_len={len(clean_output)}, thinking_steps={len(comp_steps)}")

    def finalize_conversation(self, conv_id: str):
        """完成对话记录，保存到磁盘并从内存移除（防止内存泄漏）。"""
        with self._data_lock:
            record = self._conversations.pop(conv_id, None)
        if not record:
            return
        self._save_to_disk(record)
        logger.info(f"[ConversationLogger] {conv_id[:12]}: 对话已归档并从内存移除")

    # ================================================================
    # 导出API
    # ================================================================

    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有已存储的对话（元数据摘要）。O(n) 时间复杂度。"""
        disk_map: Dict[str, Dict] = {}
        # 从磁盘加载
        if _STORAGE_DIR.exists():
            for f in sorted(_STORAGE_DIR.glob("*.json"), reverse=True):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    cid = data.get("conversation_id", f.stem)
                    disk_map[cid] = {
                        "conversation_id": cid,
                        "timestamp": data.get("timestamp", ""),
                        "character": (data.get("character", {}) or {}).get("name", ""),
                        "user_message": (data.get("user_message", "") or "")[:100],
                        "intent": (data.get("router", {}) or {}).get("intent", ""),
                        "emotion": (data.get("companion", {}) or {}).get("emotion", ""),
                        "reply": ((data.get("companion", {}) or {}).get("clean_output", "") or "")[:100],
                    }
                except Exception:
                    disk_map[f.stem] = {"conversation_id": f.stem, "error": "无法解析"}

        result = list(disk_map.values())

        # 内存中尚未保存的 → 插入最前面
        with self._data_lock:
            for conv_id, record in self._conversations.items():
                if conv_id not in disk_map:
                    result.insert(0, {
                        "conversation_id": conv_id,
                        "timestamp": record.timestamp,
                        "character": (record.character or {}).get("name", ""),
                        "user_message": (record.user_message or "")[:100],
                        "intent": record.router.intent if record.router else "",
                        "emotion": record.companion.emotion if record.companion else "",
                        "reply": ((record.companion.clean_output if record.companion else "") or "")[:100],
                    })
        return result

    def export_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """导出单条对话的完整 JSON（含人格文件）。路径遍历安全。"""
        if not self._validate_conv_id(conv_id):
            logger.warning(f"拒绝非法的 conv_id: {conv_id[:50]}")
            return None

        # 先查内存
        with self._data_lock:
            record = self._conversations.get(conv_id)
        if record is not None:
            return _record_to_dict(record)

        # 从磁盘加载
        filepath = (_STORAGE_DIR / f"{conv_id}.json").resolve()
        # 确保解析后仍在 _STORAGE_DIR 内（防止 ../ 绕过）
        storage_resolved = _STORAGE_DIR.resolve()
        if not str(filepath).startswith(str(storage_resolved)):
            logger.warning(f"拒绝路径遍历: {conv_id}")
            return None

        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def export_all(self, include_personalities: bool = True) -> Dict[str, Any]:
        """
        导出全部对话为一个 JSON 包，适合 MP 项目消费。

        返回结构：
        {
          "export_metadata": { "source", "exported_at", "total_conversations", "personalities_count" },
          "personalities": { "角色名": "SKILL.md 完整内容", ... },
          "conversations": [ ... ]
        }
        """
        conversations = []
        seen_ids = set()

        # 从磁盘加载已保存的
        if _STORAGE_DIR.exists():
            for f in sorted(_STORAGE_DIR.glob("*.json")):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    cid = data.get("conversation_id", "")
                    if cid:
                        seen_ids.add(cid)
                    conversations.append(data)
                except Exception as e:
                    logger.warning(f"跳过损坏的对话文件 {f.name}: {e}")

        # 添加内存中尚未保存的
        with self._data_lock:
            for conv_id, record in self._conversations.items():
                if conv_id not in seen_ids:
                    conversations.append(_record_to_dict(record))

        # 收集所有使用到的人格文件
        personalities = {}
        if include_personalities:
            seen_chars = set()
            for conv in conversations:
                char_info = conv.get("character", {}) or {}
                char_name = char_info.get("name", "")
                if char_name and char_name not in seen_chars:
                    seen_chars.add(char_name)
                    content = char_info.get("personality_content", "")
                    if content:
                        personalities[char_name] = content

        return {
            "export_metadata": {
                "source": "bbb_assistant",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_conversations": len(conversations),
                "personalities_count": len(personalities),
            },
            "personalities": personalities,
            "conversations": conversations,
        }

    # ================================================================
    # 维护
    # ================================================================

    def clear(self):
        """清空内存中的记录（不删除磁盘文件）。"""
        with self._data_lock:
            self._conversations.clear()

    def get_count(self) -> int:
        """获取内存中的对话计数。"""
        with self._data_lock:
            return len(self._conversations)

    def get_disk_count(self) -> int:
        """获取磁盘上已保存的对话计数。"""
        if not _STORAGE_DIR.exists():
            return 0
        return sum(1 for _ in _STORAGE_DIR.glob("*.json"))


# ================================================================
# 序列化辅助
# ================================================================

def _record_to_dict(record: ConversationRecord) -> Dict[str, Any]:
    """将 ConversationRecord 转为可序列化的字典（含完整推理链）。"""
    result: Dict[str, Any] = {
        "conversation_id": record.conversation_id,
        "timestamp": record.timestamp,
        "user_message": record.user_message,
        "user_images_count": record.user_images_count,
        "user_audios_count": record.user_audios_count,
        "character": record.character,
        "llm_provider": record.llm_provider,
        "llm_model": record.llm_model,
    }

    # Router — 含完整 LLM 原始输出（"为什么选择这个意图"）
    if record.router:
        result["router"] = {
            "intent": record.router.intent,
            "skill_name": record.router.skill_name,
            "raw_response": _safe_serialize(record.router.raw_response),
        }

    # Business Agent — 含完整 ReAct 思考链 + 技能内容
    if record.business_agent:
        ba = record.business_agent
        result["business_agent"] = {
            "agent_type": ba.agent_type,
            "output": ba.output,
            "steps": [asdict(s) for s in ba.steps],
            "tools_called": ba.tools_called,
            "skills_matched": ba.skills_matched,
            "skills_content": ba.skills_content,
            "processing_time_ms": ba.processing_time_ms,
        }

    # Companion — 含角色化回复 + 思考步骤
    if record.companion:
        comp = record.companion
        result["companion"] = {
            "emotion": comp.emotion,
            "clean_output": comp.clean_output,
            "raw_output": comp.raw_output,
            "thinking_steps": [asdict(s) for s in comp.thinking_steps],
            "triggered_live2d": comp.triggered_live2d,
            "triggered_tts": comp.triggered_tts,
        }

    return result


# 便捷单例获取
def get_conversation_logger() -> ConversationLogger:
    return ConversationLogger.get_instance()
