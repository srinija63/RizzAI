import { LinearGradient } from 'expo-linear-gradient';
import { ReactNode, useState } from 'react';
import { Pressable, StyleProp, StyleSheet, Text, ViewStyle } from 'react-native';
import { MotiView } from 'moti';

import { motionSpring } from '../../theme/motion';
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
  const [pressed, setPressed] = useState(false);

  return (
    <MotiView
      animate={{ scale: disabled ? 1 : pressed ? 0.97 : 1 }}
      transition={motionSpring.snappy}
      style={style}
    >
      <Pressable
        onPress={onPress}
        disabled={disabled}
        onPressIn={() => setPressed(true)}
        onPressOut={() => setPressed(false)}
        style={[styles.hit, disabled && styles.disabledHit]}
      >
        <LinearGradient
          colors={premiumTheme.gradients.button}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.gradient, pressed && !disabled && styles.gradientGlow]}
        >
          {icon}
          <Text style={styles.text}>{label}</Text>
        </LinearGradient>
      </Pressable>
    </MotiView>
  );
}

const styles = StyleSheet.create({
  hit: {
    borderRadius: premiumTheme.radius.button,
  },
  disabledHit: {
    opacity: 0.58,
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
});
