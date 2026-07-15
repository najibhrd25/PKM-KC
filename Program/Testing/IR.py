"""
Program Pembacaan 5 Sensor IR via 2x ADS1115 (I2C ADC) - Raspberry Pi
=======================================================================

Setup Hardware:
    2x modul ADS1115, share bus I2C yang sama:
        VDD = 3.3V
        GND = GND
        SCL = GPIO3 (SCL)
        SDA = GPIO2 (SDA)

    Board #1 (alamat 0x48, pin ADDR -> GND, default):
        A0 = Sensor IR 1
        A1 = Sensor IR 2
        A2 = Sensor IR 3
        A3 = Sensor IR 4

    Board #2 (alamat 0x49, pin ADDR -> VDD):
        A0 = Sensor IR 5

Setup Software (Raspberry Pi):
    1. Aktifkan I2C: sudo raspi-config -> Interface Options -> I2C
       (atau tambahkan dtparam=i2c_arm=on di /boot/firmware/config.txt)
    2. Install dependency: pip install adafruit-circuitpython-ads1x15
    3. Cek kedua board terdeteksi: sudo i2cdetect -y 1
       (harus muncul alamat 48 dan 49)

Referensi:
    https://github.com/adafruit/Adafruit_CircuitPython_ADS1x15
"""

import time

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ======================= KONFIGURASI =======================
ADDR_BOARD_2 = 0x48  # sensor IR 1-4 (A0-A3)
ADDR_BOARD_1 = 0x49  # sensor IR 5 (A0)
READ_INTERVAL = 0.1  # detik

# ------ Konfigurasi visualisasi bar ------
BAR_WIDTH = 30        # lebar bar maksimum (karakter)
RAW_MAX = 32767       # nilai raw full-scale ADS1115 single-ended (16-bit positif)
# Selisih minimum antara sensor tertinggi dengan rata-rata sensor lain agar
# dianggap ada api. Bila semua sensor mirip (selisih < ambang) = tidak ada api.
DIFF_THRESHOLD = 200


# ======================= INISIALISASI =======================
def init_sensors():
    """Inisialisasi I2C dan kedua ADS1115, return list 5 channel AnalogIn."""
    i2c = busio.I2C(board.SCL, board.SDA)

    ads1 = ADS.ADS1115(i2c, address=ADDR_BOARD_1)
    ads2 = ADS.ADS1115(i2c, address=ADDR_BOARD_2)

    channels = [
        AnalogIn(ads1, 0),  # Sensor IR 1
        AnalogIn(ads1, 1),  # Sensor IR 2
        AnalogIn(ads1, 2),  # Sensor IR 3
        AnalogIn(ads1, 3),  # Sensor IR 4
        AnalogIn(ads2, 0),  # Sensor IR 5
    ]
    return channels


# ======================= PEMBACAAN =======================
def read_sensor(channel):
    """Baca satu channel AnalogIn, return dict raw value & voltage."""
    return {"raw": channel.value, "voltage": channel.voltage}


def read_all_sensors(channels):
    """Baca seluruh channel, return list dict raw value & voltage per sensor."""
    return [read_sensor(channel) for channel in channels]


# ======================= VISUALISASI =======================
def render_bar(raw, max_raw=RAW_MAX, width=BAR_WIDTH):
    """Ubah nilai raw menjadi string bar ASCII sepanjang `width`."""
    ratio = 0.0 if max_raw <= 0 else max(0.0, min(1.0, raw / max_raw))
    filled = int(ratio * width)
    return "#" * filled + "-" * (width - filled)


# ======================= PROGRAM UTAMA =======================
if __name__ == "__main__":
    sensor_channels = init_sensors()
    print("Mulai pembacaan 5 sensor IR. Tekan Ctrl+C untuk berhenti.\n")

    try:
        while True:
            readings = read_all_sensors(sensor_channels)
            raws = [data["raw"] for data in readings]
            idx_max = raws.index(max(raws))  # kandidat area api paling intens

            # Ada api hanya bila sensor tertinggi menonjol dari sensor lain.
            # Bila semua sensor mirip (selisih < DIFF_THRESHOLD) = tidak ada api.
            others = raws[:idx_max] + raws[idx_max + 1:]
            avg_others = sum(others) / len(others) if others else 0
            selisih = raws[idx_max] - avg_others
            api_terdeteksi = selisih >= DIFF_THRESHOLD

            print("\033[H\033[J", end="")  # bersihkan layar + kursor ke atas
            print("Visualisasi 5 Sensor IR (Ctrl+C untuk berhenti)\n")
            for i, data in enumerate(readings):
                bar = render_bar(data["raw"])
                mark = "  <-- API" if i == idx_max and api_terdeteksi else ""
                print(
                    f"IR {i + 1} |{bar}| raw={data['raw']:6d}  {data['voltage']:.3f} V{mark}"
                )
            status = f"API di IR {idx_max + 1} (selisih {selisih:.0f})" if api_terdeteksi \
                else f"Tidak ada api (selisih {selisih:.0f} < {DIFF_THRESHOLD})"
            print(f"\nStatus: {status}")
            time.sleep(READ_INTERVAL)
    except KeyboardInterrupt:
        print("\nProgram dihentikan.")
