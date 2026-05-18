import { ReactNode } from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import { MotiView } from 'moti';

import { premiumTheme } from '../../theme/premium';
import { motionSpring } from '../../theme/motion';

type FloatingCardProps = {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  /** Staggered entrance delay (ms) for reply lists */
  enterDelay?: number;
};

export function FloatingCard({ children, style, enterDelay = 0 }: FloatingCardProps) {
  return (
    <MotiView
      from={{ opacity: 0, translateY: 18, scale: 0.98 }}
      animate={{ opacity: 1, translateY: 0, scale: 1 }}
      transition={{ ...motionSpring.card, delay: enterDelay }}
      style={[premiumTheme.shadow, style]}
    >
      {children}
    </MotiView>
  );
}
