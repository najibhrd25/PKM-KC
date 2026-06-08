import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AppButton } from '@/shared/components/AppButton';
import { colors } from '@/shared/theme/colors';
import { spacing } from '@/shared/theme/spacing';
import { typography } from '@/shared/theme/typography';

interface AuthModalProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (password: string) => boolean;
}

export function AuthModal({ visible, onClose, onSubmit }: AuthModalProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState(false);

  function handleSubmit() {
    const success = onSubmit(password);
    if (success) {
      setPassword('');
      setError(false);
      onClose();
      return;
    }

    setPassword('');
    setError(true);
  }

  return (
    <Modal transparent animationType="fade" visible={visible} onRequestClose={onClose}>
      <View style={styles.root}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.card}>
          <Text style={styles.icon}>LOCK</Text>
          <Text style={styles.title}>AUTHORIZATION REQUIRED</Text>
          <Text style={[styles.subtitle, error && styles.error]}>
            {error ? 'ACCESS DENIED' : 'Enter maintenance password'}
          </Text>

          <TextInput
            autoCapitalize="characters"
            placeholder="PASSWORD"
            placeholderTextColor={colors.muted}
            secureTextEntry
            style={[styles.input, error && styles.inputError]}
            value={password}
            onChangeText={(value) => {
              setPassword(value);
              setError(false);
            }}
          />

          <View style={styles.actions}>
            <AppButton label="CANCEL" variant="secondary" style={styles.action} onPress={onClose} />
            <AppButton label="AUTHORIZE" style={styles.action} onPress={handleSubmit} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: {
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.76)',
    flex: 1,
    justifyContent: 'center',
    padding: spacing.xl,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    padding: spacing.xl,
    width: '100%',
  },
  icon: {
    color: colors.red,
    fontFamily: typography.mono,
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 3,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  title: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1,
    textAlign: 'center',
  },
  subtitle: {
    color: colors.muted,
    fontFamily: typography.mono,
    fontSize: 10,
    letterSpacing: 1.4,
    marginBottom: spacing.lg,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  error: {
    color: colors.redSoft,
  },
  input: {
    borderColor: colors.border,
    borderWidth: 1,
    color: colors.text,
    fontFamily: typography.mono,
    fontSize: 16,
    letterSpacing: 2,
    marginBottom: spacing.lg,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    textAlign: 'center',
  },
  inputError: {
    borderColor: colors.red,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  action: {
    flex: 1,
  },
});

