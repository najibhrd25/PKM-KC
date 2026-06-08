import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { SystemState } from '@/core/system/types';
import { StatusPill } from '@/shared/components/StatusPill';
import { colors } from '@/shared/theme/colors';
import { typography } from '@/shared/theme/typography';

interface MissionHeaderProps {
  state: SystemState;
  onPowerPress: () => void;
}

export function MissionHeader({ state, onPowerPress }: MissionHeaderProps) {
  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';

  return (
    <View style={styles.root}>
      <View>
        <Text style={styles.logo}>S.A.F.E.</Text>
        <StatusPill
          label={isOff ? 'OFFLINE' : isStarting ? 'STARTING' : 'ONLINE'}
          tone={isOff ? 'idle' : 'active'}
        />
      </View>

      <Pressable
        accessibilityRole="button"
        disabled={isStarting}
        onPress={onPowerPress}
        style={({ pressed }) => [
          styles.powerButton,
          isOff ? styles.powerButtonOff : styles.powerButtonOn,
          pressed && !isStarting && styles.pressed,
        ]}
      >
        <Text style={styles.powerIcon}>{isOff ? 'ON' : 'OFF'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  logo: {
    color: colors.red,
    fontSize: 26,
    fontWeight: '900',
    letterSpacing: -1,
    marginBottom: 6,
  },
  powerButton: {
    alignItems: 'center',
    borderRadius: 28,
    borderWidth: 1,
    height: 56,
    justifyContent: 'center',
    width: 56,
  },
  powerButtonOff: {
    borderColor: colors.red,
    opacity: 0.7,
  },
  powerButtonOn: {
    backgroundColor: colors.red,
    borderColor: colors.redSoft,
  },
  powerIcon: {
    color: colors.white,
    fontFamily: typography.mono,
    fontSize: 11,
    fontWeight: '800',
  },
  pressed: {
    opacity: 0.75,
    transform: [{ scale: 0.96 }],
  },
});

