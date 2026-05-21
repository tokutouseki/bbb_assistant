"""Live2D SubAgent module.

Provides:
- call_live2d(action, **kwargs) — main entry point for Agent tool calls
- start_server(model_path) / stop_server() — lifecycle control
- Live2DClient — low-level TCP client (for direct use)

Architecture:
    Agent (@tool live2d_control)
        → call_live2d()
            → Live2DClient (TCP JSON + \\nEOF\\n, port 5003)
                → live2d_server.py (Qt window + LAppModel)
"""

from .call_live2d import call_live2d, start_server, stop_server, get_last_start_error
from .live2d_client import Live2DClient
