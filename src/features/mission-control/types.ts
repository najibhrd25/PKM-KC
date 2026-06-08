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

