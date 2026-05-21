#!/usr/bin/env python3
"""Live2D TCP client — communicates with live2d_server via JSON + \\nEOF\\n protocol.

Modeled after yolo_client.py. Supports automatic reconnection and timeout handling.
"""

import socket
import json
import time

try:
    from .config import LIVE2D_HOST, LIVE2D_PORT, CLIENT_TIMEOUT
except ImportError:
    from config import LIVE2D_HOST, LIVE2D_PORT, CLIENT_TIMEOUT  # type: ignore[no-redef]


class Live2DClient:
    """Persistent TCP client for the Live2D server."""

    def __init__(self, host: str = LIVE2D_HOST, port: int = LIVE2D_PORT, timeout: int = CLIENT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_socket: socket.socket | None = None

    def connect(self) -> bool:
        """Connect to the Live2D server."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.timeout)
            self.client_socket.connect((self.host, self.port))
            return True
        except Exception:
            return False

    def close(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None

    def send(self, request: dict) -> dict:
        """Send a request and return the response. Closes socket on error."""
        if not self.client_socket:
            return {"success": False, "message": "Not connected"}

        try:
            payload = json.dumps(request, ensure_ascii=False) + "\nEOF\n"
            self.client_socket.sendall(payload.encode("utf-8"))

            response_data = b""
            while True:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    self.close()
                    return {"success": False, "message": "Server closed connection"}
                response_data += chunk
                if b"\nEOF\n" in response_data:
                    break

            response_data = response_data.replace(b"\nEOF\n", b"")
            return json.loads(response_data.decode("utf-8"))

        except (ConnectionResetError, ConnectionAbortedError):
            self.close()
            return {"success": False, "message": "Connection reset"}
        except socket.timeout:
            self.close()
            return {"success": False, "message": "Request timed out"}
        except Exception as e:
            self.close()
            return {"success": False, "message": str(e)}

    def send_with_reconnect(self, request: dict, max_retries: int = 3) -> dict:
        """Send a request, automatically reconnecting if necessary."""
        result = None
        for retry in range(max_retries):
            if not self.client_socket:
                if not self.connect():
                    if retry < max_retries - 1:
                        time.sleep(1)
                        continue
                    return {"success": False, "message": "Failed to connect to Live2D server"}

            result = self.send(request)
            if result.get("success", False):
                return result

            if retry < max_retries - 1:
                time.sleep(1)

        return result or {"success": False, "message": "Max retries exceeded"}

    # ------------------------------------------------------------------
    # Convenience methods for each action
    # ------------------------------------------------------------------

    def health_check(self) -> dict:
        return self.send_with_reconnect({"action": "health_check"})

    def load_model(self, model_path: str = "", model_name: str = "") -> dict:
        return self.send_with_reconnect({
            "action": "load_model",
            "model_path": model_path,
            "model_name": model_name,
        })

    def unload_model(self) -> dict:
        return self.send_with_reconnect({"action": "unload_model"})

    def set_emotion(self, emotion: str, intensity: float = 1.0) -> dict:
        return self.send_with_reconnect({
            "action": "set_emotion",
            "emotion": emotion,
            "intensity": intensity,
        })

    def set_parameter(self, parameter: str, value: float, weight: float = 1.0) -> dict:
        return self.send_with_reconnect({
            "action": "set_parameter",
            "parameter": parameter,
            "value": value,
            "weight": weight,
        })

    def play_motion(self, group: str = "", index: int = 0, priority: int = 3) -> dict:
        return self.send_with_reconnect({
            "action": "play_motion",
            "group": group,
            "index": index,
            "priority": priority,
        })

    def set_lipsync(self, rms_volume: float) -> dict:
        return self.send_with_reconnect({
            "action": "set_lipsync",
            "rms_volume": rms_volume,
        })

    def set_window_size(self, width: int, height: int) -> dict:
        return self.send_with_reconnect({
            "action": "set_window_size",
            "width": width,
            "height": height,
        })

    def show_window(self) -> dict:
        return self.send_with_reconnect({"action": "show_window"})

    def hide_window(self) -> dict:
        return self.send_with_reconnect({"action": "hide_window"})

    def set_window_position(self, x: int, y: int) -> dict:
        return self.send_with_reconnect({
            "action": "set_window_position",
            "x": x,
            "y": y,
        })

    def set_window_alpha(self, alpha: float) -> dict:
        return self.send_with_reconnect({
            "action": "set_window_alpha",
            "alpha": alpha,
        })

    def get_status(self) -> dict:
        return self.send_with_reconnect({"action": "get_status"})

    def list_models(self) -> dict:
        return self.send_with_reconnect({"action": "list_models"})

    def shutdown(self) -> dict:
        return self.send_with_reconnect({"action": "shutdown"})
