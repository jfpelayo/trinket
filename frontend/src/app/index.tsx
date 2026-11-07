// importing components from react-native which are building blocks for things like images, text, buttons
import { Image, ImageBackground, Pressable, Text, Platform, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Link } from 'expo-router';

export default function HomeScreen() {
  return (
    <ImageBackground
      source={require('../../assets/background.png')}
      style={styles.backgroundImage}
      resizeMode="cover"
    >
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.topThird}>
          <Image
            source={require('../../assets/createaccountactual.png')}
            style={styles.logo}
            resizeMode="contain"
          />
        </View>

        <View style={styles.content}>
          <Pressable onPress={() => console.log('Pressed')}>
            <Image
              source={require('../../assets/Username button.png')}
              style={styles.buttonImage}
              resizeMode="contain"
            />
          </Pressable>

          <Pressable onPress={() => console.log('Pressed')}>
            <Image
              source={require('../../assets/Email Button.png')}
              style={styles.buttonImage}
              resizeMode="contain"
            />
          </Pressable>

          <Pressable onPress={() => console.log('Pressed')}>
            <Image
              source={require('../../assets/Password Button actual.png')}
              style={styles.buttonImage}
              resizeMode="contain"
            />
          </Pressable>

          <Pressable onPress={() => console.log('Pressed')}>
            <Image
              source={require('../../assets/Sign Up Button.png')}
              style={styles.buttonImage}
              resizeMode="contain"
            />
          </Pressable>
          <Link href="/uploadsyllabus" asChild>
            <Pressable>
              <Text> Open the new screen </Text>
            </Pressable>
          </Link>

        </View>
      </SafeAreaView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  backgroundImage: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  topThird: {
    height: '50%',
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    width: 300,
    height: 180,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 60,
    gap: 16,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
  },
  button : {
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 25,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonImage: {
    width: 300,
    height: 55,
  }
});