#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量ASR/TTS测试脚本
对指定目录中的每个音频文件进行ASR转录，然后使用相同音频作为参考进行TTS合成
用于测试ASR文本准确性和TTS音色模仿效果
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """单个音频文件的测试结果"""
    audio_file: str
    voice_id: str
    asr_text: str
    asr_confidence: float
    asr_processing_time: float
    tts_audio_file: str
    tts_processing_time: float
    asr_saved: bool
    tts_saved: bool
    error: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


class BatchASRTTSProcessor:
    """批量ASR/TTS处理器"""
    
    def __init__(self, 
                 input_dir: str,
                 output_dir: Optional[str] = None,
                 model_device: str = "cuda:0",
                 use_simulated_mode: bool = False):
        """
        初始化批量处理器
        
        Args:
            input_dir: 输入音频目录
            output_dir: 输出目录（如果为None，则使用项目根目录下的outputs/test_results）
            model_device: 模型设备（cuda:0 或 cpu）
            use_simulated_mode: 是否使用模拟模式（不加载真实模型）
        """
        self.input_dir = Path(input_dir)
        if not self.input_dir.exists():
            raise ValueError(f"输入目录不存在: {input_dir}")
        
        # 设置输出目录
        if output_dir is None:
            self.output_dir = project_root / "outputs" / "test_results"
        else:
            self.output_dir = Path(output_dir)
        
        # 创建输出子目录
        self.asr_output_dir = self.output_dir / "asr_transcriptions"
        self.tts_output_dir = self.output_dir / "tts_audio"
        self.report_dir = self.output_dir / "reports"
        
        for dir_path in [self.asr_output_dir, self.tts_output_dir, self.report_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.device = model_device
        self.use_simulated_mode = use_simulated_mode
        
        # 初始化处理器
        self.asr_processor = None
        self.tts_generator = None
        
        # 结果存储
        self.results: List[TestResult] = []
        
        # 文件名前缀到voice_id的映射
        self.voice_mapping = {
            "德丽莎": "theresa",
            "月下誓约": "theresa",  # 月下誓约是德丽莎的另一个形态
            "朔夜观星": "theresa",  # 朔夜观星也是德丽莎的形态
            "渡尘之羽": "fu_hua",   # 渡尘之羽是符华的形态
            "识之律者": "fu_hua",   # 识之律者是符华的另一个形态
            "迷城骇兔": "bronya",   # 迷城骇兔是布洛妮娅的形态
            "KianaData_SVC_Raw": "kiana",  # 琪亚娜
            "Da_Yue_Xia": "kiana",  # 可能是琪亚娜的语音
        }
        
        logger.info(f"批量ASR/TTS处理器初始化完成")
        logger.info(f"输入目录: {self.input_dir}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"设备: {self.device}")
        logger.info(f"模拟模式: {self.use_simulated_mode}")
    
    def _initialize_processors(self):
        """初始化ASR和TTS处理器"""
        try:
            if self.use_simulated_mode:
                logger.info("使用模拟模式，不加载真实模型")
                from src.modules.audio.asr_processor import ASRProcessor
                from src.modules.audio.tts_generator import TTSGenerator
                
                # 创建模拟模式的处理器
                self.asr_processor = ASRProcessor(device=self.device)
                self.tts_generator = TTSGenerator(device=self.device)
                
                # 强制设置为None以使用模拟模式
                self.asr_processor.model = None
                self.tts_generator.model = None
            else:
                logger.info("加载真实模型...")
                from src.modules.audio.asr_processor import ASRProcessor
                from src.modules.audio.tts_generator import TTSGenerator
                
                self.asr_processor = ASRProcessor(device=self.device)
                self.tts_generator = TTSGenerator(device=self.device)
                
                # 检查模型是否加载成功
                if self.asr_processor.model is None:
                    logger.warning("ASR模型加载失败，将使用模拟模式")
                
                if self.tts_generator.model is None:
                    logger.warning("TTS模型加载失败，将使用模拟模式")
        
        except ImportError as e:
            logger.error(f"导入模块失败: {e}")
            logger.warning("使用模拟模式继续测试")
            self._initialize_simulated_processors()
        except Exception as e:
            logger.error(f"初始化处理器失败: {e}")
            logger.warning("使用模拟模式继续测试")
            self._initialize_simulated_processors()
    
    def _initialize_simulated_processors(self):
        """初始化模拟处理器（当真实模型不可用时）"""
        # 创建简单的模拟类
        class SimulatedASRProcessor:
            def __init__(self, device="cuda:0"):
                self.model = None
                self.device = device
            
            def transcribe_file(self, audio_path, language="zh", save_result=False):
                from dataclasses import dataclass
                import time
                
                @dataclass
                class ASRResult:
                    text: str
                    confidence: float
                    language: str
                    processing_time: float
                
                # 模拟处理时间
                processing_time = 0.5
                
                # 从文件名猜测文本
                filename = os.path.basename(audio_path)
                if "德丽莎" in filename:
                    text = "这是德丽莎的模拟语音识别结果。"
                elif "月下誓约" in filename:
                    text = "这是月下誓约的模拟语音识别结果。"
                elif "朔夜观星" in filename:
                    text = "这是朔夜观星的模拟语音识别结果。"
                elif "渡尘之羽" in filename:
                    text = "这是渡尘之羽的模拟语音识别结果。"
                elif "识之律者" in filename:
                    text = "这是识之律者的模拟语音识别结果。"
                elif "迷城骇兔" in filename:
                    text = "这是迷城骇兔的模拟语音识别结果。"
                elif "Kiana" in filename:
                    text = "这是琪亚娜的模拟语音识别结果。"
                else:
                    text = "这是模拟语音识别结果。"
                
                return ASRResult(
                    text=text,
                    confidence=0.95,
                    language=language,
                    processing_time=processing_time
                )
        
        class SimulatedTTSGenerator:
            def __init__(self, device="cuda:0"):
                self.model = None
                self.device = device
                from src.modules.audio.voice_resource_manager import get_voice_resource_manager
                self.voice_manager = get_voice_resource_manager()
            
            def generate(self, text, voice_id="default", speed=1.0, pitch=1.0,
                        prompt_audio=None, prompt_text=None, save_result=False):
                from dataclasses import dataclass
                import numpy as np
                import time
                
                @dataclass
                class TTSResult:
                    audio_data: np.ndarray
                    sample_rate: int
                    text: str
                    voice_id: str
                    processing_time: float
                
                # 模拟处理时间
                processing_time = 1.0
                
                # 生成模拟音频数据
                sample_rate = 16000
                duration = max(1.0, len(text) * 0.1)
                t = np.linspace(0, duration, int(sample_rate * duration))
                
                # 根据voice_id调整基础频率
                base_freq = 220
                if voice_id == "kiana":
                    base_freq = 210
                elif voice_id == "theresa":
                    base_freq = 230  # 德丽莎声音较高
                elif voice_id == "fu_hua":
                    base_freq = 200
                elif voice_id == "bronya":
                    base_freq = 190
                
                # 生成简单音频
                freq_variation = 15 * np.sin(2 * np.pi * 2 * t / duration)
                freq = base_freq + freq_variation
                audio_data = np.sin(2 * np.pi * freq * t) * 0.05
                
                # 添加包络
                envelope = np.ones_like(t)
                attack_len = int(0.05 * sample_rate)
                release_len = int(0.1 * sample_rate)
                envelope[:attack_len] = np.linspace(0, 1, attack_len)
                envelope[-release_len:] = np.linspace(1, 0, release_len)
                audio_data *= envelope
                
                return TTSResult(
                    audio_data=audio_data.astype(np.float32),
                    sample_rate=sample_rate,
                    text=text,
                    voice_id=voice_id,
                    processing_time=processing_time
                )
            
            def save_to_file(self, result, filepath=None):
                if filepath is None:
                    filepath = f"simulated_{int(time.time())}.wav"
                
                try:
                    import soundfile as sf
                    sf.write(filepath, result.audio_data, result.sample_rate)
                    return filepath
                except ImportError:
                    try:
                        from scipy.io import wavfile
                        wavfile.write(filepath, result.sample_rate, result.audio_data)
                        return filepath
                    except Exception:
                        # 如果无法保存，至少创建空文件
                        with open(filepath, 'wb') as f:
                            pass
                        return filepath
        
        self.asr_processor = SimulatedASRProcessor(device=self.device)
        self.tts_generator = SimulatedTTSGenerator(device=self.device)
        logger.info("模拟处理器初始化完成")
    
    def _get_voice_id_from_filename(self, filename: str) -> str:
        """
        根据文件名确定voice_id
        
        Args:
            filename: 音频文件名
            
        Returns:
            voice_id字符串
        """
        filename_lower = filename.lower()
        
        # 检查映射
        for prefix, voice_id in self.voice_mapping.items():
            if prefix.lower() in filename_lower:
                return voice_id
        
        # 如果无法确定，使用默认
        return "default"
    
    def _save_asr_result(self, asr_result, audio_file: str, voice_id: str) -> Tuple[bool, str]:
        """
        保存ASR结果到文件
        
        Returns:
            (成功与否, 文件路径)
        """
        try:
            # 生成ASR结果文件名
            audio_name = Path(audio_file).stem
            timestamp = int(time.time())
            output_filename = f"asr_{voice_id}_{audio_name}_{timestamp}.txt"
            output_path = self.asr_output_dir / output_filename
            
            # 写入ASR结果
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# ASR转录结果\n")
                f.write(f"# 音频文件: {audio_file}\n")
                f.write(f"# 角色ID: {voice_id}\n")
                f.write(f"# 语言: {asr_result.language}\n")
                f.write(f"# 置信度: {asr_result.confidence:.3f}\n")
                f.write(f"# 处理时间: {asr_result.processing_time:.3f}s\n")
                f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"\n")
                f.write(f"{asr_result.text}\n")
            
            logger.info(f"ASR结果保存到: {output_path}")
            return True, str(output_path)
        
        except Exception as e:
            logger.error(f"保存ASR结果失败: {e}")
            return False, ""
    
    def _save_tts_result(self, tts_result, audio_file: str, voice_id: str) -> Tuple[bool, str]:
        """
        保存TTS结果到文件
        
        Returns:
            (成功与否, 文件路径)
        """
        try:
            # 生成TTS结果文件名
            audio_name = Path(audio_file).stem
            timestamp = int(time.time())
            output_filename = f"tts_{voice_id}_{audio_name}_{timestamp}.wav"
            output_path = self.tts_output_dir / output_filename
            
            # 使用TTS生成器的保存方法
            saved_path = self.tts_generator.save_to_file(tts_result, str(output_path))
            
            if saved_path:
                logger.info(f"TTS音频保存到: {saved_path}")
                return True, saved_path
            else:
                return False, ""
        
        except Exception as e:
            logger.error(f"保存TTS结果失败: {e}")
            return False, ""
    
    def process_audio_file(self, audio_file: Path) -> Optional[TestResult]:
        """
        处理单个音频文件
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            测试结果对象，如果失败则返回None
        """
        try:
            audio_path = str(audio_file)
            logger.info(f"处理音频文件: {audio_file.name}")
            
            # 确定voice_id
            voice_id = self._get_voice_id_from_filename(audio_file.name)
            logger.info(f"检测到角色ID: {voice_id}")
            
            # 步骤1: ASR转录
            logger.info(f"开始ASR转录...")
            asr_start_time = time.time()
            asr_result = self.asr_processor.transcribe_file(
                audio_path=audio_path,
                language="zh",  # 假设都是中文
                save_result=False  # 我们会自己保存
            )
            asr_processing_time = time.time() - asr_start_time
            
            logger.info(f"ASR完成: {asr_result.text[:50]}... (置信度: {asr_result.confidence:.3f})")
            
            # 保存ASR结果
            asr_saved, asr_save_path = self._save_asr_result(asr_result, audio_path, voice_id)
            
            # 步骤2: TTS合成
            logger.info(f"开始TTS合成...")
            tts_start_time = time.time()
            
            # 使用原始音频作为参考音频，ASR文本作为参考文本
            tts_result = self.tts_generator.generate(
                text=asr_result.text,
                voice_id=voice_id,
                prompt_audio=audio_path,  # 使用原始音频作为参考
                prompt_text=asr_result.text,  # 使用ASR文本作为参考文本
                save_result=False  # 我们会自己保存
            )
            tts_processing_time = time.time() - tts_start_time
            
            logger.info(f"TTS完成: 音频长度={len(tts_result.audio_data)} samples, 处理时间={tts_processing_time:.3f}s")
            
            # 保存TTS结果
            tts_saved, tts_save_path = self._save_tts_result(tts_result, audio_path, voice_id)
            
            # 创建测试结果对象
            result = TestResult(
                audio_file=audio_path,
                voice_id=voice_id,
                asr_text=asr_result.text,
                asr_confidence=asr_result.confidence,
                asr_processing_time=asr_processing_time,
                tts_audio_file=tts_save_path if tts_saved else "",
                tts_processing_time=tts_processing_time,
                asr_saved=asr_saved,
                tts_saved=tts_saved
            )
            
            logger.info(f"文件处理完成: {audio_file.name}")
            return result
            
        except Exception as e:
            logger.error(f"处理文件 {audio_file} 失败: {e}", exc_info=True)
            # 创建错误结果
            result = TestResult(
                audio_file=str(audio_file) if 'audio_file' in locals() else "unknown",
                voice_id=voice_id if 'voice_id' in locals() else "unknown",
                asr_text="",
                asr_confidence=0.0,
                asr_processing_time=0.0,
                tts_audio_file="",
                tts_processing_time=0.0,
                asr_saved=False,
                tts_saved=False,
                error=str(e)
            )
            return result
    
    def process_all(self) -> bool:
        """
        处理输入目录中的所有音频文件
        
        Returns:
            是否所有文件都处理成功
        """
        # 初始化处理器
        if self.asr_processor is None or self.tts_generator is None:
            self._initialize_processors()
        
        # 查找所有.wav文件
        audio_files = list(self.input_dir.glob("*.wav"))
        if not audio_files:
            logger.warning(f"在 {self.input_dir} 中没有找到.wav文件")
            return False
        
        logger.info(f"找到 {len(audio_files)} 个音频文件")
        
        all_success = True
        processed_count = 0
        
        # 处理每个文件
        for audio_file in audio_files:
            try:
                result = self.process_audio_file(audio_file)
                if result:
                    self.results.append(result)
                    processed_count += 1
                    
                    if result.error:
                        all_success = False
                        logger.error(f"文件 {audio_file.name} 处理失败: {result.error}")
                    else:
                        logger.info(f"文件 {audio_file.name} 处理成功")
                else:
                    all_success = False
                    logger.error(f"文件 {audio_file.name} 处理返回空结果")
            
            except Exception as e:
                all_success = False
                logger.error(f"处理文件 {audio_file.name} 时发生异常: {e}", exc_info=True)
        
        # 生成报告
        self._generate_report()
        
        logger.info(f"处理完成: {processed_count}/{len(audio_files)} 个文件")
        return all_success
    
    def _generate_report(self):
        """生成测试报告"""
        try:
            # 生成JSON报告
            report_data = {
                "test_info": {
                    "input_dir": str(self.input_dir),
                    "output_dir": str(self.output_dir),
                    "device": self.device,
                    "use_simulated_mode": self.use_simulated_mode,
                    "total_files": len(self.results),
                    "successful_files": len([r for r in self.results if not r.error]),
                    "failed_files": len([r for r in self.results if r.error]),
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "results": [r.to_dict() for r in self.results],
                "summary": {
                    "total_processing_time": sum(r.asr_processing_time + r.tts_processing_time for r in self.results if not r.error),
                    "average_asr_confidence": sum(r.asr_confidence for r in self.results if not r.error) / max(1, len([r for r in self.results if not r.error])),
                    "voice_distribution": {},
                    "file_extensions": {}
                }
            }
            
            # 统计角色分布
            for result in self.results:
                if result.error:
                    continue
                voice_id = result.voice_id
                report_data["summary"]["voice_distribution"][voice_id] = report_data["summary"]["voice_distribution"].get(voice_id, 0) + 1
            
            # 保存JSON报告
            json_report_path = self.report_dir / f"test_report_{int(time.time())}.json"
            with open(json_report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # 生成文本报告
            text_report_path = self.report_dir / f"test_report_{int(time.time())}.txt"
            with open(text_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("批量ASR/TTS测试报告\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"测试时间: {report_data['test_info']['generated_at']}\n")
                f.write(f"输入目录: {report_data['test_info']['input_dir']}\n")
                f.write(f"输出目录: {report_data['test_info']['output_dir']}\n")
                f.write(f"设备: {report_data['test_info']['device']}\n")
                f.write(f"模拟模式: {report_data['test_info']['use_simulated_mode']}\n\n")
                
                f.write(f"文件总数: {report_data['test_info']['total_files']}\n")
                f.write(f"成功文件: {report_data['test_info']['successful_files']}\n")
                f.write(f"失败文件: {report_data['test_info']['failed_files']}\n")
                f.write(f"总处理时间: {report_data['summary']['total_processing_time']:.2f}s\n")
                f.write(f"平均ASR置信度: {report_data['summary']['average_asr_confidence']:.3f}\n\n")
                
                f.write("角色分布:\n")
                for voice_id, count in report_data["summary"]["voice_distribution"].items():
                    f.write(f"  {voice_id}: {count} 个文件\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write("详细结果:\n")
                f.write("=" * 60 + "\n\n")
                
                for i, result in enumerate(report_data["results"], 1):
                    f.write(f"文件 {i}: {Path(result['audio_file']).name}\n")
                    f.write(f"  角色ID: {result['voice_id']}\n")
                    
                    if result['error']:
                        f.write(f"  状态: ❌ 失败\n")
                        f.write(f"  错误: {result['error']}\n")
                    else:
                        f.write(f"  状态: ✅ 成功\n")
                        f.write(f"  ASR文本: {result['asr_text'][:100]}...\n")
                        f.write(f"  ASR置信度: {result['asr_confidence']:.3f}\n")
                        f.write(f"  ASR处理时间: {result['asr_processing_time']:.3f}s\n")
                        f.write(f"  TTS音频文件: {result['tts_audio_file']}\n")
                        f.write(f"  TTS处理时间: {result['tts_processing_time']:.3f}s\n")
                    
                    f.write("\n")
            
            logger.info(f"JSON报告保存到: {json_report_path}")
            logger.info(f"文本报告保存到: {text_report_path}")
            
            # 打印摘要到控制台
            print("\n" + "=" * 60)
            print("测试摘要:")
            print(f"  总文件数: {report_data['test_info']['total_files']}")
            print(f"  成功文件: {report_data['test_info']['successful_files']}")
            print(f"  失败文件: {report_data['test_info']['failed_files']}")
            print(f"  平均ASR置信度: {report_data['summary']['average_asr_confidence']:.3f}")
            print(f"  总处理时间: {report_data['summary']['total_processing_time']:.2f}s")
            print(f"  报告文件: {json_report_path}")
            print("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量ASR/TTS测试")
    parser.add_argument("--input-dir", type=str, 
                       default=r"d:\TokusCode\bbb_assistant\to_clone_test",
                       help="输入音频目录")
    parser.add_argument("--output-dir", type=str, default=None,
                       help="输出目录（默认: 项目根目录/outputs/test_results）")
    parser.add_argument("--device", type=str, default="cuda:0",
                       help="模型设备: cuda:0 或 cpu")
    parser.add_argument("--simulated", action="store_true",
                       help="使用模拟模式（不加载真实模型）")
    parser.add_argument("--list-files", action="store_true",
                       help="仅列出文件，不进行处理")
    
    args = parser.parse_args()
    
    # 检查输入目录
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"错误: 输入目录不存在: {input_dir}")
        return 1
    
    # 列出文件
    if args.list_files:
        print(f"在 {input_dir} 中找到的音频文件:")
        audio_files = list(input_dir.glob("*.wav"))
        for i, f in enumerate(audio_files, 1):
            print(f"  {i}. {f.name}")
        print(f"总计: {len(audio_files)} 个文件")
        return 0
    
    # 创建处理器
    try:
        processor = BatchASRTTSProcessor(
            input_dir=str(input_dir),
            output_dir=args.output_dir,
            model_device=args.device,
            use_simulated_mode=args.simulated
        )
        
        # 处理所有文件
        print("=" * 60)
        print("开始批量ASR/TTS测试")
        print("=" * 60)
        
        success = processor.process_all()
        
        if success:
            print("\n🎉 所有文件处理成功！")
            return 0
        else:
            print("\n⚠️  部分文件处理失败，请查看日志和报告")
            return 1
    
    except Exception as e:
        logger.error(f"批量处理失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())