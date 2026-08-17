"""
ConfigWatcher — muat ulang core/config.py saat file-nya disimpan, tanpa restart.

KENAPA BISA BEKERJA
    Setiap modul memakai `from core import config` lalu membaca `config.NAMA`
    di titik pakai. Yang terikat adalah OBJEK MODUL-nya, bukan nilainya, jadi
    memperbarui atribut pada objek itu langsung terlihat oleh semua modul tanpa
    perlu memberi tahu siapa pun.

    Konsekuensinya: jangan pernah menulis `from core.config import YAW_MIN` di
    modul mana pun. Gaya itu menyalin nilainya sekali dan membekukannya —
    hot-reload tidak akan pernah menjangkaunya.

KENAPA exec KE NAMESPACE KOSONG, BUKAN importlib.reload
    reload() mengeksekusi langsung ke dalam modul config. Bila file sedang
    setengah tersimpan atau ada typo, eksekusi gagal DI TENGAH dan meninggalkan
    campuran nilai lama dan baru. Di sini sumber di-exec ke dict kosong lebih
    dulu: kalau gagal, gagal seluruhnya dan config lama tetap utuh.
"""
import time
import logging
import threading
from pathlib import Path

from core.interfaces import BaseModule
from core import config

logger = logging.getLogger(__name__)

# Nilai yang hanya dibaca sekali saat startup. Boleh diubah, tapi tidak akan
# berpengaruh sampai program dijalankan ulang — watcher memberi WARNING agar
# tidak terlihat seperti sistem yang rusak.
RESTART_REQUIRED = {
    "SERVO_SPEED":  "ditulis ke register servo sekali di ServoActuator.start()",
    "SERVO_MAX_HZ": "di-cache jadi _send_interval di ServoActuator.__init__",
    "MODEL_PATH":   "model dimuat di YOLODetector.start()",
    "FRAME_SIZE":   "kamera dikonfigurasi di YOLODetector.start()",
    "DETECT_MODE":  "di-resolve ke Orchestrator._detect_mode di __init__",
    "WEB_HOST":     "diteruskan ke konstruktor WebBridge lewat main.py",
    "WEB_PORT":     "diteruskan ke konstruktor WebBridge lewat main.py",
}


class ConfigWatcher(BaseModule):
    def __init__(self, event_bus=None, path=None):
        self._bus = event_bus
        self._path = Path(path) if path else Path(config.__file__)
        self._mtime = None
        self._running = False
        self._thread = None

    # ======================= LIFECYCLE =======================
    def start(self):
        if not config.CONFIG_HOT_RELOAD:
            logger.info("ConfigWatcher nonaktif (CONFIG_HOT_RELOAD=False).")
            return
        try:
            self._mtime = self._path.stat().st_mtime
        except OSError as exc:
            logger.warning("ConfigWatcher mati: %s tidak terbaca (%s).",
                           self._path, exc)
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("ConfigWatcher aktif — %s dicek tiap %.0f detik.",
                    self._path.name, config.CONFIG_POLL_SEC)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    # ======================= LOOP =======================
    def _watch_loop(self):
        while self._running:
            # tidur dipecah supaya stop() tidak perlu menunggu satu interval penuh
            slept = 0.0
            while self._running and slept < config.CONFIG_POLL_SEC:
                time.sleep(0.5)
                slept += 0.5
            if not self._running:
                return
            # watcher memuat ulang setelannya sendiri, jadi mematikan flag di
            # file harus benar-benar menghentikannya (bukan hanya saat start)
            if not config.CONFIG_HOT_RELOAD:
                logger.info("CONFIG_HOT_RELOAD dimatikan — ConfigWatcher berhenti.")
                self._running = False
                return
            try:
                mtime = self._path.stat().st_mtime
            except OSError:
                continue            # file sedang ditulis ulang; coba lagi nanti
            if mtime != self._mtime:
                self._mtime = mtime
                self._reload()

    def _reload(self):
        try:
            src = self._path.read_text()
            ns: dict = {}
            exec(compile(src, str(self._path), "exec"), ns)
        except Exception as exc:
            logger.warning("config.py gagal dimuat (%s: %s) — "
                           "nilai lama dipertahankan.", type(exc).__name__, exc)
            return

        changed = []
        for key, new in ns.items():
            if not key.isupper():
                continue            # lewati __builtins__, helper, dll
            old = getattr(config, key, None)
            if old != new:
                setattr(config, key, new)
                changed.append((key, old, new))

        if not changed:
            return

        logger.info("config.py dimuat ulang — %d nilai berubah.", len(changed))
        for key, old, new in changed:
            logger.info("  %s: %r -> %r", key, old, new)
            if key in RESTART_REQUIRED:
                logger.warning("  ^ %s butuh RESTART untuk berlaku (%s).",
                               key, RESTART_REQUIRED[key])
