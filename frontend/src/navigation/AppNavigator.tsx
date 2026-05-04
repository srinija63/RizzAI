import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { ChatInputScreen } from '../screens/ChatInputScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { ReplyResultsScreen } from '../screens/ReplyResultsScreen';
import { RootStackParamList } from '../types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerStyle: { backgroundColor: '#111827' },
        headerTintColor: '#ffffff',
        contentStyle: { backgroundColor: '#0b1220' },
      }}
    >
      <Stack.Screen
        name="Home"
        component={HomeScreen}
        options={{ title: 'RizzAI' }}
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
