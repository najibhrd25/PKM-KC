import type { ActivityLogItem } from '@/features/mission-control/types';

export const activityLogs: ActivityLogItem[] = [
  {
    id: '1',
    time: '13:22:04',
    title: 'FIRE DETECTED',
    detail: 'Accuracy 94.2% - suppressed',
    tone: 'danger',
  },
  {
    id: '2',
    time: '11:15:30',
    title: 'ROUTINE CHECK',
    detail: 'No anomaly found',
    tone: 'success',
  },
  {
    id: '3',
    time: '09:30:00',
    title: 'SENSOR CALIBRATION',
    detail: 'Temperature and acoustic modules ready',
    tone: 'info',
  },
];
