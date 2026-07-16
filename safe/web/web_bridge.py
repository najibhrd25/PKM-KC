# safe/web/web_bridge.py
"""
WebBridge — antarmuka web opsional. Modul tepi: hanya subscribe/publish
ke Event Bus. Tidak memanggil modul lain langsung.

Menyediakan:
    GET  /             -> halaman dashboard (static/index.html)
    GET  /stream       -> MJPEG live kamera (dari frame_update)
    GET  /events       -> SSE status (state, mode, deteksi, ir, audio, servo, log)
    GET  /logs         -> riwayat log kejadian (ring buffer 200 entri)
    GET  /config       -> batas & default UI (amplitude_max, duration_max, ...)
    POST /cmd/mode     -> { mode: "auto"|"manual" }  -> set_mode
    POST /cmd/jog      -> { d_yaw, d_pitch }         -> servo_jog   (manual saja)
    POST /cmd/audio    -> { action: "play"|"stop", freq, amplitude, duration,
                            waveform, ... }          -> audio_cmd / audio_stop
                          (play manual saja; stop selalu boleh)
    POST /cmd/servo    -> { action: "home"|"torque_off"|"move", yaw_deg, pitch_deg }
                          -> servo_home / servo_stop / servo_cmd
                          (home & move manual saja; torque_off selalu boleh)
    POST /heartbeat    -> tanda UI masih aktif (cegah balik ke AUTO)
"""
import json
import time
import queue
import threading
import logging
import collections

from core.interfaces import BaseModule
from core import events, config

logger = logging.getLogger(__name__)


class WebBridge(BaseModule):
    def __init__(self, event_bus, host="0.0.0.0", port=8000):
        self._bus = event_bus
        self._host = host
        self._port = port

        self._latest_jpeg: bytes | None = None
        self._sse_clients: list[queue.Queue] = []
        self._last_heartbeat = 0.0
        self._mode = "auto"
        self._running = False
        self._log: collections.deque = collections.deque(maxlen=200)
        self._fire_logged = False    # cegah banjir log: FIRE_DETECTED tiap frame
        self._last_torque = None     # log servo hanya saat torque berubah
        self._ir_readings: dict[int, dict] = {}   # cache pembacaan terakhir
        self._last_ir_push = 0.0     # throttle SSE ir (IR publish ~25 ev/dtk)
        self._ir_hot_logged = False  # log hanya transisi panas muncul/hilang

        # terima update dari sistem
        self._bus.subscribe(events.IR_READING,      self._on_ir)
        self._bus.subscribe(events.FRAME_UPDATE,    self._on_frame)
        self._bus.subscribe(events.STATE_CHANGED,   self._on_state)
        self._bus.subscribe(events.MODE_CHANGED,    self._on_mode)
        self._bus.subscribe(events.FIRE_DETECTED,   self._on_detection)
        self._bus.subscribe(events.FIRE_CLEARED,    self._on_fire_cleared)
        self._bus.subscribe(events.EXTINGUISH_DONE, self._on_extinguish_done)
        self._bus.subscribe(events.AUDIO_STATE,     self._on_audio_state)
        self._bus.subscribe(events.SERVO_STATE,     self._on_servo_state)

    # ---------- lifecycle ----------
    def start(self):
        self._running = True
        threading.Thread(target=self._serve, daemon=True).start()
        threading.Thread(target=self._heartbeat_watch, daemon=True).start()
        logger.info("WebBridge di http://%s:%d", self._host, self._port)

    def stop(self):
        self._running = False

    # ---------- handler dari bus ----------
    def _on_frame(self, data):
        self._latest_jpeg = data.get("jpeg")

    def _on_ir(self, data):
        self._ir_readings[data["sensor_id"]] = data
        now = time.time()
        if now - self._last_ir_push < 0.2:      # throttle SSE (~5 Hz)
            return
        self._last_ir_push = now
        ir_hot, ir_x = self._ir_direction()
        sensors = [self._ir_readings[k] for k in sorted(self._ir_readings)]
        self._push_sse({"type": "ir", "sensors": sensors,
                        "ir_hot": ir_hot, "ir_x": ir_x})
        if ir_hot != self._ir_hot_logged:       # log transisi saja
            self._ir_hot_logged = ir_hot
            if ir_hot:
                arah = ("kiri" if ir_x is not None and ir_x < -0.2 else
                        "kanan" if ir_x is not None and ir_x > 0.2 else "tengah")
                self._log_event(f"IR: panas terdeteksi (arah {arah})")
            else:
                self._log_event("IR: panas hilang")

    def _ir_direction(self):
        """Indikator arah panas untuk TAMPILAN dashboard saja.

        Matematika sama dengan Orchestrator._compute_fusion (deteksi
        diferensial + centroid berbobot); keputusan resmi tetap di sana.
        """
        n = config.N_IR
        raws = [self._ir_readings.get(i + 1, {}).get("raw", 0)
                for i in range(n)]
        if not any(raws):
            return False, None
        idx_max = raws.index(max(raws))
        others = raws[:idx_max] + raws[idx_max + 1:]
        avg_others = sum(others) / len(others) if others else 0.0
        ir_hot = raws[idx_max] - avg_others >= config.IR_DIFF_THRESHOLD
        mean_raw = sum(raws) / n
        weights = [max(0.0, r - mean_raw) for r in raws]
        wsum = sum(weights)
        ir_x = None
        if wsum > 0:
            half = (n - 1) / 2
            ir_x = sum(((i - half) / half) * w
                       for i, w in enumerate(weights)) / wsum
            if config.IR_REVERSE:
                ir_x = -ir_x
        return ir_hot, ir_x

    def _on_state(self, data):
        self._push_sse({"type": "state", "value": data["new"]})
        self._log_event(f"State: {data.get('old', '?')} -> {data['new']}")

    def _on_mode(self, data):
        self._mode = data["mode"]
        self._push_sse({"type": "mode", "value": data["mode"]})
        self._log_event(f"Mode: {data['mode'].upper()}")

    def _on_detection(self, data):
        self._push_sse({"type": "detection",
                        "bbox": data["bbox"],
                        "confidence": data["confidence"]})
        if not self._fire_logged:   # log hanya deteksi pertama, bukan tiap frame
            self._fire_logged = True
            self._log_event(
                f"Api terdeteksi (conf={data['confidence'] * 100:.0f}%)")

    def _on_fire_cleared(self, data):
        if self._fire_logged:
            self._fire_logged = False
            self._log_event("Api hilang dari frame")

    def _on_extinguish_done(self, data):
        self._log_event("Operasi pemadaman selesai")

    def _on_audio_state(self, data):
        self._push_sse({"type": "audio", **data})
        if data.get("playing"):
            self._log_event(
                f"Audio ON: {data.get('freq', '?')} Hz "
                f"{data.get('waveform', 'sine')} amp={data.get('amplitude', '?')}")
        else:
            self._log_event("Audio OFF")

    def _on_servo_state(self, data):
        self._push_sse({"type": "servo", **data})
        torque = data.get("torque")
        if torque != self._last_torque:   # posisi terlalu sering; log torque saja
            self._last_torque = torque
            self._log_event("Servo torque " + ("ON" if torque else "OFF"))

    def _push_sse(self, payload: dict):
        msg = f"data: {json.dumps(payload)}\n\n"
        for q in list(self._sse_clients):
            q.put(msg)

    def _log_event(self, text: str):
        entry = {"t": time.time(), "msg": text}
        self._log.append(entry)
        self._push_sse({"type": "log", **entry})

    # ---------- heartbeat: balik ke AUTO bila UI hilang ----------
    def _heartbeat_watch(self):
        while self._running:
            if (self._mode == "manual" and
                    time.time() - self._last_heartbeat
                    > config.WEB_HEARTBEAT_TIMEOUT):
                logger.info("Heartbeat UI hilang — kembali ke AUTO.")
                self._bus.publish(events.SET_MODE, {"mode": "auto"})
            time.sleep(1.0)

    # ---------- server FastAPI ----------
    def _serve(self):
        import uvicorn
        from fastapi import FastAPI, Request
        from fastapi.responses import (
            StreamingResponse, HTMLResponse, JSONResponse)
        from pathlib import Path

        app = FastAPI()
        static_dir = Path(__file__).parent / "static"

        @app.get("/", response_class=HTMLResponse)
        def index():
            return (static_dir / "index.html").read_text()

        @app.get("/stream")
        def stream():
            def gen():
                placeholder = b""  # bisa diisi gambar "kamera tidak aktif"
                while self._running:
                    frame = self._latest_jpeg or placeholder
                    if frame:
                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n"
                               + frame + b"\r\n")
                    time.sleep(0.05)   # ~20 fps maksimum
            return StreamingResponse(
                gen(),
                media_type="multipart/x-mixed-replace; boundary=frame")

        @app.get("/events")
        def events_sse():
            q: queue.Queue = queue.Queue()
            self._sse_clients.append(q)

            def gen():
                try:
                    while self._running:
                        yield q.get()
                finally:
                    self._sse_clients.remove(q)
            return StreamingResponse(gen(), media_type="text/event-stream")

        @app.post("/cmd/mode")
        async def set_mode(req: Request):
            body = await req.json()
            mode = body.get("mode", "auto")
            if mode == "manual":
                self._last_heartbeat = time.time()
            self._bus.publish(events.SET_MODE, {"mode": mode})
            return JSONResponse({"ok": True, "mode": mode})

        def _reject_not_manual():
            return JSONResponse({"ok": False, "error": "not in manual mode"},
                                status_code=409)

        @app.post("/cmd/jog")
        async def jog(req: Request):
            if self._mode != "manual":
                return _reject_not_manual()
            body = await req.json()
            self._bus.publish(events.SERVO_JOG, {
                "d_yaw":   float(body.get("d_yaw", 0.0)),
                "d_pitch": float(body.get("d_pitch", 0.0)),
            })
            return JSONResponse({"ok": True})

        @app.post("/cmd/audio")
        async def audio_cmd(req: Request):
            body = await req.json()
            if body.get("action") == "stop":
                # stop selalu aman, boleh dari mode apa pun
                self._bus.publish(events.AUDIO_STOP, {})
                return JSONResponse({"ok": True})
            if self._mode != "manual":
                return _reject_not_manual()
            # clamp amplitudo/durasi tetap di DACAudio (single source of truth)
            keys = ("freq", "amplitude", "duration", "waveform", "f_start",
                    "f_end", "n_cycles", "pulse_waveform", "inverted",
                    "half_cycle")
            self._bus.publish(events.AUDIO_CMD,
                              {k: body[k] for k in keys if k in body})
            return JSONResponse({"ok": True})

        @app.post("/cmd/servo")
        async def servo_cmd(req: Request):
            body = await req.json()
            action = body.get("action")
            if action == "torque_off":
                # mematikan torsi selalu aman, boleh dari mode apa pun
                self._bus.publish(events.SERVO_STOP, {})
                return JSONResponse({"ok": True})
            if self._mode != "manual":
                return _reject_not_manual()
            if action == "home":
                self._bus.publish(events.SERVO_HOME, {})
            elif action == "move":
                self._bus.publish(events.SERVO_CMD, {
                    "yaw_deg":   float(body.get("yaw_deg", 180.0)),
                    "pitch_deg": float(body.get("pitch_deg", 180.0)),
                })
            else:
                return JSONResponse({"ok": False, "error": "unknown action"},
                                    status_code=400)
            return JSONResponse({"ok": True})

        @app.get("/logs")
        def logs():
            return JSONResponse(list(self._log))

        @app.get("/config")
        def config_limits():
            """Batas & default untuk UI (sumber kebenaran: core/config.py)."""
            return JSONResponse({
                "freq_default":   config.AUDIO_DEFAULT_FREQ,
                "amplitude_max":  config.AMPLITUDE_MAX_SAFE,
                "duration_max":   config.AUDIO_MAX_DURATION,
                "yaw_min":        config.YAW_MIN,
                "yaw_max":        config.YAW_MAX,
                "pitch_min":      config.PITCH_MIN,
                "pitch_max":      config.PITCH_MAX,
                "jog_step_deg":   config.WEB_JOG_STEP_DEG,
                "ir_threshold_v": config.IR_THRESHOLD_V,
                "n_ir":           config.N_IR,
                "ir_reverse":     config.IR_REVERSE,
            })

        @app.post("/heartbeat")
        def heartbeat():
            self._last_heartbeat = time.time()
            return JSONResponse({"ok": True})

        uvicorn.run(app, host=self._host, port=self._port, log_level="warning") 