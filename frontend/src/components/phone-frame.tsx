import { ReactNode } from 'react';
import { useWindowDimensions, View } from 'react-native';

// the size every screen is designed at
export const FRAME_W = 500;
export const FRAME_H = 900;

export default function PhoneFrame({ children }: { children: ReactNode }) {
  const { width, height } = useWindowDimensions();
  // shrink to fit small windows, but never grow past the designed size
  const scale = Math.min(1, width / FRAME_W, height / FRAME_H);

  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#000' }}>
      {/* takes up the scaled size so centering works */}
      <View style={{ width: FRAME_W * scale, height: FRAME_H * scale, overflow: 'hidden' }}>
        {/* always exactly 500x900 inside, so top: 480 etc. always means the same spot */}
        <View style={{ width: FRAME_W, height: FRAME_H, transform: [{ scale }], transformOrigin: 'top left' }}>
          {children}
        </View>
      </View>
    </View>
  );
}
