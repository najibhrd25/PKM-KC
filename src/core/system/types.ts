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

