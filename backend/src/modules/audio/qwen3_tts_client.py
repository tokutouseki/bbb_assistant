#!/usr/bin/env python3
"""Qwen3-TTS TCP client — communicates with qwen3_tts_worker via JSON + \\nEOF\\n protocol."""

import socket
import json
import time

TTS_HOST = "127.0.0.1"
TTS_PORT = 5004
CLIENT_TIMEOUT = 120


class Qwen3TTSClient:
    def __init__(self, host: str = TTS_HOST, port: int = TTS_PORT, timeout: int = CLIENT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_socket = None

    def connect(self) -> bool:
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
        if not self.client_socket:
            return {"success": False, "error": "Not connected"}

        try:
            payload = json.dumps(request, ensure_ascii=False) + "\nEOF\n"
            self.client_socket.sendall(payload.encode("utf-8"))

            response_data = b""
            while True:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    self.close()
                    return {"success": False, "error": "Server closed connection"}
                response_data += chunk
                if b"\nEOF\n" in response_data:
                    break

            response_data = response_data.replace(b"\nEOF\n", b"")
            return json.loads(response_data.decode("utf-8"))

        except (ConnectionResetError, ConnectionAbortedError):
            self.close()
            return {"success": False, "error": "Connection reset"}
        except socket.timeout:
            self.close()
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            self.close()
            return {"success": False, "error": str(e)}

    def send_with_reconnect(self, request: dict, max_retries: int = 3) -> dict:
        result = None
        for retry in range(max_retries):
            if not self.client_socket:
                if not self.connect():
                    if retry < max_retries - 1:
                        time.sleep(1)
                        continue
                    return {"success": False, "error": "Failed to connect to TTS worker"}

            result = self.send(request)
            if result.get("success", False):
                return result

            if retry < max_retries - 1:
                time.sleep(1)

        return result or {"success": False, "error": "Max retries exceeded"}

    # ---- Convenience methods ----

    def health_check(self) -> dict:
        return self.send_with_reconnect({"action": "health_check"})

    def generate(self, text: str, ref_audio: str, language: str = "Chinese",
                 ref_text: str = "") -> dict:
        return self.send_with_reconnect({
            "action": "generate",
            "text": text,
            "ref_audio": ref_audio,
            "language": language,
            "ref_text": ref_text,
        })

    def generate_and_play(self, text: str, ref_audio: str, language: str = "Chinese",
                          ref_text: str = "") -> dict:
        return self.send_with_reconnect({
            "action": "generate_and_play",
            "text": text,
            "ref_audio": ref_audio,
            "language": language,
            "ref_text": ref_text,
        })

    def play_audio(self, filepath: str) -> dict:
        return self.send_with_reconnect({
            "action": "play_audio",
            "filepath": filepath,
        })

    def warmup(self) -> dict:
        return self.send_with_reconnect({"action": "warmup"})

    def shutdown(self) -> dict:
        return self.send_with_reconnect({"action": "shutdown"})
