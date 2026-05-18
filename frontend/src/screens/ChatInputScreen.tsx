import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as ImagePicker from 'expo-image-picker';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import {
  AiThinkingIndicator,
  AmbientOrbsBackground,
  AnimatedInput,
  GlassCard,
  GradientButton,
} from '../components/ui';
import {
  ApiClientError,
  extractConversationFromScreenshot,
  fetchReplySuggestions,
} from '../services/api';
import { motionSpring, staggerMs } from '../theme/motion';
import { premiumTheme } from '../theme/premium';
import { ConfidenceLevel, RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'ChatInput'>;

const EMPTY_TAGLINES = [
  'Your AI wingman.',
  'Turn dry chats into chemistry.',
  'Smart replies. Real vibes.',
];

function confidenceShort(cl: ConfidenceLevel): string {
  if (cl === 'low') return 'Soft';
  if (cl === 'high') return 'Bold';
  return 'Balanced';
}

export function ChatInputScreen({ navigation, route }: Props) {
  const { tone, confidenceLevel } = route.params;
  const [message, setMessage] = useState('');
  const [explainabilityMode, setExplainabilityMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isExtractingImage, setIsExtractingImage] = useState(false);
  const lastRequestTs = useRef(0);
  const pendingRequest = useRef(false);
  const helperOpacity = useSharedValue(0);

  useEffect(() => {
    helperOpacity.value = withTiming(explainabilityMode ? 1 : 0, { duration: 220 });
  }, [explainabilityMode, helperOpacity]);

  const helperAnimatedStyle = useAnimatedStyle(() => ({
    opacity: helperOpacity.value,
    maxHeight: explainabilityMode ? 36 : 0,
  }));

  function showFriendlyError(error: unknown) {
    const friendly =
      error instanceof ApiClientError
        ? error.message
        : 'Could not generate replies. Check that the backend is running.';

    Alert.alert('Something went wrong', friendly, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Retry', onPress: () => { void handleGenerate(); } },
    ]);
  }

  function guessMimeFromUri(uri: string): string {
    const lower = uri.toLowerCase();
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    return 'image/jpeg';
  }

  async function handleImportScreenshot() {
    if (Platform.OS === 'web') {
      Alert.alert(
        'Screenshot import',
        'Import from photos works in the Expo Go app on a phone. On web, paste the conversation as text.',
      );
      return;
    }
    if (isExtractingImage || isLoading) {
      return;
    }
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Photos', 'Allow photo library access to import a chat screenshot.');
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.65,
      base64: true,
    });
    if (picked.canceled || !picked.assets?.length) {
      return;
    }
    const asset = picked.assets[0];
    const b64 = asset.base64;
    if (!b64) {
      Alert.alert('Could not read image', 'Try another photo or slightly lower resolution.');
      return;
    }
    const mime = asset.mimeType ?? guessMimeFromUri(asset.uri ?? '');

    try {
      setIsExtractingImage(true);
      const { text, warning } = await extractConversationFromScreenshot(b64, mime);
      setMessage(text);
      if (warning) {
        Alert.alert('Notice', warning);
      }
    } catch (error) {
      const friendly =
        error instanceof ApiClientError ? error.message : 'Could not read text from this image.';
      Alert.alert('Screenshot import', friendly);
    } finally {
      setIsExtractingImage(false);
    }
  }

  async function handleGenerate() {
    if (!message.trim()) {
      Alert.alert('Message required', 'Please enter a message or situation.');
      return;
    }
    if (pendingRequest.current) {
      return;
    }
    const now = Date.now();
    if (now - lastRequestTs.current < 900) {
      return;
    }

    try {
      pendingRequest.current = true;
      lastRequestTs.current = now;
      setIsLoading(true);
      const data = await fetchReplySuggestions(
        message.trim(),
        tone,
        explainabilityMode,
        3,
        confidenceLevel,
      );

      if (data.warning) {
        Alert.alert('Notice', data.warning);
      }

      navigation.navigate('ReplyResults', {
        prompt: message.trim(),
        tone,
        confidenceLevel,
        suggestions: data.replies,
        retrievalDebug: data.retrievalDebug ?? undefined,
        explainabilityMode,
        providerUsed: data.providerUsed ?? null,
        latencyMs: data.latencyMs ?? null,
        warning: data.warning ?? null,
      });
    } catch (error) {
      showFriendlyError(error);
    } finally {
      pendingRequest.current = false;
      setIsLoading(false);
    }
  }

  const empty = !message.trim();

  return (
    <View style={styles.root} className="flex-1">
      <LinearGradient colors={premiumTheme.gradients.romantic} style={StyleSheet.absoluteFill} />
      <AmbientOrbsBackground />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <BlurView intensity={44} tint="dark" style={styles.glassPanel}>
          <MotiView
            from={{ opacity: 0, translateY: 10 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={motionSpring.gentle}
            style={styles.glassInner}
          >
            <View style={styles.choicesBar}>
              <View style={styles.choicesBarLeft}>
                <Text style={styles.choicesBarLabel}>Your picks</Text>
                <Text style={styles.choicesBarText}>
                  <Text style={styles.choicesEm}>{tone}</Text>
                  {' tone · '}
                  <Text style={styles.choicesEm}>{confidenceShort(confidenceLevel)}</Text>
                  {' confidence'}
                </Text>
              </View>
              <Pressable
                onPress={() => navigation.navigate('ReplySetup')}
                style={({ pressed }) => [styles.changeLink, pressed && styles.changeLinkPressed]}
              >
                <Text style={styles.changeLinkText}>Edit</Text>
              </Pressable>
            </View>

            {empty ? (
              <View style={styles.emptyBlock}>
                {EMPTY_TAGLINES.map((line, i) => (
                  <MotiView
                    key={line}
                    from={{ opacity: 0, translateY: 8 }}
                    animate={{ opacity: 1, translateY: 0 }}
                    transition={{ ...motionSpring.gentle, delay: i * staggerMs }}
                  >
                    <Text style={styles.emptyLine}>{line}</Text>
                  </MotiView>
                ))}
              </View>
            ) : null}

            <View style={styles.labelRow}>
              <Text style={styles.label}>
                Situation or draft message
              </Text>
              <Pressable
                onPress={() => { void handleImportScreenshot(); }}
                disabled={isExtractingImage || isLoading}
                style={({ pressed }) => [
                  styles.importLink,
                  (isExtractingImage || isLoading) && styles.importLinkDisabled,
                  pressed && styles.importLinkPressed,
                ]}
              >
                {isExtractingImage ? (
                  <ActivityIndicator color={premiumTheme.colors.textPrimary} size="small" />
                ) : (
                  <Text style={styles.importLinkText}>From screenshot</Text>
                )}
              </Pressable>
            </View>
            <AnimatedInput
              style={styles.multilineInput}
              value={message}
              onChangeText={setMessage}
              placeholder="Paste your conversation here..."
              multiline
            />

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

            {isLoading ? <AiThinkingIndicator /> : null}

            <GradientButton
              style={styles.button}
              onPress={handleGenerate}
              disabled={isLoading}
              label={isLoading ? 'Generating…' : 'Generate Replies'}
            />
          </MotiView>
        </BlurView>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: premiumTheme.colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
    flexGrow: 1,
  },
  glassPanel: {
    borderRadius: 28,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  glassInner: {
    padding: 16,
    backgroundColor: 'rgba(12, 10, 24, 0.35)',
  },
  emptyBlock: {
    marginBottom: 14,
    gap: 6,
  },
  emptyLine: {
    color: 'rgba(248,250,252,0.82)',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  choicesBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 16,
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
    borderWidth: 1,
    borderColor: 'rgba(244,114,182,0.18)',
  },
  choicesBarLeft: {
    flex: 1,
    marginRight: 10,
  },
  choicesBarLabel: {
    color: premiumTheme.colors.textSecondary,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 4,
  },
  choicesBarText: {
    color: premiumTheme.colors.textSecondary,
    fontSize: 13,
    lineHeight: 18,
  },
  choicesEm: {
    color: premiumTheme.colors.textPrimary,
    fontWeight: '800',
    textTransform: 'capitalize',
  },
  changeLink: {
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  changeLinkPressed: {
    opacity: 0.75,
  },
  changeLinkText: {
    color: '#fda4af',
    fontSize: 14,
    fontWeight: '800',
  },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 2,
    marginBottom: 8,
    gap: 12,
  },
  label: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 14,
    fontWeight: '600',
    flexShrink: 1,
  },
  importLink: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: 'rgba(124, 58, 237, 0.22)',
    borderWidth: 1,
    borderColor: 'rgba(167, 139, 250, 0.45)',
  },
  importLinkDisabled: {
    opacity: 0.55,
  },
  importLinkPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  importLinkText: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  multilineInput: {
    minHeight: 170,
    textAlignVertical: 'top',
  },
  explainabilityCard: {
    marginTop: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  explainabilityCardOn: {
    borderColor: 'rgba(244,114,182,0.45)',
    shadowColor: '#fb7185',
    shadowOpacity: 0.22,
    shadowRadius: 16,
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
