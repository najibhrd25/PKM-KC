"""
ServoActuator — adapter Event Bus -> Dynamixel MX-106 (driver _servo_driver.py).
Driver asli (Servo.py) tidak diubah.

Pengiriman goal memakai pola dari Program/train_yolo/step5_fusion_scan.py:
GroupSyncWrite TX-only (2 servo dalam 1 paket, tanpa tunggu status) dan
rate-limit ke config.SERVO_MAX_HZ. Kecepatan servo di-set SEKALI saat setup.
Ini mencegah I/O serial mem-block loop pemanggil (sumber lag saat scanning).

State sudut (self._yaw/_pitch) dibagi antara servo_cmd (absolut, dari Tracking)
dan servo_jog (inkremental, dari WebBridge) supaya keduanya tidak saling timpa.

Batas fisik (config): yaw & pitch center 180°, jangkauan ±45° (135-225°).
"""
import time
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
        self._gsw = None                # GroupSyncWrite goal position
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._last_send = 0.0
        self._send_interval = 1.0 / config.SERVO_MAX_HZ
        self._torque_on = False
        self._last_pub = None           # (yaw, pitch, torque) terakhir di-publish

        self._bus.subscribe(events.SERVO_CMD,  self._on_cmd)
        self._bus.subscribe(events.SERVO_HOME, self._on_home)
        self._bus.subscribe(events.SERVO_STOP, self._on_stop)
        self._bus.subscribe(events.SERVO_JOG,  self._on_jog)

    # ======================= LIFECYCLE =======================
    def start(self):
        self._port, self._pkt = drv.init_dynamixel()
        for sid in (drv.ID_X, drv.ID_Y):
            drv.set_torque(self._port, self._pkt, sid, 1)
            drv.set_joint_mode(self._port, self._pkt, sid)
            # set profil kecepatan SEKALI (bukan tiap goal)
            self._pkt.write2ByteTxRx(self._port, sid,
                                     drv.ADDR_MOVING_SPEED, config.SERVO_SPEED)
        self._gsw = drv.GroupSyncWrite(self._port, self._pkt,
                                       drv.ADDR_GOAL_POSITION, 2)
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._ready = True
        self._torque_on = True
        self._send_goals(force=True)
        self._publish_state()
        logger.info("ServoActuator siap (GroupSyncWrite, %.0f Hz).", config.SERVO_MAX_HZ)

    def stop(self):
        if self._ready:
            self._go_neutral()
            with self._lock:
                for sid in (drv.ID_X, drv.ID_Y):
                    drv.set_torque(self._port, self._pkt, sid, 0)
                self._port.closePort()
            self._ready = False
            self._torque_on = False

    # ======================= PENGIRIMAN GOAL =======================
    def _send_goals(self, force=False):
        """Kirim yaw+pitch via GroupSyncWrite (TX-only), rate-limited."""
        if not self._ready or self._gsw is None:
            return
        with self._lock:
            now = time.time()
            if not force and now - self._last_send < self._send_interval:
                return
            self._last_send = now
            self._gsw.clearParam()
            for sid, angle in ((drv.ID_X, self._yaw), (drv.ID_Y, self._pitch)):
                pos = drv.angle_to_position(angle)
                self._gsw.addParam(sid, [drv.DXL_LOBYTE(pos), drv.DXL_HIBYTE(pos)])
            self._gsw.txPacket()

    def _ensure_torque(self):
        """Nyalakan kembali torque bila sebelumnya dimatikan (servo_stop)."""
        if self._torque_on or not self._ready:
            return
        with self._lock:
            for sid in (drv.ID_X, drv.ID_Y):
                drv.set_torque(self._port, self._pkt, sid, 1)
        self._torque_on = True

    def _publish_state(self):
        """Publish servo_state hanya bila ada perubahan (hindari banjir SSE)."""
        cur = (self._yaw, self._pitch, self._torque_on)
        if cur == self._last_pub:
            return
        self._last_pub = cur
        self._bus.publish(events.SERVO_STATE, {
            "yaw_deg": self._yaw, "pitch_deg": self._pitch,
            "torque": self._torque_on})

    # ======================= HANDLER EVENT =======================
    def _on_cmd(self, data):
        if not self._ready:
            return
        self._ensure_torque()
        self._yaw = self._clamp(float(data["yaw_deg"]), config.YAW_MIN, config.YAW_MAX)
        self._pitch = self._clamp(float(data["pitch_deg"]), config.PITCH_MIN, config.PITCH_MAX)
        self._send_goals()
        self._publish_state()

    def _on_jog(self, data):
        """Joystick inkremental dari WebBridge (atau ir-seek orchestrator)."""
        if not self._ready:
            return
        self._ensure_torque()
        self._yaw = self._clamp(self._yaw + float(data.get("d_yaw", 0.0)),
                                config.YAW_MIN, config.YAW_MAX)
        self._pitch = self._clamp(self._pitch + float(data.get("d_pitch", 0.0)),
                                  config.PITCH_MIN, config.PITCH_MAX)
        self._send_goals()
        self._publish_state()

    def _on_home(self, data):
        self._ensure_torque()
        self._go_neutral()

    def _on_stop(self, data):
        if self._ready:
            with self._lock:
                for sid in (drv.ID_X, drv.ID_Y):
                    drv.set_torque(self._port, self._pkt, sid, 0)
            self._torque_on = False
            self._publish_state()

    def _go_neutral(self):
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._send_goals(force=True)   # home selalu dikirim, abaikan rate-limit
        self._publish_state()

    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, value))
