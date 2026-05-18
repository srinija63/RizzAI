import { MotiView } from 'moti';
import { StyleSheet, Text, View } from 'react-native';

import { premiumTheme } from '../../theme/premium';

type AiThinkingIndicatorProps = {
  label?: string;
};

/** Premium loading row — typing dots + soft glow (no logic coupling). */
export function AiThinkingIndicator({ label = 'CharmAI is thinking' }: AiThinkingIndicatorProps) {
  return (
    <View style={styles.row}>
      <MotiView
        from={{ opacity: 0.35 }}
        animate={{ opacity: 0.85 }}
        transition={{ type: 'timing', duration: 1400, loop: true, repeatReverse: true }}
        style={styles.glow}
      />
      <Text style={styles.label}>{label}</Text>
      <View style={styles.dots}>
        {[0, 1, 2].map((i) => (
          <MotiView
            key={i}
            from={{ translateY: 0, opacity: 0.4 }}
            animate={{ translateY: -5, opacity: 1 }}
            transition={{
              type: 'timing',
              duration: 450,
              delay: i * 110,
              loop: true,
              repeatReverse: true,
            }}
            style={styles.dot}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  glow: {
    position: 'absolute',
    width: 120,
    height: 36,
    borderRadius: 999,
    backgroundColor: 'rgba(167,139,250,0.25)',
  },
  label: {
    color: premiumTheme.colors.textSecondary,
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  dots: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 5,
    height: 18,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#fda4af',
  },
});
