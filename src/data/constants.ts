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
    time: '15:32:45',
    title: 'API PADAM',
    detail: 'Api berhasil dipadamkan total pada frekuensi 45 Hz (durasi 8.2s)',
    tone: 'success',
  },
  {
    id: 'log-2',
    time: '15:32:38',
    title: 'ACOUSTIC PULSE ACTIVE',
    detail: 'Memancarkan gelombang resonansi 45 Hz - Amplitudo 85%',
    tone: 'danger',
  },
  {
    id: 'log-3',
    time: '15:32:30',
    title: 'PENYESUAIAN ARAH SERVO',
    detail: 'Koreksi sudut nozzle akustik ke titik pusat api (Pan: 92°, Tilt: 44°)',
    tone: 'info',
  },
  {
    id: 'log-4',
    time: '15:32:25',
    title: 'API BELUM PADAM',
    detail: 'Percobaan awal belum padam (gangguan hembusan angin), menaikkan intensitas gelombang',
    tone: 'danger',
  },
  {
    id: 'log-5',
    time: '15:32:20',
    title: 'ACOUSTIC PULSE ACTIVE',
    detail: 'Frekuensi 40 Hz dipancarkan selama 5 detik',
    tone: 'info',
  },
  {
    id: 'log-6',
    time: '15:32:12',
    title: 'API TERDETEKSI',
    detail: 'Deteksi api terkonfirmasi (X: 142, Y: 98) Confidence 94.8%',
    tone: 'danger',
  },
  {
    id: 'log-7',
    time: '15:31:50',
    title: 'SISTEM STANDBY',
    detail: 'Mode monitoring otomatis aktif - Sensor & kamera siap',
    tone: 'info',
  },
];


