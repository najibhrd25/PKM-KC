import type { ActivityLogItem, StartupPhase } from './types';

export const MANUAL_MODE_PASSWORD = 'ITS2024';

export const initialStartupPhase: StartupPhase = {
  audioPlayed: false,
  filterRemoved: false,
  cameraVisible: false,
  numbersRolled: false,
  logsInitialized: false,
};

export const STARTUP_TIMELINE_MS = {
  audio: 0,
  filter: 500,
  camera: 1000,
  sensors: 1500,
  logs: 1800,
  autoMode: 2000,
} as const;

export const LIVE_SENSOR_SNAPSHOT = {
  temperature: 32,
  frequency: 45,
} as const;

export const INITIAL_ACTIVITY_LOGS: ActivityLogItem[] = [
  {
    id: 'log-1',
    time: '09:48:12',
    title: 'API GAGAL DIPADAMKAN (ALARM)',
    detail: 'Setelah 2x percobaan pemadaman (±60 detik), nyala api masih aktif. Protokol evakuasi & alarm darurat diaktifkan.',
    tone: 'danger',
  },
  {
    id: 'log-2',
    time: '09:47:10',
    title: 'FIRE DETECTED',
    detail: 'Deteksi visual mengonfirmasi adanya api aktif (Confidence: 91.2%, Koordinat pan-tilt terkunci).',
    tone: 'danger',
  },
  {
    id: 'log-3',
    time: '14:15:32',
    title: 'API BERHASIL DIPADAMKAN',
    detail: 'Api padam total setelah pemancaran gelombang akustik 45 Hz durasi 10 detik. Area dinyatakan aman.',
    tone: 'success',
  },
  {
    id: 'log-4',
    time: '14:15:22',
    title: 'FIRE DETECTED',
    detail: 'Deteksi visual mengonfirmasi api aktif (Confidence: 93.4%). Melacak & memancarkan gelombang akustik.',
    tone: 'danger',
  },
  {
    id: 'log-5',
    time: '14:15:10',
    title: 'SISTEM STANDBY & SCANNING',
    detail: 'Kamera visual dan sensor pemantau aktif memindai area sektor pengawasan.',
    tone: 'info',
  },
];


