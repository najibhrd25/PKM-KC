import { StyleSheet, Text, View } from 'react-native';

import { Panel } from '@/shared/components/Panel';
import { colors } from '@/shared/theme/colors';
import { spacing } from '@/shared/theme/spacing';
import { typography } from '@/shared/theme/typography';

interface SensorPanelProps {
  isOff: boolean;
  temperature: number;
  frequency: number;
}

export function SensorPanel({ isOff, temperature, frequency }: SensorPanelProps) {
  return (
    <View style={styles.stack}>
      <Panel style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.label}>AMBIENT TEMP</Text>
          <Text style={styles.icon}>TEMP</Text>
        </View>
        <Text style={styles.value}>
          {isOff ? '--' : temperature}
          {!isOff && <Text style={styles.unit}> C</Text>}
        </Text>
        <View style={styles.meterTrack}>
          <View style={[styles.temperatureMeter, { width: isOff ? '0%' : `${temperature}%` }]} />
        </View>
      </Panel>

      <Panel style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.label}>ACOUSTIC RANGE</Text>
          <Text style={[styles.status, !isOff && styles.statusActive]}>
            {isOff ? 'STANDBY' : 'ACTIVE'}
          </Text>
        </View>
        <Text style={[styles.value, styles.frequencyValue]}>
          {isOff ? '-- Hz' : `${frequency} Hz`}
        </Text>
        <View style={styles.barGroup}>
          {[15, 30, 45, 80, 100, 70, 40, 20].map((height, index) => (
            <View
              key={`${height}-${index}`}
              style={[
                styles.bar,
                {
                  height: isOff ? 3 : `${height}%`,
                  backgroundColor: isOff ? 'rgba(141, 133, 131, 0.2)' : colors.red,
                },
              ]}
            />
          ))}
        </View>
      </Panel>
    </View>
  );
}

const styles = StyleSheet.create({
  stack: {
    flex: 1,
    gap: spacing.md,
  },
  card: {
    flex: 1,
    justifyContent: 'space-between',
    padding: spacing.md,
  },
  cardHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  label: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 9,
    letterSpacing: 1.5,
  },
  icon: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 9,
  },
  status: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 8,
    letterSpacing: 1,
  },
  statusActive: {
    color: colors.blue,
  },
  value: {
    color: colors.text,
    fontSize: 34,
    fontWeight: '900',
    letterSpacing: -1,
  },
  unit: {
    color: colors.muted,
    fontSize: 16,
    fontWeight: '500',
  },
  frequencyValue: {
    color: colors.redSoft,
    fontSize: 27,
  },
  meterTrack: {
    backgroundColor: colors.surfaceHigh,
    height: 4,
    overflow: 'hidden',
  },
  temperatureMeter: {
    backgroundColor: colors.red,
    height: 4,
  },
  barGroup: {
    alignItems: 'flex-end',
    flexDirection: 'row',
    gap: 3,
    height: 34,
  },
  bar: {
    flex: 1,
    minHeight: 3,
  },
});

