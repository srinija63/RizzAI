import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MessageCircle, MessageSquare, PenLine, ShieldCheck } from '@tamagui/lucide-icons';

import {
  AmbientOrbsBackground,
  RizzHomeActionTile,
  RizzWireframeHeartIcon,
} from '../components/ui';
import { motionSpring, staggerMs } from '../theme/motion';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export function HomeScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.wrap}>
      <LinearGradient colors={premiumTheme.gradients.romantic} style={StyleSheet.absoluteFill} />
      <AmbientOrbsBackground />
      <LinearGradient
        colors={['rgba(12,10,24,0.2)', 'rgba(8,10,22,0.88)']}
        style={StyleSheet.absoluteFill}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24 },
        ]}
      >
        <MotiView
          from={{ opacity: 0, translateY: -12 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={motionSpring.gentle}
          style={styles.header}
        >
          <View style={styles.brandRow}>
            <RizzWireframeHeartIcon variant="header" animate={false} />
            <View>
              <Text>
                <Text style={styles.brandRizz}>rizz</Text>
                <Text style={styles.brandAi}>AI</Text>
              </Text>
              <Text style={styles.brandSub}>Dating Response Assistant</Text>
            </View>
          </View>
          <View style={styles.safePill}>
            <ShieldCheck size={12} color="#86efac" />
            <Text style={styles.safeText}>Safe advice</Text>
          </View>
        </MotiView>

        <MotiView
          from={{ opacity: 0, translateY: 16 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ ...motionSpring.gentle, delay: staggerMs }}
          style={styles.hero}
        >
          <Text style={styles.heroTitle}>Your AI wingman{'\n'}for better replies</Text>
          <Text style={styles.heroBody}>
            Context-aware texts that sound like you — pick a vibe, paste a chat, choose from multiple options.
          </Text>
        </MotiView>

        <Text style={styles.sectionLabel}>What do you need?</Text>

        <View style={styles.tiles}>
          <RizzHomeActionTile
            featured
            enterDelay={staggerMs * 2}
            title="Reply coaching"
            subtitle="Paste a chat or upload a screenshot — get 3 unique replies to pick from."
            gradient={['#fbbf24', '#ea580c']}
            icon={<MessageSquare size={24} color="#111827" />}
            onPress={() => navigation.navigate('ReplySetup')}
          />
          <RizzHomeActionTile
            enterDelay={staggerMs * 3}
            title="Opener generator"
            subtitle="Turn their profile into first messages — funny, flirty, confident, or direct."
            gradient={['#f472b6', '#ec4899']}
            icon={<MessageCircle size={22} color="#fff" />}
            onPress={() => navigation.navigate('OpenerGenerator')}
          />
          <RizzHomeActionTile
            enterDelay={staggerMs * 4}
            title="Bio writer"
            subtitle="Paste your notes — get paste-ready bio variants in different styles."
            gradient={['#a78bfa', '#7c3aed']}
            icon={<PenLine size={22} color="#fff" />}
            onPress={() => navigation.navigate('BioWriter')}
          />
        </View>

        <MotiView
          from={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: staggerMs * 5 }}
          style={styles.footerNote}
        >
          <Text style={styles.footerText}>
            You choose tone & confidence — nothing is auto-selected.
          </Text>
        </MotiView>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: premiumTheme.colors.background,
  },
  content: {
    paddingHorizontal: 18,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  brandRizz: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  brandAi: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  brandSub: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
  },
  safePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: 'rgba(34,197,94,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(134,239,172,0.35)',
  },
  safeText: {
    color: '#bbf7d0',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  hero: {
    marginBottom: 20,
    gap: 10,
  },
  heroTitle: {
    color: '#f8fafc',
    fontSize: 28,
    lineHeight: 34,
    fontWeight: '900',
  },
  heroBody: {
    color: '#cbd5e1',
    fontSize: 15,
    lineHeight: 22,
  },
  sectionLabel: {
    color: '#fde68a',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  tiles: {
    gap: 12,
  },
  footerNote: {
    marginTop: 20,
    paddingHorizontal: 8,
  },
  footerText: {
    color: '#64748b',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
});
