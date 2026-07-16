"""
State machine S.A.F.E — enum state operasi sistem.

Orchestrator mengubah state berdasarkan event masuk, lalu menerbitkan
perintah ke modul lain. State tidak mengontrol hardware langsung.
"""
from enum import Enum


class State(Enum):
    IDLE          = "idle"           # siaga, scanning pasif
    PRE_ALARM     = "pre_alarm"      # IR memicu, menunggu konfirmasi visual
    TRACKING      = "tracking"       # api terkonfirmasi, servo mengunci target
    EXTINGUISHING = "extinguishing"  # servo terkunci + audio menyala
    EVALUATING    = "evaluating"     # cek apakah api sudah padam
    COOLDOWN      = "cooldown"       # jeda wajib setelah operasi audio
    MANUAL        = "manual"         # kontrol joystick dari web; fusi sensor dijeda
