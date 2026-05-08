import { BlurView } from 'expo-blur';
import { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import { premiumTheme } from '../../theme/premium';

type GlassCardProps = {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  intensity?: number;
};

export function GlassCard({ children, style, intensity = 35 }: GlassCardProps) {
  return (
    <View style={[styles.outer, premiumTheme.shadow, style]}>
      <BlurView intensity={intensity} tint="dark" style={styles.blur}>
        {children}
      </BlurView>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    borderRadius: premiumTheme.radius.card,
    borderWidth: 1,
    borderColor: premiumTheme.colors.border,
    backgroundColor: premiumTheme.colors.surface,
    overflow: 'hidden',
  },
  blur: {
    borderRadius: premiumTheme.radius.card,
    padding: 16,
    backgroundColor: premiumTheme.colors.surface,
  },
});
