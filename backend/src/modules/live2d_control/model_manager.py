"""Live2D model manager — thread-safe wrapper around live2d-py LAppModel."""

import os
import threading
import logging

try:
    from .emotion_mapping import get_emotion_params, list_emotions
    from .lipsync_processor import LipSyncProcessor
except ImportError:
    from emotion_mapping import get_emotion_params, list_emotions  # type: ignore[no-redef]
    from lipsync_processor import LipSyncProcessor  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


class ModelManager:
    """Thread-safe Live2D model controller.

    Owns the LAppModel instance and exposes all operations under a lock.
    Both the Qt render thread (paintGL) and TCP handler threads access this.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._model = None
        self._model_path = ""
        self._model_loaded = False
        self._current_emotion = "neutral"
        self._lipsync = LipSyncProcessor()
        # Window state (written by TCP thread, read by Qt thread)
        self.window_visible = True
        self.window_x = 100
        self.window_y = 100
        self.window_alpha = 1.0
        self._win_width = 400
        self._win_height = 500
        self._pending_window_actions = []

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def load_model(self, model_path: str) -> str:
        """Load a Live2D model from a .model3.json file path or directory.

        Returns error message on failure, empty string on success.
        """
        try:
            import live2d.v3 as live2d_v3
        except ImportError:
            return "live2d-py package is not installed. Run: pip install live2d-py"

        # Resolve path: if a directory is given, look for *.model3.json inside
        if os.path.isdir(model_path):
            candidates = []
            for f in os.listdir(model_path):
                if f.endswith(".model3.json"):
                    candidates.append(os.path.join(model_path, f))
            if not candidates:
                return f"No .model3.json file found in directory: {model_path}"
            model_path = candidates[0]

        if not os.path.exists(model_path):
            return f"Model file not found: {model_path}"

        with self._lock:
            if self._model is not None:
                self._unload_locked()

            try:
                self._model = live2d_v3.LAppModel()
                self._model.LoadModelJson(model_path)
                self._model.Resize(self._win_width, self._win_height)
                self._model.SetAutoBlinkEnable(True)
                self._model.SetAutoBreathEnable(True)
                self._model_path = model_path
                self._model_loaded = True
                self._current_emotion = "neutral"
                logger.info(f"Live2D model loaded: {model_path}")
                return ""
            except Exception as e:
                self._model = None
                self._model_loaded = False
                logger.error(f"Failed to load Live2D model: {e}")
                return f"Failed to load model: {e}"

    def _unload_locked(self):
        """Unload current model. Caller must hold _lock."""
        if self._model is not None:
            try:
                del self._model
            except Exception:
                pass
            self._model = None
        self._model_loaded = False
        self._model_path = ""
        self._current_emotion = "neutral"
        self._lipsync.reset()

    def unload_model(self) -> str:
        with self._lock:
            if not self._model_loaded:
                return "No model is currently loaded."
            self._unload_locked()
            logger.info("Live2D model unloaded")
            return ""

    # ------------------------------------------------------------------
    # Emotion
    # ------------------------------------------------------------------

    def set_emotion(self, emotion: str, intensity: float = 1.0) -> str:
        """Apply an emotion preset to the model. intensity: 0.0–1.0."""
        if emotion.lower() not in list_emotions():
            return f"Unknown emotion '{emotion}'. Available: {', '.join(list_emotions())}"

        intensity = max(0.0, min(1.0, intensity))
        params = get_emotion_params(emotion)

        with self._lock:
            if not self._model_loaded:
                return "No model loaded. Use load_model first."

            for param_id, (target, weight) in params.items():
                effective_weight = weight * intensity
                if effective_weight > 0:
                    self._model.SetParameterValue(param_id, target, effective_weight)

            self._current_emotion = emotion
            logger.info(f"Live2D emotion set: {emotion} (intensity={intensity:.1f})")
            return ""

    # ------------------------------------------------------------------
    # Parameters (direct control)
    # ------------------------------------------------------------------

    def set_parameter(self, param_id: str, value: float, weight: float = 1.0) -> str:
        """Set a single Live2D parameter directly."""
        try:
            from .config import VALID_PARAMS
        except ImportError:
            from config import VALID_PARAMS  # type: ignore[no-redef]

        if param_id not in VALID_PARAMS:
            return f"Unknown parameter '{param_id}'. Valid: {', '.join(sorted(VALID_PARAMS))}"

        with self._lock:
            if not self._model_loaded:
                return "No model loaded. Use load_model first."
            self._model.SetParameterValue(param_id, float(value), float(weight))
            return ""

    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------

    def play_motion(self, group: str = "", index: int = 0, priority: int = 3) -> str:
        """Start a motion from the given group."""
        with self._lock:
            if not self._model_loaded:
                return "No model loaded. Use load_model first."

            try:
                if group:
                    self._model.StartMotion(group, int(index), int(priority))
                else:
                    self._model.StartRandomMotion(group, int(priority))
                return ""
            except Exception as e:
                return f"Failed to start motion: {e}"

    def get_motion_groups(self) -> list:
        with self._lock:
            if not self._model_loaded:
                return []
            try:
                return self._model.GetMotionGroups()
            except Exception:
                return []

    # ------------------------------------------------------------------
    # Lip sync
    # ------------------------------------------------------------------

    def set_lipsync(self, rms_volume: float) -> str:
        """Feed RMS volume (0.0–1.0) to drive mouth movement."""
        with self._lock:
            if not self._model_loaded:
                return "No model loaded. Use load_model first."

            mouth_val = self._lipsync.update(float(rms_volume))
            self._model.SetParameterValue("ParamMouthOpenY", mouth_val, 1.0)
            return ""

    def reset_lipsync(self):
        with self._lock:
            self._lipsync.reset()
            if self._model_loaded:
                self._model.SetParameterValue("ParamMouthOpenY", 0.0, 1.0)

    # ------------------------------------------------------------------
    # Render (called by Qt main thread — acquires lock briefly)
    # ------------------------------------------------------------------

    def render_model(self):
        """Render one frame. Called by Canvas.Draw() callback on the Qt thread.

        The Canvas handles all OpenGL state (viewport, clear, blend, FBO compositing).
        This method only performs Cubism-level calls.
        """
        with self._lock:
            if not self._model_loaded:
                return
            try:
                import live2d.v3 as live2d_v3
                live2d_v3.clearBuffer()
                self._model.Update()
                self._model.Draw()
            except Exception as e:
                logger.error(f"Live2D render error: {e}")

    def resize(self, width: int, height: int):
        self._win_width = width
        self._win_height = height
        with self._lock:
            if self._model_loaded:
                try:
                    self._model.Resize(width, height)
                except Exception as e:
                    logger.error(f"Live2D resize error: {e}")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        with self._lock:
            return {
                "model_loaded": self._model_loaded,
                "model_path": self._model_path,
                "emotion": self._current_emotion,
                "window_visible": self.window_visible,
                "window_position": [self.window_x, self.window_y],
                "window_alpha": self.window_alpha,
                "motion_groups": (self._model.GetMotionGroups() if self._model_loaded and self._model else []),
            }
