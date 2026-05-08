import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { AnimatedInput, GlassCard, GradientButton } from '../components/ui';
import { fetchReplySuggestions } from '../services/api';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'ChatInput'>;
const TONES = ['funny', 'flirty', 'confident', 'direct', 'sweet'] as const;

export function ChatInputScreen({ navigation }: Props) {
  const [message, setMessage] = useState('');
  const [tone, setTone] = useState<(typeof TONES)[number]>('flirty');
  const [explainabilityMode, setExplainabilityMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const helperOpacity = useSharedValue(0);

  useEffect(() => {
    helperOpacity.value = withTiming(explainabilityMode ? 1 : 0, { duration: 220 });
  }, [explainabilityMode, helperOpacity]);

  const helperAnimatedStyle = useAnimatedStyle(() => ({
    opacity: helperOpacity.value,
    maxHeight: explainabilityMode ? 36 : 0,
  }));

  async function handleGenerate() {
    if (!message.trim()) {
      Alert.alert('Message required', 'Please enter a message or situation.');
      return;
    }

    try {
      setIsLoading(true);
      const data = await fetchReplySuggestions(
        message.trim(),
        tone.trim() || 'playful',
        explainabilityMode
      );
      navigation.navigate('ReplyResults', {
        prompt: message.trim(),
        tone: tone.trim() || 'playful',
        suggestions: data.replies ?? data.suggestions,
        retrievalDebug: data.retrieval_debug ?? undefined,
        explainabilityMode,
        note: data.note,
      });
    } catch (error) {
      Alert.alert(
        'Generation failed',
        error instanceof Error ? error.message : 'Unexpected error'
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <LinearGradient colors={premiumTheme.gradients.hero} style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.label}>Situation or draft message</Text>
        <AnimatedInput
          style={styles.multilineInput}
          value={message}
          onChangeText={setMessage}
          placeholder="Paste your conversation here..."
          multiline
        />

        <Text style={styles.label}>Tone</Text>
        <View style={styles.pillWrap}>
          {TONES.map((toneOption) => {
            const selected = tone === toneOption;
            return (
              <Pressable
                key={toneOption}
                onPress={() => setTone(toneOption)}
                style={({ pressed }) => [
                  styles.pill,
                  selected && styles.pillSelected,
                  pressed && styles.pillPressed,
                ]}
              >
                <Text style={[styles.pillText, selected && styles.pillTextSelected]}>
                  {toneOption}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <GlassCard style={[styles.explainabilityCard, explainabilityMode && styles.explainabilityCardOn]}>
          <View style={styles.explainabilityTextWrap}>
            <Text style={[styles.explainabilityTitle, explainabilityMode && styles.explainabilityTitleOn]}>
              Explainability Mode
            </Text>
            <Animated.Text style={[styles.explainabilityHelper, helperAnimatedStyle]}>
              Show why CharmAI chose these reply patterns.
            </Animated.Text>
          </View>
          <Switch
            value={explainabilityMode}
            onValueChange={setExplainabilityMode}
            trackColor={{ false: '#334155', true: '#60a5fa' }}
            thumbColor={explainabilityMode ? '#7c3aed' : '#94a3b8'}
          />
        </GlassCard>

        <GradientButton
          style={styles.button}
          onPress={handleGenerate}
          disabled={isLoading}
          label={isLoading ? 'Generating...' : 'Generate Replies'}
          icon={isLoading ? <ActivityIndicator color="#ffffff" /> : undefined}
        />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: premiumTheme.colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  label: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 14,
    marginBottom: 8,
    marginTop: 14,
    fontWeight: '600',
  },
  multilineInput: {
    minHeight: 170,
    textAlignVertical: 'top',
  },
  pillWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  pill: {
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: 'rgba(148, 163, 184, 0.14)',
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.25)',
  },
  pillSelected: {
    backgroundColor: 'rgba(124, 58, 237, 0.26)',
    borderColor: 'rgba(167, 139, 250, 0.9)',
    shadowColor: '#a78bfa',
    shadowOpacity: 0.55,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 0 },
    elevation: 7,
  },
  pillPressed: {
    transform: [{ scale: 0.96 }],
  },
  pillText: {
    color: premiumTheme.colors.textSecondary,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  pillTextSelected: {
    color: premiumTheme.colors.textPrimary,
  },
  explainabilityCard: {
    marginTop: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  explainabilityCardOn: {
    borderColor: 'rgba(167,139,250,0.75)',
    shadowColor: '#a78bfa',
    shadowOpacity: 0.32,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 0 },
    elevation: 8,
  },
  explainabilityTextWrap: {
    flex: 1,
    marginRight: 12,
  },
  explainabilityTitle: {
    color: 'rgba(248,250,252,0.72)',
    fontWeight: '700',
    fontSize: 14,
    marginBottom: 2,
  },
  explainabilityTitleOn: {
    color: premiumTheme.colors.textPrimary,
  },
  explainabilityHelper: {
    color: premiumTheme.colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
  },
  button: {
    marginTop: 20,
  },
});
