import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';

import { fetchReplySuggestions } from '../services/api';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'ChatInput'>;

export function ChatInputScreen({ navigation }: Props) {
  const [message, setMessage] = useState('');
  const [tone, setTone] = useState('playful');
  const [explainabilityMode, setExplainabilityMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

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
    <View style={styles.container}>
      <Text style={styles.label}>Situation or draft message</Text>
      <TextInput
        style={[styles.input, styles.multilineInput]}
        value={message}
        onChangeText={setMessage}
        placeholder="Example: She said she loves hiking and coffee..."
        placeholderTextColor="#94a3b8"
        multiline
      />

      <Text style={styles.label}>Tone</Text>
      <TextInput
        style={styles.input}
        value={tone}
        onChangeText={setTone}
        placeholder="playful / confident / polite"
        placeholderTextColor="#94a3b8"
      />

      <View style={styles.explainabilityCard}>
        <View style={styles.explainabilityTextWrap}>
          <Text style={styles.explainabilityTitle}>Explainability Mode</Text>
          <Text style={styles.explainabilityHelper}>
            Show why CharmAI chose these reply patterns.
          </Text>
        </View>
        <Switch
          value={explainabilityMode}
          onValueChange={setExplainabilityMode}
          trackColor={{ false: '#334155', true: '#60a5fa' }}
          thumbColor={explainabilityMode ? '#2563eb' : '#94a3b8'}
        />
      </View>

      <Pressable
        style={[styles.button, isLoading && styles.disabledButton]}
        onPress={handleGenerate}
        disabled={isLoading}
      >
        {isLoading ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.buttonText}>Generate Replies</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  label: {
    color: '#f8fafc',
    fontSize: 14,
    marginBottom: 6,
    marginTop: 12,
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 10,
    backgroundColor: '#111827',
    color: '#f8fafc',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  multilineInput: {
    minHeight: 120,
    textAlignVertical: 'top',
  },
  explainabilityCard: {
    marginTop: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#334155',
    backgroundColor: 'rgba(15, 23, 42, 0.72)',
    paddingHorizontal: 12,
    paddingVertical: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  explainabilityTextWrap: {
    flex: 1,
    marginRight: 12,
  },
  explainabilityTitle: {
    color: '#f8fafc',
    fontWeight: '700',
    fontSize: 14,
    marginBottom: 2,
  },
  explainabilityHelper: {
    color: '#cbd5e1',
    fontSize: 12,
    lineHeight: 18,
  },
  button: {
    marginTop: 20,
    backgroundColor: '#2563eb',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  disabledButton: {
    opacity: 0.7,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
});
