# Dokumentasi Sistem Web S.A.F.E — Panduan Integrasi UI/UX Kustom

> Dokumen ini adalah **kontrak API lengkap** antara frontend dan backend
> (`web/web_bridge.py`). Ditujukan untuk mengganti dashboard bawaan
> (`web/static/index.html`) dengan UI/UX buatan sendiri.
>
> Base URL: `http://<IP_PI>:8000` (lihat `WEB_HOST` / `WEB_PORT` di
> `core/config.py`).

---

## 1. Arsitektur Singkat

```
Browser (UI Anda)
   │  HTTP / SSE / MJPEG
   ▼
WebBridge (FastAPI, web/web_bridge.py)     ← satu-satunya pintu HTTP
   │  bus.publish(event) / subscribe(event)
   ▼
EventBus ── Orchestrator ── ServoActuator / DACAudio / IRSensorArray / YOLO
```

- WebBridge **tidak memegang logika**: ia hanya menerjemahkan HTTP → event
  internal dan event internal → SSE. Semua keputusan & batas keamanan ada di
  modul lain (Orchestrator, DACAudio, ServoActuator).
- Frontend **tidak perlu tahu Event Bus** — cukup kontrak HTTP di dokumen ini.

### Dua mode operasi

| Mode | Perilaku |
|---|---|
| `auto` | Sistem mandiri: fusi IR+kamera, scanning, tracking, pemadaman. Semua perintah kontrol dari web **ditolak 409** (kecuali stop/torque_off). |
| `manual` | Fusi dijeda; UI memegang kendali penuh (servo, audio). **Wajib heartbeat** (lihat §5). |

### Aturan keamanan yang MEMPENGARUHI UI Anda

1. **Perintah "menyalakan" hanya di mode manual** — `audio play`,
   `servo home/move`, `jog` → 409 bila mode ≠ manual. UI harus menonaktifkan
   tombol-tombol ini di mode auto (server tetap menolak walau UI lupa).
2. **Perintah "mematikan" selalu diterima** dari mode apa pun:
   `audio stop`, `servo torque_off`.
3. **Clamp keras di backend** (bukan tugas UI, tapi UI sebaiknya mencerminkan):
   amplitudo ≤ `amplitude_max`, durasi ≤ `duration_max`, sudut servo di-clamp
   ke `yaw_min..yaw_max` / `pitch_min..pitch_max`. Ambil nilainya dari
   `GET /config` (§3.2) — **jangan hardcode**.
4. **Keluar dari manual = audio langsung dihentikan** oleh Orchestrator, baik
   karena user menekan AUTO maupun karena heartbeat timeout.
5. Amplitudo efektif maksimum untuk sinyal float adalah **1.0**; nilai di atas
   itu ter-clipping di DAC (distorsi), bukan bertambah keras.

---

## 2. Ringkasan Endpoint

| Endpoint | Metode | Fungsi | Gating |
|---|---|---|---|
| `/` | GET | Dashboard bawaan (HTML) | — |
| `/stream` | GET | Video MJPEG live | — |
| `/events` | GET | SSE status real-time | — |
| `/logs` | GET | Riwayat log kejadian (JSON) | — |
| `/config` | GET | Batas & default untuk UI | — |
| `/cmd/mode` | POST | Ganti mode auto/manual | — |
| `/cmd/jog` | POST | Servo inkremental (joystick) | manual saja |
| `/cmd/servo` | POST | home / torque_off / move | home & move: manual saja |
| `/cmd/audio` | POST | play / stop audio DAC | play: manual saja |
| `/heartbeat` | POST | Tanda UI hidup (mode manual) | — |

Semua POST memakai `Content-Type: application/json`. Respons sukses:
`{"ok": true, ...}` (HTTP 200). Respons gagal: `{"ok": false, "error": "..."}`
dengan HTTP **409** (bukan mode manual) atau **400** (action tidak dikenal).

---

## 3. Endpoint Baca (GET)

### 3.1 `GET /stream` — video live

MJPEG (`multipart/x-mixed-replace; boundary=frame`), maksimum ~20 fps.
Pemakaian paling sederhana di HTML:

```html
<img src="http://<IP_PI>:8000/stream" />
```

Frame beranotasi (kotak deteksi) hanya muncul saat `YOLODetector` aktif;
dengan FakeDetector stream kosong.

### 3.2 `GET /config` — batas & default UI

Panggil **sekali saat halaman dimuat**; gunakan untuk mengisi `min`/`max`
input, langkah joystick, dan tata letak panel IR.

```json
{
  "freq_default":   45.0,
  "amplitude_max":  0.3,     // batas keras amplitudo (config.AMPLITUDE_MAX_SAFE)
  "duration_max":   30.0,    // detik (config.AUDIO_MAX_DURATION)
  "yaw_min": 135.0,  "yaw_max": 225.0,
  "pitch_min": 135.0, "pitch_max": 225.0,
  "jog_step_deg":   3.0,     // langkah jog yang disarankan per tick
  "ir_threshold_v": 1.5,     // ambang "terpicu" per sensor (volt)
  "n_ir":           5,       // jumlah sensor IR
  "ir_reverse":     true     // true = urutan fisik sensor mirror thd kamera;
}                            //   bila true, render bar IR terbalik (S5 kiri)
```

### 3.3 `GET /logs` — riwayat log kejadian

Array (ring buffer, maksimum 200 entri, terlama → terbaru):

```json
[ {"t": 1752600000.123, "msg": "Mode: MANUAL"},
  {"t": 1752600004.582, "msg": "Audio ON: 45.0 Hz sine amp=0.3"} ]
```

`t` = Unix epoch (detik, float). Gunakan untuk mengisi panel log saat halaman
dibuka; entri baru selanjutnya datang lewat SSE `type: "log"` (§4).

Pesan yang dicatat backend: perubahan state & mode, deteksi api
muncul/hilang (transisi saja), pemadaman selesai, audio ON/OFF,
servo torque ON/OFF, IR panas muncul/hilang (transisi saja, dengan arah).

---

## 4. `GET /events` — Status Real-time (SSE)

Server-Sent Events standar; setiap pesan satu baris `data: {json}`.

```js
const es = new EventSource("http://<IP_PI>:8000/events");
es.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  switch (msg.type) { /* lihat tabel di bawah */ }
};
```

### Katalog tipe pesan

| `type` | Kapan dikirim | Payload |
|---|---|---|
| `state` | tiap transisi state machine | `{"value": "idle"\|"pre_alarm"\|"tracking"\|"extinguishing"\|"evaluating"\|"cooldown"\|"manual"}` |
| `mode` | tiap ganti mode | `{"value": "auto"\|"manual"}` |
| `detection` | tiap frame ada api (bisa sering!) | `{"bbox": [cx,cy,w,h], "confidence": 0.91}` — piksel, cx/cy = pusat kotak |
| `ir` | maks tiap **0.2 s** (throttle) | lihat di bawah |
| `audio` | saat mulai & berhenti playback | `{"playing": true, "freq": 45.0, "amplitude": 0.3, "duration": 10.0, "waveform": "sine"}` atau `{"playing": false}` |
| `servo` | saat posisi/torsi berubah | `{"yaw_deg": 183.0, "pitch_deg": 178.5, "torque": true}` |
| `log` | tiap entri log baru | `{"t": 1752600000.0, "msg": "Mode: MANUAL"}` |

### Payload `ir` (detail)

```json
{
  "type": "ir",
  "sensors": [
    {"sensor_id": 1, "raw": 12345, "voltage": 1.54, "triggered": true},
    ... (n_ir sensor, urut sensor_id)
  ],
  "ir_hot": true,      // deteksi diferensial: ada sumber panas menonjol
  "ir_x": -0.42        // arah panas -1 (kiri) .. +1 (kanan), null bila tak ada
}
```

- `voltage` 0..3.3 V; `triggered` = voltage ≥ `ir_threshold_v`.
- `ir_x` **sudah dikoreksi `ir_reverse`** — langsung bisa dipetakan ke layar
  (−1 = kiri frame kamera, +1 = kanan). Untuk menampilkan bar per-sensor yang
  konsisten dengan arah ini, balik urutan render bila `ir_reverse: true`.
- Wajib UI: `detection` bisa datang puluhan kali per detik saat api terlihat —
  jangan lakukan render berat di handler ini.

### Perilaku penting SSE

- Pesan hanya berisi **perubahan sejak connect** — tidak ada snapshot awal.
  Saat halaman dimuat: asumsikan mode `auto`, isi log dari `GET /logs`, dan
  tunggu event berikutnya. (Panel IR terisi ≤ 0.2 s karena IR terus mengalir.)
- Bila koneksi putus, `EventSource` reconnect otomatis (perilaku browser).

---

## 5. Mode & Heartbeat (WAJIB untuk mode manual)

### `POST /cmd/mode`

```json
{"mode": "manual"}        // atau "auto"
```

Respons: `{"ok": true, "mode": "manual"}`. Konfirmasi resmi datang via SSE
`{"type":"mode","value":"manual"}` — **update UI dari SSE**, bukan dari
respons POST, supaya UI juga benar saat mode diubah pihak lain (mis. watchdog).

### `POST /heartbeat`

Body kosong (atau apa pun). Selama mode `manual`, UI **wajib** POST
`/heartbeat` secara berkala. Bila backend tidak menerima heartbeat selama
`WEB_HEARTBEAT_TIMEOUT` (**5 detik**), sistem otomatis kembali ke `auto`
(dan audio manual dimatikan). Rekomendasi: interval **2 detik**, hanya saat
mode manual:

```js
setInterval(() => {
  if (mode === "manual") fetch(BASE + "/heartbeat", { method: "POST" });
}, 2000);
```

Ini fitur keselamatan — jangan di-bypass dengan heartbeat permanen; kirim
hanya selagi tab/UI benar-benar aktif memegang kendali.

---

## 6. Endpoint Kontrol (POST)

### 6.1 `POST /cmd/jog` — servo inkremental (untuk joystick)

```json
{"d_yaw": 3.0, "d_pitch": -1.5}     // delta derajat dari posisi sekarang
```

- 409 bila mode ≠ manual.
- Posisi hasil di-clamp otomatis ke rentang servo.
- Pola joystick yang dipakai dashboard bawaan: kirim tiap **100 ms** selama
  knob ditarik, besaran = `defleksi_ternormalisasi × jog_step_deg`.
- Umpan balik posisi datang via SSE `servo`.

### 6.2 `POST /cmd/servo` — aksi diskret

| `action` | Body tambahan | Efek | Gating |
|---|---|---|---|
| `"home"` | — | ke posisi netral 180/180 | manual saja |
| `"move"` | `yaw_deg`, `pitch_deg` (absolut, derajat) | posisi absolut (di-clamp) | manual saja |
| `"torque_off"` | — | torsi kedua servo mati (bisa digerakkan tangan) | **selalu boleh** |

```json
{"action": "move", "yaw_deg": 200.0, "pitch_deg": 170.0}
```

Catatan: setelah `torque_off`, perintah gerak berikutnya (jog/home/move)
otomatis menyalakan torsi kembali — UI tidak perlu aksi "torque on" terpisah.
Status torsi ada di SSE `servo.torque`.

### 6.3 `POST /cmd/audio` — kontrol DAC

**Stop** (selalu boleh, dari mode apa pun):

```json
{"action": "stop"}
```

**Play** (manual saja; 409 bila tidak):

```json
{
  "action":   "play",
  "waveform": "sine",       // sine | square | sawtooth | triangle | sweep | pulse
  "freq":      45.0,        // Hz
  "amplitude": 0.3,         // di-clamp ke amplitude_max di backend
  "duration":  10.0         // detik, di-clamp ke duration_max
}
```

Parameter tambahan per waveform:

| Waveform | Parameter ekstra | Keterangan |
|---|---|---|
| `sine` / `square` / `sawtooth` / `triangle` | — | pakai `freq` + `duration` |
| `sweep` | `f_start`, `f_end` (Hz) | chirp linier `f_start`→`f_end` sepanjang `duration`; default `f_start=freq`, `f_end=freq*2` |
| `pulse` | `n_cycles` (int ≥1), `pulse_waveform` (`"sine"`\|`"square"`), `inverted` (bool), `half_cycle` (bool) | durasi = `n_cycles / freq` (mengabaikan `duration`); `n_cycles` di-clamp agar durasi ≤ `duration_max` |

Perilaku:
- Bila masih ada playback berjalan, perintah play baru **diabaikan** backend
  (cek SSE `audio.playing` sebelum mengirim, atau kirim `stop` dulu).
- `playing: false` dikirim baik saat dihentikan manual maupun saat playback
  selesai alami — UI cukup mengikuti SSE, tanpa timer sendiri.
- Waveform tak dikenal → fallback `sine` (tidak error).

---

## 7. Log Kejadian di UI

1. Saat load: `GET /logs` → render semua entri.
2. Streaming: SSE `type: "log"` → append.
3. Format waktu: `t` epoch detik → jam lokal (`new Date(t * 1000)`).
4. Backend menyimpan maksimum 200 entri; samakan batas di DOM.

---

## 8. Menghubungkan UI Anda

### Opsi A — ganti file dashboard (paling mudah, tanpa ubah backend)

Timpa `safe/web/static/index.html` dengan build UI Anda. `GET /` menyajikan
file itu apa adanya. Satu file HTML self-contained (CSS/JS inline) paling
aman; aset terpisah perlu route static tambahan (lihat Opsi B).

### Opsi B — hosting terpisah (dev server React/Vue, atau server lain)

UI di origin lain (mis. `http://localhost:5173`) akan diblokir browser (CORS)
karena WebBridge belum memasang middleware CORS. Tambahkan di
`web/web_bridge.py`, di dalam `_serve()` setelah `app = FastAPI()`:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # persempit di produksi
    allow_methods=["*"],
    allow_headers=["*"],
)
```

MJPEG `<img src>` dan `EventSource` lintas origin umumnya jalan tanpa CORS,
tetapi semua `fetch()` POST membutuhkannya.

### Kerangka klien minimal (JS)

```js
const BASE = "http://<IP_PI>:8000";
let mode = "auto";
let LIMITS = null;

async function init() {
  LIMITS = await (await fetch(BASE + "/config")).json();
  (await (await fetch(BASE + "/logs")).json()).forEach(renderLog);

  const es = new EventSource(BASE + "/events");
  es.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "mode")  { mode = m.value; renderMode(m.value); }
    if (m.type === "state") renderState(m.value);
    if (m.type === "ir")    renderIR(m);          // maks 2x/detik
    if (m.type === "servo") renderServo(m);
    if (m.type === "audio") renderAudio(m);
    if (m.type === "log")   renderLog(m);
    if (m.type === "detection") renderDetection(m); // bisa sangat sering
  };

  setInterval(() => {                              // heartbeat wajib
    if (mode === "manual") fetch(BASE + "/heartbeat", { method: "POST" });
  }, 2000);
}

async function cmd(path, body) {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) console.warn("ditolak: bukan mode manual");
  return r.ok;
}

// contoh pemakaian:
// cmd("/cmd/mode",  { mode: "manual" });
// cmd("/cmd/audio", { action: "play", waveform: "sine",
//                     freq: LIMITS.freq_default,
//                     amplitude: LIMITS.amplitude_max, duration: 10 });
// cmd("/cmd/servo", { action: "move", yaw_deg: 200, pitch_deg: 170 });
// cmd("/cmd/jog",   { d_yaw: LIMITS.jog_step_deg, d_pitch: 0 });
```

### Checklist integrasi

- [ ] `GET /config` saat load; semua batas input dari sini (tanpa hardcode)
- [ ] `GET /logs` untuk isi awal panel log
- [ ] `EventSource("/events")` + handler 7 tipe pesan
- [ ] Mode di-update dari SSE `mode` (bukan dari respons POST)
- [ ] Heartbeat 2 s hanya saat manual
- [ ] Kontrol manual dinonaktifkan (disabled) saat mode ≠ manual
- [ ] Tangani 409 dengan anggun (toast/disable, jangan retry loop)
- [ ] `<img src="/stream">` untuk video
- [ ] Bar IR dibalik urutannya bila `ir_reverse: true`
- [ ] Joystick: interval 100 ms, berhenti kirim saat dilepas / defleksi ≈ 0

---

## 9. Uji Cepat via curl

```bash
BASE=http://<IP_PI>:8000

curl $BASE/config                                   # batas UI
curl $BASE/logs                                     # riwayat log
curl -N $BASE/events                                # SSE (Ctrl+C utk keluar)

curl -X POST $BASE/cmd/mode  -H "Content-Type: application/json" -d '{"mode":"manual"}'
curl -X POST $BASE/heartbeat
curl -X POST $BASE/cmd/jog   -H "Content-Type: application/json" -d '{"d_yaw":3,"d_pitch":0}'
curl -X POST $BASE/cmd/servo -H "Content-Type: application/json" -d '{"action":"home"}'
curl -X POST $BASE/cmd/audio -H "Content-Type: application/json" \
     -d '{"action":"play","waveform":"sine","freq":45,"amplitude":0.1,"duration":3}'
curl -X POST $BASE/cmd/audio -H "Content-Type: application/json" -d '{"action":"stop"}'
curl -X POST $BASE/cmd/mode  -H "Content-Type: application/json" -d '{"mode":"auto"}'
```

> Ingat: tanpa heartbeat berkala, mode manual otomatis kembali ke AUTO
> setelah 5 detik — saat menguji manual via curl, kirim `/heartbeat`
> di sela-sela perintah.

---

## 10. Referensi Kode

| Apa | Di mana |
|---|---|
| Semua endpoint & SSE | `web/web_bridge.py` |
| Dashboard bawaan (contoh implementasi lengkap klien) | `web/static/index.html` |
| Batas & parameter | `core/config.py` |
| Definisi event internal | `core/events.py` |
| Kontrak integrasi level event bus | `../INTEGRATION.md` |
| Arsitektur sistem penuh | `../DOKUMENTASI_SISTEM.md` |
