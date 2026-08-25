import type { StartupPhase } from './types';

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

