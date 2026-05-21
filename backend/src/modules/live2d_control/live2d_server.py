#!/usr/bin/env python3
"""Live2D TCP server — manages Qt window + Live2D model, accepts JSON/\nEOF\n commands.

Usage:
    python live2d_server.py [--host 127.0.0.1] [--port 5003] [--model MODEL_PATH]

Protocol (all JSON + \\nEOF\\n):

    Request:  {"action": "<action>", ...params}
    Response: {"success": true/false, "message": "...", ...data}

Actions:
    health_check          — check server status
    load_model            — load a Live2D model (params: model_path, model_name)
    unload_model          — unload current model
    set_emotion           — set emotion (params: emotion, intensity)
    set_parameter         — set a single parameter (params: parameter, value, weight)
    play_motion           — start a motion (params: motion, group, index, priority, fade_in)
    set_lipsync           — drive mouth from RMS volume (params: rms_volume)
    show_window / hide_window — show/hide
    set_window_position   — move window (params: x, y)
    set_window_alpha      — change opacity (params: alpha 0-1)
    get_status            — return current model/window state
    shutdown              — close server and window
"""

import sys
import os
import json
import time
import socket
import threading
import logging
import argparse

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger(__name__)

# Ensure the parent directory is importable
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from .config import LIVE2D_HOST, LIVE2D_PORT, DEFAULT_MODEL_DIR, CLIENT_TIMEOUT, MODEL_SEARCH_DIRS
    from .model_manager import ModelManager
except ImportError:
    # Running as standalone script — use absolute imports
    from config import LIVE2D_HOST, LIVE2D_PORT, DEFAULT_MODEL_DIR, CLIENT_TIMEOUT, MODEL_SEARCH_DIRS  # type: ignore[no-redef]
    from model_manager import ModelManager  # type: ignore[no-redef]


def _scan_available_models() -> list:
    """Scan configured directories for .model3.json files.
    Returns a list of dicts with name, path, and directory.
    """
    result = []
    seen_paths = set()
    try:
        from .config import MODEL_SEARCH_DIRS as _search_dirs
    except ImportError:
        from config import MODEL_SEARCH_DIRS as _search_dirs  # type: ignore[no-redef]
    for search_dir in _search_dirs:
        if not os.path.isdir(search_dir):
            continue
        for entry in os.listdir(search_dir):
            entry_path = os.path.join(search_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            for f in os.listdir(entry_path):
                if f.endswith(".model3.json"):
                    full_path = os.path.join(entry_path, f)
                    if full_path in seen_paths:
                        continue
                    seen_paths.add(full_path)
                    result.append({
                        "name": entry,
                        "path": full_path,
                        "directory": entry_path,
                    })
                    break  # One model per directory
    return result


class Live2DServerApp:
    """Top-level application: owns QApplication, window, model manager, TCP server."""

    def __init__(self, host: str = LIVE2D_HOST, port: int = LIVE2D_PORT):
        self.host = host
        self.port = port
        self.manager = ModelManager()
        self.window = None
        self.app = None
        self._running = False
        self._server_socket: socket.socket | None = None

    def run(self, auto_load_model: str = ""):
        """Start Qt event loop and TCP server. Blocks until window closes."""
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QTimer
            try:
                from .qt_window import Live2DWidget
            except ImportError:
                from qt_window import Live2DWidget  # type: ignore[no-redef]
        except ImportError as e:
            logger.error(f"PySide6 is required: {e}")
            print("ERROR: PySide6 is not installed. Run: pip install PySide6")
            sys.exit(1)

        # Must be set before QApplication is created
        os.environ.setdefault("QT_QPA_PLATFORM", "windows")

        # live2d.init() MUST be called before QApplication (sets up DLL paths etc.)
        import live2d.v3 as live2d_v3
        live2d_v3.init()

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.window = Live2DWidget(self.manager)
        self.window.show()

        # Auto-load model if specified
        if auto_load_model:
            err = self.manager.load_model(auto_load_model)
            if err:
                logger.warning(f"Auto-load model failed: {err}")
            else:
                # Resize GL widget to match model's native size
                self.window.resize(400, 500)

        # Start TCP server in daemon thread
        tcp_thread = threading.Thread(target=self._run_tcp_server, daemon=True)
        tcp_thread.start()

        self._running = True
        logger.info(f"Live2D server running on {self.host}:{self.port}")

        exit_code = self.app.exec()

        # Cleanup
        self._running = False
        self.manager.unload_model()
        logger.info("Live2D server stopped")
        sys.exit(exit_code)

    # ------------------------------------------------------------------
    # TCP server (runs in daemon thread)
    # ------------------------------------------------------------------

    def _run_tcp_server(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(2.0)
            logger.info(f"TCP server listening on {self.host}:{self.port}")

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
            logger.error(f"TCP server error: {e}")
        finally:
            if self._server_socket:
                try:
                    self._server_socket.close()
                except Exception:
                    pass

    def invoke_on_qt(self, func):
        """Schedule a callable on the Qt main thread (thread-safe).

        Uses signal emission which Qt automatically queues across threads.
        """
        if self.window:
            self.window.invoke_signal.emit(func)

    def stop(self):
        self._running = False
        if self.app:
            self.app.quit()


class ClientHandler(threading.Thread):
    """Handle one TCP client connection."""

    def __init__(self, client_socket: socket.socket, client_addr, server: Live2DServerApp):
        super().__init__()
        self.sock = client_socket
        self.addr = client_addr
        self.server = server
        self.sock.settimeout(CLIENT_TIMEOUT)

    def run(self):
        logger.info(f"Live2D client connected: {self.addr}")
        try:
            while self.server._running:
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
                    self._send({"success": False, "message": "Invalid JSON"})
                    continue

                response = self._handle(request)
                self._send(response)
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            try:
                self.sock.close()
            except Exception:
                pass
            logger.info(f"Live2D client disconnected: {self.addr}")

    def _send(self, data: dict):
        try:
            payload = json.dumps(data, ensure_ascii=False) + "\nEOF\n"
            self.sock.sendall(payload.encode("utf-8"))
        except Exception as e:
            logger.error(f"Send error: {e}")

    def _handle(self, req: dict) -> dict:
        action = req.get("action", req.get("health_check", ""))
        if not action or action is True:
            action = "health_check"

        try:
            if action == "health_check":
                return {
                    "success": True,
                    "message": "Live2D server running",
                    "timestamp": time.time(),
                    "status": self.server.manager.get_status(),
                }

            elif action == "load_model":
                model_path = req.get("model_path", "")
                model_name = req.get("model_name", "")
                if not model_path and model_name:
                    model_path = os.path.join(DEFAULT_MODEL_DIR, model_name)
                if not model_path:
                    return {"success": False, "message": "model_path or model_name required"}

                # MUST run on Qt main thread — LoadModelJson creates GL resources
                result_event = threading.Event()
                result_data = {}

                def _load_on_qt():
                    result_data["err"] = self.server.manager.load_model(model_path)
                    if not result_data["err"]:
                        self.server.window.resize(400, 500)
                    result_event.set()

                self.server.invoke_on_qt(_load_on_qt)
                if not result_event.wait(timeout=30):
                    return {"success": False, "message": "Model load timed out"}
                err = result_data.get("err", "Unknown error")
                if err:
                    return {"success": False, "message": err}
                return {"success": True, "message": f"Model loaded: {model_path}"}

            elif action == "unload_model":
                # MUST run on Qt main thread — GL resources need to be freed there
                result_event = threading.Event()
                result_data = {}

                def _unload_on_qt():
                    result_data["err"] = self.server.manager.unload_model()
                    result_event.set()

                self.server.invoke_on_qt(_unload_on_qt)
                if not result_event.wait(timeout=30):
                    return {"success": False, "message": "Model unload timed out"}
                err = result_data.get("err", "Unknown error")
                if err:
                    return {"success": False, "message": err}
                return {"success": True, "message": "Model unloaded"}

            elif action == "set_emotion":
                emotion = req.get("emotion", "neutral")
                intensity = float(req.get("intensity", 1.0))
                result_event = threading.Event()
                result_data = {}
                self.server.invoke_on_qt(lambda: (
                    result_data.setdefault("err", self.server.manager.set_emotion(emotion, intensity)),
                    result_event.set()
                ) or None)
                if not result_event.wait(timeout=10):
                    return {"success": False, "message": "Emotion set timed out"}
                err = result_data.get("err", "")
                if err:
                    return {"success": False, "message": err}
                return {"success": True, "message": f"Emotion set: {emotion}"}

            elif action == "set_parameter":
                param = req.get("parameter", "")
                value = float(req.get("value", 0.0))
                weight = float(req.get("weight", 1.0))
                result_event = threading.Event()
                result_data = {}
                self.server.invoke_on_qt(lambda: (
                    result_data.setdefault("err", self.server.manager.set_parameter(param, value, weight)),
                    result_event.set()
                ) or None)
                if not result_event.wait(timeout=10):
                    return {"success": False, "message": "Parameter set timed out"}
                err = result_data.get("err", "")
                if err:
                    return {"success": False, "message": err}
                return {"success": True, "message": f"Parameter set: {param}={value}"}

            elif action == "play_motion":
                group = req.get("group", req.get("motion", ""))
                index = int(req.get("index", 0))
                priority = int(req.get("priority", 3))
                result_event = threading.Event()
                result_data = {}
                self.server.invoke_on_qt(lambda: (
                    result_data.setdefault("err", self.server.manager.play_motion(group, index, priority)),
                    result_event.set()
                ) or None)
                if not result_event.wait(timeout=10):
                    return {"success": False, "message": "Motion start timed out"}
                err = result_data.get("err", "")
                if err:
                    return {"success": False, "message": err}
                return {"success": True, "message": "Motion started"}

            elif action == "set_lipsync":
                rms = float(req.get("rms_volume", 0.0))
                result_event = threading.Event()
                result_data = {}
                self.server.invoke_on_qt(lambda: (
                    result_data.setdefault("err", self.server.manager.set_lipsync(rms)),
                    result_event.set()
                ) or None)
                if not result_event.wait(timeout=10):
                    return {"success": False, "message": "LipSync set timed out"}
                err = result_data.get("err", "")
                if err:
                    return {"success": False, "message": err}
                return {"success": True, "message": f"LipSync RMS: {rms:.3f}"}

            elif action == "set_window_size":
                width = int(req.get("width", 400))
                height = int(req.get("height", 500))
                width = max(200, min(2000, width))
                height = max(200, min(2000, height))
                def _resize():
                    self.server.window.resize(width, height)
                    self.server.manager.resize(width, height)
                self.server.invoke_on_qt(_resize)
                return {"success": True, "message": f"Window resized to {width}x{height}"}

            elif action == "show_window":
                self.server.invoke_on_qt(
                    lambda: self.server.window.show_requested.emit()
                )
                return {"success": True, "message": "Window shown"}

            elif action == "hide_window":
                self.server.invoke_on_qt(
                    lambda: self.server.window.hide_requested.emit()
                )
                return {"success": True, "message": "Window hidden"}

            elif action == "set_window_position":
                x = int(req.get("x", 100))
                y = int(req.get("y", 100))
                self.server.invoke_on_qt(
                    lambda: self.server.window.move_requested.emit(x, y)
                )
                return {"success": True, "message": f"Window moved to ({x}, {y})"}

            elif action == "set_window_alpha":
                alpha = float(req.get("alpha", 1.0))
                alpha = max(0.0, min(1.0, alpha))
                self.server.invoke_on_qt(
                    lambda: self.server.window.alpha_requested.emit(alpha)
                )
                return {"success": True, "message": f"Window alpha: {alpha:.2f}"}

            elif action == "list_models":
                return {
                    "success": True,
                    "message": "Available models",
                    "models": _scan_available_models(),
                }

            elif action == "get_status":
                return {
                    "success": True,
                    "status": self.server.manager.get_status(),
                }

            elif action == "shutdown":
                def _shutdown():
                    self.server.stop()
                self.server.invoke_on_qt(_shutdown)
                return {"success": True, "message": "Shutting down"}

            else:
                return {"success": False, "message": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Action '{action}' error: {e}")
            return {"success": False, "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Live2D TCP Server")
    parser.add_argument("--host", default=LIVE2D_HOST)
    parser.add_argument("--port", type=int, default=LIVE2D_PORT)
    parser.add_argument("--model", default="", help="Path to .model3.json or directory")
    args = parser.parse_args()

    # stdout encoding for Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("Live2D Server")
    print("=" * 60)
    print(f"Listen: {args.host}:{args.port}")
    if args.model:
        print(f"Model: {args.model}")
    print("=" * 60)

    server = Live2DServerApp(host=args.host, port=args.port)
    server.run(auto_load_model=args.model)


if __name__ == "__main__":
    main()
