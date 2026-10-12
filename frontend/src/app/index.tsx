import { PirataOne_400Regular, useFonts } from '@expo-google-fonts/pirata-one';
import { Image, ImageBackground } from 'expo-image';
import { useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';

export default function HomeScreen() {
useFonts({ PirataOne_400Regular });
const [username, setUsername] = useState('');
const [password, setPassword] = useState('');
return (
    <View style={{ flex: 1, alignItems: 'center', backgroundColor: '#000' }}>
    <ImageBackground
        source={require('@/assets/images/login-page.png')}
        style={{ flex: 1, width: '100%', maxWidth: 500, maxHeight: 900}}
      >
        <Pressable
          id="login-button"
          testID="login-button"
          accessibilityLabel="Log in"
          onPress={() => {
            console.log('pressed');
            setUsername('');
            setPassword('');
          }}
          style={{ padding: 20, borderRadius: 15, position: 'absolute', top: 660, alignSelf: 'center' , width: 292, height: 100}}>
          {({ pressed }) => (
          <ImageBackground
            source={require('@/assets/images/woodtexture1.png')}
            contentFit="fill"
            style={{ padding: 20, borderRadius: 30, overflow: 'hidden', borderWidth: 2.5, borderColor: '#000' }}>
            <Text style={{ color: pressed ? '#f8eeee' : '#040000', fontSize: 30, fontFamily: 'PirataOne_400Regular' , alignSelf: 'center'}}>Log in</Text>
          </ImageBackground>
          )}
        </Pressable>

        <ImageBackground
          source={require('@/assets/images/mappaper.png')}
          contentFit="fill"
          style={{ position: 'absolute', top: 580, alignSelf: 'center', width: 255, height: 90, flexDirection: 'row', alignItems: 'center', borderRadius: 15, overflow: 'hidden', borderWidth: 2.5, borderColor: '#000' }}>
        <Image
            source={require('@/assets/images/password.png')}
            contentFit="contain"
            style={{ width: 30, height: 30, marginLeft: 15 }}
        />
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="Password"
            placeholderTextColor="#40300f"
            style={{ position: 'relative', flex: 1, minWidth: 0, padding: 15, fontSize: 22, color: '#040000', fontFamily: 'PirataOne_400Regular' }}
          />
        </ImageBackground>

        <ImageBackground
          source={require('@/assets/images/mappaper.png')}
          contentFit="fill"
          style={{ position: 'absolute', top: 480, alignSelf: 'center', width: 255, height: 90, flexDirection: 'row', alignItems: 'center', borderRadius: 15, overflow: 'hidden', borderWidth: 2.5, borderColor: '#000' }}>
        <Image
            source={require('@/assets/images/username.png')}
            contentFit="contain"
            style={{ width: 30, height: 30, marginLeft: 15 }}
        />
          <TextInput
            value={username}
            onChangeText={setUsername}
            placeholder="Username"
            placeholderTextColor="#40300f"
            style={{ position: 'relative', flex: 1, minWidth: 0, padding: 15, fontSize: 22, color: '#040000', fontFamily: 'PirataOne_400Regular' }}
          />
        </ImageBackground>

        <View style={{ position: 'absolute', top: 770, alignSelf: 'center', flexDirection: 'row' }}>
          <Text style={{ fontSize: 18, color: '#040000', fontFamily: 'PirataOne_400Regular' }}>
            Don&apos;t have an account?{' '}
          </Text>
          <Pressable onPress={() => console.log('sign up pressed')}>
            {({ pressed }) => (
              <Text style={{ fontSize: 18, color: pressed ? '#fff' : '#040000', fontFamily: 'PirataOne_400Regular', textDecorationLine: 'underline' }}>
                Sign Up
              </Text>
            )}
          </Pressable>
          <Text style={{ fontSize: 18, color: '#040000', fontFamily: 'PirataOne_400Regular' }}>
            {' '}Now!
          </Text>
        </View>

        <Image
            source={require('@/assets/images/welcome.png')}
            contentFit="contain"
            style={{ position: 'absolute', top: 75, alignSelf: 'center', height: 400, width: 400 }}>
        </Image>
      </ImageBackground>
    </View>
  );
}