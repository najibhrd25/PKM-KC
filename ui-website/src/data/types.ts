export type SystemState =
  | 'OFF_STATE'
  | 'STARTUP_SEQUENCE'
  | 'AUTO_MODE'
  | 'MANUAL_MODE';

export interface StartupPhase {
  audioPlayed: boolean;
  filterRemoved: boolean;
  cameraVisible: boolean;
  numbersRolled: boolean;
  logsInitialized: boolean;
}

export interface ActivityLogItem {
  id: string;
  time: string;
  title: string;
  detail: string;
  tone: 'danger' | 'success' | 'info';
}

export interface JoystickPosition {
  x: number;
  y: number;
}

