import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'ReplyResults'>;

export function ReplyResultsScreen({ route, navigation }: Props) {
  const { prompt, tone, suggestions, note, retrievalDebug, explainabilityMode } = route.params;
  const [showWhy, setShowWhy] = useState(false);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.sectionTitle}>Original Prompt</Text>
      <View style={styles.card}>
        <Text style={styles.promptText}>{prompt}</Text>
        <Text style={styles.toneText}>Tone: {tone}</Text>
      </View>

      <Text style={styles.sectionTitle}>Suggestions</Text>
      {suggestions.map((suggestion, index) => (
        <View key={`${index}-${suggestion}`} style={styles.card}>
          <Text style={styles.suggestionIndex}>#{index + 1}</Text>
          <Text style={styles.suggestionText}>{suggestion}</Text>
        </View>
      ))}

      {note ? <Text style={styles.note}>{note}</Text> : null}

      {explainabilityMode && retrievalDebug && retrievalDebug.length > 0 ? (
        <View style={styles.glassCard}>
          <Pressable
            style={styles.glassHeader}
            onPress={() => setShowWhy((prev) => !prev)}
          >
            <Text style={styles.glassTitle}>Why these suggestions?</Text>
            <Text style={styles.glassToggle}>{showWhy ? 'Hide' : 'Show'}</Text>
          </Pressable>

          {showWhy ? (
            <View style={styles.debugList}>
              {retrievalDebug.map((item, index) => (
                <View key={`${item.pattern_id ?? 'pattern'}-${index}`} style={styles.debugItem}>
                  <View style={styles.badgeRow}>
                    <Text style={styles.badge}>ID {item.pattern_id ?? 'N/A'}</Text>
                    <Text style={styles.badge}>{item.tone ?? 'unknown tone'}</Text>
                    <Text style={styles.badge}>
                      score {typeof item.score === 'number' ? item.score.toFixed(3) : 'N/A'}
                    </Text>
                  </View>
                  <Text style={styles.debugSituation}>
                    Situation: {item.situation ?? 'No situation found.'}
                  </Text>
                  <Text style={styles.debugReason}>
                    Reason: {item.reason ?? 'No ranking reason provided.'}
                  </Text>
                </View>
              ))}
            </View>
          ) : null}
        </View>
      ) : null}

      <Pressable
        style={styles.button}
        onPress={() => navigation.navigate('ChatInput')}
      >
        <Text style={styles.buttonText}>Try Another Prompt</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingBottom: 32,
  },
  sectionTitle: {
    color: '#f8fafc',
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
    marginTop: 8,
  },
  card: {
    backgroundColor: '#111827',
    borderColor: '#334155',
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
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
    color: '#f8fafc',
    fontSize: 15,
  },
  note: {
    color: '#cbd5e1',
    fontStyle: 'italic',
    marginTop: 4,
    marginBottom: 16,
  },
  glassCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.35)',
    backgroundColor: 'rgba(15, 23, 42, 0.65)',
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  glassHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 6,
    gap: 6,
  },
  badge: {
    color: '#dbeafe',
    fontSize: 11,
    fontWeight: '700',
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(37, 99, 235, 0.22)',
    borderWidth: 1,
    borderColor: 'rgba(96, 165, 250, 0.35)',
    overflow: 'hidden',
  },
  debugSituation: {
    color: '#e2e8f0',
    fontSize: 13,
    marginBottom: 4,
    lineHeight: 18,
  },
  debugReason: {
    color: '#cbd5e1',
    fontSize: 12,
    lineHeight: 17,
  },
  button: {
    marginTop: 12,
    backgroundColor: '#2563eb',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
});
