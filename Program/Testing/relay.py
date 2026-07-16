"""
Program Uji Coba Relay - Raspberry Pi
======================================

Setup Hardware:
    - GPIO17 (pin fisik 11) -> pin IN modul relay
    - 5V / 3.3V -> VCC modul relay (sesuai spesifikasi modul)
    - GND -> GND modul relay

Catatan:
    - Kebanyakan modul relay bersifat ACTIVE LOW (relay ON saat pin IN diberi LOW).
      Kalau relay terbalik (ON saat harusnya OFF), ubah ACTIVE_HIGH di bawah.
    - Pakai gpiozero karena RPi.GPIO tidak didukung penuh di Raspberry Pi 5.
"""

import time

from gpiozero import OutputDevice

# ======================= KONFIGURASI =======================
RELAY_PIN = 17       # nomor GPIO (BCM), bukan nomor pin fisik
ACTIVE_HIGH = False  # False = modul relay active low (umum), True = active high


# ======================= PROGRAM INTERAKTIF =======================
if __name__ == "__main__":
    # initial_value=False -> relay mulai dalam kondisi OFF
    relay = OutputDevice(RELAY_PIN, active_high=ACTIVE_HIGH, initial_value=False)

    print("=== Uji Coba Relay (GPIO17) ===")
    print("Perintah:")
    print("  [Enter] : toggle ON/OFF")
    print("  on      : nyalakan relay")
    print("  off     : matikan relay")
    print("  blink   : ON/OFF bergantian 5x (interval 1 detik)")
    print("  exit    : keluar\n")

    try:
        while True:
            status = "ON" if relay.value else "OFF"
            raw = input(f"[relay {status}] > ").strip().lower()

            if raw in ("exit", "quit", "q"):
                break
            elif raw == "":
                relay.toggle()
                print(f"Relay {'ON' if relay.value else 'OFF'}")
            elif raw == "on":
                relay.on()
                print("Relay ON")
            elif raw == "off":
                relay.off()
                print("Relay OFF")
            elif raw == "blink":
                for i in range(5):
                    relay.on()
                    print(f"[{i + 1}/5] Relay ON")
                    time.sleep(1)
                    relay.off()
                    print(f"[{i + 1}/5] Relay OFF")
                    time.sleep(1)
            else:
                print("Perintah tidak dikenal. Pakai: [Enter]/on/off/blink/exit")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n=== Mematikan relay & melepas GPIO ===")
        relay.off()
        relay.close()
