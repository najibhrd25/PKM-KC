"""
Program Pemutaran Sound File (MP3) - Raspberry Pi
===================================================

File audio default: tolong_BPxrsyS.mp3 (folder yang sama dengan script ini)

Setup Software (Raspberry Pi):
    1. Install ffmpeg (untuk decode MP3): sudo apt install ffmpeg -y
    2. Install dependency: pip3 install --break-system-packages pydub numpy sounddevice

Referensi output audio sama dengan DAC.py (PCM5102A, device index 0).
"""

import numpy as np
import sounddevice as sd
from pydub import AudioSegment

# ======================= KONFIGURASI =======================
SOUND_FILE = "tolong_BPxrsyS.mp3"
DEVICE = 0  # index dari list_devices() - 0 = snd_rpi_hifiberry_dac

# testing
# ======================= LOAD AUDIO =======================
def load_sound(path):
    """Load file audio (mp3/wav dll) -> (signal float32 -1.0..1.0, sample_rate)."""
    audio = AudioSegment.from_file(path)
    sample_rate = audio.frame_rate

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples /= np.iinfo(audio.array_type).max

    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels))

    return samples, sample_rate


# ======================= PLAYBACK =======================
def list_devices():
    """Tampilkan daftar audio device yang tersedia (cek PCM5102A terdeteksi)."""
    print("=== Daftar Audio Device ===")
    print(sd.query_devices())
    print("============================\n")


def play_sound(signal, sample_rate, amplitude=1.0, speed=1.0, repeat=1, inverted=False, device=DEVICE):
    """Mainkan sinyal audio dengan kontrol volume, speed, repeat, dan polaritas.

    speed mengubah sample rate playback, sehingga juga mempengaruhi pitch
    (mirip mempercepat/memperlambat kaset).
    """
    out = signal * amplitude
    if inverted:
        out = -out

    playback_rate = int(sample_rate * speed)

    for _ in range(repeat):
        sd.play(out, playback_rate, device=device)
        sd.wait()


# ======================= PROGRAM INTERAKTIF =======================
if __name__ == "__main__":
    list_devices()

    signal, sample_rate = load_sound(SOUND_FILE)
    duration = len(signal) / sample_rate
    print(f"-> {SOUND_FILE}: {sample_rate} Hz, {duration:.2f} detik\n")

    amplitude = 1.0
    speed = 1.0
    repeat = 1
    inverted = False

    print("=== Kontrol Playback Sound ===")
    print("Perintah:")
    print("  a <0.0-1.0>  - set volume (contoh: a 0.8)")
    print("  s <speed>    - set kecepatan playback, 1.0 = normal (contoh: s 1.5)")
    print("  r <jumlah>   - set jumlah pengulangan (contoh: r 3)")
    print("  i            - toggle inverted (balik polaritas sinyal)")
    print("  p / (enter)  - mainkan sound dengan setting saat ini")
    print("  exit         - keluar\n")

    while True:
        prompt = f"[vol={amplitude} speed={speed} repeat={repeat} inv={inverted}] > "
        raw = input(prompt).strip()

        if raw.lower() in ("exit", "quit", "q"):
            break

        parts = raw.split()
        if not parts or parts[0].lower() in ("p", "play"):
            play_sound(signal, sample_rate, amplitude=amplitude, speed=speed, repeat=repeat, inverted=inverted)
            continue

        cmd, *rest = parts
        cmd = cmd.lower()

        if cmd == "a" and len(rest) == 1:
            try:
                amplitude = max(0.0, min(1.0, float(rest[0])))
            except ValueError:
                print("Volume tidak valid.")
        elif cmd == "s" and len(rest) == 1:
            try:
                speed = max(0.1, float(rest[0]))
            except ValueError:
                print("Speed tidak valid.")
        elif cmd == "r" and len(rest) == 1:
            try:
                repeat = max(1, int(rest[0]))
            except ValueError:
                print("Jumlah repeat tidak valid.")
        elif cmd == "i" and not rest:
            inverted = not inverted
        else:
            print("Perintah tidak dikenali.")
