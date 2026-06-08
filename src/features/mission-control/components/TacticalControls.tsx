import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useJoystick } from '@/features/mission-control/hooks/useJoystick';
import { AuthModal } from '@/features/mission-control/components/AuthModal';
import { AppButton } from '@/shared/components/AppButton';
import { Panel } from '@/shared/components/Panel';
import { colors } from '@/shared/theme/colors';
import { spacing } from '@/shared/theme/spacing';
import { typography } from '@/shared/theme/typography';

interface TacticalControlsProps {
  isOff: boolean;
  isStarting: boolean;
  isManual: boolean;
  frequency: number;
  onAuthorize: (password: string) => boolean;
  onDeactivateManual: () => void;
  onShoot: () => void;
}

export function TacticalControls({
  isOff,
  isStarting,
  isManual,
  frequency,
  onAuthorize,
  onDeactivateManual,
  onShoot,
}: TacticalControlsProps) {
  const [authVisible, setAuthVisible] = useState(false);
  const locked = !isManual;
  const enabled = !isOff && !isStarting && isManual;
  const { position, panHandlers } = useJoystick(enabled);

  function requestUnlock() {
    if (isOff || isStarting) return;
    if (isManual) {
      onDeactivateManual();
      return;
    }
    setAuthVisible(true);
  }

  return (
    <Panel style={[styles.root, isOff && styles.off]}>
      <Pressable style={styles.modeButton} onPress={requestUnlock}>
        <Text style={[styles.modeText, isManual && styles.manualText]}>
          {isManual ? 'MANUAL' : 'AUTO LOCK'}
        </Text>
      </Pressable>

      <Pressable style={styles.joystick} onPress={requestUnlock}>
        <View style={styles.joystickRing} />
        <View
          {...panHandlers}
          style={[
            styles.joystickThumb,
            {
              transform: [{ translateX: position.x }, { translateY: position.y }],
            },
          ]}
        >
          <View style={[styles.joystickDot, enabled && styles.joystickDotActive]} />
        </View>
        {locked && !isOff && !isStarting && (
          <View style={styles.lockOverlay}>
            <Text style={styles.lockText}>LOCK</Text>
          </View>
        )}
      </Pressable>

      <View style={styles.bottomPanel}>
        <View>
          <Text style={styles.label}>RECOVERY MODE</Text>
          <Text style={[styles.value, enabled && styles.valueActive]}>
            {isOff ? 'OFFLINE' : isManual ? 'READY' : 'AUTO'}
          </Text>
        </View>
        <AppButton
          disabled={!enabled}
          label="SHOOT"
          style={styles.shootButton}
          onPress={onShoot}
        />
      </View>

      <Text style={styles.frequencyText}>{isOff ? '-- Hz' : `${frequency} Hz target`}</Text>

      <AuthModal
        visible={authVisible}
        onClose={() => setAuthVisible(false)}
        onSubmit={onAuthorize}
      />
    </Panel>
  );
}

const styles = StyleSheet.create({
  root: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.md,
    justifyContent: 'center',
    padding: spacing.md,
  },
  off: {
    opacity: 0.45,
  },
  modeButton: {
    alignSelf: 'flex-end',
  },
  modeText: {
    color: colors.redSoft,
    fontFamily: typography.mono,
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 1.4,
  },
  manualText: {
    color: colors.green,
  },
  joystick: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 58,
    borderWidth: 1,
    height: 116,
    justifyContent: 'center',
    overflow: 'hidden',
    width: 116,
  },
  joystickRing: {
    borderColor: 'rgba(226, 226, 226, 0.18)',
    borderRadius: 42,
    borderStyle: 'dashed',
    borderWidth: 1,
    height: 84,
    position: 'absolute',
    width: 84,
  },
  joystickThumb: {
    alignItems: 'center',
    backgroundColor: colors.surfaceHigh,
    borderColor: colors.border,
    borderRadius: 27,
    borderWidth: 1,
    height: 54,
    justifyContent: 'center',
    width: 54,
  },
  joystickDot: {
    backgroundColor: colors.muted,
    borderRadius: 5,
    height: 10,
    width: 10,
  },
  joystickDotActive: {
    backgroundColor: colors.redSoft,
  },
  lockOverlay: {
    bottom: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.62)',
    justifyContent: 'center',
  },
  lockText: {
    color: colors.redSoft,
    fontFamily: typography.mono,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
  },
  bottomPanel: {
    alignItems: 'center',
    alignSelf: 'stretch',
    backgroundColor: colors.surface,
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: spacing.md,
  },
  label: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 8,
    letterSpacing: 1.2,
  },
  value: {
    color: colors.text,
    fontFamily: typography.mono,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1.2,
    marginTop: 3,
  },
  valueActive: {
    color: colors.redSoft,
  },
  shootButton: {
    minHeight: 42,
    minWidth: 88,
  },
  frequencyText: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 9,
    letterSpacing: 1,
  },
});
