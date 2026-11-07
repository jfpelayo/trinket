import { Image, ImageBackground, ImageProps } from 'expo-image';
import { Tabs } from 'expo-router/tabs';
import { StyleSheet, Text, View } from 'react-native';

import PhoneFrame from '@/components/phone-frame';
import { f1 } from '@/constants/theme';

// size of every tab icon: change this one number to resize them all
const ICON_SIZE = 45;

// trinket counter (top right): the coin is bigger than the pill so it sticks out
const PILL_HEIGHT = 40;
const COIN_SIZE = 60;

export default function TabLayout() {
  return (
    // the phone-sized frame, around the pages AND the bar
    <PhoneFrame>
        <Tabs
          screenOptions={{
            tabBarStyle: { backgroundColor: 'transparent', borderTopWidth: 5, borderTopColor: '#D99B45', height: 85 },
            tabBarBackground: () => (
            <ImageBackground
                source={require('@/assets/images/BeachGradient.png')}
                contentFit="cover"
                style={StyleSheet.absoluteFill}
            />
            ),
            headerShown: false,
            tabBarActiveTintColor: '#5a3410', // label color of the tab you're on
            tabBarInactiveTintColor: '#8a6a45', // label color of the other tabs
            tabBarItemStyle: { justifyContent: 'center' },
            // the box each icon sits in: same size as the icon.
            // marginTop 'auto' + the label's marginBottom 'auto' center icon + text together
            tabBarIconStyle: { width: ICON_SIZE, height: ICON_SIZE, marginTop: 'auto' },
            // the text under each icon (comes from each tab's `title`)
            tabBarLabelStyle: { fontFamily: f1, fontSize: 14, marginBottom: 'auto' },
          }}>

        <Tabs.Screen
        name="home"
        options={{
            title: 'Home',
            tabBarIcon: ({ focused }) => (
            <TabIcon source={require('@/assets/images/tabIcons/home.png')} focused={focused} />
            ),
        }}
        />
        <Tabs.Screen
        name="chat"
        options={{
            title: 'Chat',
            tabBarIcon: ({ focused }) => (
            <TabIcon source={require('@/assets/images/tabIcons/chat.png')} focused={focused} />
            ),
        }}
        />
        <Tabs.Screen
        name="shop"
        options={{
            title: 'Shop',
            tabBarIcon: ({ focused }) => (
            <TabIcon source={require('@/assets/images/tabIcons/shop.png')} focused={focused} />
            ),
        }}
        />
        <Tabs.Screen
        name="profile"
        options={{
            title: 'Profile',
            tabBarIcon: ({ focused }) => (
            <TabIcon source={require('@/assets/images/tabIcons/profile.png')} focused={focused} />
            ),
        }}
        />

        </Tabs>

        {/* after <Tabs> so it's drawn on top of every page */}
        <TrinketCounter value={120} />
    </PhoneFrame>
  );
}

function TrinketCounter({ value }: { value: number }) {
  return (
    <View
      style={{
        position: 'absolute', // float over the page, pinned to the top right
        top: 30,
        right: 20,
        height: PILL_HEIGHT,
        justifyContent: 'center',
        paddingLeft: COIN_SIZE - 6, // room for the coin
        paddingRight: 14,
        borderRadius: PILL_HEIGHT / 2, // fully rounded ends
        backgroundColor: '#3b2414',
      }}>
      {/* the coin, hanging off the pill's left edge */}
      <Image
        source={require('@/assets/images/Trinkets.png')}
        contentFit="contain"
        style={{
          position: 'absolute',
          left: -12, // push past the left edge
          top: (PILL_HEIGHT - COIN_SIZE) / 2, // negative = sticks out top and bottom equally
          width: COIN_SIZE,
          height: COIN_SIZE,
        }}
      />
      <Text style={{ fontSize: 20, fontWeight: '700', color: '#F5C542' }}>{value}</Text>
    </View>
  );
}

function TabIcon({ source, focused }: { source: ImageProps['source']; focused: boolean }) {
  return (
    <Image
      source={source}
      contentFit="contain"
      style={{ width: ICON_SIZE, height: ICON_SIZE, opacity: focused ? 1 : 0.5 }}
    />
  );
}
