#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具集成模块
将联网搜索和百科爬虫功能集成到LLM系统中
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .web_search.web_searcher import WebSearcher, SearchEngine, create_web_search_tool
from .vision.yolo_model_manager import YOLOModelManager
# from .crawler.honkai_wiki_crawler import HonkaiWikiCrawler, sync_crawl

logger = logging.getLogger(__name__)


class LLMToolIntegration:
    """LLM工具集成"""
    
    def __init__(self, enable_search: bool = True, enable_crawler: bool = True, enable_vision: bool = True, enable_audio: bool = False):
        """
        初始化工具集成
        
        Args:
            enable_search: 启用联网搜索
            enable_crawler: 启用百科爬虫
            enable_vision: 启用视觉工具
            enable_audio: 启用音频工具（ASR/TTS）
        """
        self.enable_search = enable_search
        self.enable_crawler = enable_crawler
        self.enable_vision = enable_vision
        self.enable_audio = enable_audio
        
        # 初始化搜索器
        self.searcher = None
        if enable_search:
            try:
                self.searcher = WebSearcher(engine=SearchEngine.GOOGLE)
                logger.info("联网搜索工具初始化完成")
            except Exception as e:
                logger.warning(f"联网搜索工具初始化失败: {e}")
                self.searcher = None
        
        # 初始化爬虫
        self.crawler = None
        if enable_crawler:
            try:
                # 暂时禁用爬虫，因为honkai_wiki_crawler.py有语法错误
                # from .crawler.honkai_wiki_crawler import CrawlerMode
                # self.crawler = HonkaiWikiCrawler(mode=CrawlerMode.AUTO)
                # logger.info("百科爬虫工具初始化完成")
                logger.info("爬虫功能暂时禁用")
                self.crawler = None
            except Exception as e:
                logger.warning(f"百科爬虫工具初始化失败: {e}")
                self.crawler = None
        
        self.yolo_manager = None
        if enable_vision:
            try:
                self.yolo_manager = YOLOModelManager.get_instance()
                logger.info("YOLO工具初始化完成")
            except Exception as e:
                logger.warning(f"YOLO工具初始化失败: {e}")
                self.yolo_manager = None
        
        # 工具注册表
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_tools()
        
        logger.info(f"LLM工具集成初始化完成，可用工具: {list(self.tools.keys())}")
    
    def _register_tools(self):
        """注册可用工具"""
        # 联网搜索工具
        if self.searcher:
            self.tools["web_search"] = {
                "name": "web_search",
                "description": "执行联网搜索，获取最新信息。适用于需要实时数据、新闻、最新攻略、版本更新等场景。",
                "function": self.search_web,
                "parameters": {
                    "query": {"type": "string", "description": "搜索查询内容"},
                    "context": {"type": "string", "description": "上下文信息，用于优化搜索", "optional": True}
                },
                "examples": [
                    "搜索崩坏3 7.0版本更新内容",
                    "查找薪炎之律者最新攻略",
                    "获取崩坏3最新活动信息"
                ]
            }
        
        # 百科爬虫工具
        if self.crawler:
            self.tools["crawl_wiki"] = {
                "name": "crawl_wiki",
                "description": "爬取崩坏3官方百科信息。适用于获取游戏角色、武器、圣痕、剧情等详细资料。",
                "function": self.crawl_honkai_wiki,
                "parameters": {
                    "topic": {"type": "string", "description": "要爬取的主题或关键词"},
                    "max_pages": {"type": "integer", "description": "最大爬取页面数", "optional": True, "default": 5}
                },
                "examples": [
                    "爬取薪炎之律者相关资料",
                    "获取所有女武神信息",
                    "查找武器「涤罪七雷」的详细数据"
                ]
            }
        
        # 知识库查询工具（未来扩展）
        self.tools["query_knowledge"] = {
            "name": "query_knowledge",
            "description": "查询本地知识库中的信息。适用于已知的、静态的游戏资料查询。",
            "function": self.query_knowledge_base,
            "parameters": {
                "question": {"type": "string", "description": "查询问题"}
            },
            "examples": [
                "琪亚娜·卡斯兰娜的背景故事",
                "雷电芽衣的技能介绍",
                "往世乐土的玩法说明"
            ]
        }

        if self.yolo_manager:
            self.tools["list_yolo_models"] = {
                "name": "list_yolo_models",
                "description": "列出可用和已加载的YOLO模型，便于AI选择模型。",
                "function": self.list_yolo_models,
                "parameters": {},
                "examples": ["有哪些YOLO模型可用？", "当前加载了哪些视觉模型？"],
            }
            self.tools["load_yolo_model"] = {
                "name": "load_yolo_model",
                "description": "加载YOLO模型到内存，提升后续检测速度。",
                "function": self.load_yolo_model,
                "parameters": {
                    "model_name": {"type": "string", "description": "模型名（不含后缀）"},
                    "device": {"type": "string", "description": "设备，如cpu/cuda:0", "optional": True},
                },
                "examples": ["加载yolo11n模型", "把boss_detect模型加载到cuda:0"],
            }
            self.tools["unload_yolo_model"] = {
                "name": "unload_yolo_model",
                "description": "卸载YOLO模型，释放内存。",
                "function": self.unload_yolo_model,
                "parameters": {"model_name": {"type": "string", "description": "模型名"}},
                "examples": ["卸载yolo11n", "释放boss_detect模型"],
            }
        
        # TTS 工具
        if self.enable_audio:
            self.tools["tts_qwen3"] = {
                "name": "tts_qwen3",
                "description": "使用Qwen3-TTS引擎将文本转为语音（默认使用爱莉希雅参考音频进行高精度ICL声音克隆）。支持39位崩坏3角色（爱莉希雅/琪亚娜/芽衣/布洛妮娅/符华等），通过ref_audio指定角色名即可切换克隆目标。",
                "function": self.generate_tts_qwen3,
                "parameters": {
                    "text": {"type": "string", "description": "要合成的文本"},
                    "ref_audio": {"type": "string", "description": "参考音频路径或崩坏3角色名（默认爱莉希雅）。可选: 爱莉希雅/琪亚娜/芽衣/布洛妮娅/符华/德丽莎/希儿/八重樱/卡莲/丽塔/姬子/渡鸦/阿波尼亚/梅比乌斯/维尔薇/帕朵菲莉丝/格蕾修/伊甸/苏莎娜/李素裳/时雨绮罗/幽兰黛尔/西琳/薇塔/花火/瑟莉姆/科拉莉/赫丽娅/灯/松雀/羽兔/普罗米修斯/爱衣/菲谢尔/刻晴/卡萝尔/明日香/希娜狄雅/伏特加女孩", "optional": True, "default": "爱莉希雅"},
                    "ref_text": {"type": "string", "description": "可选，参考音频对应的文本内容。留空自动从索引读取。", "optional": True, "default": ""},
                    "language": {"type": "string", "description": "语言: Chinese/English/Japanese/Korean等", "optional": True, "default": "Chinese"}
                },
                "examples": [
                    "用爱莉希雅的声音说'大家好呀，我是爱莉希雅~'",
                    "用琪亚娜的声音说'舰长，任务完成啦'",
                    "用芽衣的声音朗读这段文本"
                ]
            }
            # ASR 工具
            self.tools["asr_transcribe"] = {
                "name": "asr_transcribe",
                "description": "语音识别。将音频文件转换为文本。",
                "function": self.transcribe_asr,
                "parameters": {
                    "audio_path": {"type": "string", "description": "音频文件路径"},
                    "language": {"type": "string", "description": "语言代码，如zh、en等", "optional": True, "default": "zh"}
                },
                "examples": [
                    "识别audio.wav文件",
                    "识别英文音频文件english.wav"
                ]
            }
        
        # CV 工具
        self.tools["cv_analyze_image"] = {
            "name": "cv_analyze_image",
            "description": "分析图像内容。使用YOLO模型进行目标检测。",
            "function": self.analyze_image,
            "parameters": {
                "image_path": {"type": "string", "description": "图像文件路径"},
                "model_name": {"type": "string", "description": "YOLO模型名称，如yolo11n", "optional": True, "default": "yolo11n"},
                "confidence_threshold": {"type": "number", "description": "置信度阈值，0-1之间", "optional": True, "default": 0.5}
            },
            "examples": [
                "分析游戏截图screenshot.png",
                "用yolo11n模型分析boss.jpg"
            ]
        }
        
        # PowerShell 工具
        self.tools["run_powershell"] = {
            "name": "run_powershell",
            "description": "执行PowerShell命令。",
            "function": self.run_powershell,
            "parameters": {
                "command": {"type": "string", "description": "要执行的PowerShell命令"},
                "timeout": {"type": "number", "description": "命令执行超时时间（秒）", "optional": True, "default": 30}
            },
            "examples": [
                "查看当前目录文件: Get-ChildItem",
                "检查系统信息: systeminfo"
            ]
        }
        
        # 键盘操作工具
        self.tools["press_key"] = {
            "name": "press_key",
            "description": "模拟按下键盘按键，可以设置持续时间。",
            "function": self.press_key,
            "parameters": {
                "key": {"type": "string", "description": "按键名称，如 'a', 'enter', 'space', 'ctrl', 'shift', 'f1' 等"},
                "duration": {"type": "number", "description": "按键持续时间（秒），默认为0.1秒", "optional": True, "default": 0.1}
            },
            "examples": [
                "按下A键: key='a', duration=0.1",
                "按回车键: key='enter'",
                "按住空格键1秒: key='space', duration=1.0"
            ]
        }
        
        # 文本输入工具
        self.tools["type_text"] = {
            "name": "type_text",
            "description": "模拟键盘输入文本内容。",
            "function": self.type_text,
            "parameters": {
                "text": {"type": "string", "description": "要输入的文本内容"},
                "delay": {"type": "number", "description": "按键之间的延迟（秒），默认为0.05秒", "optional": True, "default": 0.05}
            },
            "examples": [
                "输入Hello: text='Hello'",
                "输入中文: text='你好世界'"
            ]
        }
        
        # 热键工具
        self.tools["press_hotkey"] = {
            "name": "press_hotkey",
            "description": "按下组合键（热键），如 Ctrl+C, Alt+F4 等。",
            "function": self.press_hotkey,
            "parameters": {
                "keys": {"type": "string", "description": "按键组合，用+分隔，如 'ctrl+c', 'alt+f4', 'shift+enter'"}
            },
            "examples": [
                "复制: keys='ctrl+c'",
                "粘贴: keys='ctrl+v'",
                "保存: keys='ctrl+s'"
            ]
        }
        
        # 获取可用按键工具
        self.tools["list_keys"] = {
            "name": "list_keys",
            "description": "获取所有可用的按键列表，了解支持哪些按键操作。",
            "function": self.list_keys,
            "parameters": {},
            "examples": [
                "查看所有可用按键: list_keys"
            ]
        }
    
    def search_web(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        联网搜索工具
        
        Args:
            query: 搜索查询
            context: 上下文信息
            
        Returns:
            搜索结果
        """
        logger.info(f"执行联网搜索: query='{query}', context='{context}'")
        
        if not self.searcher:
            return {
                "success": False,
                "error": "联网搜索功能未启用",
                "results": []
            }
        
        try:
            # 执行搜索
            response = self.searcher.search_with_context(query, context)
            
            # 提取答案摘要
            search_results = []
            for r in response['results']:
                result = {
                    'title': r['title'],
                    'url': r['url'],
                    'snippet': r['snippet'],
                    'source': r['source']
                }
                search_results.append(result)
            
            # 生成回答
            answer = self.searcher.extract_answers(query, [
                type('Result', (), {
                    'title': r['title'],
                    'url': r['url'],
                    'snippet': r['snippet'],
                    'source': r['source'],
                    'content': r.get('content', ''),
                    'relevance': r.get('relevance', 0.0)
                })() for r in response['results']
            ])
            
            return {
                "success": True,
                "query": query,
                "answer": answer,
                "results": search_results[:3],  # 只返回前3个结果
                "total_results": response['total_results'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def crawl_honkai_wiki(self, topic: str, max_pages: int = 5) -> Dict[str, Any]:
        """
        爬取崩坏3百科工具
        
        Args:
            topic: 爬取主题
            max_pages: 最大页面数
            
        Returns:
            爬取结果
        """
        logger.info(f"执行百科爬取: topic='{topic}', max_pages={max_pages}")
        
        if not self.crawler:
            return {
                "success": False,
                "error": "百科爬虫功能未启用",
                "pages": []
            }
        
        try:
            # 构建搜索URL（简化实现）
            # 实际应用中可能需要更复杂的逻辑来定位相关页面
            start_url = "https://baike.mihoyo.com/bh3/wiki/"
            
            # 同步爬取
            pages = sync_crawl(start_url, mode="auto", max_pages=max_pages)
            
            # 过滤与主题相关的页面
            relevant_pages = []
            for page in pages:
                if (topic.lower() in page.title.lower() or 
                    topic.lower() in page.content.lower()):
                    relevant_pages.append({
                        'title': page.title,
                        'url': page.url,
                        'category': page.category,
                        'content_preview': page.content[:300] + "..." if len(page.content) > 300 else page.content,
                        'links_count': len(page.links)
                    })
            
            # 生成摘要
            summary = f"找到 {len(relevant_pages)} 个与'{topic}'相关的页面。"
            if relevant_pages:
                summary += " 内容包括: " + ", ".join([p['title'] for p in relevant_pages[:3]])
            
            return {
                "success": True,
                "topic": topic,
                "summary": summary,
                "pages": relevant_pages[:5],  # 只返回前5个相关页面
                "total_pages": len(pages),
                "relevant_pages": len(relevant_pages),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"百科爬取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "pages": []
            }
    
    def query_knowledge_base(self, question: str) -> Dict[str, Any]:
        """
        查询本地知识库工具
        
        Args:
            question: 查询问题
            
        Returns:
            查询结果
        """
        logger.info(f"查询知识库: question='{question}'")
        
        # 简化实现：返回静态响应
        # 实际应用中应集成向量数据库或本地知识库
        knowledge_responses = {
            "琪亚娜": "琪亚娜·卡斯兰娜是崩坏3的主角，天命组织女武神，卡斯兰娜家族成员。",
            "雷电芽衣": "雷电芽衣是ME社社长雷电龙马的女儿，第三律者雷之律者。",
            "布洛妮娅": "布洛妮娅·扎伊切克是逆熵的代理盟主，理之律者。",
            "薪炎之律者": "薪炎之律者是琪亚娜·卡斯兰娜的炎之律者形态，拥有强大的火焰能力。",
            "往世乐土": "往世乐土是崩坏3中的Roguelike玩法模式，玩家可以挑战不同难度的关卡。"
        }
        
        # 查找相关关键词
        answer = None
        for keyword, response in knowledge_responses.items():
            if keyword in question:
                answer = response
                break
        
        if answer:
            return {
                "success": True,
                "question": question,
                "answer": answer,
                "source": "本地知识库",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": True,
                "question": question,
                "answer": "未在本地知识库中找到相关信息，建议使用联网搜索获取最新信息。",
                "source": "本地知识库",
                "timestamp": datetime.now().isoformat()
            }
    
    def list_yolo_models(self) -> Dict[str, Any]:
        if not self.yolo_manager:
            return {"success": False, "error": "YOLO工具未启用"}
        return {
            "success": True,
            "available_models": self.yolo_manager.list_available_models(),
            "loaded_models": self.yolo_manager.list_loaded_models(),
            "stats": self.yolo_manager.get_stats(),
        }

    def load_yolo_model(self, model_name: str, device: str = "cuda:0") -> Dict[str, Any]:
        if not self.yolo_manager:
            return {"success": False, "error": "YOLO工具未启用"}
        return self.yolo_manager.load_model(model_name=model_name, device=device)

    def unload_yolo_model(self, model_name: str) -> Dict[str, Any]:
        if not self.yolo_manager:
            return {"success": False, "error": "YOLO工具未启用"}
        return self.yolo_manager.unload_model(model_name=model_name)
    
    def generate_tts_qwen3(self, text: str, ref_audio: str = "爱莉希雅", ref_text: str = "",
                           language: str = "Chinese") -> Dict[str, Any]:
        """
        使用Qwen3-TTS引擎生成语音（默认ICL声音克隆模式，参考角色: 爱莉希雅）

        Args:
            text: 要合成的文本
            ref_audio: 参考音频路径或崩坏3角色名（默认爱莉希雅）
            ref_text: 参考音频对应文本（可选，角色名模式自动读取）
            language: 语言

        Returns:
            生成结果
        """
        try:
            from src.utils.model_manager import get_qwen3_tts_model
            tts = get_qwen3_tts_model(device="cuda:0")

            actual_path, actual_ref_text = self._resolve_ref_audio(
                ref_audio.strip() if ref_audio.strip() else "爱莉希雅",
                ref_text.strip() if ref_text else ""
            )
            if not actual_path:
                return {"success": False, "error": f"找不到角色 '{ref_audio}' 的参考音频"}

            result = tts.generate_with_reference(
                text=text,
                reference_audio=actual_path,
                language=language,
                ref_text=actual_ref_text if actual_ref_text else None,
            )

            filepath = tts.save_to_file(result)
            return {
                "success": True,
                "engine": "qwen3",
                "mode": "clone",
                "text": text,
                "ref_audio": ref_audio,
                "language": language,
                "filepath": filepath,
                "sample_rate": result.sample_rate,
                "processing_time": result.processing_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _resolve_ref_audio(self, ref_audio: str, ref_text: str) -> tuple:
        """将角色名或文件路径解析为 (audio_path, ref_text)."""
        import os as _os
        if _os.path.isfile(ref_audio):
            return (ref_audio, ref_text)
        try:
            import json as _json
            index_path = _os.path.join(
                _os.path.dirname(__file__), "audio", "reference_audio", "index.json"
            )
            with open(index_path, "r", encoding="utf-8") as _f:
                index = _json.load(_f)
            if ref_audio in index:
                entry = index[ref_audio]
                return (entry["audio_path"], ref_text if ref_text else entry.get("ref_text", ""))
            for name, entry in index.items():
                if ref_audio in name or name in ref_audio:
                    return (entry["audio_path"], ref_text if ref_text else entry.get("ref_text", ""))
        except Exception:
            pass
        return ("", "")

    def transcribe_asr(self, audio_path: str, language: str = "zh") -> Dict[str, Any]:
        """
        语音识别
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            
        Returns:
            识别结果
        """
        try:
            from src.modules.audio.asr_processor import ASRProcessor
            asr = ASRProcessor()
            result = asr.transcribe_file(audio_path=audio_path, language=language, save_result=True)
            return {
                "success": True,
                "text": result.text,
                "confidence": result.confidence,
                "language": result.language,
                "processing_time": result.processing_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_image(self, image_path: str, model_name: str = "yolo11n", confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        分析图像内容
        
        Args:
            image_path: 图像文件路径
            model_name: YOLO模型名称
            confidence_threshold: 置信度阈值
            
        Returns:
            分析结果
        """
        try:
            from src.modules.vision.yolo_model_manager import YOLOModelManager
            yolo = YOLOModelManager.get_instance()
            import cv2
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "success": False,
                    "error": "图像读取失败"
                }
            result = yolo.detect(image=image, model_name=model_name, confidence_threshold=confidence_threshold)
            return {
                "success": True,
                "model": model_name,
                "detections": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_powershell(self, command: str, timeout: float = 30) -> Dict[str, Any]:
        """
        执行PowerShell命令
        
        Args:
            command: PowerShell命令
            timeout: 超时时间（秒）
            
        Returns:
            执行结果
        """
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": True,
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "命令执行超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def press_key(self, key: str, duration: float = 0.1) -> Dict[str, Any]:
        """
        模拟按下键盘按键
        
        Args:
            key: 按键名称
            duration: 持续时间（秒）
            
        Returns:
            Dict: 操作结果
        """
        logger.info(f"执行按键操作: key='{key}', duration={duration}秒")
        
        try:
            from src.modules.keyboard import KeyboardController
            keyboard = KeyboardController.get_instance()
            result = keyboard.press_and_hold(key, duration=duration)
            
            return {
                "success": result.success,
                "key": result.key,
                "action": result.action,
                "duration": result.duration,
                "error": result.error,
                "timestamp": result.timestamp
            }
        except Exception as e:
            logger.error(f"按键操作失败: {e}")
            return {
                "success": False,
                "key": key,
                "error": str(e)
            }
    
    def type_text(self, text: str, delay: float = 0.05) -> Dict[str, Any]:
        """
        模拟键盘输入文本
        
        Args:
            text: 要输入的文本
            delay: 按键之间的延迟（秒）
            
        Returns:
            Dict: 操作结果
        """
        logger.info(f"执行文本输入: text='{text}', delay={delay}秒")
        
        try:
            from src.modules.keyboard import KeyboardController
            keyboard = KeyboardController.get_instance()
            result = keyboard.type_text(text, delay_between_keys=delay)
            
            return result
        except Exception as e:
            logger.error(f"文本输入失败: {e}")
            return {
                "success": False,
                "text": text,
                "error": str(e)
            }
    
    def press_hotkey(self, keys: str) -> Dict[str, Any]:
        """
        按下组合键（热键）
        
        Args:
            keys: 按键组合，用+分隔，如 'ctrl+c'
            
        Returns:
            Dict: 操作结果
        """
        logger.info(f"执行热键操作: keys='{keys}'")
        
        try:
            from src.modules.keyboard import KeyboardController
            keyboard = KeyboardController.get_instance()
            
            # 解析按键组合
            key_list = [k.strip().lower() for k in keys.split('+') if k.strip()]
            
            result = keyboard.hotkey(key_list)
            
            return {
                "success": result.success,
                "keys": result.key,
                "action": result.action,
                "duration": result.duration,
                "error": result.error,
                "timestamp": result.timestamp
            }
        except Exception as e:
            logger.error(f"热键操作失败: {e}")
            return {
                "success": False,
                "keys": keys,
                "error": str(e)
            }
    
    def list_keys(self) -> Dict[str, Any]:
        """
        获取所有可用按键列表
        
        Returns:
            Dict: 可用按键列表
        """
        logger.info("获取可用按键列表")
        
        try:
            from src.modules.keyboard import KeyboardController
            keyboard = KeyboardController.get_instance()
            categories = keyboard.get_available_keys()
            
            return {
                "success": True,
                "categories": categories
            }
        except Exception as e:
            logger.error(f"获取按键列表失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        tools_list = []
        for tool_id, tool_info in self.tools.items():
            tools_list.append({
                "id": tool_id,
                "name": tool_info["name"],
                "description": tool_info["description"],
                "parameters": tool_info["parameters"],
                "examples": tool_info.get("examples", [])
            })
        
        return tools_list
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"工具 '{tool_name}' 不存在",
                "available_tools": list(self.tools.keys())
            }
        
        tool_info = self.tools[tool_name]
        try:
            result = tool_info["function"](**kwargs)
            result["tool"] = tool_name
            return result
        except Exception as e:
            logger.error(f"执行工具 '{tool_name}' 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }
    
    def should_use_tool(self, message: str) -> List[str]:
        """
        判断应该使用哪些工具
        
        Args:
            message: 用户消息
            
        Returns:
            建议使用的工具名称列表，按优先级排序
        """
        message_lower = message.lower()
        suggested_tools = []
        
        # 键盘操作工具判断 - 优先判断
        keyboard_keywords = [
            "按键", "键盘", "按", "按下", "输入", "打字", "输入文本",
            "key", "keyboard", "press", "type", "type text", "input text",
            "回车", "enter", "空格", "space", "ctrl", "shift", "alt",
            "热键", "组合键", "快捷键", "hotkey", "shortcut"
        ]
        if any(keyword in message_lower for keyword in keyboard_keywords):
            # 判断是哪种键盘操作
            if any(k in message_lower for k in ["输入", "打字", "输入文本", "type text", "input text"]):
                suggested_tools.append("type_text")
            elif any(k in message_lower for k in ["组合键", "热键", "快捷键", "hotkey", "shortcut", "ctrl+", "shift+", "alt+"]):
                suggested_tools.append("press_hotkey")
            elif any(k in message_lower for k in ["查看", "列表", "有哪些", "按键列表", "list keys"]):
                suggested_tools.append("list_keys")
            else:
                suggested_tools.append("press_key")
        
        # PowerShell 工具判断
        powershell_keywords = ["powershell", "cmd", "命令行"]
        if any(keyword in message_lower for keyword in powershell_keywords):
            suggested_tools.append("run_powershell")
        
        # TTS 工具判断
        if self.enable_audio:
            generic_tts_keywords = ["语音", "声音", "说", "朗读", "发音", "tts", "speech", "voice", "say", "speak", "generate audio", "tts_generate", "qwen3", "qwen"]
            if any(keyword in message_lower for keyword in generic_tts_keywords):
                suggested_tools.append("tts_qwen3")
        
        # ASR 工具判断
        if self.enable_audio:
            asr_keywords = ["识别", "语音识别", "听", "asr", "转录", "transcribe", "recognize", "speech to text", "audio to text", "asr_transcribe"]
            if any(keyword in message_lower for keyword in asr_keywords):
                suggested_tools.append("asr_transcribe")
        
        # CV 工具判断
        cv_keywords = ["分析", "图像", "图片", "截图", "cv", "检测", "识别图片", "analyze image", "analyze picture", "detect", "computer vision", "image analysis", "cv_analyze_image"]
        if any(keyword in message_lower for keyword in cv_keywords):
            suggested_tools.append("cv_analyze_image")
        
        # 判断是否需要联网搜索
        search_keywords = [
            "最新", "最近", "2025", "2026", "更新", "新闻", "实时",
            "现在", "当前", "今天", "本周", "本月", "今年",
            "搜索", "查找", "查询", "百度", "google", "联网",
            "search", "find", "look up", "google", "latest", "recent", "update", "news"
        ]
        
        if any(keyword in message_lower for keyword in search_keywords):
            suggested_tools.append("web_search")
            # 搜索关键词也触发知识库查询
            suggested_tools.append("query_knowledge")
        
        # 判断是否需要百科爬虫
        wiki_keywords = [
            "百科", "wiki", "资料", "数据", "详细", "介绍", "背景",
            "角色", "女武神", "武器", "圣痕", "道具", "技能",
            "攻略", "指南", "教程", "怎么玩", "如何",
            "encyclopedia", "wiki", "data", "detailed", "introduction", "background",
            "character", "valkyrie", "weapon", "stigmata", "item", "skill",
            "guide", "tutorial", "how to play", "how to"
        ]
        
        if any(keyword in message_lower for keyword in wiki_keywords):
            suggested_tools.append("crawl_wiki")
        
        # 判断是否需要知识库查询
        knowledge_keywords = [
            "是什么", "是谁", "什么是", "介绍一下", "解释一下",
            "说明", "讲述", "描述", "特点", "特性", "能力",
            "what is", "who is", "introduce", "explain", "describe", "characteristics", "features", "abilities"
        ]
        
        if any(keyword in message_lower for keyword in knowledge_keywords):
            suggested_tools.append("query_knowledge")

        yolo_list_keywords = ["yolo", "模型", "视觉模型", "目标检测模型", "有哪些模型", "已加载模型"]
        if any(keyword in message_lower for keyword in yolo_list_keywords):
            if any(k in message_lower for k in ["有哪些", "列表", "查看", "已加载"]):
                suggested_tools.append("list_yolo_models")

        if any(k in message_lower for k in ["加载", "装载"]) and "模型" in message_lower and "yolo" in message_lower:
            suggested_tools.append("load_yolo_model")

        if any(k in message_lower for k in ["卸载", "释放"]) and "模型" in message_lower and "yolo" in message_lower:
            suggested_tools.append("unload_yolo_model")
        
        return suggested_tools
    
    def enhance_response_with_tools(
        self, 
        user_message: str, 
        llm_response: str,
        max_tool_calls: int = 2
    ) -> Dict[str, Any]:
        """
        使用工具增强LLM响应
        
        Args:
            user_message: 用户消息
            llm_response: LLM原始响应
            max_tool_calls: 最大工具调用次数
            
        Returns:
            包含增强后响应和工具使用步骤的字典
        """
        logger.info(f"尝试使用工具增强响应: '{user_message[:50]}...'")
        
        # 判断应该使用哪些工具
        suggested_tools = self.should_use_tool(user_message)
        if not suggested_tools:
            return {
                "response": llm_response,
                "tool_steps": []
            }
        
        logger.info(f"建议使用工具: {suggested_tools}")
        
        # 限制工具调用次数
        tools_to_use = suggested_tools[:max_tool_calls]
        tool_steps = []
        
        try:
            enhanced_response = llm_response
            
            # 遍历推荐的工具
            for tool_name in tools_to_use:
                step = {
                    "tool": tool_name,
                    "input": user_message,
                    "start_time": datetime.now().isoformat()
                }
                
                tool_result = self._execute_tool_and_format_result(tool_name, user_message)
                
                step["end_time"] = datetime.now().isoformat()
                step["result"] = tool_result is not None
                step["output"] = tool_result
                
                tool_steps.append(step)
                
                if tool_result:
                    enhanced_response += "\n\n" + tool_result
            
            return {
                "response": enhanced_response,
                "tool_steps": tool_steps
            }
        
        except Exception as e:
            logger.error(f"工具增强失败: {e}")
            return {
                "response": llm_response,
                "tool_steps": tool_steps
            }
        
        # 如果工具调用失败，返回原始响应
        return {
            "response": llm_response,
            "tool_steps": tool_steps
        }
    
    def _execute_tool_and_format_result(self, tool_name: str, user_message: str) -> Optional[str]:
        """
        执行工具并格式化结果
        
        Args:
            tool_name: 工具名称
            user_message: 用户消息
            
        Returns:
            格式化后的工具执行结果，如果执行失败则返回None
        """
        if tool_name == "web_search":
            # 提取搜索查询
            query = user_message
            result = self.execute_tool("web_search", query=query)
            
            if result.get("success"):
                search_answer = result.get("answer", "")
                return (
                    f"📡 **联网搜索补充信息**:\n{search_answer}\n\n"
                    f"💡 *以上信息来自实时网络搜索，可能包含最新资讯*"
                )
        
        elif tool_name == "crawl_wiki":
            # 提取主题
            topic = self._extract_topic(user_message)
            result = self.execute_tool("crawl_wiki", topic=topic, max_pages=3)
            
            if result.get("success"):
                summary = result.get("summary", "")
                return (
                    f"📚 **百科资料补充**:\n{summary}\n\n"
                    f"💡 *以上信息来自崩坏3官方百科*"
                )
        
        elif tool_name == "query_knowledge":
            result = self.execute_tool("query_knowledge", question=user_message)
            
            if result.get("success"):
                knowledge_answer = result.get("answer", "")
                
                # 如果知识库有信息，优先使用
                if "未在本地知识库中找到" not in knowledge_answer:
                    return (
                        f"{knowledge_answer}\n\n"
                        f"💡 *以上信息来自本地知识库*"
                    )
        
        elif tool_name == "list_yolo_models":
            result = self.execute_tool("list_yolo_models")
            if result.get("success"):
                names = [m["name"] for m in result.get("available_models", [])]
                loaded = [m["name"] for m in result.get("loaded_models", [])]
                return (
                    f"🧠 **YOLO模型状态**:\n"
                    f"- 可用模型: {', '.join(names) if names else '无'}\n"
                    f"- 已加载模型: {', '.join(loaded) if loaded else '无'}"
                )
        
        elif tool_name == "tts_qwen3":
            import re
            text_match = re.search(r'说[“"\'](.*?)[“"\']', user_message)
            if text_match:
                text = text_match.group(1)
                result = self.execute_tool("tts_qwen3", text=text)
                if result.get("success"):
                    return (
                        f"🎤 **Qwen3-TTS 语音生成成功**:\n"
                        f"- 引擎: {result.get('engine')}\n"
                        f"- 文本: {result.get('text')}\n"
                        f"- 声音风格: {result.get('voice_style')}\n"
                        f"- 采样率: {result.get('sample_rate')} Hz\n"
                        f"- 保存路径: {result.get('filepath')}"
                    )

        elif tool_name == "asr_transcribe":
            # 提取音频路径
            import re
            path_match = re.search(r'识别(.*?)文件', user_message)
            if path_match:
                audio_path = path_match.group(1).strip()
                result = self.execute_tool("asr_transcribe", audio_path=audio_path)
                if result.get("success"):
                    return (
                        f"🎧 **语音识别结果**:\n"
                        f"- 识别文本: {result.get('text')}\n"
                        f"- 置信度: {result.get('confidence', 0.0):.2f}\n"
                        f"- 语言: {result.get('language')}\n"
                        f"- 处理时间: {result.get('processing_time', 0.0):.2f}秒"
                    )
        
        elif tool_name == "cv_analyze_image":
            # 提取图像路径
            import re
            path_match = re.search(r'分析(.*?)[图片|截图|图像]', user_message)
            if path_match:
                image_path = path_match.group(1).strip()
                result = self.execute_tool("cv_analyze_image", image_path=image_path)
                if result.get("success"):
                    detections = result.get('detections', [])
                    detection_text = []
                    for det in detections:
                        detection_text.append(f"- {det.get('class')}: 置信度 {det.get('confidence', 0.0):.2f}")
                    return (
                        f"🖼️ **图像分析结果**:\n"
                        f"- 使用模型: {result.get('model')}\n"
                        f"- 检测结果:\n{chr(10).join(detection_text) if detection_text else '未检测到任何目标'}"
                    )
        
        elif tool_name == "run_powershell":
            # 提取命令
            import re
            cmd_match = re.search(r'执行(.*?)$', user_message)
            if cmd_match:
                command = cmd_match.group(1).strip()
                result = self.execute_tool("run_powershell", command=command)
                if result.get("success"):
                    stdout = result.get('stdout', '')
                    stderr = result.get('stderr', '')
                    return (
                        f"💻 **PowerShell命令执行结果**:\n"
                        f"- 命令: {result.get('command')}\n"
                        f"- 返回码: {result.get('returncode')}\n"
                        f"- 输出:\n{stdout if stdout else '无输出'}\n"
                        f"- 错误:\n{stderr if stderr else '无错误'}"
                    )
        
        elif tool_name == "press_key":
            # 提取按键
            import re
            key_match = re.search(r'按(?:下?)?(?:键?)?([a-zA-Z0-9]+)', user_message)
            duration_match = re.search(r'持续|保持|按住|按住|按([0-9.]+)', user_message)
            
            key = "a"
            duration = 0.1
            if key_match:
                key = key_match.group(1).strip()
            if duration_match:
                try:
                    duration = float(duration_match.group(1).strip())
                except:
                    pass
            
            result = self.execute_tool("press_key", key=key, duration=duration)
            if result.get("success"):
                return (
                    f"⌨️ **按键操作成功**:\n"
                    f"- 按键: {result.get('key')}\n"
                    f"- 操作: {result.get('action')}\n"
                    f"- 持续时间: {result.get('duration', 0):.3f}秒\n"
                    f"- 时间: {result.get('timestamp', '')}"
                )
            else:
                return (
                    f"⌨️ **按键操作失败**:\n"
                    f"- 错误: {result.get('error', '未知错误')}"
                )
        
        elif tool_name == "type_text":
            # 提取文本
            import re
            text_match = re.search(r'输入[“"\'](.*?)[“"\']', user_message) or re.search(r'打字[“"\'](.*?)[“"\']', user_message)
            if text_match:
                text = text_match.group(1).strip()
                result = self.execute_tool("type_text", text=text)
                if result.get("success"):
                    return (
                        f"⌨️ **文本输入成功**:\n"
                        f"- 输入文本: {result.get('text')}\n"
                        f"- 总字符数: {result.get('total_chars', 0)}\n"
                        f"- 成功输入: {result.get('success_count', 0)}\n"
                        f"- 耗时: {result.get('total_time', 0):.3f}秒\n"
                        f"- 时间: {result.get('timestamp', '')}"
                    )
        
        elif tool_name == "press_hotkey":
            # 提取热键
            import re
            hotkey_match = re.search(r'(?:按|按下|按热键|按组合键|按快捷键)\s*[“"\']?([a-zA-Z0-9+\s]+)[“"\']?', user_message)
            if hotkey_match:
                keys = hotkey_match.group(1).strip()
                result = self.execute_tool("press_hotkey", keys=keys)
                if result.get("success"):
                    return (
                        f"⌨️ **热键操作成功**:\n"
                        f"- 热键: {result.get('keys')}\n"
                        f"- 操作: {result.get('action')}\n"
                        f"- 耗时: {result.get('duration', 0):.3f}秒\n"
                        f"- 时间: {result.get('timestamp', '')}"
                    )
                else:
                    return (
                        f"⌨️ **热键操作失败**:\n"
                        f"- 错误: {result.get('error', '未知错误')}"
                    )
        
        elif tool_name == "list_keys":
            result = self.execute_tool("list_keys")
            if result.get("success"):
                categories = result.get("categories", {})
                output = "⌨️ **可用按键列表**:\n"
                for category, keys in categories.items():
                    if len(keys) > 10:
                        output += f"- {category}: {', '.join(keys[:10])} ... (共{len(keys)}个按键)\n"
                    else:
                        output += f"- {category}: {', '.join(keys)}\n"
                return output
        
        return None
    
    def _extract_topic(self, message: str) -> str:
        """从消息中提取主题"""
        # 简单实现：返回消息本身或前20个字符
        if len(message) > 50:
            return message[:50]
        return message
    
    @classmethod
    def test_integration(cls):
        """测试工具集成"""
        print("LLM工具集成测试")
        print("=" * 60)
        
        integration = cls()
        
        # 测试可用工具
        print("\n1. 可用工具列表:")
        tools = integration.get_available_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")
        
        # 测试工具建议
        print("\n2. 工具建议测试:")
        test_messages = [
            "崩坏3最新版本更新了什么内容？",
            "薪炎之律者的技能介绍",
            "琪亚娜·卡斯兰娜的背景故事是什么？",
            "今天的天气怎么样？"
        ]
        
        for msg in test_messages:
            tool = integration.should_use_tool(msg)
            print(f"  '{msg[:30]}...' -> 建议工具: {tool}")
        
        # 测试工具执行
        print("\n3. 工具执行测试:")
        
        # 测试联网搜索（模拟）
        print("\n  测试联网搜索:")
        result = integration.search_web("崩坏3薪炎之律者", "最新版本")
        print(f"    成功: {result.get('success')}")
        if result.get('answer'):
            print(f"    答案: {result.get('answer')[:100]}...")
        
        # 测试知识库查询
        print("\n  测试知识库查询:")
        result = integration.query_knowledge_base("琪亚娜是谁？")
        print(f"    成功: {result.get('success')}")
        if result.get('answer'):
            print(f"    答案: {result.get('answer')}")
        
        print("\n" + "=" * 60)
        print("工具集成测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    LLMToolIntegration.test_integration()