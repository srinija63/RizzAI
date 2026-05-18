import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { useMemo } from 'react';
import { Dimensions, StyleSheet, View } from 'react-native';

const { width: W, height: H } = Dimensions.get('window');

/**
 * Slow ambient gradient orbs — non-interactive background layer.
 */
export function AmbientOrbsBackground() {
  const orbs = useMemo(
    () => [
      { top: -H * 0.08, left: -W * 0.15, size: W * 0.72, dy: 6, colors: ['rgba(244,63,94,0.22)', 'transparent'] as const },
      { top: H * 0.42, right: -W * 0.2, size: W * 0.65, dy: -5, colors: ['rgba(124,58,237,0.28)', 'transparent'] as const },
      { top: H * 0.12, left: W * 0.35, size: W * 0.55, dy: 4, colors: ['rgba(251,191,36,0.12)', 'transparent'] as const },
    ],
    [],
  );

  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.orbRoot]}>
      {orbs.map((orb, i) => (
        <MotiView
          key={i}
          from={{ opacity: 0.22 }}
          animate={{ opacity: 0.38 }}
          transition={{
            type: 'timing',
            duration: 5200 + i * 700,
            loop: true,
            repeatReverse: true,
          }}
          style={[
            styles.orbWrap,
            {
              top: orb.top + orb.dy,
              left: 'left' in orb ? orb.left : undefined,
              right: 'right' in orb ? orb.right : undefined,
              width: orb.size,
              height: orb.size,
            },
          ]}
        >
          <LinearGradient
            colors={[...orb.colors]}
            start={{ x: 0.2, y: 0.1 }}
            end={{ x: 0.9, y: 0.95 }}
            style={styles.orb}
          />
        </MotiView>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  orbRoot: {
    overflow: 'hidden',
  },
  orbWrap: {
    position: 'absolute',
    borderRadius: 9999,
  },
  orb: {
    flex: 1,
    borderRadius: 9999,
  },
});
