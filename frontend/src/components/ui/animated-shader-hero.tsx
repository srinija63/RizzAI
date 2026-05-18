import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ArrowRight } from '@tamagui/lucide-icons';

import { motionSpring, staggerMs } from '../../theme/motion';
import { RizzWireframeHeartIcon } from './RizzWireframeHeartIcon';

interface HeroProps {
  onGetStarted?: () => void;
}

export default function AnimatedShaderHero({ onGetStarted }: HeroProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.root}>
      <LinearGradient
        colors={['#c026d3', '#db2777', '#7c3aed', '#0891b2', '#06b6d4']}
        locations={[0, 0.25, 0.5, 0.75, 1]}
        start={{ x: 0, y: 0.2 }}
        end={{ x: 1, y: 0.9 }}
        style={StyleSheet.absoluteFill}
      />

      <View
        style={[
          styles.content,
          {
            paddingTop: insets.top + 40,
            paddingBottom: Math.max(insets.bottom, 20),
          },
        ]}
      >
        <View style={styles.brandBlock}>
          <RizzWireframeHeartIcon />

          <MotiView
            from={{ opacity: 0, translateY: 12 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ ...motionSpring.gentle, delay: staggerMs }}
          >
            <Text style={styles.wordmark}>
              <Text style={styles.wordmarkRizz}>rizz</Text>
              <Text style={styles.wordmarkAi}>AI</Text>
            </Text>
          </MotiView>

          <MotiView
            from={{ opacity: 0, translateY: 10 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ ...motionSpring.gentle, delay: staggerMs * 2 }}
          >
            <Text style={styles.tagline}>The intelligence behind your next spark.</Text>
          </MotiView>
        </View>

        <View style={styles.ctaBlock}>
          <MotiView
            from={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ ...motionSpring.gentle, delay: staggerMs * 3 }}
            style={styles.badge}
          >
            <Text style={styles.badgeText}>LEVEL UP YOUR GAME</Text>
          </MotiView>

          <MotiView
            from={{ opacity: 0, translateY: 20 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ ...motionSpring.card, delay: staggerMs * 4 }}
          >
            <Pressable
              onPress={onGetStarted}
              style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
              accessibilityRole="button"
              accessibilityLabel="Get Started"
            >
              <LinearGradient
                colors={['#f472b6', '#e879f9', '#a855f7', '#22d3ee']}
                start={{ x: 0, y: 0.5 }}
                end={{ x: 1, y: 0.5 }}
                style={styles.primaryGradient}
              >
                <Text style={styles.primaryText}>Get Started</Text>
                <ArrowRight size={20} color="#fff" strokeWidth={2.5} />
              </LinearGradient>
            </Pressable>
          </MotiView>

          <Text style={styles.legal}>
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#581c87',
  },
  content: {
    flex: 1,
    paddingHorizontal: 28,
    justifyContent: 'space-between',
  },
  brandBlock: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 16,
  },
  wordmark: {
    textAlign: 'center',
    marginBottom: 10,
  },
  wordmarkRizz: {
    color: '#fff',
    fontSize: 42,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  wordmarkAi: {
    color: '#fff',
    fontSize: 42,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  tagline: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
    fontWeight: '400',
    paddingHorizontal: 12,
  },
  ctaBlock: {
    gap: 14,
    alignItems: 'center',
    width: '100%',
  },
  badge: {
    paddingHorizontal: 18,
    paddingVertical: 9,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.28)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.35)',
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.4,
  },
  primaryBtn: {
    width: '100%',
    borderRadius: 999,
    overflow: 'hidden',
    shadowColor: '#22d3ee',
    shadowOpacity: 0.35,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 10,
  },
  primaryGradient: {
    minHeight: 58,
    paddingHorizontal: 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  primaryText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 18,
    letterSpacing: 0.2,
  },
  legal: {
    color: 'rgba(255,255,255,0.65)',
    fontSize: 11,
    lineHeight: 16,
    textAlign: 'center',
    paddingHorizontal: 8,
    marginTop: 4,
  },
  pressed: {
    opacity: 0.88,
    transform: [{ scale: 0.98 }],
  },
});
