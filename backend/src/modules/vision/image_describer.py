"""
图片描述器 — 多后端图片分析工具
支持: bailian (阿里百炼 Qwen-VL), pixai_tagger (本地 Danbooru 标签), lmstudio (本地视觉模型)
按配置的优先级顺序尝试，返回第一个成功的后端结果
"""
import base64
import io
import json
import logging
import os
from typing import List, Optional, Tuple

import numpy as np
import onnxruntime as ort
from PIL import Image

logger = logging.getLogger(__name__)

# ONNX 强制 CPU（避免 CUDA 版本冲突）
os.environ.setdefault("ONNX_MODE", "cpu")


class ImageDescriber:
    """多后端图片描述器，按优先级自动降级。"""

    BACKENDS = ["bailian", "pixai_tagger", "lmstudio"]

    def __init__(self, backend_order: Optional[List[str]] = None):
        from src.config.settings import get_settings
        from src.config.runtime_settings import get_runtime_settings

        self._settings = get_settings()
        self._runtime = get_runtime_settings()

        if backend_order is None:
            raw = self._runtime.get("image_describer_backend", "bailian")
            if isinstance(raw, str):
                backend_order = [b.strip() for b in raw.split(",") if b.strip() in self.BACKENDS]
            else:
                backend_order = ["bailian"]
        self.backend_order = backend_order or ["bailian"]

    def describe(self, images: List[str]) -> Tuple[str, str]:
        """
        描述图片，按优先级尝试各后端。

        Returns:
            (description, backend_used) — 文本描述和实际使用的后端名称
        """
        # 每次调用时重新读取运行时设置，确保用户在前端的修改即时生效
        from src.config.runtime_settings import get_runtime_settings
        self._runtime = get_runtime_settings()
        raw = self._runtime.get("image_describer_backend", "bailian")
        if isinstance(raw, str):
            self.backend_order = [b.strip() for b in raw.split(",") if b.strip() in self.BACKENDS]
        if not self.backend_order:
            self.backend_order = ["bailian"]

        errors = []
        for backend in self.backend_order:
            try:
                desc = getattr(self, f"_describe_{backend}")(images)
                if desc and desc.strip():
                    logger.info(f"图片描述成功，使用后端: {backend}")
                    return desc, backend
                else:
                    errors.append(f"{backend}: 返回空描述")
            except Exception as e:
                logger.warning(f"图片描述后端 {backend} 失败: {e}")
                errors.append(f"{backend}: {e}")

        raise RuntimeError(f"所有图片描述后端均失败: {'; '.join(errors)}")

    # ── Bailian (阿里百炼 Qwen-VL) ──────────────────────────

    def _describe_bailian(self, images: List[str]) -> str:
        api_key = self._runtime.get("bailian_api_key") or self._settings.bailian_api_key
        if not api_key:
            raise RuntimeError("阿里百炼 API Key 未配置")

        base_url = self._settings.bailian_base_url
        model = self._settings.bailian_vision_model

        content_parts = [
            {
                "type": "text",
                "text": (
                    "请详细描述这张图片中的所有内容，包括但不限于："
                    "角色外观特征（发色、瞳色、服装、标志性装饰）、"
                    "场景环境、文字内容、UI界面元素、物品道具等。"
                    "请尽可能详细和准确。"
                ),
            }
        ]
        for img in images:
            content_parts.append({"type": "image_url", "image_url": {"url": img}})

        messages = [{"role": "user", "content": content_parts}]

        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
        return completion.choices[0].message.content or ""

    # ── PixAI Tagger (本地 Danbooru 标签) ───────────────────

    def _describe_pixai_tagger(self, images: List[str]) -> str:
        import pandas as pd
        from imgutils.data import load_image
        from imgutils.preprocess import create_pillow_transforms

        # 一次加载，多次复用
        model, df_tags, transforms = self._load_pixai_model()

        all_tags: dict = {}
        for img_b64 in images:
            pil_image = self._b64_to_pil(img_b64)
            input_image = load_image(pil_image, force_background="white", mode="RGB")
            input_tensor = transforms(input_image)[None, ...]
            # transforms 可能返回 torch tensor 或 numpy array
            if hasattr(input_tensor, 'numpy'):
                input_tensor = input_tensor.numpy()

            output_names = [o.name for o in model.get_outputs()]
            outputs = model.run(output_names, {"input": input_tensor})
            output_dict = dict(zip(output_names, [o[0] for o in outputs]))
            prediction = output_dict.get("prediction", outputs[0])

            # 按类别分别提取
            for category in sorted(set(df_tags["category"].tolist())):
                mask = df_tags["category"] == category
                tag_names = df_tags["name"][mask]
                cat_pred = prediction[mask]
                for name, score in zip(tag_names, cat_pred):
                    score = float(score)
                    if score > all_tags.get(name, 0):
                        all_tags[name] = score

        if not all_tags:
            return ""

        # 按置信度排序，取前 40 个高置信标签
        sorted_tags = sorted(all_tags.items(), key=lambda x: -x[1])
        high_conf = [(t, s) for t, s in sorted_tags if s >= 0.35][:40]

        if not high_conf:
            return ""

        lines = ["[图片标签识别结果 (PixAI Tagger)]"]
        lines.append(", ".join(f"{t}({s:.0%})" for t, s in high_conf))

        # 从 tags 中提取角色名 (category=4)
        character_tags = df_tags[df_tags["category"] == 4]
        character_names = set(character_tags["name"].tolist())
        detected_chars = [(t, s) for t, s in high_conf if t in character_names and s >= 0.6]
        if detected_chars:
            lines.append(f"角色: {', '.join(f'{t}({s:.0%})' for t, s in detected_chars[:10])}")

        return "\n".join(lines)

    # ── PixAI 模型懒加载缓存 ───────────────────────────────

    _pixai_model_cache = None
    _pixai_tags_cache = None
    _pixai_transforms_cache = None

    def _load_pixai_model(self):
        if self._pixai_model_cache is not None:
            return self._pixai_model_cache, self._pixai_tags_cache, self._pixai_transforms_cache

        import pandas as pd
        from imgutils.preprocess import create_pillow_transforms

        model_dir = self._settings.pixai_tagger_model_path
        if not os.path.isdir(model_dir):
            raise RuntimeError(f"PixAI Tagger 模型目录不存在: {model_dir}")

        onnx_path = os.path.join(model_dir, "model.onnx")
        tags_path = os.path.join(model_dir, "selected_tags.csv")
        preproc_path = os.path.join(model_dir, "preprocess.json")

        if not os.path.isfile(onnx_path):
            raise RuntimeError(f"ONNX 模型文件不存在: {onnx_path}")

        # ONNX session (CPU only)
        opts = ort.SessionOptions()
        model = ort.InferenceSession(onnx_path, opts, providers=["CPUExecutionProvider"])

        # 标签表
        df_tags = pd.read_csv(tags_path)

        # 预处理 pipeline
        with open(preproc_path, "r") as f:
            preproc_cfg = json.load(f)
        transforms = create_pillow_transforms(preproc_cfg["stages"])

        ImageDescriber._pixai_model_cache = model
        ImageDescriber._pixai_tags_cache = df_tags
        ImageDescriber._pixai_transforms_cache = transforms

        logger.info(f"PixAI Tagger 模型已加载: {onnx_path}")
        return model, df_tags, transforms

    # ── LM Studio (本地 Qwen 等视觉模型) ─────────────────────

    def _describe_lmstudio(self, images: List[str]) -> str:
        from src.modules.llm.lm_studio_client import create_lm_studio_client

        client = create_lm_studio_client(
            base_url=self._settings.lm_studio_base_url,
            model=self._settings.lm_studio_model,
        )
        if not client.test_connection():
            client.close()
            raise RuntimeError("LM Studio 未运行")

        content_parts = [
            {
                "type": "text",
                "text": (
                    "请详细描述这张图片中的所有内容，包括但不限于："
                    "角色外观特征、场景环境、文字内容、UI界面元素、物品道具等。"
                    "请尽可能详细和准确。"
                ),
            }
        ]
        for img in images:
            content_parts.append({"type": "image_url", "image_url": {"url": img}})

        messages = [{"role": "user", "content": content_parts}]
        result = client.chat_completion(messages=messages, temperature=0.3, stream=False)
        client.close()

        if isinstance(result, dict):
            content = result.get("content", "")
            if not content:
                raise RuntimeError("LM Studio 视觉模型返回空描述")
            return content
        return str(result)

    # ── helpers ─────────────────────────────────────────────

    @staticmethod
    def _b64_to_pil(b64_str: str) -> Image.Image:
        """将 base64 data URI 转为 PIL Image。"""
        if b64_str.startswith("data:"):
            _, b64_data = b64_str.split(",", 1)
        else:
            b64_data = b64_str
        img_bytes = base64.b64decode(b64_data)
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")


_instance: Optional[ImageDescriber] = None


def get_image_describer(backend_order: Optional[List[str]] = None) -> ImageDescriber:
    global _instance
    if _instance is None or backend_order is not None:
        _instance = ImageDescriber(backend_order=backend_order)
    return _instance
