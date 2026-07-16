"""
Program Uji Coba Servo Dynamixel MX-106 (Protocol 1.0) - Raspberry Pi
=======================================================================

Setup Software (Raspberry Pi):
    1. Install Dynamixel SDK: pip3 install --break-system-packages dynamixel-sdk
    2. Aktifkan UART:
        sudo raspi-config -> Interface Options -> Serial Port
            - "Would you like a login shell over serial?" -> No
            - "Would you like the serial port hardware enabled?" -> Yes
       (pastikan /boot/firmware/config.txt punya enable_uart=1)
    3. Reboot

Setup Hardware:
    - GPIO14 (TXD) -> DI modul UART-RS485 (auto direction)
    - GPIO15 (RXD) -> RO modul UART-RS485 (auto direction)
    - A/B RS485 -> bus Dynamixel (semua servo paralel, ID 1-4)
    - MX-106 disuplai 12V terpisah (jangan dari 5V Raspberry Pi)

Referensi:
    https://emanual.robotis.com/docs/en/dxl/mx/mx-106/
"""

import time

from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    GroupSyncWrite,
    COMM_SUCCESS,
    DXL_LOBYTE,
    DXL_HIBYTE,
)

# ======================= KONFIGURASI =======================
PROTOCOL_VERSION = 1.0
# Pi 5: /dev/serial0 -> ttyAMA10 (UART Bluetooth, bukan GPIO14/15).
# Dengan dtparam=uart0=on, GPIO14/15 muncul sebagai /dev/ttyAMA0.
DEVICENAME = "/dev/ttyAMA0"
BAUDRATE = 1000000

# Control table address (Protocol 1.0 - MX-106)
ADDR_CW_ANGLE_LIMIT = 6
ADDR_CCW_ANGLE_LIMIT = 8
ADDR_TORQUE_ENABLE = 24
ADDR_MOVING_SPEED = 32
ADDR_GOAL_POSITION = 30
ADDR_PRESENT_POSITION = 36

# ID servo per axis
ID_X = 1
ID_Y = 2
ID_Z1 = 3
ID_Z2 = 4
ALL_IDS = (ID_X, ID_Y, ID_Z1, ID_Z2)

# Arah putaran (wheel mode)
CCW = 0  # maju
CW = 1   # mundur

TEST_SPEED = 100  # sesuai 'laju' di kode STM32

# Resolusi posisi MX-106/MX-64 (Protocol 1.0): 0-4095 ~ 0-360 derajat
POSITION_MIN = 0
POSITION_MAX = 4095
ANGLE_MAX = 360.0

SCAN_ID_RANGE = range(0, 253)  # rentang ID yang di-scan saat startup


# ======================= INISIALISASI =======================
def init_dynamixel():
    """Buka port serial & siapkan packet handler. Return (port_handler, packet_handler)."""
    port_handler = PortHandler(DEVICENAME)
    packet_handler = PacketHandler(PROTOCOL_VERSION)

    if port_handler.openPort():
        print(f"Port {DEVICENAME} berhasil dibuka")
    else:
        print(f"Gagal membuka port {DEVICENAME}")

    if port_handler.setBaudRate(BAUDRATE):
        print(f"Baudrate diset ke {BAUDRATE}")
    else:
        print(f"Gagal set baudrate {BAUDRATE}")

    return port_handler, packet_handler


def scan_ids(port_handler, packet_handler, id_range=SCAN_ID_RANGE):
    """Scan seluruh ID Dynamixel yang terhubung di bus. Return list ID yang terdeteksi."""
    print("\n=== Scan ID Dynamixel ===")
    found_ids = []
    for dxl_id in id_range:
        model_number, result, _ = packet_handler.ping(port_handler, dxl_id)
        if result == COMM_SUCCESS:
            print(f"[ID {dxl_id}] Terdeteksi, model number: {model_number}")
            found_ids.append(dxl_id)

    if found_ids:
        print(f"Total servo terdeteksi: {len(found_ids)} -> {found_ids}")
    else:
        print("Tidak ada servo terdeteksi!")

    return found_ids


def set_torque(port_handler, packet_handler, dxl_id, enable):
    """Enable/disable torque servo (1=on, 0=off)."""
    result, error = packet_handler.write1ByteTxRx(port_handler, dxl_id, ADDR_TORQUE_ENABLE, enable)
    if result != COMM_SUCCESS:
        print(f"[ID {dxl_id}] Gagal set torque: {packet_handler.getTxRxResult(result)}")
    elif error != 0:
        print(f"[ID {dxl_id}] Error set torque: {packet_handler.getRxPacketError(error)}")
    else:
        print(f"[ID {dxl_id}] Torque {'ON' if enable else 'OFF'}")


def set_wheel_mode(port_handler, packet_handler, dxl_id):
    """Set CW & CCW angle limit ke 0 -> wheel mode (rotasi kontinu)."""
    packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_CW_ANGLE_LIMIT, 0)
    result, error = packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_CCW_ANGLE_LIMIT, 0)
    if result != COMM_SUCCESS:
        print(f"[ID {dxl_id}] Gagal set wheel mode: {packet_handler.getTxRxResult(result)}")
    elif error != 0:
        print(f"[ID {dxl_id}] Error set wheel mode: {packet_handler.getRxPacketError(error)}")
    else:
        print(f"[ID {dxl_id}] Wheel mode aktif")


def set_joint_mode(port_handler, packet_handler, dxl_id, cw_limit=POSITION_MIN, ccw_limit=POSITION_MAX):
    """Set CW & CCW angle limit ke rentang non-zero -> joint mode (kontrol posisi/sudut)."""
    packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_CW_ANGLE_LIMIT, cw_limit)
    result, error = packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_CCW_ANGLE_LIMIT, ccw_limit)
    if result != COMM_SUCCESS:
        print(f"[ID {dxl_id}] Gagal set joint mode: {packet_handler.getTxRxResult(result)}")
    elif error != 0:
        print(f"[ID {dxl_id}] Error set joint mode: {packet_handler.getRxPacketError(error)}")
    else:
        print(f"[ID {dxl_id}] Joint mode aktif")


# ======================= FUNGSI GERAK =======================
def _speed_value(direction, speed):
    """Hitung nilai Moving Speed: 0-1023 = CCW, 1024-2047 = CW."""
    return speed if direction == CCW else 1024 + speed


def move_axis(port_handler, packet_handler, dxl_id, direction, speed):
    """Gerakkan 1 servo (axis X atau Y) dengan arah & kecepatan tertentu."""
    value = _speed_value(direction, speed)
    result, error = packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_MOVING_SPEED, value)
    if result != COMM_SUCCESS:
        print(f"[ID {dxl_id}] Gagal gerak: {packet_handler.getTxRxResult(result)}")
    elif error != 0:
        print(f"[ID {dxl_id}] Error gerak: {packet_handler.getRxPacketError(error)}")


def move_axis_z(port_handler, packet_handler, direction, speed):
    """Gerakkan axis Z (servo ID_Z1 & ID_Z2 sekaligus via sync write)."""
    value = _speed_value(direction, speed)
    param = [DXL_LOBYTE(value), DXL_HIBYTE(value)]

    group_sync_write = GroupSyncWrite(port_handler, packet_handler, ADDR_MOVING_SPEED, 2)
    group_sync_write.addParam(ID_Z1, param)
    group_sync_write.addParam(ID_Z2, param)

    result = group_sync_write.txPacket()
    if result != COMM_SUCCESS:
        print(f"[ID {ID_Z1},{ID_Z2}] Gagal gerak axis Z: {packet_handler.getTxRxResult(result)}")

    group_sync_write.clearParam()


def stop_axis(port_handler, packet_handler, dxl_id):
    """Hentikan 1 servo (axis X/Y)."""
    move_axis(port_handler, packet_handler, dxl_id, CCW, 0)


def stop_axis_z(port_handler, packet_handler):
    """Hentikan axis Z (servo ID_Z1 & ID_Z2)."""
    move_axis_z(port_handler, packet_handler, CCW, 0)


# ======================= FUNGSI GERAK (JOINT MODE / SUDUT) =======================
def angle_to_position(angle_deg):
    """Konversi sudut (0-360 derajat) ke nilai posisi (0-4095)."""
    angle_deg = max(0.0, min(ANGLE_MAX, angle_deg))
    return int(round(angle_deg / ANGLE_MAX * POSITION_MAX))


def position_to_angle(position):
    """Konversi nilai posisi (0-4095) ke sudut (derajat)."""
    return position / POSITION_MAX * ANGLE_MAX


def move_to_angle(port_handler, packet_handler, dxl_id, angle_deg, speed=TEST_SPEED):
    """Gerakkan servo ke sudut tertentu (0-360 derajat) dalam joint mode."""
    position = angle_to_position(angle_deg)
    packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_MOVING_SPEED, speed)
    result, error = packet_handler.write2ByteTxRx(port_handler, dxl_id, ADDR_GOAL_POSITION, position)
    if result != COMM_SUCCESS:
        print(f"[ID {dxl_id}] Gagal gerak ke sudut: {packet_handler.getTxRxResult(result)}")
    elif error != 0:
        print(f"[ID {dxl_id}] Error gerak ke sudut: {packet_handler.getRxPacketError(error)}")
    else:
        print(f"[ID {dxl_id}] Bergerak ke {angle_deg:.1f} derajat (posisi {position})")


def read_angle(port_handler, packet_handler, dxl_id):
    """Baca posisi servo sekarang (derajat). Return None kalau tidak ada status packet.

    Error non-fatal (misal Input Voltage Error) diabaikan karena data posisi
    pada status packet tetap valid walau bit error tersebut aktif.
    """
    position, result, _ = packet_handler.read2ByteTxRx(port_handler, dxl_id, ADDR_PRESENT_POSITION)
    if result != COMM_SUCCESS:
        print(f"[ID {dxl_id}] Gagal baca posisi: {packet_handler.getTxRxResult(result)}")
        return None
    return position_to_angle(position)


def wait_until_reached(port_handler, packet_handler, dxl_id, target_angle, timeout=5.0, interval=0.1, tolerance=1.0):
    """Tampilkan posisi servo secara berkala selagi bergerak menuju target_angle.

    Berhenti memantau kalau posisi sudah dekat target, posisi berhenti berubah,
    atau timeout (detik) tercapai.
    """
    start = time.time()
    last_angle = None
    while time.time() - start < timeout:
        current = read_angle(port_handler, packet_handler, dxl_id)
        if current is not None:
            print(f"[ID {dxl_id}] Posisi: {current:.1f} derajat")
            if abs(current - target_angle) <= tolerance:
                break
            if last_angle is not None and abs(current - last_angle) < 0.1:
                break
            last_angle = current
        time.sleep(interval)


# ======================= PROGRAM INTERAKTIF =======================
if __name__ == "__main__":
    port_handler, packet_handler = init_dynamixel()
    active_ids = set()

    try:
        scan_ids(port_handler, packet_handler)

        print("\n=== Kontrol manual servo (joint mode) ===")
        print("Format: <id> <sudut 0-360>")
        print("Contoh: 1 90")
        print("Ketik 'exit' untuk keluar.\n")

        while True:
            raw = input("> ").strip()
            if raw.lower() in ("exit", "quit", "q"):
                break
            if not raw:
                continue

            parts = raw.split()
            if len(parts) != 2:
                print("Format salah. Contoh: 1 90")
                continue

            try:
                dxl_id = int(parts[0])
                angle = float(parts[1])
            except ValueError:
                print("ID harus angka bulat, sudut harus angka.")
                continue

            if dxl_id not in active_ids:
                set_torque(port_handler, packet_handler, dxl_id, 1)
                set_joint_mode(port_handler, packet_handler, dxl_id)
                active_ids.add(dxl_id)

            move_to_angle(port_handler, packet_handler, dxl_id, angle)
            wait_until_reached(port_handler, packet_handler, dxl_id, angle)

    finally:
        print("\n=== Mematikan torque & menutup port ===")
        for dxl_id in active_ids:
            set_torque(port_handler, packet_handler, dxl_id, 0)
        port_handler.closePort()
