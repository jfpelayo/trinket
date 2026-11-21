import { Pressable, Image, Text, View, StyleSheet, useWindowDimensions } from "react-native";
import Background from "../components/screen-background";
import { Link } from 'expo-router';
// created a background component to wrap each screen's containers by adding it to the stack in layout
// creat account page needs to lead to homepage with tabs
// 11/20/2026 open the app, on index.tsx which can go to create account page or to testhomepage, then on creataccount which can go to testhomepage which has navigation bar at the bottom
// 11/20/2026 added shop and chat page to tabs navigation bar
export default function CreateAccount() {
    return (
        <Background>
            <View style={styles.container}>
            <Text>Create Account Screen</Text>
            <Link href="/testhomepage" asChild>
                  <Pressable style={styles.button}>
                    {/* <Image
      source={require("../../assets/images/signup-button.png")}
      style={StyleSheet.absoluteFill}
      resizeMode="stretch"
    /> */}
                    <Text style= {styles.text}>
                        Sign Up!
                    </Text>
                  
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
    button: {
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 12,
    },
    text: {
        fontSize: 30, fontFamily: 'PirataOne_400Regular'
    },
    image: {
        color: 'white'
    }
});