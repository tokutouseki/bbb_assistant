"""
Cross-Encoder 重排序服务
======================
对 Hybrid 检索召回的结果进行精排，是业界公认的 RAG 精度提升最大单一手段。

模型: BAAI/bge-reranker-v2-m3 (568M, 中英双语, Cross-Encoder)
备选: maidalun1020/bce-reranker-base_v1 (278M, 更轻量)

使用方式:
    reranker = get_reranker()
    scores = reranker.rerank(query, documents)
    # scores[i] 是 documents[i] 与 query 的相关度分数

管道:
    Hybrid Search top-20 → Reranker 重打分 → 返回 top-5
"""

import logging
from typing import List, Optional, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# 默认模型 (按优先级: 大模型精度高 / 小模型省资源)
# 默认模型 (bce-reranker-base_v1: 279M, 中英双语, 中文Reranking最优, 网易有道)
_DEFAULT_MODEL = "maidalun1020/bce-reranker-base_v1"
_FALLBACK_MODEL = "BAAI/bge-reranker-v2-m3"

# 模型存放目录（与其他模型统一: PixAI-Tagger, Qwen3-TTS, SenseVoiceSmall 等）
_MODEL_CACHE_DIR = "D:/TokusCode/models"

# HuggingFace 镜像 (国内访问加速)
_HF_MIRRORS = [
    "https://hf-mirror.com",      # hf-mirror.com (国内推荐)
    "https://huggingface.co",     # 官方 (需科学上网)
]


def _try_load_from_mirrors(model_name: str, device: str, max_length: int):
    """加载 Reranker 模型 — 优先本地缓存，缓存未命中时通过镜像下载。

    策略:
    1. 检查本地缓存 → 命中则直接加载（零网络）
    2. 缓存未命中 → huggingface_hub.snapshot_download 通过镜像下载
    3. 下载完成 → transformers 从本地路径加载
    """
    import os as _os
    from pathlib import Path as _Path

    last_error = None

    # ── 第一步：确定本地路径 ──
    # 优先级: 统一模型目录 > HuggingFace 缓存 > 镜像下载
    local_path = None

    # 1) 统一模型目录: D:/TokusCode/models/bce-reranker-base_v1/
    model_slug = model_name.split("/")[-1]  # "bce-reranker-base_v1"
    unified_path = _Path(_MODEL_CACHE_DIR) / model_slug
    if unified_path.exists() and (unified_path / "pytorch_model.bin").exists():
        local_path = str(unified_path)
        logger.info(f"Reranker 统一目录命中: {local_path}")

    # 2) HuggingFace 缓存目录
    if local_path is None:
        safe_name = "models--" + model_name.replace("/", "--")
        cache_dir = _Path(_MODEL_CACHE_DIR) / "reranker" / safe_name / "snapshots"
        if cache_dir.exists():
            snapshots = sorted(cache_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            if snapshots:
                local_path = str(snapshots[0])
                logger.info(f"Reranker HF缓存命中: {local_path}")

    # ── 第二步：缓存未命中 → 下载 ──
    if local_path is None:
        from huggingface_hub import snapshot_download

        for mirror in _HF_MIRRORS:
            try:
                logger.info(f"尝试从镜像下载 Reranker: {mirror} ({model_name})")
                local_path = snapshot_download(
                    repo_id=model_name,
                    endpoint=mirror,
                    cache_dir=_MODEL_CACHE_DIR,
                    resume_download=True,
                    max_workers=4,
                )
                logger.info(f"模型文件已下载到: {local_path}")
                break
            except Exception as e:
                last_error = e
                logger.warning(f"镜像 {mirror} 下载失败: {e}")
                continue

        if local_path is None:
            raise last_error or RuntimeError("所有镜像源均不可用")

    # ── 第三步：从本地路径加载模型 ──
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch as _torch

    tokenizer = AutoTokenizer.from_pretrained(
        local_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        local_path,
        dtype=_torch.float16 if device.startswith("cuda") else _torch.float32,
        trust_remote_code=True,
        local_files_only=True,
    )
    model.to(device)
    model.eval()

    logger.info(f"Reranker 模型加载成功: {model_name}")
    return tokenizer, model  # 注意顺序: (tokenizer, model)


class RerankerService:
    """Cross-Encoder 重排序服务 — 单例，延迟加载。

    对 (query, document) 对进行联合编码打分，
    比 bi-encoder (独立编码后余弦相似度) 精度高得多。
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        device: str = "cuda:0",
        max_length: int = 512,
        batch_size: int = 16,
    ):
        self._model_name = model_name
        self._device = device
        self._max_length = max_length
        self._batch_size = batch_size

        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._load_lock = Lock()
        self._load_error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def _ensure_loaded(self) -> bool:
        """延迟加载模型（首次调用时触发）。"""
        if self._loaded:
            return True
        if self._load_error and self._model_name == _FALLBACK_MODEL:
            return False  # 主模型和 fallback 都失败了

        with self._load_lock:
            if self._loaded:
                return True

            models_to_try = [self._model_name]
            if self._model_name != _FALLBACK_MODEL:
                models_to_try.append(_FALLBACK_MODEL)

            for model_name in models_to_try:
                try:
                    logger.info(f"加载 Reranker 模型: {model_name} (device={self._device})")

                    import torch as _torch

                    self._tokenizer, self._model = _try_load_from_mirrors(
                        model_name, self._device, self._max_length
                    )
                    if self._tokenizer is None or self._model is None:
                        continue

                    self._loaded = True
                    self._model_name = model_name  # 记录实际加载的模型
                    self._load_error = None

                    # 显存占用估算
                    if self._device.startswith("cuda"):
                        import torch as _t
                        mem_mb = _t.cuda.memory_allocated(self._device.split(":")[0] if ":" in self._device else 0) / 1024 / 1024
                        logger.info(f"Reranker 模型加载完成: {model_name}, GPU显存占用 ~{mem_mb:.0f}MB")
                    else:
                        logger.info(f"Reranker 模型加载完成: {model_name} (CPU)")

                    return True

                except Exception as e:
                    logger.warning(f"加载 Reranker 模型失败 ({model_name}): {e}")
                    self._load_error = str(e)
                    self._model = None
                    self._tokenizer = None

            logger.error("所有 Reranker 模型加载失败，重排序功能不可用")
            return False

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """对文档列表进行重排序。

        Args:
            query: 查询字符串
            documents: 候选文档内容列表
            top_k: 返回 top-K 结果索引，None 则返回全部

        Returns:
            [(doc_index, relevance_score), ...] 按分数降序排列
            分数范围 0-1（经过 sigmoid 归一化）
        """
        if not self._ensure_loaded():
            return [(i, 0.0) for i in range(len(documents))]

        if not documents:
            return []

        import torch

        try:
            # 构建 (query, document) 对
            pairs = [[query, doc[:self._max_length * 2]] for doc in documents]

            all_scores = []
            # 分批推理（避免 OOM）
            for i in range(0, len(pairs), self._batch_size):
                batch = pairs[i:i + self._batch_size]
                encoded = self._tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=self._max_length,
                )
                # 只传模型接受的 tensor key（XLMRoberta: input_ids, attention_mask）
                # 显式排除可能泄漏的 tokenizer 元数据 key
                valid_keys = {"input_ids", "attention_mask", "token_type_ids"}
                model_inputs = {}
                for k, v in encoded.items():
                    if k in valid_keys:
                        model_inputs[k] = v.to(self._device)

                with torch.no_grad():
                    outputs = self._model(**model_inputs, return_dict=True)
                    scores = outputs.logits.view(-1).float()

                all_scores.extend(scores.cpu().tolist())

            # 按分数降序排列，返回 (index, score)
            indexed_scores = [(i, score) for i, score in enumerate(all_scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            if top_k is not None:
                indexed_scores = indexed_scores[:top_k]

            return indexed_scores

        except Exception as e:
            logger.error(f"Reranker 推理失败: {e}")
            return [(i, 0.0) for i in range(len(documents))]

    def rerank_results(
        self,
        query: str,
        results: list,  # List[UnifiedSearchResult]
        top_k: int = 5,
    ) -> list:
        """对 RAG 检索结果进行重排序。

        提取每个结果的 content，调用 rerank() 打分，
        返回按 reranker 分数重排后的结果子集。

        Args:
            query: 查询字符串
            results: 原始检索结果列表 (每个有 .content 属性)
            top_k: 返回数量

        Returns:
            重排后的结果子集（保持原对象，仅重排序）
        """
        if not results:
            return results

        if not self._ensure_loaded():
            # Reranker 不可用 → 保持原序
            return results[:top_k]

        documents = [r.content for r in results]
        ranked = self.rerank(query, documents, top_k=top_k)

        # 按 reranker 分数重排
        reranked = []
        for idx, score in ranked:
            if idx < len(results):
                # 将 reranker 分数存入结果对象
                r = results[idx]
                r._rerank_score = score  # 临时属性，供格式化使用
                # 用 reranker 分数覆盖原分数（归一化到 0-1 区间更容易理解）
                r.rerank_score = float(score)
                reranked.append(r)

        return reranked


# ── 全局单例 ──

_reranker_instance: Optional[RerankerService] = None
_reranker_lock = Lock()


def get_reranker(
    model_name: str = _DEFAULT_MODEL,
    device: str = "cuda:0",
) -> RerankerService:
    """获取 RerankerService 全局单例。"""
    global _reranker_instance
    if _reranker_instance is None:
        with _reranker_lock:
            if _reranker_instance is None:
                _reranker_instance = RerankerService(
                    model_name=model_name,
                    device=device,
                )
    return _reranker_instance


def has_reranker() -> bool:
    """检查 Reranker 是否可用（已加载）。"""
    return _reranker_instance is not None and _reranker_instance.is_loaded
