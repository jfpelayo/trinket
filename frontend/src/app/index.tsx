import { Pressable, Image, Text, View, StyleSheet, useWindowDimensions } from "react-native";
import { Link } from 'expo-router';
import Background from "../components/screen-background";
// index just has background image and text, assets has good-trinket-background.png, need to work on building another screen and top header navigation bar and navigating between index and another screen then moving top header navigation bar into bottom navigation bar
export default function Index() {
  const {width, height} = useWindowDimensions();
  return (
    <Background>
      <View style={styles.container}>
      <Text style= {styles.text}>Login Page</Text>
      <Link href="/createaccount" style={styles.button}>
      Go to Create Account screen
      </Link>
      {/* <Link href="/testhomepage" style={styles.button}>
      Go to testhomepage
      </Link> */}
      <Link href="/testhomepage" asChild>
      <Pressable>
        <Text>Log In!</Text>
      </Pressable>
      </Link>
    </View>
    </Background>
  ); 
} 

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontSize:20,
  },
  button: {
    fontSize: 20,
    textDecorationLine: 'underline',
    color: '#fff',
  }
});
