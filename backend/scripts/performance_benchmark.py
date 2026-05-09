#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程性能测速脚本
流程：任意文本 -> TTS -> ASR -> LLM -> TTS

功能：
1. 测量每个环节的处理时间
2. 统计资源使用情况
3. 生成性能报告
4. 支持多次运行取平均值
"""

import sys
import os
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import argparse
import tempfile

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, device: str = "auto", voice_id: str = "elysia", 
                 simulated: bool = False):
        """
        初始化性能测试
        
        Args:
            device: 计算设备 (auto/cpu/cuda/cuda:0)。auto表示自动检测最佳设备
            voice_id: TTS使用的角色ID
            simulated: 是否使用模拟模式
        """
        # 自动检测最佳设备
        if device == "auto":
            self.device = self._get_best_device()
        else:
            self.device = device
            
        self.voice_id = voice_id
        self.simulated = simulated
        self.results = []
        
        # 检查模型文件是否存在
        self.has_models = self._check_models()
        
        # 初始化处理器（延迟加载）
        self.tts_generator = None
        self.asr_processor = None
        self.llm_router = None
        
    def _check_models(self) -> bool:
        """检查模型文件是否存在"""
        sensevoice_path = project_root.parent / "SenseVoiceSmall"
        voxcpm_path = project_root.parent / "VoxCPM-0.5B"
        
        has_models = sensevoice_path.exists() and voxcpm_path.exists()
        
        if not has_models:
            logger.warning("未检测到完整的ASR/TTS模型文件，将使用模拟模式")
            logger.info(f"SenseVoiceSmall存在: {sensevoice_path.exists()}")
            logger.info(f"VoxCPM-0.5B存在: {voxcpm_path.exists()}")
        
        return has_models
    
    def _get_best_device(self) -> str:
        """自动检测最佳计算设备"""
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                # 检查每个GPU的可用内存
                best_device = "cuda:0"
                for i in range(device_count):
                    props = torch.cuda.get_device_properties(i)
                    memory_gb = props.total_memory / 1e9
                    logger.info(f"GPU {i}: {props.name}, 显存: {memory_gb:.2f} GB")
                logger.info(f"选择设备: {best_device}")
                return best_device
            else:
                logger.info("未检测到GPU，使用CPU")
                return "cpu"
        except Exception as e:
            logger.warning(f"设备检测失败: {e}, 使用CPU")
            return "cpu"
    
    def _init_tts(self):
        """初始化TTS生成器（使用模型单例管理器）"""
        if self.tts_generator is not None:
            return
            
        try:
            # 使用模型单例管理器获取TTS模型
            from src.utils.model_manager import get_tts_model
            self.tts_generator = get_tts_model(device=self.device)
            
            if self.simulated or not self.has_models:
                logger.info("使用TTS生成器（模拟模式）")
            else:
                logger.info(f"使用TTS生成器 (设备: {self.device})，通过模型单例管理器")
                
                # 模型预热：运行一个小的推理，让模型加载到GPU并预热
                try:
                    logger.info("开始TTS模型预热...")
                    warmup_result = self.tts_generator.generate(
                        text="预热测试",
                        voice_id=self.voice_id,
                        speed=1.0,
                        pitch=1.0
                    )
                    logger.info(f"TTS模型预热完成，生成音频长度: {len(warmup_result.audio_data) if hasattr(warmup_result, 'audio_data') else 0}")
                except Exception as warmup_error:
                    logger.warning(f"TTS模型预热失败（不影响正常使用）: {warmup_error}")
                
        except Exception as e:
            logger.error(f"初始化TTS生成器失败: {e}")
            # 如果导入失败，创建基本模拟类
            self.tts_generator = self._create_mock_tts()
            logger.info("使用模拟TTS生成器（备用）")
    
    def _init_asr(self):
        """初始化ASR处理器（使用模型单例管理器）"""
        if self.asr_processor is not None:
            return
            
        try:
            # 使用模型单例管理器获取ASR模型
            from src.utils.model_manager import get_asr_model
            self.asr_processor = get_asr_model(device=self.device)
            
            if self.simulated or not self.has_models:
                logger.info("使用ASR处理器（模拟模式）")
            else:
                logger.info(f"使用ASR处理器 (设备: {self.device})，通过模型单例管理器")
                
                # 模型预热：运行一个小的推理，让模型加载到GPU并预热
                try:
                    logger.info("开始ASR模型预热...")
                    import numpy as np
                    # 创建一个短的测试音频（0.5秒静音）
                    warmup_audio = np.zeros(8000, dtype=np.float32)  # 16kHz * 0.5秒
                    warmup_result = self.asr_processor.transcribe(
                        audio_data=warmup_audio,
                        sample_rate=16000,
                        language="zh"
                    )
                    logger.info(f"ASR模型预热完成，转录文本: {warmup_result.text[:50]}...")
                except Exception as warmup_error:
                    logger.warning(f"ASR模型预热失败（不影响正常使用）: {warmup_error}")
                
        except Exception as e:
            logger.error(f"初始化ASR处理器失败: {e}")
            # 如果导入失败，创建基本模拟类
            self.asr_processor = self._create_mock_asr()
            logger.info("使用模拟ASR处理器（备用）")
    
    def _init_llm(self):
        """初始化LLM路由器"""
        if self.llm_router is not None:
            return
            
        try:
            from src.modules.llm.llm_router import get_llm_router, TaskType
            self.llm_router = get_llm_router()
            self.task_type = TaskType.GAME_GUIDE
            logger.info("LLM路由器初始化成功")
        except Exception as e:
            logger.error(f"初始化LLM路由器失败: {e}")
            # 创建模拟LLM
            self.llm_router = self._create_mock_llm()
            logger.info("使用模拟LLM路由器")
    

    
    def _create_mock_llm(self):
        """创建模拟LLM路由器"""
        class MockLLMRouter:
            def route_request(self, messages, task_type, temperature=0.7, max_tokens=300):
                user_message = messages[-1]["content"] if messages else "你好"
                return {
                    "content": f"这是模拟LLM对'{user_message[:20]}...'的回复。在真实环境中，这里会是LLM生成的游戏攻略或对话回复。",
                    "model_info": {"name": "mock-llm", "provider": "simulated"}
                }
        return MockLLMRouter()
    
    def _create_mock_tts(self):
        """创建模拟TTS生成器（备用）"""
        import numpy as np
        
        class MockTTSGenerator:
            def __init__(self, device="cpu"):
                self.device = device
            
            def generate(self, text, voice_id, speed=1.0, pitch=1.0):
                class MockTTSResult:
                    def __init__(self, text):
                        self.audio_data = np.random.randn(16000)  # 1秒音频
                        self.sample_rate = 16000
                        self.voice_id = voice_id
                return MockTTSResult(text)
        
        return MockTTSGenerator(device=self.device)
    
    def _create_mock_asr(self):
        """创建模拟ASR处理器（备用）"""
        import numpy as np
        
        class MockASRProcessor:
            def __init__(self, device="cpu"):
                self.device = device
            
            def transcribe(self, audio_data, sample_rate, language="zh"):
                class MockASRResult:
                    def __init__(self):
                        self.text = "这是模拟ASR转录结果。原始音频长度: {} samples。".format(len(audio_data))
                        self.confidence = 0.95
                        self.language = language
                        self.processing_time = 0.5
                return MockASRResult()
        
        return MockASRProcessor(device=self.device)
    
    def run_tts(self, text: str) -> Tuple[Optional[bytes], Optional[int], float]:
        """
        运行TTS生成音频
        
        Returns:
            (audio_data, sample_rate, processing_time)
        """
        start_time = time.time()
        
        try:
            self._init_tts()
            
            result = self.tts_generator.generate(
                text=text,
                voice_id=self.voice_id,
                speed=1.0,
                pitch=1.0
            )
            
            processing_time = time.time() - start_time
            
            if result.audio_data is None or len(result.audio_data) == 0:
                logger.error("TTS生成音频失败")
                return None, None, processing_time
            
            logger.info(f"TTS生成成功: {len(result.audio_data)} samples, 耗时: {processing_time:.3f}s")
            return result.audio_data, result.sample_rate, processing_time
            
        except Exception as e:
            logger.error(f"TTS生成失败: {e}")
            return None, None, time.time() - start_time
    
    def run_asr(self, audio_data: bytes, sample_rate: int) -> Tuple[Optional[str], float]:
        """
        运行ASR转录音频
        
        Returns:
            (transcribed_text, processing_time)
        """
        start_time = time.time()
        
        try:
            self._init_asr()
            
            result = self.asr_processor.transcribe(
                audio_data=audio_data,
                sample_rate=sample_rate,
                language="zh"
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"ASR转录成功: {len(result.text)} 字符, 耗时: {processing_time:.3f}s")
            logger.debug(f"转录文本: {result.text}")
            
            return result.text, processing_time
            
        except Exception as e:
            logger.error(f"ASR转录失败: {e}")
            return None, time.time() - start_time
    
    def run_llm(self, text: str) -> Tuple[Optional[str], float]:
        """
        运行LLM处理文本
        
        Returns:
            (llm_response, processing_time)
        """
        start_time = time.time()
        
        try:
            self._init_llm()
            
            messages = [
                {"role": "system", "content": "你是一个崩坏3游戏专家，请用中文简洁回答。"},
                {"role": "user", "content": text}
            ]
            
            response = self.llm_router.route_request(
                messages=messages,
                task_type=getattr(self, 'task_type', None),
                temperature=0.7,
                max_tokens=200
            )
            
            processing_time = time.time() - start_time
            
            # 提取响应内容
            if "error" in response:
                logger.error(f"LLM处理失败: {response['error']}")
                return None, processing_time
            
            if "content" in response:
                llm_response = response["content"]
            elif isinstance(response, dict) and "response" in response:
                llm_response = response["response"]
            else:
                logger.error(f"LLM响应格式未知: {response}")
                return None, processing_time
            
            logger.info(f"LLM处理成功: {len(llm_response)} 字符, 耗时: {processing_time:.3f}s")
            logger.debug(f"LLM响应: {llm_response[:100]}...")
            
            return llm_response, processing_time
            
        except Exception as e:
            logger.error(f"LLM处理失败: {e}")
            return None, time.time() - start_time
    
    def run_full_pipeline(self, input_text: str, run_id: int = 0) -> Dict[str, Any]:
        """
        运行完整流程：文本 -> TTS -> ASR -> LLM -> TTS
        
        Returns:
            包含每个步骤时间和结果的字典
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"运行完整流程 (Run {run_id+1})")
        logger.info(f"输入文本: {input_text}")
        logger.info(f"{'='*60}")
        
        result = {
            "run_id": run_id,
            "input_text": input_text,
            "timestamp": datetime.now().isoformat(),
            "device": self.device,
            "voice_id": self.voice_id,
            "simulated": self.simulated,
            "has_models": self.has_models
        }
        
        # 顺序初始化TTS和ASR模型（如果尚未初始化）
        init_times = {}
        if self.tts_generator is None:
            tts_start = time.time()
            self._init_tts()
            init_times["tts"] = time.time() - tts_start
        
        if self.asr_processor is None:
            asr_start = time.time()
            self._init_asr()
            init_times["asr"] = time.time() - asr_start
        
        result["model_init_times"] = init_times
        result["model_init_success"] = True
        
        # 步骤1: TTS生成音频
        logger.info("\n步骤1: TTS生成音频")
        audio_data, sample_rate, tts1_time = self.run_tts(input_text)
        result["tts1"] = {
            "success": audio_data is not None,
            "audio_length": len(audio_data) if audio_data is not None else 0,
            "sample_rate": sample_rate,
            "processing_time": tts1_time
        }
        
        if audio_data is None:
            logger.error("TTS生成失败，终止流程")
            result["overall_success"] = False
            return result
        
        # 步骤2: ASR转录音频
        logger.info("\n步骤2: ASR转录音频")
        transcribed_text, asr_time = self.run_asr(audio_data, sample_rate)
        result["asr"] = {
            "success": transcribed_text is not None,
            "text_length": len(transcribed_text) if transcribed_text else 0,
            "text": transcribed_text,
            "processing_time": asr_time
        }
        
        if transcribed_text is None:
            logger.error("ASR转录失败，终止流程")
            result["overall_success"] = False
            return result
        
        # 步骤3: LLM处理文本
        logger.info("\n步骤3: LLM处理文本")
        llm_response, llm_time = self.run_llm(transcribed_text)
        result["llm"] = {
            "success": llm_response is not None,
            "text_length": len(llm_response) if llm_response else 0,
            "text": llm_response[:200] + "..." if llm_response and len(llm_response) > 200 else llm_response,
            "processing_time": llm_time
        }
        
        if llm_response is None:
            logger.error("LLM处理失败，终止流程")
            result["overall_success"] = False
            return result
        
        # 步骤4: TTS生成回复音频
        logger.info("\n步骤4: TTS生成回复音频")
        # 限制TTS文本长度，避免过长
        tts2_text = llm_response[:150] if len(llm_response) > 150 else llm_response
        reply_audio, reply_sample_rate, tts2_time = self.run_tts(tts2_text)
        result["tts2"] = {
            "success": reply_audio is not None,
            "audio_length": len(reply_audio) if reply_audio is not None else 0,
            "sample_rate": reply_sample_rate,
            "processing_time": tts2_time
        }
        
        # 计算总时间
        total_time = tts1_time + asr_time + llm_time + tts2_time
        result["total_processing_time"] = total_time
        result["overall_success"] = all([
            result["tts1"]["success"],
            result["asr"]["success"], 
            result["llm"]["success"],
            result["tts2"]["success"]
        ])
        
        logger.info(f"\n流程完成 - 总耗时: {total_time:.3f}s")
        logger.info(f"  TTS1: {tts1_time:.3f}s")
        logger.info(f"  ASR:  {asr_time:.3f}s")
        logger.info(f"  LLM:  {llm_time:.3f}s")
        logger.info(f"  TTS2: {tts2_time:.3f}s")
        
        # 保存生成的音频文件（如果成功）
        if reply_audio is not None:
            self._save_output_audio(reply_audio, reply_sample_rate, run_id, input_text)
        
        return result
    
    def _save_output_audio(self, audio_data: bytes, sample_rate: int, 
                          run_id: int, input_text: str):
        """保存输出音频文件"""
        try:
            output_dir = project_root / "outputs" / "performance_test"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 使用输入文本的前20个字符作为文件名部分
            text_snippet = input_text[:20].replace(" ", "_").replace("/", "_")
            filename = f"output_{timestamp}_run{run_id+1}_{text_snippet}.wav"
            output_path = output_dir / filename
            
            import soundfile as sf
            sf.write(str(output_path), audio_data, sample_rate)
            
            logger.info(f"输出音频已保存: {output_path}")
        except Exception as e:
            logger.warning(f"保存输出音频失败: {e}")
    
    def run_benchmark(self, test_texts: List[str], num_runs: int = 3) -> List[Dict[str, Any]]:
        """
        运行性能基准测试
        
        Args:
            test_texts: 测试文本列表
            num_runs: 每个文本的运行次数
        
        Returns:
            所有运行结果的列表
        """
        logger.info(f"\n{'='*60}")
        logger.info("开始性能基准测试")
        logger.info(f"测试文本数量: {len(test_texts)}")
        logger.info(f"每个文本运行次数: {num_runs}")
        logger.info(f"设备: {self.device}")
        logger.info(f"模拟模式: {self.simulated}")
        logger.info(f"{'='*60}")
        
        all_results = []
        
        for text_idx, text in enumerate(test_texts):
            logger.info(f"\n测试文本 {text_idx+1}/{len(test_texts)}: {text[:50]}...")
            
            for run in range(num_runs):
                result = self.run_full_pipeline(text, run)
                all_results.append(result)
                
                # 短暂暂停，避免资源冲突
                if run < num_runs - 1:
                    time.sleep(1)
        
        # 生成性能报告
        self._generate_performance_report(all_results)
        
        return all_results
    
    def _generate_performance_report(self, results: List[Dict[str, Any]]):
        """生成性能报告"""
        if not results:
            logger.warning("没有测试结果，无法生成报告")
            return
        
        # 计算统计信息
        successful_runs = [r for r in results if r.get("overall_success", False)]
        
        if not successful_runs:
            logger.warning("没有成功的测试运行")
            return
        
        # 提取时间数据
        tts1_times = [r["tts1"]["processing_time"] for r in successful_runs]
        asr_times = [r["asr"]["processing_time"] for r in successful_runs]
        llm_times = [r["llm"]["processing_time"] for r in successful_runs]
        tts2_times = [r["tts2"]["processing_time"] for r in successful_runs]
        total_times = [r["total_processing_time"] for r in successful_runs]
        
        # 计算统计值
        stats = {
            "total_runs": len(results),
            "successful_runs": len(successful_runs),
            "success_rate": len(successful_runs) / len(results) * 100,
            "tts1": self._calculate_stats(tts1_times, "TTS生成"),
            "asr": self._calculate_stats(asr_times, "ASR转录"),
            "llm": self._calculate_stats(llm_times, "LLM处理"),
            "tts2": self._calculate_stats(tts2_times, "TTS回复"),
            "total": self._calculate_stats(total_times, "总流程")
        }
        
        # 生成报告文件
        report_dir = project_root / "outputs" / "performance_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"performance_report_{timestamp}.json"
        
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "device": self.device,
                "simulated": self.simulated,
                "has_models": self.has_models,
                "test_config": {
                    "num_texts": len(set(r["input_text"] for r in results)),
                    "total_runs": len(results)
                }
            },
            "statistics": stats,
            "raw_results": results
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("性能测试报告")
        logger.info(f"{'='*60}")
        logger.info(f"总运行次数: {stats['total_runs']}")
        logger.info(f"成功次数: {stats['successful_runs']}")
        logger.info(f"成功率: {stats['success_rate']:.1f}%")
        logger.info(f"\n各环节平均处理时间:")
        logger.info(f"  TTS生成:  {stats['tts1']['mean']:.3f}s ± {stats['tts1']['std']:.3f}s")
        logger.info(f"  ASR转录:  {stats['asr']['mean']:.3f}s ± {stats['asr']['std']:.3f}s")
        logger.info(f"  LLM处理:  {stats['llm']['mean']:.3f}s ± {stats['llm']['std']:.3f}s")
        logger.info(f"  TTS回复:  {stats['tts2']['mean']:.3f}s ± {stats['tts2']['std']:.3f}s")
        logger.info(f"  总流程:   {stats['total']['mean']:.3f}s ± {stats['total']['std']:.3f}s")
        logger.info(f"\n报告已保存: {report_path}")
        logger.info(f"{'='*60}")
    
    def _calculate_stats(self, times: List[float], name: str) -> Dict[str, Any]:
        """计算时间统计信息"""
        if not times:
            return {"mean": 0, "min": 0, "max": 0, "std": 0, "count": 0}
        
        return {
            "mean": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "std": statistics.stdev(times) if len(times) > 1 else 0,
            "count": len(times),
            "name": name
        }

def get_test_texts() -> List[str]:
    """获取测试文本列表"""
    return [
        "讲解一下薪炎之律者的攻击方式",
        "德丽莎的休伯利安战舰有什么功能",
        "崩坏3中女武神如何获得圣痕",
        "月下誓约和德丽莎是什么关系",
        "逆熵组织和天命总部有什么区别"
    ]

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="完整流程性能测速脚本")
    parser.add_argument("--device", "-d", default="auto", choices=["auto", "cpu", "cuda", "cuda:0"],
                       help="计算设备 (auto/cpu/cuda/cuda:0)。auto表示自动检测最佳设备 (默认: auto)")
    parser.add_argument("--voice", "-v", default="elysia",
                       help="TTS角色ID (默认: elysia)")
    parser.add_argument("--simulated", "-s", action="store_true",
                       help="使用模拟模式（不加载真实模型）")
    parser.add_argument("--text", "-t", 
                       help="自定义测试文本（如不指定则使用内置文本）")
    parser.add_argument("--runs", "-r", type=int, default=3,
                       help="每个文本的运行次数 (默认: 3)")
    parser.add_argument("--output", "-o",
                       help="输出报告文件路径")
    
    args = parser.parse_args()
    
    # 准备测试文本
    if args.text:
        test_texts = [args.text]
    else:
        test_texts = get_test_texts()
    
    # 运行性能测试
    benchmark = PerformanceBenchmark(
        device=args.device,
        voice_id=args.voice,
        simulated=args.simulated
    )
    
    try:
        results = benchmark.run_benchmark(test_texts, num_runs=args.runs)
        
        # 如果有指定输出路径，额外保存一份
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "config": vars(args),
                    "results": results
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"额外报告已保存: {output_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())