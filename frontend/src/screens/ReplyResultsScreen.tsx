import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Clipboard from 'expo-clipboard';
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import Animated, {
  interpolate,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { FloatingCard, GlassCard, GradientButton } from '../components/ui';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'ReplyResults'>;
const LABELS = ['smooth', 'playful', 'bold'] as const;

export function ReplyResultsScreen({ route, navigation }: Props) {
  const {
    prompt,
    tone,
    suggestions,
    retrievalDebug,
    explainabilityMode,
    providerUsed,
    latencyMs,
    warning,
  } = route.params;
  const [showWhy, setShowWhy] = useState(false);
  const [showAllDebug, setShowAllDebug] = useState(false);
  const [copyToast, setCopyToast] = useState('');
  const { width } = useWindowDimensions();
  const pageWidth = width - 32;
  const expandProgress = useSharedValue(0);

  useEffect(() => {
    expandProgress.value = withTiming(showWhy ? 1 : 0, { duration: 250 });
  }, [showWhy, expandProgress]);

  const chevronStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${interpolate(expandProgress.value, [0, 1], [0, 90])}deg` }],
  }));

  const debugBodyStyle = useAnimatedStyle(() => ({
    opacity: expandProgress.value,
    maxHeight: interpolate(expandProgress.value, [0, 1], [0, 520]),
  }));

  const visibleDebugItems = useMemo(() => {
    if (!retrievalDebug) return [];
    return showAllDebug ? retrievalDebug : retrievalDebug.slice(0, 3);
  }, [retrievalDebug, showAllDebug]);

  async function copyText(text: string) {
    await Clipboard.setStringAsync(text);
    setCopyToast('Reply copied');
    setTimeout(() => setCopyToast(''), 1400);
  }

  return (
    <LinearGradient colors={premiumTheme.gradients.hero} style={styles.screen}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.sectionTitle}>Original Prompt</Text>
        <View style={styles.card}>
          <Text style={styles.promptText}>{prompt}</Text>
          <Text style={styles.toneText}>Tone: {tone}</Text>
        </View>

        <Text style={styles.sectionTitle}>Swipe Replies</Text>
        <Animated.ScrollView
          horizontal
          pagingEnabled
          snapToInterval={pageWidth}
          decelerationRate="fast"
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.swipeTrack}
        >
          {suggestions.map((suggestion, index) => {
            const label = suggestion.label ?? LABELS[index % LABELS.length];
            const score = suggestion.score ?? Math.max(7, 9 - (index % 3));

            return (
              <FloatingCard key={`${index}-${suggestion}`} style={[styles.replyCardWrap, { width: pageWidth }]}>
                <View style={styles.replyCard}>
                  <View style={styles.replyTopRow}>
                    <Text style={styles.labelPill}>{label}</Text>
                    <Text style={styles.scoreBadge}>Score {score}/10</Text>
                  </View>
                  <Text style={styles.suggestionText}>{suggestion.text}</Text>
                  <Pressable
                    style={({ pressed }) => [styles.copyButton, pressed && styles.copyButtonPressed]}
                    onPress={() => copyText(suggestion.text)}
                  >
                    <Text style={styles.copyButtonText}>Copy</Text>
                  </Pressable>
                </View>
              </FloatingCard>
            );
          })}
        </Animated.ScrollView>

        {warning ? <Text style={styles.warningText}>{warning}</Text> : null}
        <Text style={styles.metaFooter}>
          Generated in {latencyMs ?? 'N/A'} ms using {providerUsed ?? 'mock'}
        </Text>

        {explainabilityMode && retrievalDebug && retrievalDebug.length > 0 ? (
          <GlassCard style={styles.explainCard}>
            <Pressable
              style={styles.glassHeader}
              onPress={() => {
                setShowWhy((prev) => !prev);
                if (showWhy) setShowAllDebug(false);
              }}
            >
              <Text style={styles.glassTitle}>Why these suggestions?</Text>
              <View style={styles.toggleWrap}>
                <Text style={styles.glassToggle}>{showWhy ? 'Hide' : 'Show'}</Text>
                <Animated.Text style={[styles.chevron, chevronStyle]}>▶</Animated.Text>
              </View>
            </Pressable>

            <Animated.View style={[styles.expandWrap, debugBodyStyle]}>
              <View style={styles.debugList}>
                {visibleDebugItems.map((item, index) => (
                  <View key={`${item.pattern_id ?? 'pattern'}-${index}`} style={styles.debugItem}>
                    <Text style={styles.debugMetaTitle}>
                      Pattern: {(item.pattern_id ?? 'N/A').toUpperCase()}   •   Tone:{' '}
                      {item.tone ?? 'unknown'}
                    </Text>
                    <Text style={styles.debugLine}>
                      Relevance:{' '}
                      {typeof item.score === 'number'
                        ? `${Math.round(item.score * 100)}%`
                        : 'N/A'}
                    </Text>
                    <Text style={styles.debugLine}>
                      Situation: {item.situation ?? 'No situation found.'}
                    </Text>
                    <Text style={styles.debugLine}>
                      Reason: {item.reason ?? 'No ranking reason provided.'}
                    </Text>
                  </View>
                ))}
              </View>
              {retrievalDebug.length > 3 ? (
                <Pressable
                  style={({ pressed }) => [styles.showMoreBtn, pressed && styles.copyButtonPressed]}
                  onPress={() => setShowAllDebug((prev) => !prev)}
                >
                  <Text style={styles.showMoreText}>
                    {showAllDebug ? 'Show less' : `Show more (${retrievalDebug.length - 3} more)`}
                  </Text>
                </Pressable>
              ) : null}
            </Animated.View>
          </GlassCard>
        ) : null}

        <GradientButton
          style={styles.button}
          label="Try Another Prompt"
          onPress={() => navigation.navigate('ChatInput')}
        />

        {copyToast ? (
          <View style={styles.toast}>
            <Text style={styles.toastText}>{copyToast}</Text>
          </View>
        ) : null}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: premiumTheme.colors.background,
  },
  container: {
    padding: 16,
    paddingBottom: 32,
  },
  sectionTitle: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
    marginTop: 8,
  },
  card: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(167, 139, 250, 0.3)',
    backgroundColor: 'rgba(255,255,255,0.05)',
    padding: 16,
    marginBottom: 10,
  },
  swipeTrack: {
    paddingBottom: 12,
  },
  replyCardWrap: {
    paddingRight: 12,
  },
  replyCard: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(167, 139, 250, 0.3)',
    backgroundColor: 'rgba(255,255,255,0.07)',
    padding: 18,
    minHeight: 200,
    justifyContent: 'space-between',
    ...premiumTheme.shadow,
  },
  replyTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
    alignItems: 'center',
  },
  labelPill: {
    borderRadius: 999,
    overflow: 'hidden',
    backgroundColor: 'rgba(124,58,237,0.35)',
    color: '#f1f5f9',
    paddingHorizontal: 10,
    paddingVertical: 5,
    textTransform: 'capitalize',
    fontWeight: '700',
    fontSize: 12,
  },
  scoreBadge: {
    color: '#bfdbfe',
    fontWeight: '700',
    fontSize: 12,
  },
  promptText: {
    color: '#e2e8f0',
    fontSize: 15,
    marginBottom: 6,
  },
  toneText: {
    color: '#93c5fd',
    fontSize: 13,
    fontWeight: '600',
  },
  suggestionIndex: {
    color: '#93c5fd',
    fontWeight: '700',
    marginBottom: 6,
  },
  suggestionText: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 15,
  },
  warningText: {
    color: '#fde68a',
    fontSize: 12,
    marginTop: 4,
    marginBottom: 6,
  },
  metaFooter: {
    color: '#94a3b8',
    fontSize: 12,
    marginBottom: 16,
  },
  explainCard: {
    marginBottom: 12,
  },
  glassHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  toggleWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  glassTitle: {
    color: '#f8fafc',
    fontSize: 15,
    fontWeight: '700',
  },
  glassToggle: {
    color: '#93c5fd',
    fontWeight: '700',
  },
  chevron: {
    color: '#93c5fd',
    fontSize: 12,
    fontWeight: '800',
  },
  expandWrap: {
    overflow: 'hidden',
  },
  debugList: {
    marginTop: 10,
    gap: 10,
  },
  debugItem: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(51, 65, 85, 0.9)',
    backgroundColor: 'rgba(2, 6, 23, 0.58)',
    padding: 10,
  },
  debugMetaTitle: {
    color: '#dbeafe',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 6,
  },
  debugLine: {
    color: '#e2e8f0',
    fontSize: 12,
    marginBottom: 6,
    lineHeight: 17,
  },
  showMoreBtn: {
    marginTop: 8,
    alignSelf: 'flex-start',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(167, 139, 250, 0.55)',
    backgroundColor: 'rgba(124,58,237,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  showMoreText: {
    color: '#ddd6fe',
    fontWeight: '700',
    fontSize: 12,
  },
  button: {
    marginTop: 12,
  },
  copyButton: {
    marginTop: 14,
    alignSelf: 'flex-start',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(96,165,250,0.5)',
    backgroundColor: 'rgba(59,130,246,0.18)',
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  copyButtonPressed: {
    transform: [{ scale: 0.96 }],
  },
  copyButtonText: {
    color: '#dbeafe',
    fontWeight: '700',
    fontSize: 13,
  },
  toast: {
    alignSelf: 'center',
    marginTop: 10,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(96,165,250,0.45)',
    backgroundColor: 'rgba(15,23,42,0.9)',
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  toastText: {
    color: '#dbeafe',
    fontSize: 12,
    fontWeight: '700',
  },
});
