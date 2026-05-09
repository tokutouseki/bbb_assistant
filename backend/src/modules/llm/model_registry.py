"""
模型注册表
管理所有可用的LLM模型配置和状态
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置"""
    model_id: str  # 唯一标识符
    model_type: str  # 模型类型：deepseek_v3_api, local_gguf, ollama等
    display_name: str  # 显示名称
    description: str = ""  # 描述
    enabled: bool = True  # 是否启用
    priority: int = 5  # 优先级（1-10，越大优先级越高）
    capabilities: List[str] = field(default_factory=list)  # 支持的能力列表
    config: Dict[str, Any] = field(default_factory=dict)  # 模型特定配置
    stats: Dict[str, Any] = field(default_factory=dict)  # 使用统计


class ModelRegistry:
    """模型注册表"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化模型注册表
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config"
        )
        self.models: Dict[str, ModelConfig] = {}
        self._load_default_configs()
        logger.info(f"模型注册表初始化完成，加载了 {len(self.models)} 个模型")
    
    def _load_default_configs(self):
        """加载默认配置"""

        
        # LM Studio Qwen3.5 4B (用户更换的更好模型，主模型)
        self.register_model(ModelConfig(
            model_id="lm-studio-qwen3.5-4b",
            model_type="lm_studio",
            display_name="Qwen3.5 4B (LM Studio)",
            description="通过LM Studio运行的Qwen3.5 4B模型，支持vision和tool_use，性能更优",
            enabled=True,
            priority=10,  # 最高优先级，主模型
            capabilities=["chat", "reasoning", "code", "translation", "summarization", "vision"],
            config={
                "base_url": "http://192.168.104.210:1234",
                "model": "qwen3.5-4b",
                "timeout": 120,
                "requires_api_key": False,
                "requires_internet": False,
                "requires_gpu": True
            },
            stats={"call_count": 0, "success_count": 0, "error_count": 0}
        ))
        

        

        

        

    
    def register_model(self, config: ModelConfig):
        """
        注册模型
        
        Args:
            config: 模型配置
        """
        self.models[config.model_id] = config
        logger.info(f"注册模型: {config.display_name} ({config.model_id})")
    
    def unregister_model(self, model_id: str):
        """
        注销模型
        
        Args:
            model_id: 模型ID
        """
        if model_id in self.models:
            model = self.models[model_id]
            logger.info(f"注销模型: {model.display_name} ({model_id})")
            del self.models[model_id]
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """
        获取模型配置
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型配置，如果不存在则返回None
        """
        return self.models.get(model_id)
    
    def get_all_models(self) -> List[ModelConfig]:
        """
        获取所有模型
        
        Returns:
            模型配置列表
        """
        return list(self.models.values())
    
    def get_enabled_models(self) -> List[ModelConfig]:
        """
        获取所有启用的模型
        
        Returns:
            启用的模型配置列表
        """
        return [model for model in self.models.values() if model.enabled]
    
    def get_models_by_type(self, model_type: str) -> List[ModelConfig]:
        """
        按类型获取模型
        
        Args:
            model_type: 模型类型
            
        Returns:
            指定类型的模型配置列表
        """
        return [model for model in self.models.values() if model.model_type == model_type]
    
    def get_models_by_capability(self, capability: str) -> List[ModelConfig]:
        """
        按能力获取模型
        
        Args:
            capability: 能力名称
            
        Returns:
            支持指定能力的模型配置列表
        """
        return [model for model in self.models.values() if capability in model.capabilities]
    
    def enable_model(self, model_id: str):
        """
        启用模型
        
        Args:
            model_id: 模型ID
        """
        if model_id in self.models:
            self.models[model_id].enabled = True
            logger.info(f"启用模型: {model_id}")
    
    def disable_model(self, model_id: str):
        """
        禁用模型
        
        Args:
            model_id: 模型ID
        """
        if model_id in self.models:
            self.models[model_id].enabled = False
            logger.info(f"禁用模型: {model_id}")
    
    def update_model_config(self, model_id: str, config_updates: Dict[str, Any]):
        """
        更新模型配置
        
        Args:
            model_id: 模型ID
            config_updates: 配置更新字典
        """
        if model_id in self.models:
            for key, value in config_updates.items():
                if key == "config":
                    # 合并配置字典
                    self.models[model_id].config.update(value)
                elif hasattr(self.models[model_id], key):
                    setattr(self.models[model_id], key, value)
            
            logger.info(f"更新模型配置: {model_id}")
    
    def record_model_call(self, model_id: str, success: bool = True):
        """
        记录模型调用
        
        Args:
            model_id: 模型ID
            success: 是否成功
        """
        if model_id in self.models:
            model = self.models[model_id]
            model.stats["call_count"] = model.stats.get("call_count", 0) + 1
            
            if success:
                model.stats["success_count"] = model.stats.get("success_count", 0) + 1
            else:
                model.stats["error_count"] = model.stats.get("error_count", 0) + 1
    
    def get_model_stats(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模型统计
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型统计字典，如果模型不存在则返回None
        """
        if model_id in self.models:
            return self.models[model_id].stats.copy()
        return None
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有模型统计
        
        Returns:
            模型ID到统计字典的映射
        """
        return {
            model_id: model.stats.copy()
            for model_id, model in self.models.items()
        }
    
    def save_configs(self, filepath: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            filepath: 配置文件路径
        """
        if filepath is None:
            os.makedirs(self.config_dir, exist_ok=True)
            filepath = os.path.join(self.config_dir, "model_registry.json")
        
        configs = {
            "models": {
                model_id: asdict(model)
                for model_id, model in self.models.items()
            }
        }
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            logger.info(f"模型配置已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存模型配置失败: {e}")
    
    def load_configs(self, filepath: Optional[str] = None):
        """
        从文件加载配置
        
        Args:
            filepath: 配置文件路径
        """
        if filepath is None:
            filepath = os.path.join(self.config_dir, "model_registry.json")
        
        if not os.path.exists(filepath):
            logger.warning(f"配置文件不存在: {filepath}")
            return
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                configs = json.load(f)
            
            # 清除现有模型
            self.models.clear()
            
            # 加载模型配置
            for model_id, model_data in configs.get("models", {}).items():
                try:
                    # 转换回ModelConfig对象
                    config = ModelConfig(
                        model_id=model_data.get("model_id", model_id),
                        model_type=model_data.get("model_type", ""),
                        display_name=model_data.get("display_name", ""),
                        description=model_data.get("description", ""),
                        enabled=model_data.get("enabled", True),
                        priority=model_data.get("priority", 5),
                        capabilities=model_data.get("capabilities", []),
                        config=model_data.get("config", {}),
                        stats=model_data.get("stats", {})
                    )
                    self.models[model_id] = config
                except Exception as e:
                    logger.error(f"加载模型配置失败 {model_id}: {e}")
            
            logger.info(f"从 {filepath} 加载了 {len(self.models)} 个模型配置")
            
        except Exception as e:
            logger.error(f"加载模型配置文件失败: {e}")
    
    def get_recommended_model(self, capability: str, requires_internet: bool = True) -> Optional[ModelConfig]:
        """
        获取推荐模型
        
        Args:
            capability: 所需能力
            requires_internet: 是否需要网络
            
        Returns:
            推荐的模型配置
        """
        # 过滤启用的、支持能力的模型
        candidates = [
            model for model in self.get_enabled_models()
            if capability in model.capabilities
        ]
        
        if not candidates:
            return None
        
        # 根据网络要求进一步过滤
        if not requires_internet:
            candidates = [
                model for model in candidates
                if not model.config.get("requires_internet", False)
            ]
        
        if not candidates:
            return None
        
        # 按优先级排序，选择优先级最高的
        candidates.sort(key=lambda m: m.priority, reverse=True)
        return candidates[0]
    
    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """
        获取模型状态
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型状态字典
        """
        model = self.get_model(model_id)
        if not model:
            return {"error": f"模型不存在: {model_id}"}
        
        return {
            "model_id": model.model_id,
            "display_name": model.display_name,
            "model_type": model.model_type,
            "enabled": model.enabled,
            "priority": model.priority,
            "capabilities": model.capabilities,
            "stats": model.stats,
            "config_summary": {
                "requires_api_key": model.config.get("requires_api_key", False),
                "requires_internet": model.config.get("requires_internet", False),
                "requires_gpu": model.config.get("requires_gpu", False),
                "max_tokens": model.config.get("max_tokens", "unknown")
            }
        }


# 全局注册表实例
_global_registry = None

def get_model_registry() -> ModelRegistry:
    """
    获取全局模型注册表实例
    
    Returns:
        ModelRegistry实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry