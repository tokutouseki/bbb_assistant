"""Live2D 模型管理 API — 列出、导入、删除模型。"""

import os
import shutil
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# 模型存储根目录
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LIVE2D_MODEL_DIR = os.path.join(_project_root, "backend", "data", "models", "live2d")

# 确保目录存在
os.makedirs(LIVE2D_MODEL_DIR, exist_ok=True)


class ModelInfo(BaseModel):
    name: str
    path: str
    model_json: str
    has_expressions: bool
    has_motions: bool


class ImportRequest(BaseModel):
    source_path: str


def _scan_models() -> list[ModelInfo]:
    """扫描 live2d 目录，返回所有可用模型列表。"""
    models = []
    if not os.path.isdir(LIVE2D_MODEL_DIR):
        return models

    for entry in sorted(os.listdir(LIVE2D_MODEL_DIR)):
        entry_path = os.path.join(LIVE2D_MODEL_DIR, entry)
        if not os.path.isdir(entry_path):
            continue

        # 查找 .model3.json 文件
        model_json = ""
        for f in sorted(os.listdir(entry_path)):
            if f.endswith(".model3.json"):
                model_json = os.path.join(entry_path, f)
                break

        # 也检查目录本身是否包含 model3.json（用户可能直接放入单个模型文件夹）
        if not model_json:
            for f in sorted(os.listdir(entry_path)):
                if f.endswith(".model3.json"):
                    model_json = os.path.join(entry_path, f)
                    break

        if not model_json:
            continue

        # 检查是否有表情和动作
        exp_dir = os.path.join(entry_path, "expressions")
        mot_dir = os.path.join(entry_path, "motions")
        has_exp = os.path.isdir(exp_dir) and len(os.listdir(exp_dir)) > 0
        has_mot = os.path.isdir(mot_dir) and len(os.listdir(mot_dir)) > 0

        models.append(ModelInfo(
            name=entry,
            path=entry_path,
            model_json=model_json,
            has_expressions=has_exp,
            has_motions=has_mot,
        ))

    return models


@router.get("/models")
async def list_models():
    """列出所有可用的 Live2D 模型。"""
    try:
        models = _scan_models()
        return {"success": True, "models": [m.model_dump() for m in models]}
    except Exception as e:
        logger.error(f"列出模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/import")
async def import_model(req: ImportRequest):
    """从外部路径导入模型（复制到项目 live2d 目录）。"""
    source = req.source_path.strip().strip('"').strip("'").strip()

    if not source:
        raise HTTPException(status_code=400, detail="source_path 不能为空")

    if not os.path.exists(source):
        raise HTTPException(status_code=400, detail=f"路径不存在: {source}")

    # 确定模型名称：如果是目录用目录名；如果是文件用文件名去后缀
    if os.path.isdir(source):
        model_name = os.path.basename(source.rstrip("/\\"))
    elif source.endswith(".model3.json"):
        # 取 model3.json 所在目录名
        parent = os.path.dirname(source)
        model_name = os.path.basename(parent.rstrip("/\\"))
        # 如果是根目录下的单个文件，用文件名
        if not model_name:
            model_name = os.path.splitext(os.path.basename(source))[0]
    else:
        raise HTTPException(status_code=400, detail="请选择 .model3.json 文件或其所在目录")

    dest = os.path.join(LIVE2D_MODEL_DIR, model_name)

    if os.path.exists(dest):
        raise HTTPException(
            status_code=409,
            detail=f"模型 '{model_name}' 已存在。请先删除旧模型或使用其他名称。",
        )

    try:
        if os.path.isdir(source):
            shutil.copytree(source, dest)
        else:
            # 单个文件：复制所在目录的全部内容
            parent_dir = os.path.dirname(source)
            shutil.copytree(parent_dir, dest)

        logger.info(f"模型已导入: {model_name} ← {source}")
        return {"success": True, "message": f"模型 '{model_name}' 已导入", "model_name": model_name}
    except Exception as e:
        logger.error(f"导入模型失败: {e}")
        # 清理失败的复制
        if os.path.exists(dest):
            try:
                shutil.rmtree(dest)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """删除指定模型。"""
    dest = os.path.join(LIVE2D_MODEL_DIR, model_name)
    if not os.path.exists(dest):
        raise HTTPException(status_code=404, detail=f"模型 '{model_name}' 不存在")

    try:
        shutil.rmtree(dest)
        logger.info(f"模型已删除: {model_name}")
        return {"success": True, "message": f"模型 '{model_name}' 已删除"}
    except Exception as e:
        logger.error(f"删除模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


class Live2DApplyRequest(BaseModel):
    """Real-time window control params. All fields optional — only provided ones are applied."""
    window_x: Optional[int] = Field(None, ge=0)
    window_y: Optional[int] = Field(None, ge=0)
    window_width: Optional[int] = Field(None, ge=200, le=2000)
    window_height: Optional[int] = Field(None, ge=200, le=2000)
    window_alpha: Optional[float] = Field(None, ge=0.0, le=1.0)


@router.put("/apply")
async def apply_live2d_settings(req: Live2DApplyRequest):
    """即时应用 Live2D 窗口设置（位置、大小、透明度）到运行中的服务器。"""
    try:
        from src.modules.live2d_control.config import LIVE2D_HOST, LIVE2D_PORT, CLIENT_TIMEOUT
        from src.modules.live2d_control.live2d_client import Live2DClient
    except ImportError:
        return {"success": False, "message": "Live2D module not available"}

    client = Live2DClient(host=LIVE2D_HOST, port=LIVE2D_PORT, timeout=CLIENT_TIMEOUT)
    if not client.connect():
        return {"success": False, "message": "Live2D server is not running"}

    applied = []
    if req.window_x is not None or req.window_y is not None:
        # Get current values from server if not provided
        status = client.send({"action": "get_status"})
        cur_x = status.get("status", {}).get("window_position", [100, 100])[0]
        cur_y = status.get("status", {}).get("window_position", [100, 100])[1]
        x = req.window_x if req.window_x is not None else cur_x
        y = req.window_y if req.window_y is not None else cur_y
        client.send({"action": "set_window_position", "x": x, "y": y})
        applied.append(f"position=({x},{y})")

    if req.window_width is not None or req.window_height is not None:
        w = req.window_width or 400
        h = req.window_height or 500
        client.send({"action": "set_window_size", "width": w, "height": h})
        applied.append(f"size={w}x{h}")

    if req.window_alpha is not None:
        client.send({"action": "set_window_alpha", "alpha": req.window_alpha})
        applied.append(f"alpha={req.window_alpha:.2f}")

    client.close()

    if not applied:
        return {"success": True, "message": "No changes"}

    # Also persist to runtime settings so changes survive restart
    try:
        from src.config.runtime_settings import update_runtime_settings
        overrides = {}
        if req.window_x is not None:
            overrides["live2d_window_x"] = req.window_x
        if req.window_y is not None:
            overrides["live2d_window_y"] = req.window_y
        if req.window_width is not None:
            overrides["live2d_window_width"] = req.window_width
        if req.window_height is not None:
            overrides["live2d_window_height"] = req.window_height
        if req.window_alpha is not None:
            overrides["live2d_window_alpha"] = req.window_alpha
        if overrides:
            update_runtime_settings(overrides)
    except Exception:
        pass

    return {"success": True, "message": f"Applied: {', '.join(applied)}"}
