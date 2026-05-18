import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { useMemo } from 'react';
import { Dimensions, StyleSheet, View } from 'react-native';

const { width: W, height: H } = Dimensions.get('window');

/**
 * Abstract splash-style background: soft gradient blobs + subtle rings (Stitch-inspired).
 */
export function RizzAbstractSplashBackground() {
  const blobs = useMemo(
    () => [
      {
        top: H * 0.08,
        left: -W * 0.2,
        size: W * 0.9,
        colors: ['rgba(236,72,153,0.35)', 'rgba(124,58,237,0.12)', 'transparent'] as const,
        dy: 8,
        duration: 5200,
      },
      {
        top: H * 0.35,
        right: -W * 0.25,
        size: W * 0.85,
        colors: ['rgba(251,191,36,0.22)', 'rgba(249,115,22,0.08)', 'transparent'] as const,
        dy: -6,
        duration: 6100,
      },
      {
        top: H * 0.55,
        left: W * 0.15,
        size: W * 0.7,
        colors: ['rgba(99,102,241,0.28)', 'rgba(168,85,247,0.1)', 'transparent'] as const,
        dy: 5,
        duration: 4800,
      },
    ],
    [],
  );

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <LinearGradient
        colors={['#05030a', '#0f0820', '#120a24', '#08060f']}
        locations={[0, 0.35, 0.7, 1]}
        style={StyleSheet.absoluteFill}
      />

      {blobs.map((blob, i) => (
        <MotiView
          key={i}
          from={{ opacity: 0.2, translateY: 0 }}
          animate={{ opacity: 0.42, translateY: blob.dy }}
          transition={{
            type: 'timing',
            duration: blob.duration,
            loop: true,
            repeatReverse: true,
          }}
          style={[
            styles.blob,
            {
              top: blob.top,
              left: 'left' in blob ? blob.left : undefined,
              right: 'right' in blob ? blob.right : undefined,
              width: blob.size,
              height: blob.size,
            },
          ]}
        >
          <LinearGradient colors={[...blob.colors]} style={styles.blobFill} />
        </MotiView>
      ))}

      <MotiView
        from={{ opacity: 0.15, scale: 0.95 }}
        animate={{ opacity: 0.28, scale: 1.05 }}
        transition={{ type: 'timing', duration: 4000, loop: true, repeatReverse: true }}
        style={styles.ringOuter}
      >
        <View style={styles.ringOuterBorder} />
      </MotiView>
      <MotiView
        from={{ opacity: 0.1, scale: 1 }}
        animate={{ opacity: 0.22, scale: 1.08 }}
        transition={{ type: 'timing', duration: 5000, loop: true, repeatReverse: true }}
        style={styles.ringInner}
      >
        <View style={styles.ringInnerBorder} />
      </MotiView>

      <LinearGradient
        colors={['transparent', 'rgba(5,3,10,0.85)']}
        style={styles.bottomFade}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  blob: {
    position: 'absolute',
    borderRadius: 9999,
    overflow: 'hidden',
  },
  blobFill: {
    flex: 1,
    borderRadius: 9999,
  },
  ringOuter: {
    position: 'absolute',
    top: H * 0.12,
    alignSelf: 'center',
    left: W / 2 - 130,
    width: 260,
    height: 260,
    borderRadius: 130,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringOuterBorder: {
    width: 260,
    height: 260,
    borderRadius: 130,
    borderWidth: 1,
    borderColor: 'rgba(251,191,36,0.2)',
  },
  ringInner: {
    position: 'absolute',
    top: H * 0.16,
    alignSelf: 'center',
    left: W / 2 - 100,
    width: 200,
    height: 200,
    borderRadius: 100,
  },
  ringInnerBorder: {
    width: 200,
    height: 200,
    borderRadius: 100,
    borderWidth: 1,
    borderColor: 'rgba(244,114,182,0.25)',
  },
  bottomFade: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: H * 0.45,
  },
});
