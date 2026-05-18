import './global.css';

import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import type { TamaguiInternalConfig } from 'tamagui';
import { TamaguiProvider, Theme } from 'tamagui';

import { AppNavigator } from './src/navigation/AppNavigator';
import tamaguiConfig from './tamagui.config';

export default function App() {
  return (
    <TamaguiProvider config={tamaguiConfig as TamaguiInternalConfig} defaultTheme="dark">
      <Theme name="dark">
        <NavigationContainer>
          <StatusBar style="light" />
          <AppNavigator />
        </NavigationContainer>
      </Theme>
    </TamaguiProvider>
  );
}
