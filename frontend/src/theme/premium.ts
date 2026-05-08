import { ColorValue } from 'react-native';

export const premiumTheme = {
  colors: {
    background: '#0f0f0f',
    surface: 'rgba(255, 255, 255, 0.06)',
    border: 'rgba(167, 139, 250, 0.25)',
    textPrimary: '#f8fafc',
    textSecondary: '#cbd5e1',
  },
  gradients: {
    hero: ['#1f1235', '#111827', '#0f172a'] as readonly [
      ColorValue,
      ColorValue,
      ColorValue,
    ],
    button: ['#7c3aed', '#3b82f6'] as readonly [ColorValue, ColorValue],
  },
  radius: {
    card: 24,
    input: 22,
    button: 24,
  },
  shadow: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.28,
    shadowRadius: 22,
    elevation: 8,
  },
};
