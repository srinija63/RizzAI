import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { BioWriterScreen } from '../screens/BioWriterScreen';
import { ChatInputScreen } from '../screens/ChatInputScreen';
import { HeroIntroScreen } from '../screens/HeroIntroScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { OpenerGeneratorScreen } from '../screens/OpenerGeneratorScreen';
import { ReplyResultsScreen } from '../screens/ReplyResultsScreen';
import { ReplySetupScreen } from '../screens/ReplySetupScreen';
import { TextResultsScreen } from '../screens/TextResultsScreen';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="HeroIntro"
      screenOptions={{
        headerStyle: { backgroundColor: '#0f0f0f' },
        headerTintColor: '#ffffff',
        headerShadowVisible: false,
        contentStyle: { backgroundColor: premiumTheme.colors.background },
        animation: 'fade_from_bottom',
        animationDuration: 340,
      }}
    >
      <Stack.Screen
        name="HeroIntro"
        component={HeroIntroScreen}
        options={{ headerShown: false, animation: 'fade' }}
      />
      <Stack.Screen
        name="Home"
        component={HomeScreen}
        options={{ title: 'Rizz AI', animation: 'slide_from_right', headerShown: false }}
      />
      <Stack.Screen
        name="ReplySetup"
        component={ReplySetupScreen}
        options={{ title: 'Tone & confidence', animation: 'slide_from_right' }}
      />
      <Stack.Screen
        name="ChatInput"
        component={ChatInputScreen}
        options={{ title: 'Chat or upload' }}
      />
      <Stack.Screen
        name="ReplyResults"
        component={ReplyResultsScreen}
        options={{ title: 'Reply Suggestions' }}
      />
      <Stack.Screen
        name="OpenerGenerator"
        component={OpenerGeneratorScreen}
        options={{ title: 'Openers' }}
      />
      <Stack.Screen
        name="BioWriter"
        component={BioWriterScreen}
        options={{ title: 'Bio writer' }}
      />
      <Stack.Screen
        name="TextResults"
        component={TextResultsScreen}
        options={{ title: 'Results' }}
      />
    </Stack.Navigator>
  );
}
