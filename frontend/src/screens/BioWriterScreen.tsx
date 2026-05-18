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

import { AmbientOrbsBackground, BioStylePersonaPicker, GradientButton } from '../components/ui';
import { ApiClientError, BioStyleTemplate, fetchBioVariants } from '../services/api';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'BioWriter'>;

const STYLE_LABELS: Record<BioStyleTemplate, string> = {
  witty_minimal: 'Witty · minimal',
  warm_story: 'Warm story',
  bold_confident: 'Bold',
  playful: 'Playful',
  authentic_soft: 'Authentic soft',
};

export function BioWriterScreen({ navigation }: Props) {
  const [about, setAbout] = useState('');
  const [style, setStyle] = useState<BioStyleTemplate | null>(null);
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);

  const canGenerate = about.trim().length > 0 && style !== null;

  async function handleGenerate() {
    if (!about.trim()) {
      Alert.alert('Add something', 'Paste rough notes, interests, or how you want to come across.');
      return;
    }
    if (!style) {
      Alert.alert('Pick a style', 'Choose a bio style template before generating.');
      return;
    }
    if (busy.current) return;
    busy.current = true;
    setLoading(true);
    try {
      const { bios, providerUsed } = await fetchBioVariants(about.trim(), style, 3);
      navigation.navigate('TextResults', {
        title: 'Bio ideas',
        subtitle: `Style: ${STYLE_LABELS[style]} · from your notes`,
        items: bios,
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
        <Text style={styles.heading}>Bio writer</Text>
        <Text style={styles.helper}>
          Drop messy notes or bullet facts — pick a style. Each bio will use specifics from what you
          write (hobbies, job, vibe, goals), not generic filler.
        </Text>

        <Text style={styles.label}>About you (rough draft)</Text>
        <TextInput
          style={styles.input}
          multiline
          value={about}
          onChangeText={setAbout}
          placeholder="Interests, job, humor, what you're looking for…"
          placeholderTextColor="#64748b"
        />

        <BioStylePersonaPicker value={style} onChange={setStyle} />

        <GradientButton
          label={loading ? 'Writing…' : 'Generate bios'}
          onPress={() => {
            void handleGenerate();
          }}
          disabled={loading || !canGenerate}
          icon={loading ? <ActivityIndicator color="#fff" /> : undefined}
          style={styles.btn}
        />
        {!style ? <Text style={styles.hint}>Select a style above to enable generate.</Text> : null}
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
    minHeight: 140,
    textAlignVertical: 'top',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(148,163,184,0.35)',
    backgroundColor: 'rgba(15,23,42,0.65)',
    color: premiumTheme.colors.textPrimary,
    padding: 14,
    fontSize: 15,
    marginBottom: 4,
  },
  btn: { marginTop: 20 },
  hint: {
    color: '#94a3b8',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 10,
  },
});
