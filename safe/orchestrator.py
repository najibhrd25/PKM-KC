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
    def __init__(self, bus: EventBus, detect_mode: str | None = None):
        self._bus = bus
        self._state = State.IDLE
        self._lock = threading.Lock()

        # sensor mana yang dipakai untuk keputusan: "fusion" / "camera" / "ir"
        mode = detect_mode or config.DETECT_MODE
        if mode not in config.VALID_DETECT_MODES:
            logger.warning("DETECT_MODE '%s' tidak dikenal -> pakai 'fusion'.", mode)
            mode = "fusion"
        self._detect_mode = mode
        self._ir_lock_count = 0     # siklus berturut ir_x terpusat (mode "ir")
        self._last_ir_jog = 0.0     # throttle SERVO_JOG dari IR
        self._locked_since: float | None = None   # awal kunci stabil
        self._last_lock: float | None = None      # target_locked terakhir
        self._last_detection_at: float | None = None   # deteksi kamera terakhir
        self._freq_index = 0            # percobaan pemadaman ke-berapa
        self._alarm_since: float | None = None

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
        logger.info("Orchestrator berjalan. Deteksi: %s. State awal: %s",
                    self._detect_mode, self._state.value)

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
            self._ir_lock_count = 0
            self._locked_since = None
            self._last_lock = None
            # Mode "ir": JANGAN aktifkan TrackingLogic. YOLODetector tetap jalan,
            # jadi _last_detection bisa terisi dan TrackingLogic akan ikut menulis
            # SERVO_CMD — bentrok dengan jog berbasis IR.
            if self._detect_mode != "ir" and self._last_detection:
                self._bus.publish(events.TRACK_START, {
                    "bbox": self._last_detection["bbox"],
                    "frame_w": self._last_detection["frame_w"],
                    "frame_h": self._last_detection["frame_h"],
                })

        elif state == State.EXTINGUISHING:
            self._extinguish_since = now
            freq = self._attempt_freq()
            logger.info("Pemadaman percobaan %d/%d @ %.0f Hz",
                        self._freq_index + 1, self._max_attempts(), freq)
            self._freq_index += 1
            self._bus.publish(events.AUDIO_CMD, {
                "freq": freq,
                "amplitude": config.AMPLITUDE_MAX_SAFE,
                "duration": config.AUDIO_MAX_DURATION,
                "waveform": config.AUDIO_WAVEFORM,
                "pulse_waveform": config.PULSE_WAVEFORM,
                "n_cycles": config.PULSE_N_CYCLES,
                "gap": config.PULSE_GAP_SEC,
            })

        elif state == State.EVALUATING:
            self._bus.publish(events.AUDIO_STOP, {})

        elif state == State.ALARM:
            # semua frekuensi gagal: hentikan tracking, turret ke netral,
            # lalu bunyikan sirine sebagai peringatan
            self._alarm_since = now
            self._bus.publish(events.TRACK_STOP, {})
            self._bus.publish(events.SERVO_HOME, {})
            logger.warning("Semua %d percobaan gagal — sirine %.0f detik.",
                           self._max_attempts(), config.ALARM_DURATION)
            self._bus.publish(events.AUDIO_CMD, {
                "waveform": "siren",
                "amplitude": config.AMPLITUDE_MAX_SAFE,
                "duration": config.ALARM_DURATION,
                "f_low": config.ALARM_FREQ_LOW,
                "f_high": config.ALARM_FREQ_HIGH,
                "sweep_period": config.ALARM_SWEEP_PERIOD,
            })

        elif state == State.COOLDOWN:
            self._cooldown_until = now + config.AUDIO_COOLDOWN
            self._bus.publish(events.TRACK_STOP, {})
            self._bus.publish(events.SERVO_HOME, {})
            self._bus.publish(events.EXTINGUISH_DONE, {})

        elif state == State.IDLE:
            self._last_detection = None
            self._fire_present = False
            # engagement selesai -> percobaan berikutnya mulai dari frekuensi awal
            self._freq_index = 0
            self._alarm_since = None
            self._bus.publish(events.SERVO_HOME, {})

    # ======================= HANDLER EVENT =======================
    def _on_ir(self, data: dict):
        self._ir_readings[data["sensor_id"]] = data
        self._evaluate_fusion(ir_sensor_id=data["sensor_id"])

    def _on_fire_detected(self, data: dict):
        self._last_detection = data
        self._last_detection_at = time.time()
        self._fire_present = True
        self._evaluate_fusion()

    def _on_fire_cleared(self, data: dict):
        self._fire_present = False
        # WAJIB: tanpa ini _last_detection tetap berisi bbox lama, sehingga
        # cam_present/visual selamanya True dan sistem tidak pernah tahu
        # apinya sudah hilang.
        self._last_detection = None
        # mode "ir": status padam ditentukan IR (lihat _fire_still_present),
        # bukan kamera yang sedang diabaikan
        if self._detect_mode == "ir":
            return
        # jika sedang evaluasi dan api hilang -> berhasil padam
        if self._state == State.EVALUATING:
            self._transition(State.COOLDOWN)

    # Deteksi kamera datang tiap DETECT_EVERY frame (~2-3 Hz). Jeda antar
    # target_locked lebih lama dari ini dianggap kunci sempat lepas.
    _LOCK_GAP_MAX = 1.0

    def _on_target_locked(self, data: dict):
        """Audio baru menyala setelah terkunci STABIL selama LOCK_SETTLE_SEC."""
        if self._state != State.TRACKING:
            return
        now = time.time()

        # kunci baru, atau kunci lama sempat putus -> mulai hitung dari nol
        if self._last_lock is None or now - self._last_lock > self._LOCK_GAP_MAX:
            self._locked_since = now
        self._last_lock = now

        if now - self._locked_since >= config.LOCK_SETTLE_SEC:
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

        Matematika IR dan kamera SELALU dihitung penuh (dashboard & log tetap
        butuh keduanya). config.DETECT_MODE hanya mengubah baris keputusan di
        akhir: sensor mana yang boleh memicu dan mengkonfirmasi.
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

        visual = cam_present and cam_conf >= config.YOLO_CONF_THRESHOLD

        # ---- keputusan per mode deteksi ----
        if self._detect_mode == "camera":
            agree = True                # tidak ada pembanding -> jangan penalti
            fused = cam_conf
            trigger = visual
            fire_confirmed = visual
        elif self._detect_mode == "ir":
            agree = True
            fused = ir_conf
            trigger = ir_hot
            fire_confirmed = ir_hot
        else:                           # "fusion" — perilaku asli
            fused = config.W_IR * ir_conf + config.W_CAM * cam_conf
            if not agree:
                fused *= config.DISAGREE_PENALTY
            fused = self._clamp(fused, 0.0, 1.0)
            trigger = ir_hot
            fire_confirmed = ir_hot and visual and fused >= config.FUSED_THRESHOLD

        return {
            "ir_hot": ir_hot, "ir_x": ir_x, "cam_present": cam_present,
            "cam_x": cam_x, "agree": agree, "fused": fused,
            "visual": visual, "fire_confirmed": fire_confirmed,
            "trigger": trigger, "mode": self._detect_mode,
        }

    def _jog_toward_ir(self, ir_x: float, gain: float):
        """Geser yaw ke arah panas IR, dibatasi config.IR_JOG_HZ.

        Throttle wajib: _evaluate_fusion dipanggil tiap IR_READING (5 sensor x
        ~10 Hz = ~50 Hz), jadi tanpa batas ini turret langsung menabrak YAW_MAX.
        """
        now = time.time()
        if now - self._last_ir_jog < 1.0 / config.IR_JOG_HZ:
            return
        self._last_ir_jog = now
        self._bus.publish(events.SERVO_JOG, {
            "d_yaw": ir_x * gain,
            "d_pitch": 0.0,
        })

    def _evaluate_fusion(self, ir_sensor_id: int | None = None):
        # ir_sensor_id: sensor pemicu bila panggilan datang dari IR_READING,
        # None bila dari FIRE_DETECTED. Dipakai mode "ir" untuk memutuskan hanya
        # di akhir sapuan.

        # mode manual: fusi dijeda. Event tetap ter-cache untuk dashboard,
        # tapi tidak memicu transisi state.
        if self._mode == "manual":
            return

        # masih cooldown -> abaikan trigger baru
        if time.time() < self._cooldown_until:
            return

        f = self._compute_fusion()
        self._maybe_scan_hint(f, ir_sensor_id)

        if self._detect_mode == "camera":
            self._eval_camera(f)
        elif self._detect_mode == "ir":
            self._eval_ir(f, ir_sensor_id)
        else:
            self._eval_fusion(f)

    def _maybe_scan_hint(self, f: dict, ir_sensor_id: int | None):
        """Terbitkan arah panas IR sebagai PETUNJUK sapuan.

        Sengaja petunjuk, bukan perintah servo: saat IDLE, Scanner adalah pemilik
        tunggal servo_cmd. Kalau Orchestrator ikut mengirim servo_jog, keduanya
        saling menimpa dan turret bergetar.

        Tidak menyentuh keputusan pemadaman sama sekali — itu tetap milik
        _eval_camera / _eval_fusion / _eval_ir sesuai DETECT_MODE.
        """
        if not config.IR_SCAN_GUIDE or self._state != State.IDLE:
            return
        if ir_sensor_id != config.N_IR:      # sekali per sapuan, bukan 50 Hz
            return
        self._bus.publish(events.SCAN_HINT,
                          {"ir_hot": f["ir_hot"], "ir_x": f["ir_x"]})

    def _cam_lost(self, now=None) -> bool:
        """True bila kamera sudah TRACK_LOST_SEC tidak melihat api."""
        if self._last_detection_at is None:
            return True
        return (now or time.time()) - self._last_detection_at > config.TRACK_LOST_SEC

    def _settled(self, now=None) -> bool:
        """True bila sudah cukup lama di PRE_ALARM untuk turret menenangkan diri."""
        if self._pre_alarm_since is None:
            return True
        return (now or time.time()) - self._pre_alarm_since >= config.TRACK_SETTLE_SEC

    def _eval_fusion(self, f: dict):
        """Mode "fusion": IR memicu pre-alarm, kamera mengkonfirmasi."""
        if self._state == State.IDLE and f["ir_hot"]:
            self._transition(State.PRE_ALARM)

        elif self._state == State.PRE_ALARM:
            if f["fire_confirmed"] and self._settled():
                self._transition(State.TRACKING)
            elif not f["ir_hot"]:
                self._transition(State.IDLE)   # alarm palsu
            elif not f["cam_present"] and f["ir_x"] is not None:
                # ir-seek: kamera belum lihat api, geser yaw pelan ke arah IR
                self._jog_toward_ir(f["ir_x"], config.FALLBACK_YAW_GAIN)

    def _eval_camera(self, f: dict):
        """Mode "camera": YOLO satu-satunya pemicu.

        PRE_ALARM dipakai sebagai jeda penenang: begitu api terlihat, sapuan
        Scanner berhenti (state != IDLE) dan turret dibiarkan tenang selama
        TRACK_SETTLE_SEC sebelum tracking mengambil alih. Setelah TRACKING,
        pengarahan sepenuhnya ditangani TrackingLogic.
        """
        if self._state == State.IDLE and f["visual"]:
            self._transition(State.PRE_ALARM)

        elif self._state == State.PRE_ALARM:
            if self._cam_lost():
                self._transition(State.IDLE)      # alarm palsu -> lanjut menyapu
            elif f["visual"] and self._settled():
                self._transition(State.TRACKING)

    def _eval_ir(self, f: dict, ir_sensor_id: int | None = None):
        """Mode "ir": IR satu-satunya pemicu DAN sumber pengarahan.

        Tidak ada bbox, jadi TrackingLogic tidak dipakai (lihat _on_enter_state).
        Turret di-jog ke arah ir_x sampai terpusat beberapa siklus berturut-turut,
        lalu TARGET_LOCKED diterbitkan sendiri. Pitch tidak disentuh: array IR
        horizontal tidak memberi informasi elevasi.
        """
        # Putuskan HANYA di akhir sapuan. Di tengah sapuan sebagian kanal masih
        # berisi nilai sapuan sebelumnya, sehingga ir_hot/ir_x bisa berkedip —
        # di TRACKING itu berarti jatuh ke IDLE dan SERVO_HOME merusak bidikan.
        # (Panggilan dari FIRE_DETECTED punya id None; kamera diabaikan di mode ini.)
        if ir_sensor_id != config.N_IR:
            return

        if self._state == State.IDLE and f["ir_hot"]:
            self._transition(State.TRACKING)

        elif self._state == State.TRACKING:
            if not f["ir_hot"]:
                self._transition(State.IDLE)   # target hilang
            elif f["ir_x"] is not None:
                if abs(f["ir_x"]) <= config.IR_TRACK_TOL:
                    self._ir_lock_count += 1
                    if self._ir_lock_count >= config.IR_LOCK_COUNT:
                        self._bus.publish(events.TARGET_LOCKED,
                                          {"ir_x": f["ir_x"]})
                else:
                    self._ir_lock_count = 0
                    self._jog_toward_ir(f["ir_x"], config.IR_TRACK_YAW_GAIN)

    def _max_attempts(self) -> int:
        """Jatah percobaan pemadaman sebelum menyerah ke ALARM."""
        if config.FREQ_SEQUENCE_ENABLED and config.AUDIO_FREQ_SEQUENCE:
            return len(config.AUDIO_FREQ_SEQUENCE)
        return max(1, config.MAX_ATTEMPTS_FIXED)

    def _attempt_freq(self) -> float:
        """Frekuensi untuk percobaan saat ini.

        Sequence aktif -> elemen ke-_freq_index dari AUDIO_FREQ_SEQUENCE.
        Sequence mati   -> selalu AUDIO_DEFAULT_FREQ.
        """
        seq = config.AUDIO_FREQ_SEQUENCE
        if not config.FREQ_SEQUENCE_ENABLED or not seq:
            return config.AUDIO_DEFAULT_FREQ
        return float(seq[min(self._freq_index, len(seq) - 1)])

    def _freqs_exhausted(self) -> bool:
        """True bila jatah percobaan sudah habis."""
        return self._freq_index >= self._max_attempts()

    def _fire_still_present(self) -> bool:
        """Apakah api masih ada saat EVALUATING, menurut sensor mode aktif."""
        if self._detect_mode == "ir":
            return self._compute_fusion()["ir_hot"]
        return self._fire_present

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

            # target hilang saat TRACKING -> kembali menyapu, jangan diam menunggu.
            # Mode "ir" punya jalannya sendiri di _eval_ir (dan tidak pernah
            # menerima fire_detected), jadi dikecualikan.
            if (self._state == State.TRACKING and self._detect_mode != "ir"
                    and self._cam_lost(now)):
                logger.info("Target hilang %.1f s — kembali ke scanning.",
                            config.TRACK_LOST_SEC)
                self._transition(State.IDLE)

            # durasi pemadaman habis -> evaluasi
            if (self._state == State.EXTINGUISHING and
                    self._extinguish_since and
                    now - self._extinguish_since >= config.AUDIO_MAX_DURATION):
                self._transition(State.EVALUATING)

            # setelah jeda evaluasi, putuskan ulang
            if self._state == State.EVALUATING:
                time.sleep(config.EVAL_RECHECK_DELAY)
                if not self._fire_still_present():
                    self._transition(State.COOLDOWN)          # berhasil padam
                elif not self._freqs_exhausted():
                    self._transition(State.TRACKING)          # coba frekuensi berikutnya
                elif config.ALARM_ENABLED:
                    self._transition(State.ALARM)             # semua gagal -> sirine
                else:
                    self._transition(State.COOLDOWN)          # sirine dimatikan

            # sirine selesai -> kembali menyapu
            if (self._state == State.ALARM and self._alarm_since and
                    now - self._alarm_since >= config.ALARM_DURATION):
                self._bus.publish(events.AUDIO_STOP, {})
                self._transition(State.IDLE)

            # cooldown selesai -> kembali siaga
            if self._state == State.COOLDOWN and now >= self._cooldown_until:
                self._transition(State.IDLE)

            time.sleep(0.1)