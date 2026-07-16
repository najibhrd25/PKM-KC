"""
WebBridge — antarmuka web opsional. Modul tepi: hanya subscribe/publish
ke Event Bus. Tidak memanggil modul lain langsung.

Menyediakan:
    GET  /             -> halaman dashboard (static/index.html)
    GET  /stream       -> MJPEG live kamera (dari frame_update)
    GET  /events       -> SSE status (state, mode, deteksi)
    POST /cmd/mode     -> { mode: "auto"|"manual" }  -> set_mode
    POST /cmd/jog      -> { d_yaw, d_pitch }         -> servo_jog
    POST /cmd/shoot    -> { frequency }               -> audio manual
    POST /heartbeat    -> tanda UI masih aktif (cegah balik ke AUTO)
"""
import json
import time
import queue
import threading
import logging

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

        # terima update dari sistem
        self._bus.subscribe(events.FRAME_UPDATE,  self._on_frame)
        self._bus.subscribe(events.STATE_CHANGED, self._on_state)
        self._bus.subscribe(events.MODE_CHANGED,  self._on_mode)
        self._bus.subscribe(events.FIRE_DETECTED, self._on_detection)

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

    def _on_state(self, data):
        self._push_sse({"type": "state", "value": data["new"]})

    def _on_mode(self, data):
        self._mode = data["mode"]
        self._push_sse({"type": "mode", "value": data["mode"]})

    def _on_detection(self, data):
        self._push_sse({"type": "detection",
                        "bbox": data["bbox"],
                        "confidence": data["confidence"]})

    def _push_sse(self, payload: dict):
        msg = f"data: {json.dumps(payload)}\n\n"
        for q in list(self._sse_clients):
            q.put(msg)

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
        from fastapi.middleware.cors import CORSMiddleware
        from pathlib import Path

        app = FastAPI()

        # Izinkan akses dari dashboard mobile (React Native / Expo)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        static_dir = Path(__file__).parent / "static"

        @app.get("/", response_class=HTMLResponse)
        def index():
            html_path = static_dir / "index.html"
            if html_path.exists():
                return html_path.read_text()
            return HTMLResponse("<h1>S.A.F.E. WebBridge aktif</h1>")

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

        @app.post("/cmd/jog")
        async def jog(req: Request):
            body = await req.json()
            self._bus.publish(events.SERVO_JOG, {
                "d_yaw":   float(body.get("d_yaw", 0.0)),
                "d_pitch": float(body.get("d_pitch", 0.0)),
            })
            return JSONResponse({"ok": True})


        @app.post("/cmd/home")
        async def home(req: Request):
            self._bus.publish(events.SERVO_HOME, {})
            return JSONResponse({"ok": True})

        @app.post("/cmd/stop")
        async def stop_actuators(req: Request):
            self._bus.publish(events.AUDIO_STOP, {})
            self._bus.publish(events.TRACK_STOP, {})
            self._bus.publish(events.SERVO_HOME, {})
            return JSONResponse({"ok": True})



        @app.post("/cmd/shoot")
        async def shoot(req: Request):
            """Pemadaman manual — hanya diizinkan saat MANUAL mode."""
            body = await req.json()
            freq = float(body.get("frequency", config.AUDIO_DEFAULT_FREQ))
            amp = float(body.get("amplitude", config.AMPLITUDE_MAX_SAFE))
            dur = float(body.get("duration", config.AUDIO_MAX_DURATION))
            waveform = body.get("waveform", "sine")
            
            self._bus.publish(events.AUDIO_CMD, {
                "freq": freq,
                "amplitude": amp,
                "duration": dur,
                "waveform": waveform,
            })
            return JSONResponse({"ok": True, "frequency": freq, "amplitude": amp, "duration": dur, "waveform": waveform})



        @app.post("/heartbeat")
        def heartbeat():
            self._last_heartbeat = time.time()
            return JSONResponse({"ok": True})

        uvicorn.run(app, host=self._host, port=self._port, log_level="warning")
