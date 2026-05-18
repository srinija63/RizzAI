import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Clipboard from 'expo-clipboard';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AmbientOrbsBackground } from '../components/ui';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'TextResults'>;

export function TextResultsScreen({ route }: Props) {
  const { title, items, subtitle, providerUsed } = route.params;
  const [toast, setToast] = useState('');

  async function copyOne(text: string) {
    await Clipboard.setStringAsync(text);
    setToast('Copied');
    setTimeout(() => setToast(''), 1200);
  }

  return (
    <View style={styles.root}>
      <LinearGradient colors={premiumTheme.gradients.romantic} style={StyleSheet.absoluteFill} />
      <AmbientOrbsBackground />
      <LinearGradient colors={['rgba(15,23,42,0.2)', 'rgba(15,23,42,0.85)']} style={StyleSheet.absoluteFill} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}

        {items.map((text, index) => (
          <View key={`${index}-${text.slice(0, 24)}`} style={styles.card}>
            <Text style={styles.itemText}>{text}</Text>
            <Pressable
              onPress={() => copyOne(text)}
              style={({ pressed }) => [styles.copyBtn, pressed && styles.copyBtnPressed]}
            >
              <Text style={styles.copyBtnText}>Copy</Text>
            </Pressable>
          </View>
        ))}

        <Text style={styles.meta}>
          {providerUsed ? `Generated with ${providerUsed}` : ''}
        </Text>
        {toast ? (
          <View style={styles.toast}>
            <Text style={styles.toastText}>{toast}</Text>
          </View>
        ) : null}
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
    paddingBottom: 40,
  },
  title: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 6,
  },
  subtitle: {
    color: premiumTheme.colors.textSecondary,
    fontSize: 14,
    marginBottom: 16,
    lineHeight: 20,
  },
  card: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(244,114,182,0.22)',
    backgroundColor: 'rgba(15,23,42,0.65)',
    padding: 16,
    marginBottom: 12,
  },
  itemText: {
    color: premiumTheme.colors.textPrimary,
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 12,
  },
  copyBtn: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(96,165,250,0.5)',
    backgroundColor: 'rgba(59,130,246,0.2)',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  copyBtnPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  copyBtnText: {
    color: '#dbeafe',
    fontWeight: '800',
    fontSize: 13,
  },
  meta: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 8,
  },
  toast: {
    alignSelf: 'center',
    marginTop: 12,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(15,23,42,0.95)',
    borderWidth: 1,
    borderColor: 'rgba(96,165,250,0.4)',
  },
  toastText: {
    color: '#e0f2fe',
    fontWeight: '700',
    fontSize: 12,
  },
});
