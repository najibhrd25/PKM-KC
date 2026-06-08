import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/shared/theme/colors';
import { typography } from '@/shared/theme/typography';

interface StatusPillProps {
  label: string;
  tone?: 'active' | 'idle' | 'danger';
}

export function StatusPill({ label, tone = 'idle' }: StatusPillProps) {
  return (
    <View style={styles.root}>
      <View style={[styles.dot, toneStyles[tone]]} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const toneStyles = StyleSheet.create({
  active: {
    backgroundColor: colors.green,
  },
  idle: {
    backgroundColor: colors.muted,
  },
  danger: {
    backgroundColor: colors.red,
  },
});

const styles = StyleSheet.create({
  root: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },
  dot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  label: {
    color: colors.text,
    fontFamily: typography.mono,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.8,
  },
});

