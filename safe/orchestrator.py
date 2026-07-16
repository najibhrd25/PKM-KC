"""
orchestrator.py — Otak S.A.F.E

Tidak mengontrol hardware langsung. Tugasnya:
    1. Mendengarkan event sensor (ir_reading) dan detektor (fire_detected,
       fire_cleared) dari Event Bus.
    2. Menjalankan fusi sensor + state machine.
    3. Menerbitkan perintah (track_start, audio_cmd, servo_home, dst.).
    4. Menegakkan aturan keamanan: durasi pemadaman & cooldown.

Semua keputusan terpusat di sini, sehingga modul lain tetap "bodoh" dan
mudah diuji secara terpisah.
"""

import time
import threading
import logging

from core.event_bus import EventBus
from core.state_machine import State
from core import events, config

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, bus: EventBus):
        self._bus = bus
        self._state = State.IDLE
        self._lock = threading.Lock()

        # cache pembacaan terakhir
        self._ir_readings: dict[int, dict] = {}
        self._last_detection: dict | None = None
        self._fire_present = False

        # penanda waktu untuk timeout & cooldown
        self._pre_alarm_since: float | None = None
        self._extinguish_since: float | None = None
        self._cooldown_until: float = 0.0

        self._running = False
        self._timer_thread: threading.Thread | None = None

        # mode operasi: "auto" (default) atau "manual"
        self._mode = "auto"

        # subscribe event masuk
        self._bus.subscribe(events.IR_READING, self._on_ir)
        self._bus.subscribe(events.FIRE_DETECTED, self._on_fire_detected)
        self._bus.subscribe(events.FIRE_CLEARED, self._on_fire_cleared)
        self._bus.subscribe(events.TARGET_LOCKED, self._on_target_locked)
        self._bus.subscribe(events.SET_MODE, self._on_set_mode)

    # ======================= LIFECYCLE =======================
    def start(self):
        self._running = True
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        logger.info("Orchestrator berjalan. State awal: %s", self._state.value)

    def stop(self):
        self._running = False
        if self._timer_thread:
            self._timer_thread.join(timeout=2.0)
        # pastikan aktuator aman saat shutdown
        self._bus.publish(events.AUDIO_STOP, {})
        self._bus.publish(events.TRACK_STOP, {})
        self._bus.publish(events.SERVO_HOME, {})

    # ======================= TRANSISI STATE =======================
    def _transition(self, new_state: State):
        with self._lock:
            if new_state == self._state:
                return
            old = self._state
            self._state = new_state
            logger.info("STATE: %s -> %s", old.value, new_state.value)
            self._bus.publish(events.STATE_CHANGED,
                              {"old": old.value, "new": new_state.value})
            self._on_enter_state(new_state)

    def _on_enter_state(self, state: State):
        """Aksi yang dijalankan tepat saat memasuki sebuah state."""
        now = time.time()
        if state == State.PRE_ALARM:
            self._pre_alarm_since = now

        elif state == State.TRACKING:
            self._pre_alarm_since = None
            if self._last_detection:
                self._bus.publish(events.TRACK_START, {
                    "bbox": self._last_detection["bbox"],
                    "frame_w": self._last_detection["frame_w"],
                    "frame_h": self._last_detection["frame_h"],
                })

        elif state == State.EXTINGUISHING:
            self._extinguish_since = now
            self._bus.publish(events.AUDIO_CMD, {
                "freq": config.AUDIO_DEFAULT_FREQ,
                "amplitude": config.AMPLITUDE_MAX_SAFE,
                "duration": config.AUDIO_MAX_DURATION,
            })

        elif state == State.EVALUATING:
            self._bus.publish(events.AUDIO_STOP, {})

        elif state == State.COOLDOWN:
            self._cooldown_until = now + config.AUDIO_COOLDOWN
            self._bus.publish(events.TRACK_STOP, {})
            self._bus.publish(events.SERVO_HOME, {})
            self._bus.publish(events.EXTINGUISH_DONE, {})

        elif state == State.IDLE:
            self._last_detection = None
            self._fire_present = False
            self._bus.publish(events.SERVO_HOME, {})

    # ======================= HANDLER EVENT =======================
    def _on_ir(self, data: dict):
        self._ir_readings[data["sensor_id"]] = data
        self._evaluate_fusion()

    def _on_fire_detected(self, data: dict):
        self._last_detection = data
        self._fire_present = True
        self._evaluate_fusion()

    def _on_fire_cleared(self, data: dict):
        self._fire_present = False
        # jika sedang evaluasi dan api hilang -> berhasil padam
        if self._state == State.EVALUATING:
            self._transition(State.COOLDOWN)

    def _on_target_locked(self, data: dict):
        if self._state == State.TRACKING:
            self._transition(State.EXTINGUISHING)

    def _on_set_mode(self, data: dict):
        """Switch AUTO <-> MANUAL dari WebBridge (atau heartbeat timeout)."""
        mode = data.get("mode", "auto")
        self._mode = mode
        if mode == "manual":
            # hentikan operasi otomatis yang sedang berjalan demi keamanan
            self._bus.publish(events.AUDIO_STOP, {})
            self._bus.publish(events.TRACK_STOP, {})
            self._transition(State.MANUAL)
        else:
            # safety: matikan audio manual sebelum kembali ke otomatis
            self._bus.publish(events.AUDIO_STOP, {})
            self._transition(State.IDLE)   # kembali siaga otomatis
        self._bus.publish(events.MODE_CHANGED, {"mode": mode})

    # ======================= LOGIKA FUSI SENSOR =======================
    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, value))

    @staticmethod
    def _ir_pos(index):
        """Posisi sudut ternormalisasi sensor ke-index dalam [-1, +1].

        5 sensor -> [-1, -0.5, 0, +0.5, +1]. Dibalik bila IR_REVERSE (urutan
        sensor mirror terhadap sumbu-x kamera).
        """
        n = config.N_IR
        pos = (index - (n - 1) / 2) / ((n - 1) / 2)
        return -pos if config.IR_REVERSE else pos

    def _compute_fusion(self) -> dict:
        """Gabungkan panas IR + deteksi kamera menjadi status keputusan.

        Di-port dari fuse() di Program/train_yolo/step3_fusion_monitor.py:
        deteksi diferensial IR, arah IR (centroid berbobot), arah kamera,
        cek kesepakatan arah, dan skor gabungan.
        """
        n = config.N_IR
        raws = [self._ir_readings.get(i + 1, {}).get("raw", 0) for i in range(n)]

        ir_hot, ir_conf, ir_x = False, 0.0, None
        if any(raws):
            idx_max = raws.index(max(raws))
            others = raws[:idx_max] + raws[idx_max + 1:]
            avg_others = sum(others) / len(others) if others else 0.0
            selisih = raws[idx_max] - avg_others
            ir_hot = selisih >= config.IR_DIFF_THRESHOLD
            ir_conf = self._clamp(selisih / config.IR_CONF_SCALE, 0.0, 1.0)
            # arah IR: centroid berbobot sensor di atas rata-rata
            mean_raw = sum(raws) / len(raws)
            weights = [max(0.0, r - mean_raw) for r in raws]
            wsum = sum(weights)
            if wsum > 0:
                ir_x = sum(self._ir_pos(i) * w for i, w in enumerate(weights)) / wsum

        # sisi kamera
        cam_present = self._last_detection is not None
        cam_conf = self._last_detection.get("confidence", 0.0) if cam_present else 0.0
        cam_x = None
        if cam_present:
            bbox = self._last_detection["bbox"]        # [cx, cy, w, h]
            fw = self._last_detection["frame_w"]
            cam_x = (bbox[0] - fw / 2) / (fw / 2)

        # kesepakatan arah (hanya bila kedua arah tersedia)
        if cam_x is not None and ir_x is not None:
            agree = (cam_x * ir_x >= 0) or (abs(cam_x - ir_x) <= config.AGREE_TOL)
        else:
            agree = True   # info kurang -> jangan penalti

        fused = config.W_IR * ir_conf + config.W_CAM * cam_conf
        if not agree:
            fused *= config.DISAGREE_PENALTY
        fused = self._clamp(fused, 0.0, 1.0)

        visual = cam_present and cam_conf >= config.YOLO_CONF_THRESHOLD
        fire_confirmed = ir_hot and visual and fused >= config.FUSED_THRESHOLD

        return {
            "ir_hot": ir_hot, "ir_x": ir_x, "cam_present": cam_present,
            "cam_x": cam_x, "agree": agree, "fused": fused,
            "visual": visual, "fire_confirmed": fire_confirmed,
        }

    def _evaluate_fusion(self):
        # mode manual: fusi dijeda. Event tetap ter-cache untuk dashboard,
        # tapi tidak memicu transisi state.
        if self._mode == "manual":
            return

        # masih cooldown -> abaikan trigger baru
        if time.time() < self._cooldown_until:
            return

        f = self._compute_fusion()

        if self._state == State.IDLE and f["ir_hot"]:
            self._transition(State.PRE_ALARM)

        elif self._state == State.PRE_ALARM:
            if f["fire_confirmed"]:
                self._transition(State.TRACKING)
            elif not f["ir_hot"]:
                self._transition(State.IDLE)   # alarm palsu
            elif not f["cam_present"] and f["ir_x"] is not None:
                # ir-seek: kamera belum lihat api, geser yaw pelan ke arah IR
                self._bus.publish(events.SERVO_JOG, {
                    "d_yaw": f["ir_x"] * config.FALLBACK_YAW_GAIN,
                    "d_pitch": 0.0,
                })

    # ======================= TIMER (timeout & evaluasi) =======================
    def _timer_loop(self):
        while self._running:
            now = time.time()

            # timeout pre-alarm: IR memicu tapi visual tak kunjung konfirmasi
            if (self._state == State.PRE_ALARM and
                    self._pre_alarm_since and
                    now - self._pre_alarm_since > config.PRE_ALARM_TIMEOUT):
                logger.info("Pre-alarm timeout — tidak ada konfirmasi visual.")
                self._transition(State.IDLE)

            # durasi pemadaman habis -> evaluasi
            if (self._state == State.EXTINGUISHING and
                    self._extinguish_since and
                    now - self._extinguish_since >= config.AUDIO_MAX_DURATION):
                self._transition(State.EVALUATING)

            # setelah jeda evaluasi, putuskan ulang
            if self._state == State.EVALUATING:
                time.sleep(config.EVAL_RECHECK_DELAY)
                if self._fire_present:
                    self._transition(State.TRACKING)   # ulang pemadaman
                else:
                    self._transition(State.COOLDOWN)

            # cooldown selesai -> kembali siaga
            if self._state == State.COOLDOWN and now >= self._cooldown_until:
                self._transition(State.IDLE)

            time.sleep(0.1)