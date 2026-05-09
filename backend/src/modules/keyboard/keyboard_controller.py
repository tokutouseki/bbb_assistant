#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
键盘控制器
提供键盘模拟操作功能
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import ctypes
from ctypes import wintypes

logger = logging.getLogger(__name__)


@dataclass
class KeyResult:
    """按键操作结果"""
    success: bool
    key: str
    action: str
    duration: float
    error: Optional[str] = None
    timestamp: str = ""


class KeyboardController:
    """键盘控制器"""

    # 常用按键映射
    KEY_MAPPING = {
        # 字母键
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47,
        'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E,
        'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55,
        'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
        
        # 数字键
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
        '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        
        # 功能键
        'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
        'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
        
        # 特殊键
        'enter': 0x0D, 'return': 0x0D, 'space': 0x20, 'tab': 0x09, 'backspace': 0x08,
        'escape': 0x1B, 'esc': 0x1B, 'shift': 0x10, 'ctrl': 0x11, 'control': 0x11,
        'alt': 0x12, 'win': 0x5B, 'windows': 0x5B, 'cmd': 0x5B, 'capslock': 0x14,
        'insert': 0x2D, 'delete': 0x2E, 'home': 0x24, 'end': 0x23, 'pageup': 0x21,
        'pagedown': 0x22, 'left': 0x25, 'right': 0x27, 'up': 0x26, 'down': 0x28,
        
        # 小键盘
        'num0': 0x60, 'num1': 0x61, 'num2': 0x62, 'num3': 0x63, 'num4': 0x64,
        'num5': 0x65, 'num6': 0x66, 'num7': 0x67, 'num8': 0x68, 'num9': 0x69,
        'num+': 0x6B, 'num-': 0x6D, 'num*': 0x6A, 'num/': 0x6F, 'numenter': 0x6C,
        
        # 符号键
        '`': 0xC0, '-': 0xBD, '=': 0xBB, '[': 0xDB, ']': 0xDD, ';': 0xBA,
        "'": 0xDE, ',': 0xBC, '.': 0xBE, '/': 0xBF, '\\': 0xDC,
    }

    # Windows API 结构体
    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            class _KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ('wVk', wintypes.WORD),
                    ('wScan', wintypes.WORD),
                    ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
                ]
            _fields_ = [
                ('ki', _KEYBDINPUT),
            ]
        _anonymous_ = ('_input',)
        _fields_ = [
            ('type', wintypes.DWORD),
            ('_input', _INPUT),
        ]

    # 常量
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if KeyboardController._initialized:
            return
        self.user32 = ctypes.windll.user32
        self._send_input = self.user32.SendInput
        self._send_input.argtypes = (
            ctypes.c_uint,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        )
        self._send_input.restype = ctypes.c_uint
        KeyboardController._initialized = True
        logger.info("键盘控制器初始化完成")

    @classmethod
    def get_instance(cls):
        """获取单例"""
        return cls()

    def _get_key_code(self, key: str) -> Optional[int]:
        """获取按键的虚拟键码"""
        key_lower = key.strip().lower()
        
        if key_lower in self.KEY_MAPPING:
            return self.KEY_MAPPING[key_lower]
        
        # 尝试处理单个字符
        if len(key) == 1:
            # 大写字母
            if 'A' <= key <= 'Z':
                return ord(key)
            # 小写字母
            elif 'a' <= key <= 'z':
                return ord(key.upper())
            # 数字
            elif '0' <= key <= '9':
                return ord(key)
        
        logger.warning(f"未知按键: {key}")
        return None

    def _press_key(self, key_code: int):
        """按下指定按键"""
        inputs = (self.INPUT * 1)()
        inputs[0].type = self.INPUT_KEYBOARD
        inputs[0].ki.wVk = key_code
        inputs[0].ki.dwFlags = 0
        self._send_input(1, inputs, ctypes.sizeof(inputs[0]))

    def _release_key(self, key_code: int):
        """释放指定按键"""
        inputs = (self.INPUT * 1)()
        inputs[0].type = self.INPUT_KEYBOARD
        inputs[0].ki.wVk = key_code
        inputs[0].ki.dwFlags = self.KEYEVENTF_KEYUP
        self._send_input(1, inputs, ctypes.sizeof(inputs[0]))

    def press_and_hold(self, key: str, duration: float = 0.1) -> KeyResult:
        """
        按下并按住指定按键一段时间
        
        Args:
            key: 按键名称
            duration: 持续时间（秒）
            
        Returns:
            KeyResult: 操作结果
        """
        start_time = time.time()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            key_code = self._get_key_code(key)
            if key_code is None:
                return KeyResult(
                    success=False,
                    key=key,
                    action='press_hold',
                    duration=duration,
                    error=f"未知按键: {key}",
                    timestamp=timestamp
                )
            
            # 按下按键
            self._press_key(key_code)
            
            # 保持按下状态
            time.sleep(duration)
            
            # 释放按键
            self._release_key(key_code)
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            logger.info(f"按键操作成功: {key} (持续 {actual_duration:.3f}秒)")
            
            return KeyResult(
                success=True,
                key=key,
                action='press_hold',
                duration=actual_duration,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"按键操作失败: {key}, 错误: {e}")
            return KeyResult(
                success=False,
                key=key,
                action='press_hold',
                duration=duration,
                error=str(e),
                timestamp=timestamp
            )

    def tap(self, key: str) -> KeyResult:
        """
        快速点击按键
        
        Args:
            key: 按键名称
            
        Returns:
            KeyResult: 操作结果
        """
        return self.press_and_hold(key, duration=0.05)

    def type_text(self, text: str, delay_between_keys: float = 0.05) -> Dict[str, Any]:
        """
        输入文本
        
        Args:
            text: 要输入的文本
            delay_between_keys: 按键之间的延迟（秒）
            
        Returns:
            Dict: 操作结果
        """
        start_time = time.time()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        results = []
        
        try:
            for char in text:
                # 处理特殊字符
                if char == '\n':
                    result = self.tap('enter')
                elif char == '\t':
                    result = self.tap('tab')
                elif char == ' ':
                    result = self.tap('space')
                else:
                    result = self.press_and_hold(char, duration=0.01)
                
                results.append({
                    'char': char,
                    'success': result.success,
                    'error': result.error
                })
                
                if delay_between_keys > 0:
                    time.sleep(delay_between_keys)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            success_count = sum(1 for r in results if r['success'])
            
            logger.info(f"文本输入完成: 总字符数 {len(results)}, 成功 {success_count}, 耗时 {total_time:.3f}秒")
            
            return {
                'success': success_count == len(results),
                'text': text,
                'total_chars': len(results),
                'success_count': success_count,
                'total_time': total_time,
                'timestamp': timestamp,
                'details': results
            }
            
        except Exception as e:
            logger.error(f"文本输入失败: {e}")
            return {
                'success': False,
                'text': text,
                'error': str(e),
                'timestamp': timestamp
            }

    def get_available_keys(self) -> Dict[str, list]:
        """
        获取所有可用按键列表
        
        Returns:
            Dict: 按键分类列表
        """
        categories = {
            '字母键': [k for k in self.KEY_MAPPING if len(k) == 1 and 'a' <= k <= 'z'],
            '数字键': [k for k in self.KEY_MAPPING if k.isdigit()],
            '功能键': [k for k in self.KEY_MAPPING if k.startswith('f') and len(k) <= 3],
            '特殊键': [k for k in self.KEY_MAPPING if k in [
                'enter', 'space', 'tab', 'backspace', 'escape', 'shift', 'ctrl', 'alt', 'win',
                'home', 'end', 'pageup', 'pagedown', 'left', 'right', 'up', 'down',
                'insert', 'delete', 'capslock'
            ]],
            '小键盘': [k for k in self.KEY_MAPPING if k.startswith('num')],
            '符号键': [k for k in self.KEY_MAPPING if k in '`-=[];,./\\']
        }
        return categories

    def hotkey(self, keys: list) -> KeyResult:
        """
        按下组合键（热键）
        
        Args:
            keys: 按键列表，例如 ['ctrl', 'c']
            
        Returns:
            KeyResult: 操作结果
        """
        start_time = time.time()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # 验证所有按键
            key_codes = []
            for key in keys:
                key_code = self._get_key_code(key)
                if key_code is None:
                    return KeyResult(
                        success=False,
                        key='+'.join(keys),
                        action='hotkey',
                        duration=0,
                        error=f"未知按键: {key}",
                        timestamp=timestamp
                    )
                key_codes.append(key_code)
            
            # 按下所有按键
            for key_code in key_codes:
                self._press_key(key_code)
            
            # 短暂保持
            time.sleep(0.05)
            
            # 反向释放所有按键
            for key_code in reversed(key_codes):
                self._release_key(key_code)
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            logger.info(f"热键操作成功: {'+'.join(keys)}")
            
            return KeyResult(
                success=True,
                key='+'.join(keys),
                action='hotkey',
                duration=actual_duration,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"热键操作失败: {'+'.join(keys)}, 错误: {e}")
            return KeyResult(
                success=False,
                key='+'.join(keys),
                action='hotkey',
                duration=0,
                error=str(e),
                timestamp=timestamp
            )
