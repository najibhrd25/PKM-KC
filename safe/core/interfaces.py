"""
Base class abstrak. Setiap modul nyata maupun fake mengimplementasikan
salah satu dari kelas ini. Orchestrator hanya tahu kontraknya.
"""
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Kontrak lifecycle dasar untuk semua modul."""

    @abstractmethod
    def start(self) -> None:
        """Inisialisasi hardware / thread. Dipanggil sekali saat boot."""

    @abstractmethod
    def stop(self) -> None:
        """Matikan dengan aman. Dipanggil saat shutdown."""


class BaseSensor(BaseModule):
    """Sensor mempublish pembacaan ke Event Bus secara periodik."""


class BaseDetector(BaseModule):
    """Detektor api. Mempublish fire_detected / fire_cleared."""


class BaseActuator(BaseModule):
    """Aktuator (servo). Subscribe perintah dari bus."""


class BaseAudio(BaseModule):
    """Pembangkit sinyal audio. Subscribe audio_cmd."""
