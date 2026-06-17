"""
Event Bus internal — publish/subscribe sederhana, thread-safe.

Modul tidak saling memanggil langsung. Mereka publish event ke bus,
dan bus meneruskan ke semua subscriber event tersebut.
"""

import queue
import threading
import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()

    # ---------- API publik ----------
    def subscribe(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """Daftarkan handler untuk sebuah jenis event."""
        with self._lock:
            self._subscribers[event_type].append(handler)
        logger.debug("Subscribe '%s' -> %s", event_type, handler.__qualname__)

    def publish(self, event_type: str, data: dict | None = None) -> None:
        """Kirim event ke bus. Non-blocking — diproses oleh worker thread."""
        self._queue.put((event_type, data or {}))

    # ---------- lifecycle ----------
    def start(self) -> None:
        self._running = True
        self._worker = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._worker.start()
        logger.info("EventBus berjalan.")

    def stop(self) -> None:
        self._running = False
        self._queue.put(("__stop__", {}))
        if self._worker:
            self._worker.join(timeout=2.0)
        logger.info("EventBus berhenti.")

    # ---------- internal ----------
    def _dispatch_loop(self) -> None:
        while self._running:
            event_type, data = self._queue.get()
            if event_type == "__stop__":
                break
            for handler in list(self._subscribers.get(event_type, [])):
                try:
                    handler(data)
                except Exception:
                    logger.exception("Handler gagal untuk event '%s'", event_type)
