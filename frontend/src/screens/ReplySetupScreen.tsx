import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { ArrowRight, Gauge, Sparkles } from '@tamagui/lucide-icons';
import { Button, Card, Paragraph, ScrollView, Text, XStack, YStack } from 'tamagui';

import { AmbientOrbsBackground, SparkTonePersonaPicker } from '../components/ui';
import { motionSpring, staggerMs } from '../theme/motion';
import { premiumTheme } from '../theme/premium';
import { ReplyTone } from '../components/ui/SparkTonePersonaPicker';
import { ConfidenceLevel, RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'ReplySetup'>;

const CONFIDENCE_OPTIONS: {
  id: ConfidenceLevel;
  title: string;
  subtitle: string;
}[] = [
  { id: 'low', title: 'Soft', subtitle: 'Low-key, plenty of room' },
  { id: 'medium', title: 'Balanced', subtitle: 'Clear and warm' },
  { id: 'high', title: 'Bold', subtitle: 'Direct, still respectful' },
];

export function ReplySetupScreen({ navigation }: Props) {
  const [tone, setTone] = useState<ReplyTone | null>(null);
  const [confidenceLevel, setConfidenceLevel] = useState<ConfidenceLevel | null>(null);

  const canContinue = tone !== null && confidenceLevel !== null;

  function handleContinue() {
    if (!tone) {
      Alert.alert('Pick a persona', 'Choose how CharmAI should sound (Witty, Flirty, Bold, or Direct).');
      return;
    }
    if (!confidenceLevel) {
      Alert.alert('Pick confidence', 'Choose Soft, Balanced, or Bold before continuing.');
      return;
    }
    navigation.navigate('ChatInput', { tone, confidenceLevel });
  }

  return (
    <View style={styles.root}>
      <LinearGradient colors={premiumTheme.gradients.romantic} style={StyleSheet.absoluteFill} />
      <AmbientOrbsBackground />
      <MotiView
        from={{ opacity: 0, scaleX: 0 }}
        animate={{ opacity: 0.9, scaleX: 1 }}
        transition={{ type: 'timing', duration: 900, delay: 200 }}
        style={styles.topAccent}
      >
        <LinearGradient
          colors={['transparent', 'rgba(244,114,182,0.7)', 'transparent']}
          start={{ x: 0, y: 0.5 }}
          end={{ x: 1, y: 0.5 }}
          style={styles.topAccentLine}
        />
      </MotiView>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        <YStack gap="$4">
          <MotiView
            from={{ opacity: 0, translateY: 20, scale: 0.97 }}
            animate={{ opacity: 1, translateY: 0, scale: 1 }}
            transition={{ ...motionSpring.gentle, delay: 0 }}
          >
            <Card
              elevate
              bordered
              backgroundColor="rgba(10,14,30,0.72)"
              borderColor="rgba(251,146,60,0.45)"
              borderRadius="$6"
              padding="$4"
            >
              <YStack gap="$3">
                <XStack alignItems="center" gap="$2">
                  <Sparkles size={18} color="#f59e0b" />
                  <Text color="#fff" fontSize={18} fontWeight="900">
                    Set your vibe first
                  </Text>
                </XStack>
                <Paragraph color="#cbd5e1" size="$4" lineHeight={22}>
                  Nothing is pre-selected — tap a Spark persona and a confidence level. CharmAI will use only what
                  you choose.
                </Paragraph>
              </YStack>
            </Card>
          </MotiView>

          <MotiView
            from={{ opacity: 0, translateY: 16 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ ...motionSpring.gentle, delay: staggerMs }}
          >
            <Card
              bordered
              backgroundColor="rgba(15,23,42,0.72)"
              borderColor="rgba(251,146,60,0.28)"
              borderRadius="$6"
              padding="$4"
            >
              <SparkTonePersonaPicker value={tone} onChange={setTone} />
            </Card>
          </MotiView>

          <MotiView
            from={{ opacity: 0, translateY: 16 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ ...motionSpring.gentle, delay: staggerMs * 2 }}
          >
            <Card
              bordered
              backgroundColor="rgba(15,23,42,0.72)"
              borderColor="rgba(148,163,184,0.35)"
              borderRadius="$6"
              padding="$4"
            >
              <YStack gap="$3">
                <XStack alignItems="center" gap="$2">
                  <Gauge size={17} color="#93c5fd" />
                  <Text color="#f8fafc" fontSize={15} fontWeight="800">
                    Confidence level
                  </Text>
                </XStack>
                <Paragraph color="#94a3b8" size="$3" lineHeight={20}>
                  How strong the replies should feel — not the AI’s self-doubt, but how forward you want to sound.
                </Paragraph>
                <YStack gap="$2">
                  {CONFIDENCE_OPTIONS.map((opt, index) => {
                    const selected = confidenceLevel === opt.id;
                    return (
                      <MotiView
                        key={opt.id}
                        from={{ opacity: 0, translateX: index % 2 === 0 ? -14 : 14 }}
                        animate={{ opacity: 1, translateX: 0, scale: selected ? 1.02 : 1 }}
                        transition={{ ...motionSpring.snappy, delay: staggerMs * (index + 1) }}
                      >
                        <Button
                          size="$4"
                          justifyContent="flex-start"
                          backgroundColor={selected ? 'rgba(59,130,246,0.35)' : 'rgba(148,163,184,0.1)'}
                          borderWidth={1}
                          borderColor={selected ? 'rgba(147,197,253,0.85)' : 'rgba(148,163,184,0.28)'}
                          borderRadius="$4"
                          onPress={() => setConfidenceLevel(opt.id)}
                        >
                          <YStack alignItems="flex-start" gap="$0.5">
                            <Text color="#f8fafc" fontWeight="900" fontSize={14}>
                              {opt.title}
                            </Text>
                            <Text color="#94a3b8" fontSize={12}>
                              {opt.subtitle}
                            </Text>
                          </YStack>
                        </Button>
                      </MotiView>
                    );
                  })}
                </YStack>
              </YStack>
            </Card>
          </MotiView>

          <MotiView
            from={{ opacity: 0, translateY: 24 }}
            animate={{ opacity: 1, translateY: 0 }}
            transition={{ ...motionSpring.card, delay: staggerMs * 3 }}
          >
            <MotiView
              from={{ scale: 1 }}
              animate={{ scale: 1.015 }}
              transition={{
                type: 'timing',
                duration: 1500,
                loop: true,
                repeatReverse: true,
              }}
            >
              <Button
                size="$5"
                iconAfter={ArrowRight}
                backgroundColor={canContinue ? '#f59e0b' : 'rgba(148,163,184,0.35)'}
                color={canContinue ? '#111827' : '#94a3b8'}
                fontWeight="900"
                borderRadius={999}
                opacity={canContinue ? 1 : 0.85}
                pressStyle={{ opacity: 0.92, scale: 0.985 }}
                onPress={handleContinue}
              >
                {canContinue ? 'Next: chat or screenshot' : 'Select persona & confidence'}
              </Button>
            </MotiView>
          </MotiView>
        </YStack>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: premiumTheme.colors.background,
  },
  topAccent: {
    position: 'absolute',
    top: 0,
    left: 24,
    right: 24,
    zIndex: 2,
    height: 3,
  },
  topAccentLine: {
    flex: 1,
    borderRadius: 2,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: 16,
    paddingVertical: 24,
    paddingBottom: 40,
  },
});
