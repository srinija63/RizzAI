import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Sparkles } from '@tamagui/lucide-icons';

import { motionSpring, staggerMs } from '../../theme/motion';

export type ReplyTone = 'funny' | 'flirty' | 'confident' | 'direct';

type Persona = {
  id: ReplyTone;
  label: string;
  tagline: string;
  emoji: string;
  gradient: readonly [string, string];
};

const PERSONAS: Persona[] = [
  {
    id: 'funny',
    label: 'Witty',
    tagline: 'Playful tease, light humor',
    emoji: '😏',
    gradient: ['#fbbf24', '#f59e0b'],
  },
  {
    id: 'flirty',
    label: 'Flirty',
    tagline: 'Warm spark, subtle charm',
    emoji: '💫',
    gradient: ['#f472b6', '#ec4899'],
  },
  {
    id: 'confident',
    label: 'Bold',
    tagline: 'Clear and self-assured',
    emoji: '⚡',
    gradient: ['#60a5fa', '#3b82f6'],
  },
  {
    id: 'direct',
    label: 'Direct',
    tagline: 'Straight to the point',
    emoji: '🎯',
    gradient: ['#a78bfa', '#7c3aed'],
  },
];

type Props = {
  value: ReplyTone | null;
  onChange: (tone: ReplyTone) => void;
};

export function SparkTonePersonaPicker({ value, onChange }: Props) {
  return (
    <View style={styles.wrap}>
      <MotiView
        from={{ opacity: 0, translateY: 8 }}
        animate={{ opacity: 1, translateY: 0 }}
        transition={motionSpring.gentle}
        style={styles.headerRow}
      >
        <View style={styles.sparkBadge}>
          <Sparkles size={14} color="#fbbf24" />
        </View>
        <View style={styles.headerText}>
          <Text style={styles.sectionTitle}>Spark · AI Persona</Text>
          <Text style={styles.sectionSub}>How should CharmAI sound in your replies?</Text>
        </View>
      </MotiView>

      <View style={styles.grid}>
        {PERSONAS.map((persona, index) => {
          const selected = value === persona.id;
          return (
            <MotiView
              key={persona.id}
              from={{ opacity: 0, translateY: 14, scale: 0.94 }}
              animate={{ opacity: 1, translateY: 0, scale: selected ? 1.02 : 1 }}
              transition={{ ...motionSpring.snappy, delay: staggerMs * index }}
              style={styles.cell}
            >
              <Pressable
                onPress={() => onChange(persona.id)}
                style={({ pressed }) => [pressed && styles.pressed]}
                accessibilityRole="button"
                accessibilityState={{ selected }}
              >
                {selected ? (
                  <LinearGradient
                    colors={[...persona.gradient, persona.gradient[0]]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 1 }}
                    style={styles.ring}
                  >
                    <View style={styles.cardInner}>{personaBody(persona, selected)}</View>
                  </LinearGradient>
                ) : (
                  <View style={styles.cardOuter}>{personaBody(persona, selected)}</View>
                )}
              </Pressable>
            </MotiView>
          );
        })}
      </View>
    </View>
  );
}

function personaBody(persona: Persona, selected: boolean) {
  return (
    <>
      <LinearGradient
        colors={selected ? [...persona.gradient] : ['rgba(148,163,184,0.2)', 'rgba(71,85,105,0.35)']}
        style={styles.avatar}
      >
        <Text style={styles.emoji}>{persona.emoji}</Text>
      </LinearGradient>
      <Text style={[styles.label, selected && styles.labelSelected]}>{persona.label}</Text>
      <Text style={styles.tagline} numberOfLines={2}>
        {persona.tagline}
      </Text>
      {selected ? (
        <MotiView
          from={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={motionSpring.snappy}
          style={styles.activePill}
        >
          <Sparkles size={10} color="#fbbf24" />
          <Text style={styles.activeText}>Active</Text>
        </MotiView>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 14,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  sparkBadge: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: 'rgba(251,191,36,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(251,191,36,0.45)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerText: {
    flex: 1,
    gap: 2,
  },
  sectionTitle: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 0.2,
  },
  sectionSub: {
    color: '#94a3b8',
    fontSize: 12,
    lineHeight: 17,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -6,
  },
  cell: {
    width: '50%',
    padding: 6,
  },
  ring: {
    borderRadius: 20,
    padding: 2,
  },
  cardOuter: {
    borderRadius: 18,
    backgroundColor: 'rgba(15,23,42,0.78)',
    borderWidth: 1,
    borderColor: 'rgba(148,163,184,0.28)',
    paddingVertical: 14,
    paddingHorizontal: 10,
    alignItems: 'center',
    minHeight: 148,
  },
  cardInner: {
    borderRadius: 16,
    backgroundColor: 'rgba(10,14,30,0.92)',
    paddingVertical: 14,
    paddingHorizontal: 10,
    alignItems: 'center',
    minHeight: 144,
  },
  pressed: {
    opacity: 0.9,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  emoji: {
    fontSize: 22,
  },
  label: {
    color: '#e2e8f0',
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 4,
  },
  labelSelected: {
    color: '#fff',
  },
  tagline: {
    color: '#94a3b8',
    fontSize: 11,
    lineHeight: 15,
    textAlign: 'center',
    paddingHorizontal: 4,
  },
  activePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: 'rgba(251,191,36,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(251,191,36,0.35)',
  },
  activeText: {
    color: '#fde68a',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
});
