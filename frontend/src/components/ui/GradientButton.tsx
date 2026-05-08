import { LinearGradient } from 'expo-linear-gradient';
import { ReactNode } from 'react';
import { Pressable, StyleProp, StyleSheet, Text, ViewStyle } from 'react-native';

import { premiumTheme } from '../../theme/premium';

type GradientButtonProps = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  icon?: ReactNode;
};

export function GradientButton({
  label,
  onPress,
  disabled,
  style,
  icon,
}: GradientButtonProps) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        style,
        styles.wrapper,
        pressed && styles.wrapperPressed,
        disabled && styles.disabled,
      ]}
    >
      {({ pressed }) => (
        <LinearGradient
          colors={premiumTheme.gradients.button}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.gradient, pressed && styles.gradientGlow]}
        >
          {icon}
          <Text style={styles.text}>{label}</Text>
        </LinearGradient>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    transform: [{ scale: 1 }],
  },
  wrapperPressed: {
    transform: [{ scale: 0.96 }],
  },
  gradient: {
    borderRadius: premiumTheme.radius.button,
    paddingVertical: 14,
    paddingHorizontal: 18,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 8,
    shadowColor: '#7c3aed',
    shadowOpacity: 0.22,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  gradientGlow: {
    shadowOpacity: 0.45,
    shadowRadius: 20,
    elevation: 10,
  },
  text: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  disabled: {
    opacity: 0.6,
  },
});
