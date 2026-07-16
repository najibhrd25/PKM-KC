"""
Definisi terpusat semua event yang lewat di Event Bus.

Pakai konstanta ini, jangan string mentah, supaya typo ketahuan
saat import (bukan saat runtime).
"""

# ---- Event dari sensor / detektor (INPUT) ----
IR_READING      = "ir_reading"       # IR Sensor   -> bus
FIRE_DETECTED   = "fire_detected"    # YOLO        -> bus
FIRE_CLEARED    = "fire_cleared"     # YOLO        -> bus (api hilang dari frame)

# ---- Event perintah dari Orchestrator (COMMAND) ----
TRACK_START     = "track_start"      # Orchestrator -> Tracking
TRACK_STOP      = "track_stop"       # Orchestrator -> Tracking
SERVO_CMD       = "servo_cmd"        # Tracking     -> Servo
SERVO_HOME      = "servo_home"       # Orchestrator -> Servo
SERVO_STOP      = "servo_stop"       # Orchestrator -> Servo
AUDIO_CMD       = "audio_cmd"        # Orchestrator -> DAC (mulai pemadaman)
AUDIO_STOP      = "audio_stop"       # Orchestrator -> DAC

# ---- Event status (NOTIFIKASI, untuk logging / dashboard) ----
STATE_CHANGED   = "state_changed"    # Orchestrator -> siapa saja
TARGET_LOCKED   = "target_locked"    # Tracking     -> Orchestrator
EXTINGUISH_DONE = "extinguish_done"  # Orchestrator -> siapa saja

# ---- Event antarmuka web (OPSIONAL, tepi sistem) ----
FRAME_UPDATE    = "frame_update"     # YOLO        -> WebBridge (stream MJPEG)
SET_MODE        = "set_mode"         # WebBridge   -> Orchestrator (AUTO/MANUAL)
SERVO_JOG       = "servo_jog"        # WebBridge   -> Servo (joystick inkremental)
MODE_CHANGED    = "mode_changed"     # Orchestrator -> WebBridge (notifikasi mode)
