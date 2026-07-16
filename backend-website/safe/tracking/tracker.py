"""
TrackingLogic — ubah posisi bounding box di frame menjadi sudut servo
absolut (yaw, pitch), lalu publish servo_cmd.

Pendekatan: proportional centering. Error piksel dari pusat frame
dipetakan ke koreksi sudut. Sudut absolut = netral + koreksi terakumulasi.
"""
import logging

from core.interfaces import BaseModule
from core import events, config

logger = logging.getLogger(__name__)


class TrackingLogic(BaseModule):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._active = False
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._bus.subscribe(events.TRACK_START, self._on_start)
        self._bus.subscribe(events.TRACK_STOP, self._on_stop)
        self._bus.subscribe(events.FIRE_DETECTED, self._on_detection)

    def start(self):
        logger.info("TrackingLogic siap.")

    def stop(self):
        self._active = False

    def _on_start(self, data):
        self._active = True
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._on_detection(data)

    def _on_stop(self, data):
        self._active = False

    def _on_detection(self, data):
        """Konversi bbox -> koreksi sudut -> servo_cmd."""
        if not self._active:
            return
        cx, cy, _, _ = data["bbox"]
        fw, fh = data["frame_w"], data["frame_h"]

        # error piksel dari pusat frame, dinormalisasi ke [-1, 1]
        err_x = (cx - fw / 2) / (fw / 2)
        err_y = (cy - fh / 2) / (fh / 2)

        # koreksi proporsional (gain dari config)
        self._yaw   += err_x * config.YAW_GAIN_DEG
        self._pitch += err_y * config.PITCH_GAIN_DEG

        # clamp ke batas fisik
        self._yaw   = max(config.YAW_MIN,   min(config.YAW_MAX,   self._yaw))
        self._pitch = max(config.PITCH_MIN, min(config.PITCH_MAX, self._pitch))

        self._bus.publish(events.SERVO_CMD, {
            "yaw_deg": self._yaw,
            "pitch_deg": self._pitch,
        })

        # beri tahu Orchestrator kalau sudah cukup terpusat
        err_px = ((cx - fw / 2) ** 2 + (cy - fh / 2) ** 2) ** 0.5
        if err_px <= config.TARGET_LOCK_PX:
            self._bus.publish(events.TARGET_LOCKED, {"error_px": err_px})
