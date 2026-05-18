import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MotiView } from 'moti';
import { StyleSheet, View } from 'react-native';

import AnimatedShaderHero from '../components/ui/animated-shader-hero';
import { motionSpring } from '../theme/motion';
import { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'HeroIntro'>;

export function HeroIntroScreen({ navigation }: Props) {
  const goHome = () => navigation.replace('Home');

  return (
    <View style={styles.container}>
      <MotiView
        from={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={motionSpring.gentle}
        style={styles.fill}
      >
        <AnimatedShaderHero onGetStarted={goHome} />
      </MotiView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1e1033',
  },
  fill: {
    flex: 1,
  },
});
