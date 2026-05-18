import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { StyleSheet, Text, View } from 'react-native';
import { Sparkles } from '@tamagui/lucide-icons';

import { motionSpring } from '../../theme/motion';

type Props = {
  tagline?: string;
  enterDelay?: number;
};

/** Centered Rizz AI logo — matches Stitch abstract splash screen. */
export function RizzLogoMark({ tagline = 'Dating response assistant', enterDelay = 0 }: Props) {
  return (
    <MotiView
      from={{ opacity: 0, scale: 0.88 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ ...motionSpring.gentle, delay: enterDelay }}
      style={styles.block}
    >
      <MotiView
        from={{ rotate: '0deg' }}
        animate={{ rotate: '8deg' }}
        transition={{ type: 'timing', duration: 8000, loop: true, repeatReverse: true }}
        style={styles.logoGlow}
      >
        <LinearGradient
          colors={['rgba(244,114,182,0.5)', 'rgba(251,191,36,0.35)', 'transparent']}
          style={StyleSheet.absoluteFill}
        />
      </MotiView>

      <LinearGradient
        colors={['#fbbf24', '#f472b6', '#a855f7']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.logoRing}
      >
        <View style={styles.logoCore}>
          <Sparkles size={40} color="#fde68a" />
        </View>
      </LinearGradient>

      <Text style={styles.wordmark}>Rizz AI</Text>
      {tagline ? <Text style={styles.tagline}>{tagline}</Text> : null}
    </MotiView>
  );
}

const styles = StyleSheet.create({
  block: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoGlow: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    top: 0,
  },
  logoRing: {
    padding: 3,
    borderRadius: 56,
    marginBottom: 18,
    shadowColor: '#f472b6',
    shadowOpacity: 0.5,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 10 },
    elevation: 14,
  },
  logoCore: {
    width: 104,
    height: 104,
    borderRadius: 52,
    backgroundColor: 'rgba(8,6,18,0.94)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  wordmark: {
    color: '#fff',
    fontSize: 38,
    fontWeight: '900',
    letterSpacing: 1.2,
    textShadowColor: 'rgba(244,114,182,0.45)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 14,
  },
  tagline: {
    color: 'rgba(226,232,240,0.72)',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 8,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
});
