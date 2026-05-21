"""Live2D module configuration — ports, paths, window defaults, standard parameter IDs."""

import os

LIVE2D_HOST = '127.0.0.1'
LIVE2D_PORT = 5003

_current_dir = os.path.dirname(os.path.abspath(__file__))
_modules_dir = os.path.dirname(_current_dir)
_src_dir = os.path.dirname(_modules_dir)
_backend_dir = os.path.dirname(_src_dir)
_project_root = os.path.dirname(_backend_dir)

DEFAULT_MODEL_DIR = os.path.join(_backend_dir, "data", "models", "live2d")

# Directories to scan for Live2D models when listing available models
MODEL_SEARCH_DIRS = [
    DEFAULT_MODEL_DIR,
]

SERVER_LOG_DIR = os.path.join(_current_dir, "logs")

# Position persistence
WINDOW_STATE_FILE = os.path.join(_current_dir, "window_state.json")

# Window defaults
DEFAULT_WINDOW_WIDTH = 400
DEFAULT_WINDOW_HEIGHT = 500
DEFAULT_WINDOW_ALPHA = 1.0
DEFAULT_WINDOW_X = 100
DEFAULT_WINDOW_Y = 100

# Standard Live2D Cubism parameter IDs
PARAM_MOUTH_OPEN_Y = "ParamMouthOpenY"
PARAM_EYE_L_OPEN = "ParamEyeLOpen"
PARAM_EYE_R_OPEN = "ParamEyeROpen"
PARAM_BROW_L_Y = "ParamBrowLY"
PARAM_BROW_R_Y = "ParamBrowRY"
PARAM_ANGLE_X = "ParamAngleX"
PARAM_ANGLE_Y = "ParamAngleY"
PARAM_ANGLE_Z = "ParamAngleZ"
PARAM_BODY_ANGLE_X = "ParamBodyAngleX"
PARAM_BODY_ANGLE_Y = "ParamBodyAngleY"
PARAM_BODY_ANGLE_Z = "ParamBodyAngleZ"
PARAM_EYE_BALL_X = "ParamEyeBallX"
PARAM_EYE_BALL_Y = "ParamEyeBallY"
PARAM_BREATH = "ParamBreath"

VALID_PARAMS = {
    PARAM_MOUTH_OPEN_Y, PARAM_EYE_L_OPEN, PARAM_EYE_R_OPEN,
    PARAM_BROW_L_Y, PARAM_BROW_R_Y,
    PARAM_ANGLE_X, PARAM_ANGLE_Y, PARAM_ANGLE_Z,
    PARAM_BODY_ANGLE_X, PARAM_BODY_ANGLE_Y, PARAM_BODY_ANGLE_Z,
    PARAM_EYE_BALL_X, PARAM_EYE_BALL_Y, PARAM_BREATH,
}

CLIENT_TIMEOUT = 60
