#!/usr/bin/env python3
"""Interactive Live2D emotion debugger.

Usage:
    python debug_emotion.py [--model PATH]

Launches the Live2D server with the given model, then provides a CLI menu
to switch emotions, tweak parameters, play motions, and adjust lip sync in
real time.  Useful for tuning the emotion_mapping.py presets.

Commands (type at prompt):
    1-7           — apply emotion: 1=neutral 2=happy 3=sad 4=angry
                    5=surprised 6=love 7=sleepy
    e <name> <i>  — set emotion with intensity 0.0–1.0, e.g. "e happy 0.5"
    p <id> <v>    — set raw parameter, e.g. "p ParamMouthOpenY 0.8"
    m <group>     — play motion from group, e.g. "m TapBody"
    mg            — list available motion groups
    l <rms>       — set lip-sync RMS, e.g. "l 0.5"
    a <alpha>     — set window opacity 0.0–1.0
    s             — print current status
    h             — print this help
    q             — quit (shuts down server too)
"""

import sys
import os
import time

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_dir)))))

from src.modules.live2d_control import call_live2d, start_server, stop_server

EMOTIONS = ["neutral", "happy", "sad", "angry", "surprised", "love", "sleepy"]


def print_help():
    print("""
  1=neutral  2=happy  3=sad    4=angry
  5=surprised  6=love   7=sleepy

  e <name> <i>  — emotion with intensity  (e happy 0.8)
  p <id> <v>    — raw parameter           (p ParamMouthOpenY 0.5)
  m <group>     — play motion             (m TapBody)
  mg             — list motion groups
  l <rms>        — lip-sync RMS            (l 0.3)
  a <alpha>      — window opacity          (a 0.8)
  s               — print status
  h               — help
  q               — quit
""")


def main():
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--model", default="", help="Path to model directory or .model3.json")
    args = parser.parse_args()

    # Start server
    print("Starting Live2D server...")
    ok = start_server(args.model)
    if not ok:
        print("FAILED to start server. Check logs at:")
        print(f"  {os.path.join(_current_dir, 'logs', 'live2d_server.log')}")
        sys.exit(1)

    time.sleep(1)

    # Load model if provided
    if args.model:
        res = call_live2d("load_model", model_path=args.model)
        print(f"load_model: {res.get('message', res)}")

    print_help()

    while True:
        try:
            cmd = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        parts = cmd.split()
        head = parts[0].lower()

        # Numeric emotion shortcut
        if head in ("1", "2", "3", "4", "5", "6", "7"):
            emotion = EMOTIONS[int(head) - 1]
            res = call_live2d("set_emotion", emotion=emotion, intensity=1.0)
            print(f"  emotion={emotion} → {res.get('message', res)}")

        elif head == "e" and len(parts) >= 2:
            emotion = parts[1]
            intensity = float(parts[2]) if len(parts) >= 3 else 1.0
            res = call_live2d("set_emotion", emotion=emotion, intensity=intensity)
            print(f"  emotion={emotion} i={intensity:.1f} → {res.get('message', res)}")

        elif head == "p" and len(parts) >= 3:
            param = parts[1]
            value = float(parts[2])
            weight = float(parts[3]) if len(parts) >= 4 else 1.0
            res = call_live2d("set_parameter", parameter=param, value=value, weight=weight)
            print(f"  {param}={value} w={weight:.1f} → {res.get('message', res)}")

        elif head == "m":
            group = parts[1] if len(parts) >= 2 else ""
            res = call_live2d("play_motion", group=group)
            print(f"  motion group={group} → {res.get('message', res)}")

        elif head == "mg":
            res = call_live2d("get_status")
            if res.get("success"):
                groups = res.get("status", {}).get("motion_groups", [])
                print(f"  motion groups: {groups}")
            else:
                print(f"  FAILED: {res.get('message')}")

        elif head == "l" and len(parts) >= 2:
            rms = float(parts[1])
            res = call_live2d("set_lipsync", rms_volume=rms)
            print(f"  rms={rms:.2f} → {res.get('message', res)}")

        elif head == "a" and len(parts) >= 2:
            alpha = float(parts[1])
            res = call_live2d("set_window_alpha", alpha=alpha)
            print(f"  alpha={alpha:.2f} → {res.get('message', res)}")

        elif head == "s":
            res = call_live2d("get_status")
            if res.get("success"):
                s = res["status"]
                print(f"""  model_loaded:    {s.get('model_loaded')}
  emotion:         {s.get('emotion')}
  window_visible:  {s.get('window_visible')}
  window_pos:      {s.get('window_position')}
  window_alpha:    {s.get('window_alpha')}
  motion_groups:   {s.get('motion_groups')}""")
            else:
                print(f"  FAILED: {res.get('message')}")

        elif head in ("h", "help", "?"):
            print_help()

        elif head in ("q", "quit", "exit"):
            break

        else:
            print(f"  Unknown: {cmd}  (type h for help)")

    # Shutdown
    print("Stopping...")
    res = call_live2d("shutdown")
    print(f"  {res.get('message', res)}")
    stop_server()
    print("Done.")


if __name__ == "__main__":
    main()
