import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';

import { FloatingCard, GlassCard, GradientButton } from '../components/ui';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export function HomeScreen({ navigation }: Props) {
  return (
    <LinearGradient colors={premiumTheme.gradients.hero} style={styles.container}>
      <FloatingCard style={styles.heroWrap}>
        <GlassCard>
          <Text style={styles.title}>CharmAI</Text>
          <Text style={styles.subtitle}>
            Your AI dating assistant
          </Text>
        </GlassCard>
      </FloatingCard>

      <GradientButton
        label="Start"
        onPress={() => navigation.navigate('ChatInput')}
      />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: premiumTheme.colors.background,
  },
  heroWrap: {
    marginBottom: 18,
  },
  title: {
    fontSize: 36,
    fontWeight: '700',
    color: premiumTheme.colors.textPrimary,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: premiumTheme.colors.textSecondary,
    lineHeight: 22,
  },
});
