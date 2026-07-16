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
READ_INTERVAL = 0.3  # detik


# ======================= INISIALISASI =======================
def init_sensors():
    """Inisialisasi I2C dan kedua ADS1115, return list 5 channel AnalogIn."""
    i2c = busio.I2C(board.SCL, board.SDA)

    ads1 = ADS.ADS1115(i2c, address=ADDR_BOARD_1)
    ads2 = ADS.ADS1115(i2c, address=ADDR_BOARD_2)

    # data rate maksimum (default 128 SPS -> ~8 ms/konversi; 860 SPS -> ~1.2 ms)
    ads1.data_rate = 860
    ads2.data_rate = 860

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
    """Baca satu channel AnalogIn, return dict raw value & voltage.

    Satu konversi ADC saja: properti .value dan .voltage masing-masing
    memicu konversi single-shot terpisah. Baca raw sekali, lalu hitung
    voltage dari raw yang sama via convert_to_voltage (aritmetika murni,
    tanpa konversi kedua).
    """
    raw = channel.value
    return {"raw": raw, "voltage": channel.convert_to_voltage(raw)}


def read_all_sensors(channels):
    """Baca seluruh channel, return list dict raw value & voltage per sensor."""
    return [read_sensor(channel) for channel in channels]


# ======================= PROGRAM UTAMA =======================
if __name__ == "__main__":
    sensor_channels = init_sensors()
    print("Mulai pembacaan 5 sensor IR. Tekan Ctrl+C untuk berhenti.\n")

    try:
        while True:
            readings = read_all_sensors(sensor_channels)
            for i, data in enumerate(readings, start=1):
                print(f"Sensor IR {i}: raw={data['raw']:6d}  voltage={data['voltage']:.4f} V")
            print("-" * 40)
            time.sleep(READ_INTERVAL)
    except KeyboardInterrupt:
        print("\nProgram dihentikan.")
