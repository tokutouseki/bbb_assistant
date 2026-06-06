#!/usr/bin/env python3
"""Qwen3-TTS TCP worker — standalone subprocess that loads the TTS model once and serves requests.

Usage:
    python qwen3_tts_worker.py [--host 127.0.0.1] [--port 5004] [--model MODEL_PATH] [--quantize none|8bit|4bit]

Protocol (JSON + \\nEOF\\n):
    Request:  {"action": "<action>", ...params}
    Response: {"success": true/false, ...data}

Actions:
    health_check       — server + model status, GPU memory
    generate           — TTS generation, save WAV, return filepath
    generate_and_play  — TTS generation + audio playback
    warmup             — run test inference to warm up GPU
    shutdown           — graceful exit
"""

import sys
import os
import json
import time
import socket
import threading
import logging
import argparse
import signal
import datetime
import hashlib
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger(__name__)

TTS_PORT = 5004
TTS_HOST = "127.0.0.1"
CLIENT_TIMEOUT = 120

_current_dir = os.path.dirname(os.path.abspath(__file__))

# ---- Model Loading ----

def _normalize_model_path(model_path: str) -> str:
    base = Path(model_path)
    if (base / "config.json").exists():
        return str(base)
    candidates = [
        base / "models" / "Qwen" / "Qwen3-TTS-12Hz-1___7B-Base",
        base / "models" / "Qwen" / "Qwen3-TTS-12Hz-1.7B-Base",
        base / "models" / "Qwen3-TTS-12Hz-1.7B-Base",
        base / "Qwen3-TTS-12Hz-1___7B-Base",
        base / "Qwen3-TTS-12Hz-1.7B-Base",
    ]
    for candidate in candidates:
        if (candidate / "config.json").exists():
            return str(candidate)
    return str(base)


def _get_default_model_path() -> str:
    env_path = os.environ.get("QWEN3_TTS_MODEL_PATH")
    if env_path:
        p = _normalize_model_path(env_path)
        if os.path.exists(p):
            return p

    possible = [
        Path("D:/TokusCode/models/Qwen3-TTS"),
    ]
    for p in possible:
        norm = _normalize_model_path(str(p))
        if os.path.exists(norm):
            return norm

    return "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def _load_ref_index():
    index_path = os.path.join(_current_dir, "reference_audio", "index.json")
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_model(model_path: str, device: str, quantize: str):
    import torch
    from qwen_tts import Qwen3TTSModel

    kwargs = {"device_map": device}

    if quantize in ("8bit", "4bit"):
        try:
            from transformers import BitsAndBytesConfig
            if quantize == "8bit":
                kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                logger.info("启用 8-bit 量化 (bitsandbytes)")
            else:
                kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                )
                logger.info("启用 4-bit 量化 (bitsandbytes NF4)")
        except ImportError:
            logger.warning("bitsandbytes 未安装，回退到 bf16。安装: pip install bitsandbytes")
            kwargs["dtype"] = torch.bfloat16
        except Exception as e:
            logger.warning(f"量化配置失败: {e}，回退到 bf16")
            kwargs["dtype"] = torch.bfloat16
    else:
        kwargs["dtype"] = torch.bfloat16

    logger.info(f"加载模型: {model_path}")
    model = Qwen3TTSModel.from_pretrained(model_path, **kwargs)
    logger.info("模型加载完成")
    return model


# ---- Audio Playback ----

def _play_audio(filepath: str):
    import subprocess
    if sys.platform == "win32":
        subprocess.run(
            ["powershell", "-c",
             f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
            capture_output=True,
        )
    elif sys.platform == "darwin":
        subprocess.run(["afplay", filepath], capture_output=True)
    else:
        subprocess.run(["aplay", filepath], capture_output=True)


# ---- TCP Server ----

class TTSWorker:
    def __init__(self, host: str, port: int, model_path: str, quantize: str = "none",
                 output_dir: str = None, device: str = "cuda:0"):
        self.host = host
        self.port = port
        self.model_path = model_path
        self.quantize = quantize
        self.device = device
        self.model = None
        self._start_time = time.time()
        self._running = False
        self._server_socket = None
        self._warmup_done = False

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.join(os.getcwd(), "outputs", "qwen3_tts")
        os.makedirs(self.output_dir, exist_ok=True)

        self.ref_index = _load_ref_index()

    def run(self):
        logger.info(f"加载模型中... (量化: {self.quantize})")
        self.model = _load_model(self.model_path, self.device, self.quantize)
        self._warmup()
        logger.info(f"TTS Worker 就绪 {self.host}:{self.port}")
        self._run_tcp_server()

    def _warmup(self):
        try:
            entries = list(self.ref_index.values())
            if not entries:
                logger.warning("无参考音频，跳过预热")
                return
            entry = entries[0]
            ref_audio = entry["audio_path"]
            ref_text = entry.get("ref_text", "")
            logger.info("执行预热推理...")
            t0 = time.time()
            self._do_generate("模型预热测试", ref_audio, "Chinese", ref_text)
            logger.info(f"预热完成，耗时 {time.time() - t0:.2f}s")
            self._warmup_done = True
        except Exception as e:
            logger.warning(f"预热失败: {e}")

    def _do_generate(self, text: str, ref_audio: str, language: str, ref_text: str):
        wavs, sr = self.model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=False if ref_text else True,
        )
        if isinstance(wavs, list) and len(wavs) > 0:
            audio_data = wavs[0]
        else:
            audio_data = np.array(wavs)
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        return audio_data, sr

    def _save_audio(self, audio_data: np.ndarray, sample_rate: int, text: str) -> str:
        import soundfile as sf
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:6]
        filename = f"qwen3_tts_{timestamp}_cloned_{text_hash}.wav"
        filepath = os.path.join(self.output_dir, filename)
        sf.write(filepath, audio_data, sample_rate)
        return filepath

    def _get_gpu_memory_mb(self) -> int:
        try:
            import torch
            if torch.cuda.is_available():
                return int(torch.cuda.memory_allocated() / 1024 / 1024)
        except Exception:
            pass
        return -1

    # ---- TCP Server ----

    def _run_tcp_server(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(2.0)
            self._running = True
            logger.info(f"TCP 监听 {self.host}:{self.port}")

            while self._running:
                try:
                    client_sock, client_addr = self._server_socket.accept()
                    handler = ClientHandler(client_sock, client_addr, self)
                    handler.daemon = True
                    handler.start()
                except socket.timeout:
                    continue
                except OSError:
                    break
        except Exception as e:
            logger.error(f"TCP 服务错误: {e}")
        finally:
            if self._server_socket:
                try:
                    self._server_socket.close()
                except Exception:
                    pass

    def stop(self):
        self._running = False


class ClientHandler(threading.Thread):
    def __init__(self, client_socket: socket.socket, client_addr, worker: TTSWorker):
        super().__init__()
        self.sock = client_socket
        self.addr = client_addr
        self.worker = worker
        self.sock.settimeout(CLIENT_TIMEOUT)

    def run(self):
        logger.info(f"客户端连接: {self.addr}")
        try:
            data = b""
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        return
                    data += chunk
                    if b"\nEOF\n" in data:
                        break
                except socket.timeout:
                    return
                except Exception:
                    return

            request_str = data.decode("utf-8").replace("\nEOF\n", "")
            try:
                request = json.loads(request_str)
            except json.JSONDecodeError:
                self._send({"success": False, "error": "Invalid JSON"})
                return

            response = self._handle(request)
            self._send(response)
        except Exception as e:
            logger.error(f"客户端处理错误: {e}")
        finally:
            try:
                self.sock.close()
            except Exception:
                pass

    def _send(self, data: dict):
        try:
            payload = json.dumps(data, ensure_ascii=False) + "\nEOF\n"
            self.sock.sendall(payload.encode("utf-8"))
        except Exception as e:
            logger.error(f"发送错误: {e}")

    def _handle(self, req: dict) -> dict:
        action = req.get("action", "")
        try:
            if action == "health_check":
                return {
                    "success": True,
                    "model_loaded": self.worker.model is not None,
                    "quantization": self.worker.quantize,
                    "uptime": time.time() - self.worker._start_time,
                    "gpu_memory_mb": self.worker._get_gpu_memory_mb(),
                    "warmup_done": self.worker._warmup_done,
                }

            elif action == "generate":
                text = req.get("text", "")
                ref_audio = req.get("ref_audio", "")
                language = req.get("language", "Chinese")
                ref_text = req.get("ref_text", "")

                if not text or not ref_audio:
                    return {"success": False, "error": "text and ref_audio required"}

                t0 = time.time()
                audio_data, sr = self.worker._do_generate(text, ref_audio, language, ref_text)
                filepath = self.worker._save_audio(audio_data, sr, text)
                processing_time = time.time() - t0

                logger.info(f"生成完成: {len(audio_data) / sr:.1f}s, 耗时 {processing_time:.2f}s")
                return {
                    "success": True,
                    "action": "generate",
                    "filepath": filepath,
                    "sample_rate": sr,
                    "processing_time": processing_time,
                }

            elif action == "generate_and_play":
                text = req.get("text", "")
                ref_audio = req.get("ref_audio", "")
                language = req.get("language", "Chinese")
                ref_text = req.get("ref_text", "")

                if not text or not ref_audio:
                    return {"success": False, "error": "text and ref_audio required"}

                t0 = time.time()
                audio_data, sr = self.worker._do_generate(text, ref_audio, language, ref_text)
                filepath = self.worker._save_audio(audio_data, sr, text)
                processing_time = time.time() - t0

                _play_audio(filepath)

                logger.info(f"生成+播放完成: {len(audio_data) / sr:.1f}s, 耗时 {processing_time:.2f}s")
                return {
                    "success": True,
                    "action": "generate_and_play",
                    "filepath": filepath,
                    "sample_rate": sr,
                    "processing_time": processing_time,
                }

            elif action == "play_audio":
                filepath = req.get("filepath", "")
                if not filepath or not os.path.exists(filepath):
                    return {"success": False, "error": "filepath not found"}
                _play_audio(filepath)
                return {"success": True}

            elif action == "warmup":
                self.worker._warmup()
                return {"success": True, "warmup_done": self.worker._warmup_done}

            elif action == "shutdown":
                logger.info("收到 shutdown 请求")
                self.worker.stop()
                return {"success": True, "message": "Shutting down"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"处理 '{action}' 错误: {e}")
            return {"success": False, "error": str(e), "error_type": type(e).__name__}


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS TCP Worker")
    parser.add_argument("--host", default=TTS_HOST)
    parser.add_argument("--port", type=int, default=TTS_PORT)
    parser.add_argument("--model", default="", help="Model path (default: auto-detect)")
    parser.add_argument("--quantize", default="none", choices=["none", "8bit", "4bit"])
    parser.add_argument("--output-dir", default="", help="Audio output directory")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    model_path = args.model if args.model else _get_default_model_path()
    model_path = _normalize_model_path(model_path)

    output_dir = args.output_dir if args.output_dir else None

    print(f"Qwen3-TTS Worker")
    print(f"  Model: {model_path}")
    print(f"  Device: {args.device}")
    print(f"  Quantize: {args.quantize}")
    print(f"  Listen: {args.host}:{args.port}")

    worker = TTSWorker(
        host=args.host,
        port=args.port,
        model_path=model_path,
        quantize=args.quantize,
        output_dir=output_dir,
        device=args.device,
    )

    def _sig_handler(sig, frame):
        logger.info("收到终止信号")
        worker.stop()

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    worker.run()


if __name__ == "__main__":
    main()
