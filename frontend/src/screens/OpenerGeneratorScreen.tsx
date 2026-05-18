import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { AmbientOrbsBackground, GradientButton, SparkTonePersonaPicker } from '../components/ui';
import type { ReplyTone } from '../components/ui/SparkTonePersonaPicker';
import { ApiClientError, fetchOpeners } from '../services/api';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'OpenerGenerator'>;

export function OpenerGeneratorScreen({ navigation }: Props) {
  const [profile, setProfile] = useState('');
  const [tone, setTone] = useState<ReplyTone | null>(null);
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);

  const canGenerate = profile.trim().length > 0 && tone !== null;

  async function handleGenerate() {
    if (!profile.trim()) {
      Alert.alert('Profile needed', 'Paste their profile, prompts, or a few facts.');
      return;
    }
    if (!tone) {
      Alert.alert('Pick a tone', 'Choose Witty, Flirty, Bold, or Direct — nothing is auto-selected.');
      return;
    }
    if (busy.current) return;
    busy.current = true;
    setLoading(true);
    try {
      const { openers, providerUsed } = await fetchOpeners(profile.trim(), tone, 6);
      navigation.navigate('TextResults', {
        title: 'Opener ideas',
        subtitle: `Tone: ${tone} · grounded in their profile`,
        items: openers,
        providerUsed,
      });
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : 'Something went wrong.';
      Alert.alert('Could not generate', msg);
    } finally {
      busy.current = false;
      setLoading(false);
    }
  }

  return (
    <View style={styles.root}>
      <LinearGradient colors={premiumTheme.gradients.romantic} style={StyleSheet.absoluteFill} />
      <AmbientOrbsBackground />
      <LinearGradient colors={['rgba(15,23,42,0.15)', 'rgba(15,23,42,0.8)']} style={StyleSheet.absoluteFill} />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.heading}>Opener generator</Text>
        <Text style={styles.helper}>
          Paste their profile or prompts first. Pick a tone — CharmAI only uses what you select, and each opener
          should hook to something specific they wrote.
        </Text>

        <Text style={styles.label}>Their profile / prompts</Text>
        <TextInput
          style={styles.input}
          multiline
          value={profile}
          onChangeText={setProfile}
          placeholder="e.g. Loves climbing, bad at karaoke, looking for someone who…"
          placeholderTextColor="#64748b"
        />

        <SparkTonePersonaPicker value={tone} onChange={setTone} />

        <GradientButton
          label={loading ? 'Generating…' : 'Generate openers'}
          onPress={() => {
            void handleGenerate();
          }}
          disabled={loading || !canGenerate}
          icon={loading ? <ActivityIndicator color="#fff" /> : undefined}
          style={styles.btn}
        />
        {!tone ? (
          <Text style={styles.hint}>Select a persona above to enable generate.</Text>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: premiumTheme.colors.background },
  content: { padding: 16, paddingBottom: 36 },
  heading: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 22,
    fontWeight: '900',
    marginBottom: 8,
  },
  helper: {
    color: premiumTheme.colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 20,
  },
  label: {
    color: premiumTheme.colors.textPrimary,
    fontWeight: '700',
    marginBottom: 8,
    marginTop: 4,
  },
  input: {
    minHeight: 160,
    textAlignVertical: 'top',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(148,163,184,0.35)',
    backgroundColor: 'rgba(15,23,42,0.65)',
    color: premiumTheme.colors.textPrimary,
    padding: 14,
    fontSize: 15,
    marginBottom: 8,
  },
  btn: { marginTop: 20 },
  hint: {
    color: '#94a3b8',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 10,
  },
});
