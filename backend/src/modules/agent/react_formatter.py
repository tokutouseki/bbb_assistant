#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReAct格式解析和修正器
将LLM输出的内容解析为符合ReAct格式的结构化输出
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class StepType(Enum):
    """ReAct步骤类型"""
    QUESTION = "Question"
    THOUGHT = "Thought"
    ACTION = "Action"
    ACTION_INPUT = "Action Input"
    OBSERVATION = "Observation"
    FINAL_ANSWER = "Final Answer"


@dataclass
class ReActStep:
    """ReAct步骤"""
    step_type: StepType
    content: str
    raw_text: str


@dataclass
class ParsedReAct:
    """解析后的ReAct结构"""
    question: str
    steps: List[ReActStep]
    final_answer: Optional[str] = None
    
    def get_thoughts(self) -> List[str]:
        """获取所有思考内容"""
        thoughts = []
        for step in self.steps:
            if step.step_type == StepType.THOUGHT:
                thoughts.append(step.content)
        return thoughts
    
    def get_actions(self) -> List[Tuple[str, str]]:
        """获取所有工具调用（工具名, 输入）"""
        actions = []
        current_action = None
        current_input = None
        
        for step in self.steps:
            if step.step_type == StepType.ACTION:
                current_action = step.content.strip()
            elif step.step_type == StepType.ACTION_INPUT and current_action:
                actions.append((current_action, step.content.strip()))
                current_action = None
        
        return actions
    
    def get_observations(self) -> List[str]:
        """获取所有观察结果"""
        observations = []
        for step in self.steps:
            if step.step_type == StepType.OBSERVATION:
                observations.append(step.content)
        return observations


class ReActFormatter:
    """ReAct格式化和修正器"""
    
    def __init__(self):
        self.patterns = {
            StepType.QUESTION: re.compile(r'^Question:\s*(.+)', re.IGNORECASE),
            StepType.THOUGHT: re.compile(r'^Thought(?:\s*\d+)?:\s*(.+)', re.IGNORECASE),
            StepType.ACTION: re.compile(r'^Action(?:\s*\d+)?:\s*(.+)', re.IGNORECASE),
            StepType.ACTION_INPUT: re.compile(r'^Action\s+Input(?:\s*\d+)?:\s*(.+)', re.IGNORECASE),
            StepType.OBSERVATION: re.compile(r'^Observation(?:\s*\d+)?:\s*(.+)', re.IGNORECASE),
            StepType.FINAL_ANSWER: re.compile(r'^Final\s+Answer:\s*(.+)', re.IGNORECASE),
        }
        
        self.error_patterns = [
            re.compile(r'For troubleshooting, visit:', re.IGNORECASE),
            re.compile(r'Invalid or incomplete response', re.IGNORECASE),
            re.compile(r'Parsing LLM output produced both', re.IGNORECASE),
        ]
        
        self.format_separator_patterns = [
            re.compile(r'^===.*===$'),
            re.compile(r'^---.*---$'),
            re.compile(r'^【.*】$'),
            re.compile(r'^#.*$'),
        ]
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除错误信息和干扰内容"""
        cleaned = text
        
        for pattern in self.error_patterns:
            cleaned = pattern.sub('', cleaned)
        
        lines = cleaned.split('\n')
        cleaned_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            is_error = any(pattern.search(line_stripped) for pattern in self.error_patterns)
            is_separator = any(pattern.match(line_stripped) for pattern in self.format_separator_patterns)
            
            if not is_error and not is_separator:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def parse(self, text: str) -> ParsedReAct:
        """
        解析LLM输出为ReAct结构
        
        Args:
            text: LLM原始输出
            
        Returns:
            ParsedReAct: 解析后的结构
        """
        cleaned_text = self._clean_text(text)
        lines = cleaned_text.split('\n')
        
        parsed = ParsedReAct(
            question="",
            steps=[]
        )
        
        current_step = None
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            matched_type = None
            matched_content = None
            
            for step_type, pattern in self.patterns.items():
                match = pattern.match(line_stripped)
                if match:
                    matched_type = step_type
                    matched_content = match.group(1).strip()
                    break
            
            if matched_type:
                if current_step and current_content:
                    full_text = '\n'.join(current_content)
                    if current_step != StepType.QUESTION:
                        parsed.steps.append(ReActStep(
                            step_type=current_step,
                            content='\n'.join(current_content).strip(),
                            raw_text=full_text
                        ))
                
                current_step = matched_type
                current_content = [matched_content]
                
                if matched_type == StepType.QUESTION:
                    parsed.question = matched_content
                    current_step = None
                    current_content = []
            else:
                if current_step:
                    current_content.append(line_stripped)
        
        if current_step and current_content:
            full_text = '\n'.join(current_content)
            parsed.steps.append(ReActStep(
                step_type=current_step,
                content='\n'.join(current_content).strip(),
                raw_text=full_text
            ))
        
        for step in parsed.steps:
            if step.step_type == StepType.FINAL_ANSWER:
                parsed.final_answer = step.content
                break
        
        return parsed
    
    def format(self, parsed: ParsedReAct) -> str:
        """
        将ParsedReAct格式化为字符串
        
        Args:
            parsed: 解析后的结构
            
        Returns:
            str: 格式化后的字符串
        """
        lines = []
        
        if parsed.question:
            lines.append(f"Question: {parsed.question}")
        
        for step in parsed.steps:
            prefix = step.step_type.value
            if step.step_type == StepType.ACTION_INPUT:
                prefix = "Action Input"
            
            lines.append(f"{prefix}: {step.content}")
        
        return '\n'.join(lines)
    
    def correct(self, text: str) -> str:
        """
        修正LLM输出为符合ReAct格式的字符串
        
        Args:
            text: LLM原始输出
            
        Returns:
            str: 修正后的字符串
        """
        parsed = self.parse(text)
        return self.format(parsed)
    
    def extract_final_answer(self, text: str) -> Optional[str]:
        """
        从LLM输出中提取最终答案
        
        Args:
            text: LLM原始输出
            
        Returns:
            Optional[str]: 最终答案，如果没有则返回None
        """
        parsed = self.parse(text)
        
        if parsed.final_answer:
            return parsed.final_answer
        
        thoughts = parsed.get_thoughts()
        if thoughts:
            last_thought = thoughts[-1]
            if any(keyword in last_thought.lower() for keyword in ['最终', '回答', '答案', '总结', '回复']):
                return last_thought
        
        observations = parsed.get_observations()
        if observations:
            return observations[-1]
        
        thoughts = parsed.get_thoughts()
        if thoughts:
            return thoughts[-1]
        
        return None
    
    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """
        验证LLM输出是否符合ReAct格式
        
        Args:
            text: LLM原始输出
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误列表)
        """
        errors = []
        
        if not text or not text.strip():
            errors.append("输出为空")
            return False, errors
        
        for pattern in self.error_patterns:
            if pattern.search(text):
                errors.append("包含错误信息")
                break
        
        if errors:
            return False, errors
        
        lines = text.split('\n')
        
        has_action = False
        has_answer = False
        has_thought = False
        
        for line in lines:
            stripped = line.strip()
            if re.match(r'^Action(?:\s*\d+)?:', stripped, re.IGNORECASE):
                has_action = True
            elif re.match(r'^Final\s+Answer:', stripped, re.IGNORECASE):
                has_answer = True
            elif re.match(r'^Thought(?:\s*\d+)?:', stripped, re.IGNORECASE):
                has_thought = True
        
        if has_action and has_answer:
            errors.append("同时包含Action和Final Answer")
            return False, errors
        
        if has_action:
            action_input_count = 0
            action_count = 0
            for line in lines:
                if re.match(r'^Action\s+Input(?:\s*\d+)?:', line, re.MULTILINE | re.IGNORECASE):
                    action_input_count += 1
                if re.match(r'^Action(?:\s*\d+)?:', line, re.MULTILINE | re.IGNORECASE):
                    action_count += 1
            
            if action_input_count < action_count:
                errors.append("Action缺少对应的Action Input")
                return False, errors
        
        if has_answer:
            has_content = False
            for i, line in enumerate(lines):
                if re.match(r'^Final\s+Answer:', line, re.IGNORECASE):
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line:
                            has_content = True
                            break
                    break
            
            if not has_content:
                for line in lines:
                    match = re.match(r'^Final\s+Answer:\s*(.+)$', line, re.IGNORECASE)
                    if match and match.group(1).strip():
                        has_content = True
                        break
            
            if not has_content:
                errors.append("Final Answer内容为空")
                return False, errors
        
        if not has_action and not has_answer:
            if has_thought:
                has_content = False
                found_thought = False
                for line in lines:
                    stripped = line.strip()
                    if re.match(r'^Thought(?:\s*\d+)?:', stripped, re.IGNORECASE):
                        found_thought = True
                    elif found_thought and stripped:
                        if not re.match(r'^[A-Z][a-z]*\s*:', stripped):
                            has_content = True
                            break
                
                if not has_content:
                    errors.append("既没有Action也没有Final Answer")
                    return False, errors
        
        return len(errors) == 0, errors
    
    def generate_retry_prompt(self, original_prompt: str, errors: List[str]) -> str:
        """
        生成重试提示，指导LLM修正格式错误
        
        Args:
            original_prompt: 原始提示词
            errors: 错误列表
            
        Returns:
            str: 包含错误信息的重试提示
        """
        error_messages = "\n".join([f"- {error}" for error in errors])
        
        retry_prompt = f"""
你之前的输出存在以下格式错误：
{error_messages}

请重新输出，严格遵循以下格式：

【需要调用工具时】
Thought: 你的思考过程
Action: 工具名称
Action Input: 工具输入内容

【不需要调用工具时】
Thought: 我已经得到最终答案
Final Answer: 你的中文答复

注意：
1. 不要同时输出Action和Final Answer
2. Action和Action Input必须成对出现
3. 不要包含任何错误信息或格式说明文本
4. 工具输入必须是纯文本，不要使用JSON格式
"""
        
        return retry_prompt.strip()
    
    def has_both_action_and_answer(self, text: str) -> bool:
        """检查是否同时包含Action和Final Answer"""
        has_action = bool(re.search(r'^Action(?:\s*\d+)?:', text, re.MULTILINE | re.IGNORECASE))
        has_answer = bool(re.search(r'^Final\s+Answer:', text, re.MULTILINE | re.IGNORECASE))
        return has_action and has_answer
    
    def extract_clean_answer(self, text: str) -> str:
        """提取干净的最终答案，移除所有ReAct格式标记"""
        parsed = self.parse(text)
        
        if parsed.final_answer:
            return parsed.final_answer
        
        text_lower = text.lower()
        if 'final answer:' in text_lower:
            idx = text.lower().find('final answer:') + len('final answer:')
            return text[idx:].strip()
        
        if '总结:' in text_lower:
            idx = text.lower().find('总结:') + len('总结:')
            return text[idx:].strip()
        
        if '回答:' in text_lower:
            idx = text.lower().find('回答:') + len('回答:')
            return text[idx:].strip()
        
        return self._clean_text(text)


def format_react_output(text: str, strict: bool = False) -> Dict[str, Any]:
    """
    格式化LLM输出为ReAct格式的便捷函数
    
    Args:
        text: LLM原始输出
        strict: 是否严格模式（严格模式下会验证格式）
        
    Returns:
        Dict[str, Any]: 包含格式化结果的字典
            - original: 原始文本
            - formatted: 格式化后的文本
            - final_answer: 最终答案
            - is_valid: 是否符合格式
            - errors: 错误列表（如果有）
    """
    formatter = ReActFormatter()
    
    result = {
        'original': text,
        'formatted': formatter.correct(text),
        'final_answer': formatter.extract_final_answer(text),
        'is_valid': True,
        'errors': []
    }
    
    if strict:
        is_valid, errors = formatter.validate(text)
        result['is_valid'] = is_valid
        result['errors'] = errors
    
    return result