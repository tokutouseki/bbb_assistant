"""Lip-sync processor — RMS volume → ParamMouthOpenY with exponential smoothing.

Supports two modes:
1. Direct RMS injection: set_lipsync(rms_volume) → smoothed mouth value
2. Audio file analysis: process_audio(audio_path) → sampled RMS over time
"""

import math
import struct
import wave
from collections import deque


class LipSyncProcessor:
    """Computes smoothed mouth-open values from RMS audio volume."""

    def __init__(self, alpha: float = 0.3, history_size: int = 5):
        """
        Args:
            alpha: Exponential smoothing factor (0–1). Higher = more responsive.
            history_size: Number of recent values to keep for trend analysis.
        """
        self.alpha = alpha
        self._smoothed = 0.0
        self._history = deque(maxlen=history_size)

    def update(self, rms_volume: float) -> float:
        """Feed a new RMS volume value (0.0–1.0), return smoothed mouth-open value."""
        # Clamp input
        rms = max(0.0, min(1.0, rms_volume))
        # Exponential moving average
        self._smoothed = self.alpha * rms + (1.0 - self.alpha) * self._smoothed
        self._history.append(self._smoothed)
        return self._smoothed

    def reset(self):
        """Reset the smoother state."""
        self._smoothed = 0.0
        self._history.clear()

    @property
    def current_value(self) -> float:
        return self._smoothed

    @staticmethod
    def compute_rms(audio_samples: bytes, sample_width: int = 2) -> float:
        """Compute RMS volume from raw PCM audio samples.

        Args:
            audio_samples: Raw PCM bytes.
            sample_width: Bytes per sample (1=uint8, 2=int16, 4=int32).

        Returns:
            Normalized RMS value (0.0–1.0).
        """
        if not audio_samples:
            return 0.0

        fmt = {1: "B", 2: "h", 4: "i"}.get(sample_width, "h")
        max_val = float((1 << (sample_width * 8 - 1)) - 1)

        try:
            count = len(audio_samples) // sample_width
            samples = struct.unpack(f"<{count}{fmt}", audio_samples)
        except struct.error:
            return 0.0

        if not samples:
            return 0.0

        sum_sq = sum(float(s) ** 2 for s in samples)
        rms = math.sqrt(sum_sq / len(samples))
        return min(1.0, rms / max_val)

    @classmethod
    def from_wav_file(cls, wav_path: str) -> list:
        """Read a WAV file and return a list of (time_sec, rms_value) tuples.

        Each tuple represents ~50ms of audio, suitable for driving lip-sync
        at ~20 fps.
        """
        results = []
        try:
            with wave.open(wav_path, 'rb') as wf:
                sample_rate = wf.get_framerate()
                sample_width = wf.getsampwidth()
                channels = wf.getnchannels()
                total_frames = wf.getnframes()

                # Process in chunks of ~50ms
                chunk_frames = int(sample_rate * 0.05)
                t = 0.0

                while t * sample_rate < total_frames:
                    raw = wf.readframes(chunk_frames)
                    if not raw:
                        break
                    rms = cls.compute_rms(raw, sample_width)
                    results.append((t, rms))
                    t += 0.05

        except Exception:
            pass

        return results
