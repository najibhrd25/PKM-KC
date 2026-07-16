"""
DACAudio — adapter Event Bus -> PCM5102A (driver _dac_driver.py = DAC.py).

PENTING (safety, sesuai catatan proyek):
    - amplitude dibatasi <= AMPLITUDE_MAX_SAFE (limiting perangkat lunak)
    - durasi tiap operasi dibatasi <= AUDIO_MAX_DURATION
    - wajib cooldown setelah operasi (dijaga Orchestrator)

Payload audio_cmd:
    { freq, amplitude, duration, waveform,          # waveform opsional (default sine)
      f_start, f_end,                               # khusus waveform "sweep"
      n_cycles, pulse_waveform, inverted, half_cycle }  # khusus waveform "pulse"

Setiap play/stop mem-publish audio_state {playing, ...} untuk dashboard.

CATATAN THREADING (jangan disederhanakan kembali ke drv.play + sd.stop):
    sounddevice memakai SATU stream global dan tidak thread-safe. Di platform
    ini sd.stop() dari thread lain TIDAK membangunkan sd.wait() — thread play
    menggantung selamanya, dan sd.play() berikutnya yang tumpang tindih dengan
    stream lama memicu "double free or corruption" (crash proses).
    Solusi: thread play memutar non-blocking (sd.play) lalu polling flag
    _stop_requested; sd.stop() hanya dipanggil DARI thread play itu sendiri.
    _on_stop cukup set flag + join singkat.
"""
import time
import threading
import logging

from core.interfaces import BaseAudio
from core import events, config
from audio import _dac_driver as drv   # = DAC.py lama

logger = logging.getLogger(__name__)

# waveform kontinu -> generator(freq, dur, amplitude=)
_WAVEFORMS = {
    "sine":     drv.generate_sine,
    "square":   drv.generate_square,
    "sawtooth": drv.generate_sawtooth,
    "triangle": drv.generate_triangle,
}


class DACAudio(BaseAudio):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._playing = False
        self._play_thread = None      # lihat CATATAN THREADING di docstring
        self._stop_requested = False
        self._bus.subscribe(events.AUDIO_CMD,  self._on_cmd)
        self._bus.subscribe(events.AUDIO_STOP, self._on_stop)

    def start(self):
        drv.list_devices()
        logger.info("DACAudio siap.")

    def stop(self):
        self._on_stop({})

    def _publish_state(self, playing, **info):
        self._bus.publish(events.AUDIO_STATE, {"playing": playing, **info})

    def _on_cmd(self, data):
        t = self._play_thread
        if t is not None and t.is_alive():
            if self._playing:
                logger.warning("audio_cmd diabaikan: masih memutar audio.")
                return
            # playback baru saja berakhir; tunggu thread lama benar-benar
            # keluar dari sounddevice sebelum memulai stream baru
            t.join(timeout=1.0)
            if t.is_alive():
                logger.warning("audio_cmd diabaikan: thread audio lama macet.")
                return

        freq = float(data.get("freq", config.AUDIO_DEFAULT_FREQ))
        amp = min(float(data.get("amplitude", config.AMPLITUDE_MAX_SAFE)),
                  config.AMPLITUDE_MAX_SAFE)               # hard limit
        dur = min(float(data.get("duration", config.AUDIO_MAX_DURATION)),
                  config.AUDIO_MAX_DURATION)               # hard limit
        waveform = str(data.get("waveform", "sine")).lower()

        if waveform == "sweep":
            f_start = float(data.get("f_start", freq))
            f_end = float(data.get("f_end", freq * 2))
            signal = drv.generate_sweep(f_start, f_end, dur, amplitude=amp)
        elif waveform == "pulse":
            # pulse menentukan durasinya sendiri (= n_cycles/freq);
            # clamp n_cycles agar tetap <= AUDIO_MAX_DURATION
            n_max = max(1, int(freq * config.AUDIO_MAX_DURATION))
            n_cycles = max(1, min(int(data.get("n_cycles", 1)), n_max))
            signal = drv.generate_pulse(
                freq, n_cycles, amplitude=amp,
                waveform=str(data.get("pulse_waveform", "sine")),
                inverted=bool(data.get("inverted", False)),
                half_cycle=bool(data.get("half_cycle", False)))
        else:
            gen = _WAVEFORMS.get(waveform)
            if gen is None:
                logger.warning("Waveform '%s' tak dikenal — fallback sine.", waveform)
                waveform, gen = "sine", drv.generate_sine
            signal = gen(freq, dur, amplitude=amp)

        def _play():
            import sounddevice as sd
            self._playing = True
            self._publish_state(True, freq=freq, amplitude=amp,
                                duration=dur, waveform=waveform)
            try:
                if not self._stop_requested:   # stop bisa tiba sebelum play
                    logger.info("Memainkan: %s Hz (%s)", freq, waveform)
                    sd.play(signal, drv.SAMPLE_RATE, device=drv.DEVICE)
                    end = time.time() + len(signal) / drv.SAMPLE_RATE + 0.25
                    while time.time() < end and not self._stop_requested:
                        time.sleep(0.05)
                    sd.stop()   # dari thread INI (lihat catatan threading)
            except Exception:
                logger.exception("Gagal memutar audio.")
            finally:
                self._playing = False
                self._publish_state(False)

        self._stop_requested = False
        self._play_thread = threading.Thread(target=_play, daemon=True)
        self._play_thread.start()

    def _on_stop(self, data):
        # cukup minta berhenti; thread play yang memanggil sd.stop sendiri
        self._stop_requested = True
        t = self._play_thread
        if (t is not None and t.is_alive()
                and t is not threading.current_thread()):
            t.join(timeout=1.0)   # keluar <=~100 ms setelah flag terlihat
            if t.is_alive():
                logger.warning("Thread audio tidak berhenti tepat waktu.")
        self._playing = False
        self._publish_state(False)
