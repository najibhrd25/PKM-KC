import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { MissionHeader } from '@/features/mission-control/components/MissionHeader';
import { VideoPanel } from '@/features/mission-control/components/VideoPanel';
import { SensorPanel } from '@/features/mission-control/components/SensorPanel';
import { TacticalControls } from '@/features/mission-control/components/TacticalControls';
import { ActivityLog } from '@/features/mission-control/components/ActivityLog';
import { developmentCameraSource } from '@/services/camera/cameraSource';
import { triggerAcousticPulse } from '@/services/safe-api/safeApi';
import { colors } from '@/shared/theme/colors';
import { spacing } from '@/shared/theme/spacing';
import { typography } from '@/shared/theme/typography';
import { useSystemState } from '@/store/useSystemState';

export function MissionControlScreen() {
  const {
    authPassword,
    deactivateManual,
    frequency,
    isManual,
    powerOff,
    powerOn,
    startupPhase,
    state,
    temperature,
  } = useSystemState();

  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';
  const contentDisabled = isOff || (isStarting && !startupPhase.filterRemoved);

  function handlePowerPress() {
    if (isOff) {
      powerOn();
      return;
    }

    Alert.alert('Shutdown all systems?', 'All modules will return to cold standby.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Shutdown', style: 'destructive', onPress: powerOff },
    ]);
  }

  function handleShoot() {
    triggerAcousticPulse({ action: 'shoot', frequency }).catch(() => {});
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <MissionHeader state={state} onPowerPress={handlePowerPress} />

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.heroText}>
          <Text style={styles.eyebrow}>
            {isOff ? 'COLD STANDBY' : isStarting ? 'INITIALIZING' : 'ACTIVE MONITORING'}
          </Text>
          <Text style={styles.title}>MISSION CONTROL</Text>
        </View>

        <View style={contentDisabled && styles.systemOff}>
          <VideoPanel
            cameraVisible={startupPhase.cameraVisible}
            isOff={isOff}
            source={developmentCameraSource}
          />

          <View style={styles.middleGrid}>
            <SensorPanel
              frequency={frequency}
              isOff={isOff}
              temperature={temperature}
            />
            <TacticalControls
              frequency={frequency}
              isManual={isManual}
              isOff={isOff}
              isStarting={isStarting}
              onAuthorize={authPassword}
              onDeactivateManual={deactivateManual}
              onShoot={handleShoot}
            />
          </View>

          <ActivityLog isOff={isOff} logsReady={startupPhase.logsInitialized} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.lg,
  },
  heroText: {
    gap: 4,
    paddingTop: spacing.sm,
  },
  eyebrow: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 10,
    letterSpacing: 2.4,
  },
  title: {
    color: colors.text,
    fontSize: 30,
    fontWeight: '900',
    letterSpacing: -1,
  },
  systemOff: {
    opacity: 0.62,
  },
  middleGrid: {
    flexDirection: 'row',
    gap: spacing.md,
    minHeight: 286,
  },
});

