"""
ServoActuator — adapter Event Bus -> Dynamixel MX-106 (driver _servo_driver.py).
Driver asli (Servo.py) tidak diubah.

Batas fisik dari proposal:
    Yaw  (ID 1): 0-180°, netral 90°  (90° kiri / 90° kanan)
    Pitch (ID 2): 50-140°, netral 70° (20° atas / 70° bawah)
    * Nilai pitch dikalibrasi ulang setelah perakitan mekanik.
"""
import threading
import logging

from core.interfaces import BaseActuator
from core import events, config
from actuation import _servo_driver as drv   # = Servo.py lama

logger = logging.getLogger(__name__)


class ServoActuator(BaseActuator):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._lock = threading.Lock()   # Dynamixel bus tidak thread-safe
        self._ready = False
        self._port = None
        self._pkt = None

        # posisi terakhir untuk jog inkremental dari joystick dashboard
        self._current_yaw = config.YAW_NEUTRAL
        self._current_pitch = config.PITCH_NEUTRAL

        self._bus.subscribe(events.SERVO_CMD,  self._on_cmd)
        self._bus.subscribe(events.SERVO_HOME, self._on_home)
        self._bus.subscribe(events.SERVO_STOP, self._on_stop)
        self._bus.subscribe(events.SERVO_JOG,  self._on_jog)

    def start(self):
        self._port, self._pkt = drv.init_dynamixel()
        for sid in (drv.ID_X, drv.ID_Y):
            drv.set_torque(self._port, self._pkt, sid, 1)
            drv.set_joint_mode(self._port, self._pkt, sid)
        self._go_neutral()
        self._ready = True
        logger.info("ServoActuator siap.")

    def stop(self):
        if self._ready:
            self._go_neutral()
            for sid in (drv.ID_X, drv.ID_Y):
                drv.set_torque(self._port, self._pkt, sid, 0)
            self._port.closePort()
            self._ready = False

    def _on_cmd(self, data):
        if not self._ready:
            return
        yaw = max(config.YAW_MIN,   min(config.YAW_MAX,   float(data["yaw_deg"])))
        pitch = max(config.PITCH_MIN, min(config.PITCH_MAX, float(data["pitch_deg"])))
        self._current_yaw = yaw
        self._current_pitch = pitch
        with self._lock:
            drv.move_to_angle(self._port, self._pkt, drv.ID_X, yaw)
            drv.move_to_angle(self._port, self._pkt, drv.ID_Y, pitch)

    def _on_home(self, data):
        self._current_yaw = config.YAW_NEUTRAL
        self._current_pitch = config.PITCH_NEUTRAL
        self._go_neutral()

    def _on_stop(self, data):
        if self._ready:
            with self._lock:
                for sid in (drv.ID_X, drv.ID_Y):
                    drv.set_torque(self._port, self._pkt, sid, 0)

    def _on_jog(self, data):
        """Joystick inkremental dari dashboard — geser servo sebesar delta."""
        if not self._ready:
            return
        d_yaw = float(data.get("d_yaw", 0.0))
        d_pitch = float(data.get("d_pitch", 0.0))

        self._current_yaw   = max(config.YAW_MIN,   min(config.YAW_MAX,   self._current_yaw + d_yaw))
        self._current_pitch = max(config.PITCH_MIN, min(config.PITCH_MAX, self._current_pitch + d_pitch))

        with self._lock:
            drv.move_to_angle(self._port, self._pkt, drv.ID_X, self._current_yaw)
            drv.move_to_angle(self._port, self._pkt, drv.ID_Y, self._current_pitch)

    def _go_neutral(self):
        with self._lock:
            drv.move_to_angle(self._port, self._pkt, drv.ID_X, config.YAW_NEUTRAL)
            drv.move_to_angle(self._port, self._pkt, drv.ID_Y, config.PITCH_NEUTRAL)
