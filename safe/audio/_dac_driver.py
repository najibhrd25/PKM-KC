"""
Program Uji Coba Modul DAC PCM5102A (I2S DAC) - Raspberry Pi
==============================================================

Setup Hardware (wiring ke Raspberry Pi):
    VIN = 3.3V (JANGAN 5V)
    GND = GND
    LCK = GPIO19 (PCM FS)
    DIN = GPIO21 (PCM DOUT)
    BCK = GPIO18 (PCM CLK)
    SCK = GND

Setup Software (Raspberry Pi):
    1. Edit /boot/config.txt:
        - Tambahkan: dtoverlay=hifiberry-dac
        - Hapus/komentari: dtparam=audio=on
    2. Tambahkan user ke grup audio: sudo usermod -aG audio $USER
    3. Reboot, lalu cek: aplay -l (harus muncul card PCM5102A / sndrpihifiberry)
    4. Install dependency: pip install sounddevice numpy
       (perlu libportaudio2: sudo apt install libportaudio2)

Referensi:
    https://gist.github.com/Autr/921c1d1b8e5f4ee15e39123b3f774052
    https://www.instructables.com/Raspberry-Pi-HQ-Audio-PCM5102-and-MPD/
"""

import numpy as np
import sounddevice as sd

# ======================= KONFIGURASI =======================
SAMPLE_RATE = 44100  # Hz
AMPLITUDE = 0.3      # skala 0.0 - 1.0
DEVICE = 0           # index dari list_devices() - 0 = snd_rpi_hifiberry_dac


# ======================= UTILITAS =======================
def _apply_fade(signal, sample_rate, fade_ms=10):
    """Tambahkan fade-in/fade-out singkat untuk menghindari bunyi 'klik'."""
    fade_samples = min(int(sample_rate * fade_ms / 1000), len(signal) // 2)
    if fade_samples > 0:
        signal[:fade_samples] *= np.linspace(0, 1, fade_samples)
        signal[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    return signal


# ======================= GENERATOR SINYAL =======================
def generate_sine(freq, duration, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate gelombang sinus."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = amplitude * np.sin(2 * np.pi * freq * t)
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_square(freq, duration, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate gelombang kotak (square wave)."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = amplitude * np.sign(np.sin(2 * np.pi * freq * t))
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_sawtooth(freq, duration, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate gelombang gigi gergaji (sawtooth wave)."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = amplitude * 2 * (t * freq - np.floor(t * freq + 0.5))
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_triangle(freq, duration, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate gelombang segitiga (triangle wave)."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    saw = 2 * (t * freq - np.floor(t * freq + 0.5))
    signal = amplitude * (2 * np.abs(saw) - 1)
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_sweep(f_start, f_end, duration, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate frequency sweep (linear chirp) dari f_start ke f_end."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    rate = (f_end - f_start) / duration
    phase = 2 * np.pi * (f_start * t + 0.5 * rate * t ** 2)
    signal = amplitude * np.sin(phase)
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_white_noise(duration, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate white noise."""
    n_samples = int(sample_rate * duration)
    signal = amplitude * np.random.uniform(-1, 1, n_samples)
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_pulse(freq, n_cycles=1, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE, waveform="sine",
                    inverted=False, half_cycle=False):
    """Generate pulsa singkat pada freq tertentu (untuk uji vortex ring).

    n_cycles    - jumlah periode (atau setengah periode jika half_cycle=True)
    inverted    - balik polaritas sinyal (uji arah dorongan vortex ring)
    half_cycle  - True: setiap siklus hanya dorongan satu arah (tanpa lembah/puncak balik)
    """
    if half_cycle:
        duration = n_cycles / (2 * freq)
    else:
        duration = n_cycles / freq

    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    if half_cycle:
        if waveform == "square":
            signal = amplitude * np.ones_like(t)
        else:
            signal = amplitude * np.abs(np.sin(2 * np.pi * freq * t))
    elif waveform == "square":
        signal = amplitude * np.sign(np.sin(2 * np.pi * freq * t))
    else:
        signal = amplitude * np.sin(2 * np.pi * freq * t)

    if inverted:
        signal = -signal

    return _apply_fade(signal.astype(np.float32), sample_rate, fade_ms=2)


def generate_siren(f_low, f_high, duration, period=1.0, sample_rate=SAMPLE_RATE,
                   amplitude=AMPLITUDE):
    """Sirine: frekuensi naik-turun berulang antara f_low dan f_high.

    Beda dengan generate_sweep yang sekali jalan f_start -> f_end; ini profil
    segitiga yang berulang tiap `period` detik, jadi terdengar seperti sirine.

    period - detik untuk satu siklus naik+turun penuh
    """
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    # profil frekuensi segitiga: 0 -> 1 -> 0 dalam tiap periode
    ph = (t / max(period, 1e-6)) % 1.0
    freq_inst = f_low + (f_high - f_low) * (1.0 - np.abs(2.0 * ph - 1.0))

    # fase = integral frekuensi sesaat (bukan f*t — itu salah untuk freq berubah)
    phase = 2 * np.pi * np.cumsum(freq_inst) / sample_rate
    signal = amplitude * np.sin(phase)
    return _apply_fade(signal.astype(np.float32), sample_rate)


def generate_pulse_train(freq, duration, n_cycles=1, gap=0.2, sample_rate=SAMPLE_RATE,
                         amplitude=AMPLITUDE, waveform="sine", inverted=False,
                         half_cycle=False):
    """Rentetan pulsa: satu pulsa lalu hening `gap` detik, diulang sampai `duration`.

    Beda dengan generate_pulse yang hanya menghasilkan SATU letupan kontinu.

    duration - total panjang sinyal (detik); jumlah pengulangan dihitung dari sini
    gap      - jeda hening antar pulsa (detik); gap=0 -> pulsa beruntun tanpa jeda

    Tiap pulsa sudah ber-fade sendiri (generate_pulse), jadi tidak ada 'klik' di
    tiap batas pulsa.
    """
    pulse = generate_pulse(freq, n_cycles, sample_rate, amplitude, waveform,
                           inverted, half_cycle)
    silence = np.zeros(max(0, int(sample_rate * gap)), dtype=np.float32)
    period = len(pulse) + len(silence)
    if period == 0:
        return pulse
    n_rep = max(1, int(sample_rate * duration) // period)
    return np.tile(np.concatenate([pulse, silence]), n_rep)


# ======================= PLAYBACK =======================
def list_devices():
    """Tampilkan daftar audio device yang tersedia (cek PCM5102A terdeteksi)."""
    print("=== Daftar Audio Device ===")
    print(sd.query_devices())
    print("============================\n")


def play(signal, sample_rate=SAMPLE_RATE, label=""):
    """Mainkan sinyal audio ke output device."""
    if label:
        print(f"-> Memainkan: {label}")
    sd.play(signal, sample_rate, device=DEVICE)
    sd.wait()


# ======================= KONTROL INTERAKTIF PULSA VORTEX RING =======================
if __name__ == "__main__":
    list_devices()

    freq = 30.0
    amplitude = AMPLITUDE
    n_cycles = 1
    waveform = "square"
    inverted = False
    half_cycle = False

    print("=== Kontrol Pulsa Vortex Ring ===")
    print("Perintah:")
    print("  f <hz>         - set frekuensi (contoh: f 30)")
    print("  a <0.0-1.0>    - set amplitudo (contoh: a 0.8)")
    print("  n <jumlah>     - set jumlah siklus per pulsa (contoh: n 1)")
    print("  w sine|square  - set bentuk gelombang")
    print("  i              - toggle inverted (balik polaritas sinyal)")
    print("  h              - toggle half cycle (dorongan satu arah saja)")
    print("  p / (enter)    - trigger pulsa dengan setting saat ini")
    print("  exit           - keluar\n")

    while True:
        prompt = f"[f={freq}Hz a={amplitude} n={n_cycles} w={waveform} inv={inverted} half={half_cycle}] > "
        raw = input(prompt).strip()

        if raw.lower() in ("exit", "quit", "q"):
            break

        parts = raw.split()
        if not parts or parts[0].lower() in ("p", "play"):
            signal = generate_pulse(freq, n_cycles, amplitude=amplitude, waveform=waveform,
                                     inverted=inverted, half_cycle=half_cycle)
            label = f"Pulse {waveform} {freq} Hz x{n_cycles}"
            label += " half-cycle" if half_cycle else " siklus"
            if inverted:
                label += " (inverted)"
            play(signal, label=label)
            continue

        cmd, *rest = parts
        cmd = cmd.lower()

        if cmd == "f" and len(rest) == 1:
            try:
                freq = float(rest[0])
            except ValueError:
                print("Frekuensi tidak valid.")
        elif cmd == "a" and len(rest) == 1:
            try:
                amplitude = max(0.0, min(2.0, float(rest[0])))
            except ValueError:
                print("Amplitudo tidak valid.")
        elif cmd == "n" and len(rest) == 1:
            try:
                n_cycles = max(1, int(rest[0]))
            except ValueError:
                print("Jumlah siklus tidak valid.")
        elif cmd == "w" and len(rest) == 1 and rest[0].lower() in ("sine", "square"):
            waveform = rest[0].lower()
        elif cmd == "i" and not rest:
            inverted = not inverted
        elif cmd == "h" and not rest:
            half_cycle = not half_cycle
        else:
            print("Perintah tidak dikenali.")
