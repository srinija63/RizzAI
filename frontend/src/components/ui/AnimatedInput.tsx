import { useState } from 'react';
import { StyleSheet, TextInput, TextInputProps, View } from 'react-native';
import Animated, {
  interpolate,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import { MotiView } from 'moti';

import { motionSpring } from '../../theme/motion';
import { premiumTheme } from '../../theme/premium';

type AnimatedInputProps = TextInputProps;

export function AnimatedInput(props: AnimatedInputProps) {
  const [focused, setFocused] = useState(false);
  const focusProgress = useSharedValue(0);

  const handleFocus: NonNullable<TextInputProps['onFocus']> = (e) => {
    setFocused(true);
    focusProgress.value = withTiming(1, { duration: 220 });
    props.onFocus?.(e);
  };

  const handleBlur: NonNullable<TextInputProps['onBlur']> = (e) => {
    setFocused(false);
    focusProgress.value = withTiming(0, { duration: 220 });
    props.onBlur?.(e);
  };

  const ringStyle = useAnimatedStyle(() => ({
    opacity: interpolate(focusProgress.value, [0, 1], [0.2, 1]),
    transform: [{ scale: interpolate(focusProgress.value, [0, 1], [1, 1.01]) }],
  }));

  return (
    <MotiView
      animate={{
        scale: focused ? 1.015 : 1,
        translateY: focused ? -3 : 0,
      }}
      transition={motionSpring.gentle}
      style={styles.wrapper}
    >
      <View style={styles.inner}>
        <Animated.View style={[styles.ring, ringStyle, focused && styles.ringFocused]} />
        <TextInput
          {...props}
          onFocus={handleFocus}
          onBlur={handleBlur}
          style={[styles.input, props.style]}
          placeholderTextColor={props.placeholderTextColor ?? '#94a3b8'}
        />
      </View>
    </MotiView>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderRadius: premiumTheme.radius.input,
  },
  inner: {
    borderRadius: premiumTheme.radius.input,
  },
  ring: {
    ...StyleSheet.absoluteFillObject,
    borderRadius: premiumTheme.radius.input,
    borderWidth: 1,
    borderColor: 'rgba(96,165,250,0.28)',
  },
  ringFocused: {
    borderColor: 'rgba(244,114,182,0.55)',
    shadowColor: '#7c3aed',
    shadowOpacity: 0.35,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 0 },
  },
  input: {
    borderRadius: premiumTheme.radius.input,
    backgroundColor: 'rgba(15, 23, 42, 0.55)',
    borderWidth: 1,
    borderColor: 'rgba(96,165,250,0.22)',
    color: premiumTheme.colors.textPrimary,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
  },
});
