import { StyleSheet, Text, View } from 'react-native';

import type { CameraSource } from '@/services/camera/cameraSource';
import { Panel } from '@/shared/components/Panel';
import { StatusPill } from '@/shared/components/StatusPill';
import { colors } from '@/shared/theme/colors';
import { typography } from '@/shared/theme/typography';

interface VideoPanelProps {
  isOff: boolean;
  cameraVisible: boolean;
  source: CameraSource;
}

export function VideoPanel({ isOff, cameraVisible, source }: VideoPanelProps) {
  return (
    <Panel style={[styles.root, isOff && styles.off]}>
      <View style={[styles.cameraSurface, cameraVisible && !isOff && styles.cameraSurfaceActive]}>
        <View style={styles.scanline} />
        <View style={styles.reticle}>
          <View style={[styles.reticleLine, styles.reticleTop]} />
          <View style={[styles.reticleLine, styles.reticleBottom]} />
          <View style={[styles.reticleLineHorizontal, styles.reticleLeft]} />
          <View style={[styles.reticleLineHorizontal, styles.reticleRight]} />
        </View>
      </View>

      <View style={styles.topRow}>
        <StatusPill label={isOff ? 'OFFLINE' : 'LIVE'} tone={isOff ? 'idle' : 'danger'} />
      </View>

      <View style={styles.bottomBar}>
        <Text style={styles.cameraLabel}>{source.label}</Text>
        <Text style={styles.cameraMode}>{source.kind.toUpperCase()}</Text>
      </View>
    </Panel>
  );
}

const styles = StyleSheet.create({
  root: {
    aspectRatio: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  off: {
    opacity: 0.45,
  },
  cameraSurface: {
    backgroundColor: '#050505',
    flex: 1,
    opacity: 0.2,
  },
  cameraSurfaceActive: {
    opacity: 0.72,
  },
  scanline: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(220, 38, 38, 0.035)',
  },
  topRow: {
    left: 16,
    position: 'absolute',
    top: 16,
  },
  reticle: {
    alignItems: 'center',
    borderColor: 'rgba(220, 38, 38, 0.55)',
    borderWidth: 1,
    height: 160,
    justifyContent: 'center',
    left: '50%',
    marginLeft: -80,
    marginTop: -80,
    position: 'absolute',
    top: '50%',
    width: 160,
  },
  reticleLine: {
    backgroundColor: colors.red,
    height: 30,
    position: 'absolute',
    width: 2,
  },
  reticleLineHorizontal: {
    backgroundColor: colors.red,
    height: 2,
    position: 'absolute',
    width: 30,
  },
  reticleTop: {
    top: 0,
  },
  reticleBottom: {
    bottom: 0,
  },
  reticleLeft: {
    left: 0,
  },
  reticleRight: {
    right: 0,
  },
  bottomBar: {
    alignItems: 'center',
    backgroundColor: 'rgba(19, 19, 19, 0.92)',
    bottom: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    left: 0,
    paddingHorizontal: 16,
    paddingVertical: 12,
    position: 'absolute',
    right: 0,
  },
  cameraLabel: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 10,
    letterSpacing: 1,
  },
  cameraMode: {
    color: colors.text,
    fontFamily: typography.mono,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
});
