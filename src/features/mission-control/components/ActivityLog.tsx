import { StyleSheet, Text, View } from 'react-native';

import type { ActivityLogItem } from '@/features/mission-control/types';
import { Panel } from '@/shared/components/Panel';
import { colors } from '@/shared/theme/colors';
import { spacing } from '@/shared/theme/spacing';
import { typography } from '@/shared/theme/typography';

const logs: ActivityLogItem[] = [
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

interface ActivityLogProps {
  isOff: boolean;
  logsReady: boolean;
}

export function ActivityLog({ isOff, logsReady }: ActivityLogProps) {
  return (
    <Panel style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.title}>LOG KEJADIAN</Text>
        <Text style={styles.sync}>{isOff ? 'OFFLINE' : 'REAL-TIME SYNC'}</Text>
      </View>

      {isOff || !logsReady ? (
        <Text style={styles.empty}>{isOff ? 'SYSTEM OFFLINE' : 'INITIALIZING LOGS'}</Text>
      ) : (
        logs.map((log) => (
          <View key={log.id} style={styles.row}>
            <Text style={styles.time}>{log.time}</Text>
            <View style={styles.logBody}>
              <Text style={[styles.logTitle, toneStyles[log.tone]]}>{log.title}</Text>
              <Text style={styles.detail}>{log.detail}</Text>
            </View>
          </View>
        ))
      )}
    </Panel>
  );
}

const toneStyles = StyleSheet.create({
  danger: {
    color: colors.redSoft,
  },
  success: {
    color: colors.green,
  },
  info: {
    color: colors.text,
  },
});

const styles = StyleSheet.create({
  root: {
    padding: spacing.lg,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
  },
  title: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  sync: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 9,
    letterSpacing: 1,
  },
  empty: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 11,
    letterSpacing: 1,
    paddingVertical: spacing.xl,
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.sm,
  },
  time: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 10,
    width: 58,
  },
  logBody: {
    flex: 1,
  },
  logTitle: {
    fontFamily: typography.mono,
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
  detail: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 10,
    marginTop: 3,
  },
});

