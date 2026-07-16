"""
DACAudio — adapter Event Bus -> PCM5102A (driver _dac_driver.py = DAC.py).

PENTING (safety, sesuai catatan proyek):
    - amplitude dibatasi <= AMPLITUDE_MAX_SAFE (limiting perangkat lunak)
    - durasi tiap operasi dibatasi <= AUDIO_MAX_DURATION
    - wajib cooldown setelah operasi (dijaga Orchestrator)
"""
import threading
import logging

from core.interfaces import BaseAudio
from core import events, config
from audio import _dac_driver as drv   # = DAC.py lama

logger = logging.getLogger(__name__)


class DACAudio(BaseAudio):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._playing = False
        self._bus.subscribe(events.AUDIO_CMD,  self._on_cmd)
        self._bus.subscribe(events.AUDIO_STOP, self._on_stop)

    def start(self):
        drv.list_devices()
        logger.info("DACAudio siap.")

    def stop(self):
        self._on_stop({})

    def _on_cmd(self, data):
        freq = float(data.get("freq", config.AUDIO_DEFAULT_FREQ))
        amp = min(float(data.get("amplitude", config.AMPLITUDE_MAX_SAFE)),
                  config.AMPLITUDE_MAX_SAFE)               # hard limit
        dur = min(float(data.get("duration", config.AUDIO_MAX_DURATION)),
                  config.AUDIO_MAX_DURATION)               # hard limit
        waveform = data.get("waveform", "sine").lower()

        def _play():
            self._playing = True
            if waveform == "square":
                signal = drv.generate_square(freq, dur, amplitude=amp)
            elif waveform == "sawtooth":
                signal = drv.generate_sawtooth(freq, dur, amplitude=amp)
            elif waveform == "triangle":
                signal = drv.generate_triangle(freq, dur, amplitude=amp)
            elif waveform == "sweep":
                # Sweep from 20Hz up to target freq
                signal = drv.generate_sweep(20, freq, dur, amplitude=amp)
            elif waveform == "pulse":
                n_cycles = max(1, int(freq * dur))
                signal = drv.generate_pulse(freq, n_cycles=n_cycles, amplitude=amp, waveform="sine")
            else:
                signal = drv.generate_sine(freq, dur, amplitude=amp)
                
            drv.play(signal, label=f"Pemadaman {waveform.upper()} {freq} Hz")
            self._playing = False

        threading.Thread(target=_play, daemon=True).start()

    def _on_stop(self, data):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            logger.exception("Gagal menghentikan audio.")
        self._playing = False
