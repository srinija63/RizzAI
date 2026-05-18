import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { ChevronRight } from '@tamagui/lucide-icons';

import { motionSpring } from '../../theme/motion';

type Props = {
  title: string;
  subtitle: string;
  icon: ReactNode;
  gradient: readonly [string, string];
  onPress: () => void;
  featured?: boolean;
  enterDelay?: number;
};

export function RizzHomeActionTile({
  title,
  subtitle,
  icon,
  gradient,
  onPress,
  featured = false,
  enterDelay = 0,
}: Props) {
  return (
    <MotiView
      from={{ opacity: 0, translateY: 18 }}
      animate={{ opacity: 1, translateY: 0 }}
      transition={{ ...motionSpring.gentle, delay: enterDelay }}
    >
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.hit, pressed && styles.pressed]}
        accessibilityRole="button"
      >
        {featured ? (
          <LinearGradient colors={[...gradient, gradient[0]]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.ring}>
            <View style={styles.innerFeatured}>{tileBody()}</View>
          </LinearGradient>
        ) : (
          <View style={styles.outer}>{tileBody()}</View>
        )}
      </Pressable>
    </MotiView>
  );

  function tileBody() {
    return (
      <>
        <LinearGradient colors={[...gradient]} style={styles.iconOrb}>
          {icon}
        </LinearGradient>
        <View style={styles.copy}>
          <Text style={[styles.title, featured && styles.titleFeatured]}>{title}</Text>
          <Text style={styles.subtitle} numberOfLines={2}>
            {subtitle}
          </Text>
        </View>
        <View style={styles.chevron}>
          <ChevronRight size={20} color={featured ? '#fde68a' : '#94a3b8'} />
        </View>
      </>
    );
  }
}

const styles = StyleSheet.create({
  hit: {
    borderRadius: 20,
  },
  pressed: {
    opacity: 0.9,
    transform: [{ scale: 0.985 }],
  },
  ring: {
    borderRadius: 20,
    padding: 2,
  },
  innerFeatured: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: 18,
    backgroundColor: 'rgba(10,14,30,0.94)',
  },
  outer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: 18,
    backgroundColor: 'rgba(15,23,42,0.78)',
    borderWidth: 1,
    borderColor: 'rgba(148,163,184,0.28)',
  },
  iconOrb: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: {
    flex: 1,
    gap: 4,
  },
  title: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '900',
  },
  titleFeatured: {
    color: '#fff',
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: 12,
    lineHeight: 17,
  },
  chevron: {
    opacity: 0.9,
  },
});
