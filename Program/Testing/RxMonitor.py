"""
Monitor Jalur RX - Diagnostik Hardware Dynamixel
=================================================
Membaca /dev/ttyAMA0 (GPIO15/RXD) secara terus menerus dan menampilkan
SEMUA byte mentah yang masuk, tanpa parsing protokol Dynamixel sama sekali.

Tujuan: memastikan apakah ada sinyal APAPUN yang benar-benar sampai ke
RXD Pi (dari servo, dari echo TX sendiri, atau dari noise bus), untuk
mengisolasi masalah "TX jalan tapi tidak ada balasan":
    - Tidak ada byte sama sekali muncul  -> curigai GND tidak nyambung,
      DI/RO tertukar, atau RO modul tidak benar-benar terhubung ke GPIO15.
    - Byte muncul tapi acak/tidak masuk akal -> curigai baudrate/level
      sinyal/polaritas A-B, bukan wiring putus total.

Cara pakai:
    1. Jalankan script ini di satu terminal:
        python3 RxMonitor.py
    2. Di terminal lain, jalankan Servo.py (atau scan dari Wizard bila
       memungkinkan) supaya ada aktivitas di bus.
    3. Perhatikan output di sini - kalau tetap kosong terus selama
       scan berjalan, RX benar-benar tidak menerima apa pun.
    Tekan Ctrl+C untuk berhenti.
"""

import sys
import time

import serial

DEVICENAME = "/dev/ttyAMA0"
BAUDRATE = 1000000
IDLE_GAP = 0.05  # detik; jeda ini dipakai untuk memisahkan satu "burst" data ke baris baru


def main():
    ser = serial.Serial(port=DEVICENAME, baudrate=BAUDRATE, timeout=0.05)
    print(f"Membuka {DEVICENAME} @ {BAUDRATE} bps")
    print("Menunggu data masuk di RX... (Ctrl+C untuk berhenti)\n")

    buffer = bytearray()
    last_byte_time = None

    try:
        while True:
            data = ser.read(256)
            now = time.time()

            if data:
                if buffer and last_byte_time is not None and (now - last_byte_time) > IDLE_GAP:
                    flush(buffer)
                    buffer.clear()
                buffer.extend(data)
                last_byte_time = now
            elif buffer and last_byte_time is not None and (now - last_byte_time) > IDLE_GAP:
                flush(buffer)
                buffer.clear()

    except KeyboardInterrupt:
        pass
    finally:
        if buffer:
            flush(buffer)
        ser.close()
        print("\nPort ditutup.")


def flush(buffer):
    ts = time.strftime("%H:%M:%S")
    hex_str = " ".join(f"{b:02X}" for b in buffer)
    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in buffer)
    print(f"[{ts}] ({len(buffer):3d} byte) {hex_str}    |{ascii_str}|")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
