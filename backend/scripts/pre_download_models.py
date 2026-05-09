#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预下载所有依赖模型到项目本地目录

功能：
1. 下载zipenhancer音频增强模型到项目本地
2. 避免运行时下载耗时（10-15秒）
3. 便于版本控制和团队共享

使用方法：
  python pre_download_models.py [--force] [--cache-dir <目录>]

注意事项：
1. 首次运行需要网络连接
2. 下载后模型会缓存在指定目录
3. 后续运行无需下载
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_zipenhancer_model(cache_dir: str = None, force: bool = False):
    """
    下载zipenhancer音频增强模型
    
    Args:
        cache_dir: 缓存目录，如果为None则使用项目本地目录
        force: 是否强制重新下载
    
    Returns:
        模型本地路径
    """
    try:
        from modelscope import snapshot_download
        
        # 设置缓存目录
        if cache_dir is None:
            # 使用项目本地目录: models/zipenhancer
            cache_dir = project_root.parent / "models" / "zipenhancer"
        else:
            cache_dir = Path(cache_dir)
        
        # 确保目录存在
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始下载zipenhancer模型...")
        logger.info(f"目标目录: {cache_dir}")
        logger.info(f"模型ID: iic/speech_zipenhancer_ans_multiloss_16k_base")
        
        # 检查是否已存在
        model_files = list(cache_dir.glob("*"))
        if model_files and not force:
            logger.info(f"模型已存在，跳过下载")
            logger.info(f"现有文件: {len(model_files)} 个")
            return str(cache_dir)
        
        # 下载模型
        model_dir = snapshot_download(
            'iic/speech_zipenhancer_ans_multiloss_16k_base',
            cache_dir=str(cache_dir),
            revision='master'
        )
        
        logger.info(f"模型下载完成: {model_dir}")
        
        # 验证下载的文件
        downloaded_files = list(Path(model_dir).glob("*"))
        logger.info(f"下载文件数量: {len(downloaded_files)}")
        for f in downloaded_files[:5]:  # 显示前5个文件
            logger.debug(f"  - {f.name}")
        
        return model_dir
        
    except ImportError:
        logger.error("modelscope库未安装，请运行: pip install modelscope")
        return None
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return None

def check_voxcpm_dependencies():
    """
    检查VoxCPM相关依赖
    """
    logger.info("检查VoxCPM依赖...")
    
    # 检查voxcpm库
    try:
        import voxcpm
        # 尝试获取版本信息（部分版本可能没有__version__属性）
        try:
            version = voxcpm.__version__
            logger.info(f"voxcpm版本: {version}")
        except AttributeError:
            logger.info("voxcpm库可用（版本信息不可用）")
        
        # 尝试获取VoxCPM类
        from voxcpm import VoxCPM
        logger.info("VoxCPM库可用")
        
        # 检查模型路径
        model_path = project_root.parent / "VoxCPM-0.5B"
        if model_path.exists():
            logger.info(f"VoxCPM模型存在: {model_path}")
            model_files = list(model_path.glob("*"))
            logger.info(f"模型文件数量: {len(model_files)}")
        else:
            logger.warning(f"VoxCPM模型不存在: {model_path}")
            
        return True
    except ImportError:
        logger.warning("voxcpm库未安装，TTS将使用模拟模式")
        return False
    except Exception as e:
        logger.error(f"检查VoxCPM依赖失败: {e}")
        return False

def create_config_file(model_dir: str):
    """
    创建配置文件，指定使用本地模型
    
    Args:
        model_dir: 模型目录
    """
    config_path = project_root / "config" / "model_cache.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config_content = f"""# 模型缓存配置
# 预下载模型路径配置，避免运行时下载

model_cache:
  # VoxCPM主模型路径
  voxcpm_path: "{project_root.parent / 'VoxCPM-0.5B'}"
  
  # SenseVoice ASR模型路径  
  sensevoice_path: "{project_root.parent / 'SenseVoiceSmall'}"
  
  # ZipEnhancer音频增强模型路径
  zipenhancer_path: "{model_dir}"
  
  # 是否跳过运行时下载
  skip_download: true
  
  # 缓存策略
  cache_policy:
    max_size_gb: 10
    cleanup_interval_hours: 24
    
# 环境变量覆盖（优先级更高）
# 可以通过设置环境变量覆盖上述路径
# 例如: export MODELSCOPE_CACHE="/path/to/cache"
"""
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"配置文件已创建: {config_path}")
        
        # 同时创建.env文件示例
        env_path = project_root / ".env.example"
        env_content = f"""# 模型路径环境变量配置
# 复制为.env文件并修改

# ModelScope缓存目录
MODELSCOPE_CACHE="{project_root.parent / 'models'}"

# VoxCPM模型路径
VOXCPM_MODEL_PATH="{project_root.parent / 'VoxCPM-0.5B'}"

# SenseVoice模型路径
SENSEVOICE_MODEL_PATH="{project_root.parent / 'SenseVoiceSmall'}"

# 跳过运行时下载
SKIP_MODEL_DOWNLOAD=true

# GPU设备设置
CUDA_VISIBLE_DEVICES=0
"""
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        logger.info(f"环境变量示例文件已创建: {env_path}")
        
        return True
    except Exception as e:
        logger.error(f"创建配置文件失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="预下载依赖模型到项目本地目录")
    parser.add_argument("--force", "-f", action="store_true",
                       help="强制重新下载，即使已存在")
    parser.add_argument("--cache-dir", "-c",
                       help="自定义缓存目录（默认: models/zipenhancer）")
    parser.add_argument("--skip-config", action="store_true",
                       help="跳过配置文件创建")
    parser.add_argument("--check-only", action="store_true",
                       help="仅检查依赖，不下载")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("预下载依赖模型")
    logger.info("=" * 60)
    
    # 检查VoxCPM依赖
    voxcpm_available = check_voxcpm_dependencies()
    
    if args.check_only:
        logger.info("仅检查模式，跳过下载")
        return 0 if voxcpm_available else 1
    
    # 下载zipenhancer模型
    model_dir = download_zipenhancer_model(
        cache_dir=args.cache_dir,
        force=args.force
    )
    
    if not model_dir:
        logger.error("模型下载失败")
        return 1
    
    # 创建配置文件
    if not args.skip_config:
        create_config_file(model_dir)
    
    # 总结
    logger.info("=" * 60)
    logger.info("预下载完成！")
    logger.info("=" * 60)
    logger.info(f"模型目录: {model_dir}")
    logger.info(f"VoxCPM可用: {'是' if voxcpm_available else '否'}")
    logger.info("")
    logger.info("下一步:")
    logger.info("1. 修改TTS生成器使用本地模型路径")
    logger.info("2. 运行性能测试验证优化效果")
    logger.info("3. 考虑实现模型单例管理器")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())