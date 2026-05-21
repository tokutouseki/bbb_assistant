"""Emotion → Live2D parameter mapping.

Maps 7 discrete emotions to standard Cubism parameter deltas.
Each emotion is a dict of {ParamID: (value, weight)} applied via SetParameterValue.
"""

try:
    from .config import (
        PARAM_MOUTH_OPEN_Y, PARAM_EYE_L_OPEN, PARAM_EYE_R_OPEN,
        PARAM_BROW_L_Y, PARAM_BROW_R_Y,
        PARAM_ANGLE_X, PARAM_ANGLE_Y, PARAM_ANGLE_Z,
        PARAM_BODY_ANGLE_X, PARAM_EYE_BALL_X, PARAM_EYE_BALL_Y,
    )
except ImportError:
    from config import (  # type: ignore[no-redef]
        PARAM_MOUTH_OPEN_Y, PARAM_EYE_L_OPEN, PARAM_EYE_R_OPEN,
        PARAM_BROW_L_Y, PARAM_BROW_R_Y,
        PARAM_ANGLE_X, PARAM_ANGLE_Y, PARAM_ANGLE_Z,
        PARAM_BODY_ANGLE_X, PARAM_EYE_BALL_X, PARAM_EYE_BALL_Y,
    )

# Each entry: {ParamID: (target_value, blend_weight)}
# Target values are ABSOLUTE (0.0–1.0 for most params, -30–30 for angles).
# Weights control how strongly the value is applied (0.0–1.0).

EMOTION_MAP = {
    "neutral": {
        # Reset everything to defaults
        PARAM_MOUTH_OPEN_Y: (0.0, 1.0),
        PARAM_EYE_L_OPEN: (1.0, 1.0),
        PARAM_EYE_R_OPEN: (1.0, 1.0),
        PARAM_BROW_L_Y: (0.0, 1.0),
        PARAM_BROW_R_Y: (0.0, 1.0),
        PARAM_ANGLE_X: (0.0, 1.0),
        PARAM_ANGLE_Y: (0.0, 1.0),
        PARAM_ANGLE_Z: (0.0, 1.0),
        PARAM_BODY_ANGLE_X: (0.0, 1.0),
        PARAM_EYE_BALL_X: (0.0, 1.0),
        PARAM_EYE_BALL_Y: (0.0, 1.0),
    },
    "happy": {
        PARAM_MOUTH_OPEN_Y: (0.4, 1.0),
        PARAM_EYE_L_OPEN: (0.8, 1.0),
        PARAM_EYE_R_OPEN: (0.8, 1.0),
        PARAM_BROW_L_Y: (-0.3, 1.0),
        PARAM_BROW_R_Y: (-0.3, 1.0),
        PARAM_ANGLE_Z: (3.0, 0.5),
    },
    "sad": {
        PARAM_MOUTH_OPEN_Y: (0.0, 1.0),
        PARAM_EYE_L_OPEN: (0.6, 1.0),
        PARAM_EYE_R_OPEN: (0.6, 1.0),
        PARAM_BROW_L_Y: (0.4, 1.0),
        PARAM_BROW_R_Y: (0.4, 1.0),
        PARAM_ANGLE_Z: (5.0, 0.5),
        PARAM_ANGLE_X: (-5.0, 0.5),
    },
    "angry": {
        PARAM_MOUTH_OPEN_Y: (0.1, 1.0),
        PARAM_EYE_L_OPEN: (0.8, 1.0),
        PARAM_EYE_R_OPEN: (0.8, 1.0),
        PARAM_BROW_L_Y: (0.6, 1.0),
        PARAM_BROW_R_Y: (0.6, 1.0),
        PARAM_ANGLE_X: (3.0, 0.5),
    },
    "surprised": {
        PARAM_MOUTH_OPEN_Y: (0.6, 1.0),
        PARAM_EYE_L_OPEN: (1.0, 1.0),
        PARAM_EYE_R_OPEN: (1.0, 1.0),
        PARAM_BROW_L_Y: (-0.5, 1.0),
        PARAM_BROW_R_Y: (-0.5, 1.0),
        PARAM_ANGLE_X: (-3.0, 0.5),
    },
    "love": {
        PARAM_MOUTH_OPEN_Y: (0.15, 1.0),
        PARAM_EYE_L_OPEN: (0.7, 1.0),
        PARAM_EYE_R_OPEN: (0.7, 1.0),
        PARAM_BROW_L_Y: (-0.1, 1.0),
        PARAM_BROW_R_Y: (-0.1, 1.0),
        PARAM_ANGLE_Z: (-5.0, 0.5),
    },
    "sleepy": {
        PARAM_MOUTH_OPEN_Y: (0.05, 1.0),
        PARAM_EYE_L_OPEN: (0.2, 1.0),
        PARAM_EYE_R_OPEN: (0.2, 1.0),
        PARAM_BROW_L_Y: (0.1, 1.0),
        PARAM_BROW_R_Y: (0.1, 1.0),
        PARAM_ANGLE_Z: (3.0, 0.3),
    },
}


def get_emotion_params(emotion: str) -> dict:
    """Return {ParamID: (value, weight)} for the given emotion name.
    Falls back to 'neutral' for unknown emotions.
    """
    return EMOTION_MAP.get(emotion.lower(), EMOTION_MAP["neutral"])


def list_emotions() -> list:
    return list(EMOTION_MAP.keys())
