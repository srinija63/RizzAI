import { ReactNode, useEffect } from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { premiumTheme } from '../../theme/premium';

type FloatingCardProps = {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
};

export function FloatingCard({ children, style }: FloatingCardProps) {
  const y = useSharedValue(0);

  useEffect(() => {
    y.value = withRepeat(
      withSequence(
        withTiming(-6, { duration: 2200, easing: Easing.inOut(Easing.quad) }),
        withTiming(0, { duration: 2200, easing: Easing.inOut(Easing.quad) }),
      ),
      -1,
      true,
    );
  }, [y]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: y.value }],
    shadowOpacity: 0.22 + Math.abs(y.value) * 0.02,
    shadowRadius: 14 + Math.abs(y.value) * 1.2,
  }));

  return <Animated.View style={[premiumTheme.shadow, animatedStyle, style]}>{children}</Animated.View>;
}
