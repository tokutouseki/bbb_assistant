#!/usr/bin/env python3
"""Qwen3-TTS orchestrator — manages TTS worker subprocess lifecycle.

Lazy-start on first use. All TTS calls go through call_qwen3_tts().
"""

import subprocess
import os
import sys
import time
import socket
import datetime
import threading

_current_dir = os.path.dirname(os.path.abspath(__file__))

TTS_HOST = "127.0.0.1"
TTS_PORT = 5004

_client = None
_worker_process = None
_worker_running = False
_worker_starting = False  # 防止并发启动多个 worker
_init_lock = threading.Lock()
_last_start_error = ""

# Restart tracking
_restart_count = 0
_restart_window_start = 0.0
MAX_RESTARTS = 3
RESTART_WINDOW = 300  # 5 minutes


def _get_client():
    global _client
    if _client is None:
        from .qwen3_tts_client import Qwen3TTSClient
        _client = Qwen3TTSClient()
    return _client


def reset_client():
    global _client
    if _client:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


def _is_worker_alive() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((TTS_HOST, TTS_PORT))
        s.close()
        return True
    except Exception:
        return False


def get_last_start_error() -> str:
    return _last_start_error


def start_worker(quantize: str = "none") -> bool:
    global _worker_process, _worker_running, _worker_starting, _last_start_error

    if _is_worker_alive():
        _worker_running = True
        _worker_starting = False
        return True

    _worker_starting = True
    worker_script = os.path.join(_current_dir, "qwen3_tts_worker.py")
    python_exe = sys.executable

    log_dir = os.path.join(_current_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "qwen3_tts_worker.log")

    try:
        log_file = open(log_path, "a", encoding="utf-8")
        log_file.write(f"\n[{datetime.datetime.now()}] TTS worker starting (Python: {python_exe})\n")
        log_file.flush()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [python_exe, worker_script, "--quantize", quantize]

        _worker_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            env=env,
            shell=False,
        )

        # Quick crash check
        for _ in range(3):
            time.sleep(1)
            exit_code = _worker_process.poll()
            if exit_code is not None:
                log_file.close()
                _last_start_error = _read_log_tail(log_path)
                if not _last_start_error:
                    _last_start_error = f"Worker process exited immediately with code {exit_code}"
                _worker_process = None
                print(f"[TTS Worker] Crashed on startup:\n{_last_start_error}")
                return False

        # Wait up to 30s for model loading + warmup
        max_wait = 27
        for i in range(max_wait):
            exit_code = _worker_process.poll()
            if exit_code is not None:
                log_file.close()
                _last_start_error = _read_log_tail(log_path)
                if not _last_start_error:
                    _last_start_error = f"Worker process exited with code {exit_code}"
                _worker_process = None
                print(f"[TTS Worker] Exited during startup:\n{_last_start_error}")
                return False

            time.sleep(1)
            if _is_worker_alive():
                _worker_running = True
                _start_health_monitor()
                return True

        # Timeout
        try:
            _worker_process.terminate()
            _worker_process.wait(timeout=3)
        except Exception:
            pass
        _worker_process = None
        log_file.close()
        _last_start_error = f"Worker startup timed out after 30s. Log tail:\n{_read_log_tail(log_path)}"
        print(f"[TTS Worker] {_last_start_error}")
        return False

    except Exception as e:
        log_file.close()
        _last_start_error = f"Failed to start worker: {e}"
        print(f"[TTS Worker] {_last_start_error}")
        _worker_running = False
        return False

    finally:
        _worker_starting = False


def _read_log_tail(log_path: str) -> str:
    try:
        if not os.path.exists(log_path):
            return "(log file not found)"
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-20:]).rstrip()
    except Exception as e:
        return f"(could not read log: {e})"


def stop_worker():
    global _worker_process, _worker_running

    client = _get_client()
    try:
        client.shutdown()
    except Exception:
        pass

    reset_client()

    if _worker_process:
        try:
            _worker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _worker_process.terminate()
        _worker_process = None

    _worker_running = False


def _can_restart() -> bool:
    global _restart_count, _restart_window_start
    now = time.time()
    if now - _restart_window_start > RESTART_WINDOW:
        _restart_count = 0
        _restart_window_start = now
    if _restart_count >= MAX_RESTARTS:
        return False
    _restart_count += 1
    return True


def _get_quantize() -> str:
    """从 settings 读取量化配置，默认 8bit。"""
    try:
        from src.config.settings import get_settings
        return get_settings().qwen3_tts_quantize
    except Exception:
        return "8bit"


def _start_health_monitor():
    """Background daemon that pings the worker every 30s and auto-restarts on crash."""
    def _monitor():
        while _worker_running:
            time.sleep(30)
            if not _worker_running:
                break
            if not _is_worker_alive():
                print("[TTS Worker] Health check failed — worker appears dead")
                if _can_restart() and not _worker_starting:
                    print("[TTS Worker] Attempting auto-restart...")
                    reset_client()
                    start_worker(quantize=_get_quantize())
                else:
                    print(f"[TTS Worker] Max restarts ({MAX_RESTARTS}) reached in {RESTART_WINDOW}s, giving up")

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()


def _ensure_worker() -> bool:
    global _worker_running, _worker_starting

    if _worker_running and _is_worker_alive():
        return True

    # 如果已有 worker 正在启动中，等待它完成而不是再启一个
    if _worker_starting:
        for _ in range(35):  # 最多等 35s
            time.sleep(1)
            if _is_worker_alive():
                _worker_running = True
                return True
        return False

    with _init_lock:
        if _worker_running and _is_worker_alive():
            return True
        if _worker_starting:
            return True  # 另一个线程已在启动
        return start_worker(quantize=_get_quantize())


def call_qwen3_tts(action: str, **kwargs) -> dict:
    """Main entry point for all TTS operations.

    Args:
        action: generate | generate_and_play | play_audio | health_check | warmup | shutdown
        **kwargs: Action-specific parameters.

    Returns:
        dict with at least {"success": bool}.
    """
    if not _ensure_worker():
        err = get_last_start_error()
        detail = f": {err}" if err else ""
        return {"success": False, "error": f"TTS worker is not running{detail}"}

    client = _get_client()

    method_map = {
        "health_check": lambda: client.health_check(),
        "generate": lambda: client.generate(
            kwargs.get("text", ""),
            kwargs.get("ref_audio", ""),
            kwargs.get("language", "Chinese"),
            kwargs.get("ref_text", ""),
        ),
        "generate_and_play": lambda: client.generate_and_play(
            kwargs.get("text", ""),
            kwargs.get("ref_audio", ""),
            kwargs.get("language", "Chinese"),
            kwargs.get("ref_text", ""),
        ),
        "play_audio": lambda: client.play_audio(kwargs.get("filepath", "")),
        "warmup": lambda: client.warmup(),
        "shutdown": lambda: client.shutdown(),
    }

    handler = method_map.get(action)
    if handler is None:
        return {"success": False, "error": f"Unknown action: {action}"}

    try:
        return handler()
    except Exception as e:
        return {"success": False, "error": str(e)}
