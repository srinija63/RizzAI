import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { ChatInputScreen } from '../screens/ChatInputScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { ReplyResultsScreen } from '../screens/ReplyResultsScreen';
import { premiumTheme } from '../theme/premium';
import { RootStackParamList } from '../types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerStyle: { backgroundColor: '#0f0f0f' },
        headerTintColor: '#ffffff',
        headerShadowVisible: false,
        contentStyle: { backgroundColor: premiumTheme.colors.background },
        animation: 'fade_from_bottom',
        animationDuration: 300,
      }}
    >
      <Stack.Screen
        name="Home"
        component={HomeScreen}
        options={{ title: 'CharmAI' }}
      />
      <Stack.Screen
        name="ChatInput"
        component={ChatInputScreen}
        options={{ title: 'Compose Prompt' }}
      />
      <Stack.Screen
        name="ReplyResults"
        component={ReplyResultsScreen}
        options={{ title: 'Reply Suggestions' }}
      />
    </Stack.Navigator>
  );
}
