import { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import { colors } from '@/shared/theme/colors';

interface PanelProps {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function Panel({ children, style }: PanelProps) {
  return <View style={[styles.panel, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  panel: {
    backgroundColor: colors.surfaceLow,
    borderColor: colors.border,
    borderWidth: StyleSheet.hairlineWidth,
  },
});
