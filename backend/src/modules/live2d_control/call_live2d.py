#!/usr/bin/env python3
"""Live2D orchestrator — manages server lifecycle and provides a singleton client.

Modeled after call_YOLO.py. The Live2D server is lazily started on first use.
All Agent tool calls go through the single `call_live2d()` entry point.
"""

import subprocess
import json
import os
import sys
import time
import socket
import datetime
import threading

try:
    from .config import LIVE2D_HOST, LIVE2D_PORT
except ImportError:
    from config import LIVE2D_HOST, LIVE2D_PORT  # type: ignore[no-redef]

_current_dir = os.path.dirname(os.path.abspath(__file__))

_client: "Live2DClient | None" = None
_server_process: "subprocess.Popen | None" = None
_server_running = False
_init_lock = threading.Lock()


def _get_client():
    """Return the singleton Live2DClient, creating it if needed."""
    global _client
    if _client is None:
        from .live2d_client import Live2DClient
        _client = Live2DClient()
    return _client


def reset_client():
    """Close the current client connection (e.g., after server restart)."""
    global _client
    if _client:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


def _is_server_alive() -> bool:
    """Check if the Live2D server is listening on its port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((LIVE2D_HOST, LIVE2D_PORT))
        s.close()
        return True
    except Exception:
        return False


_last_start_error = ""


def get_last_start_error() -> str:
    """Return the error message from the last failed server start."""
    return _last_start_error


def start_server(model_path: str = "") -> bool:
    """Start the Live2D server process. Returns True if successful.
    On failure, sets _last_start_error with diagnostic info.
    """
    global _server_process, _server_running, _last_start_error

    if _is_server_alive():
        _server_running = True
        return True

    # Pre-flight: check dependencies are importable
    try:
        import live2d.v3  # noqa: F401
    except ImportError:
        _last_start_error = "live2d-py is not installed. Run: pip install live2d-py"
        print(f"[Live2D] {_last_start_error}")
        return False
    try:
        import PySide6.QtWidgets  # noqa: F401
    except ImportError:
        _last_start_error = "PySide6 is not installed. Run: pip install PySide6"
        print(f"[Live2D] {_last_start_error}")
        return False

    server_script = os.path.join(_current_dir, "live2d_server.py")
    python_exe = sys.executable

    log_dir = os.path.join(_current_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "live2d_server.log")

    try:
        log_file = open(log_path, "a", encoding="utf-8")
        log_file.write(f"\n[{datetime.datetime.now()}] Live2D server starting (Python: {python_exe})\n")
        log_file.flush()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [python_exe, server_script]
        if model_path:
            cmd.extend(["--model", model_path])

        _server_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            env=env,
            shell=False,
        )

        # Quick crash check: wait 2 seconds, see if process died immediately
        for _ in range(2):
            time.sleep(1)
            exit_code = _server_process.poll()
            if exit_code is not None:
                log_file.close()
                _last_start_error = _read_log_tail(log_path)
                if not _last_start_error:
                    _last_start_error = f"Server process exited immediately with code {exit_code}"
                _server_process = None
                print(f"[Live2D] Server crashed on startup:\n{_last_start_error}")
                return False

        # Wait up to 10 more seconds for the server to be ready
        max_wait_remaining = 13
        for i in range(max_wait_remaining):
            exit_code = _server_process.poll()
            if exit_code is not None:
                log_file.close()
                _last_start_error = _read_log_tail(log_path)
                if not _last_start_error:
                    _last_start_error = f"Server process exited with code {exit_code}"
                _server_process = None
                print(f"[Live2D] Server exited during startup:\n{_last_start_error}")
                return False

            time.sleep(1)
            if _is_server_alive():
                _server_running = True
                return True

        # Timeout — kill the process
        try:
            _server_process.terminate()
            _server_process.wait(timeout=3)
        except Exception:
            pass
        _server_process = None
        log_file.close()
        _last_start_error = f"Server startup timed out after 15s. Log tail:\n{_read_log_tail(log_path)}"
        print(f"[Live2D] {_last_start_error}")
        return False

    except Exception as e:
        log_file.close()
        _last_start_error = f"Failed to start server: {e}"
        print(f"[Live2D] {_last_start_error}")
        _server_running = False
        return False


def _read_log_tail(log_path: str) -> str:
    """Read the last 20 lines of the server log."""
    try:
        if not os.path.exists(log_path):
            return "(log file not found)"
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-20:]).rstrip()
    except Exception as e:
        return f"(could not read log: {e})"


def stop_server():
    """Gracefully stop the Live2D server."""
    global _server_process, _server_running

    client = _get_client()
    try:
        client.shutdown()
    except Exception:
        pass

    reset_client()

    if _server_process:
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.terminate()
        _server_process = None

    _server_running = False


def _ensure_server() -> bool:
    """Ensure the server is running, starting it if needed."""
    global _server_running

    if _server_running and _is_server_alive():
        return True

    with _init_lock:
        if _server_running and _is_server_alive():
            return True
        return start_server()


def call_live2d(action: str, **kwargs) -> dict:
    """Main entry point for all Live2D operations.

    Args:
        action: One of health_check, load_model, unload_model, set_emotion,
                set_parameter, play_motion, set_lipsync,
                show_window, hide_window, set_window_position, set_window_alpha, set_window_size,
                get_status, list_models, shutdown.
        **kwargs: Action-specific parameters (see live2d_server.py for details).

    Returns:
        dict with at least {"success": bool, "message": str}.
    """
    if not _ensure_server():
        err = get_last_start_error()
        detail = f": {err}" if err else ""
        return {"success": False, "message": f"Live2D server is not running and could not be started{detail}"}

    client = _get_client()

    # Map action to client method
    method_map = {
        "health_check": lambda: client.health_check(),
        "load_model": lambda: client.load_model(
            kwargs.get("model_path", ""),
            kwargs.get("model_name", ""),
        ),
        "unload_model": lambda: client.unload_model(),
        "set_emotion": lambda: client.set_emotion(
            kwargs.get("emotion", "neutral"),
            float(kwargs.get("intensity", 1.0)),
        ),
        "set_parameter": lambda: client.set_parameter(
            kwargs.get("parameter", ""),
            float(kwargs.get("value", 0.0)),
            float(kwargs.get("weight", 1.0)),
        ),
        "play_motion": lambda: client.play_motion(
            kwargs.get("group", kwargs.get("motion", "")),
            int(kwargs.get("index", 0)),
            int(kwargs.get("priority", 3)),
        ),
        "set_lipsync": lambda: client.set_lipsync(
            float(kwargs.get("rms_volume", 0.0)),
        ),
        "set_window_size": lambda: client.set_window_size(
            int(kwargs.get("width", 400)),
            int(kwargs.get("height", 500)),
        ),
        "show_window": lambda: client.show_window(),
        "hide_window": lambda: client.hide_window(),
        "set_window_position": lambda: client.set_window_position(
            int(kwargs.get("x", 100)),
            int(kwargs.get("y", 100)),
        ),
        "set_window_alpha": lambda: client.set_window_alpha(
            float(kwargs.get("alpha", 1.0)),
        ),
        "get_status": lambda: client.get_status(),
        "list_models": lambda: client.list_models(),
        "shutdown": lambda: client.shutdown(),
    }

    handler = method_map.get(action)
    if handler is None:
        return {"success": False, "message": f"Unknown action: {action}"}

    try:
        return handler()
    except Exception as e:
        return {"success": False, "message": str(e)}


def call_live2d_cli():
    """CLI entry point for quick testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Live2D control CLI")
    parser.add_argument("action", help="Action to perform")
    parser.add_argument("--model", default="", help="Model path or directory")
    parser.add_argument("--emotion", default="neutral")
    parser.add_argument("--intensity", type=float, default=1.0)
    parser.add_argument("--parameter", default="")
    parser.add_argument("--value", type=float, default=0.0)
    parser.add_argument("--rms", type=float, default=0.0)
    parser.add_argument("--x", type=int, default=100)
    parser.add_argument("--y", type=int, default=100)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--enabled", type=bool, default=False)
    parser.add_argument("--start-server", action="store_true")

    args = parser.parse_args()

    if args.start_server:
        ok = start_server(args.model)
        print(f"Server start: {'OK' if ok else 'FAILED'}")
        return

    result = call_live2d(
        action=args.action,
        model_path=args.model,
        emotion=args.emotion,
        intensity=args.intensity,
        parameter=args.parameter,
        value=args.value,
        rms_volume=args.rms,
        x=args.x,
        y=args.y,
        alpha=args.alpha,
        enabled=args.enabled,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    call_live2d_cli()
