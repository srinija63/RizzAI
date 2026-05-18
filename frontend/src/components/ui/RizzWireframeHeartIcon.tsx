import { MotiView } from 'moti';
import { Image, StyleSheet, View, ViewStyle } from 'react-native';

import { motionSpring } from '../../theme/motion';

type Variant = 'hero' | 'header';

const SIZES: Record<Variant, { size: number; radius: number; glow: number }> = {
  hero: { size: 120, radius: 28, glow: 180 },
  header: { size: 44, radius: 12, glow: 0 },
};

type Props = {
  variant?: Variant;
  style?: ViewStyle;
  animate?: boolean;
};

/** rizzAI app logo from Stitch abstract logo screen. */
export function RizzWireframeHeartIcon({
  variant = 'hero',
  style,
  animate = true,
}: Props) {
  const { size, radius, glow } = SIZES[variant];
  const isHero = variant === 'hero';

  const icon = (
    <Image
      source={require('../../../assets/rizz-logo.png')}
      style={{ width: size, height: size, borderRadius: radius }}
      resizeMode="cover"
      accessibilityLabel="rizzAI logo"
    />
  );

  if (!animate) {
    return <View style={[styles.wrap, isHero && styles.wrapHero, style]}>{icon}</View>;
  }

  return (
    <MotiView
      from={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={motionSpring.gentle}
      style={[styles.wrap, isHero && styles.wrapHero, style]}
    >
      {glow > 0 ? (
        <MotiView
          from={{ opacity: 0.25 }}
          animate={{ opacity: 0.55 }}
          transition={{ type: 'timing', duration: 2200, loop: true, repeatReverse: true }}
          style={[styles.glow, { width: glow, height: glow, borderRadius: glow / 2 }]}
        />
      ) : null}
      {icon}
    </MotiView>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  wrapHero: {
    marginBottom: 22,
  },
  glow: {
    position: 'absolute',
    backgroundColor: 'rgba(236,72,153,0.22)',
  },
});
