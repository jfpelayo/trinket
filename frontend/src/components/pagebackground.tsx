import { ImageBackground } from 'expo-image';
import { ReactNode } from 'react';

export default function PageBackground({ children }: { children?: ReactNode }) {
  return (
    <ImageBackground
      source={require('@/assets/images/login-page.png')}
      style={{ flex: 1, width: '100%', alignItems: 'center', justifyContent: 'center' }}>
      {children}
    </ImageBackground>
  );
}
