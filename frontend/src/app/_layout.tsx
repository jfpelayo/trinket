import { Stack } from "expo-router";
import { View, Image, StyleSheet, useWindowDimensions } from "react-native";
// import { useSafeAreaInsets } from "react-native-safe-area-context";
// i made background in layout so each screen that is made its own file should work with stack to have the same background
// added stack.screen titles for log in (index) and create account page
export default function RootLayout() {
  const { width, height } = useWindowDimensions();
  // const insets = useSafeAreaInsets();
  return (
    <View style={styles.container}>
      <Image
      source={require("../../assets/images/good-trinnket-background.png")}
      style={[StyleSheet.absoluteFill, {width, height}] }
      resizeMode="cover"
    />
      <Stack screenOptions={{ contentStyle: { backgroundColor: "transparent" }, headerTransparent: true, headerTintColor: "#fff", headerTitleStyle: { color: "white" } }}>
        {/* <Stack.Screen name= "index" options={{ title: 'Log In' }} />
        <Stack.Screen name= "createaccount" options={{ title: 'Create Account' }} /> */}
        <Stack.Screen name= "(tabs)" options={{ headerShown: false }} />
      </Stack>
      </View>
  );
}



const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
})