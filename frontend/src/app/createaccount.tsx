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
                
                <Image
                source={require("../../assets/images/createaccountactual.png")}
                style={styles.bigtrinketlogo}
                resizeMode="stretch"
                />
                <Image
                source={require("../../assets/images/Username-button.png")}
                style={styles.usernameButton}
                resizeMode="contain"
                />
                <Image
                source={require("../../assets/images/Email-Button.png")}
                style={styles.emailButton}
                resizeMode="contain"
                />
                <Image
                source={require("../../assets/images/Password-Button.png")}
                style={styles.PasswordButton}
                resizeMode="contain"
                />
            <Link href="/testhomepage" asChild>
                <Pressable style={styles.signupbutton}>
                <Image
                source={require("../../assets/images/Sign-Up-Button.png")}
                style={styles.buttonImage}
                resizeMode="stretch"
                />
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
        //justifyContent: 'center',
    },
    usernameButton: {
        marginTop:90,
        width: 180,
        height: 91,
    },
    emailButton: {
        marginTop: -20,
        // aspectRatio: 175/50,
        width: 180,
        height: 91,
    },
    PasswordButton: {
        marginTop: -20,
        width: 180,
        height: 91,
    },
    signupbutton: {
        width: 150,
        height: 60,
        // 
        marginTop: 20,

        alignItems: "center",
        justifyContent: "center",
    },
    buttonImage: {
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        zIndex: 0,
    },
    text: {
        fontSize: 30,
        fontFamily: "PirataOne_400Regular",
        color: "black",
        zIndex: 1,
        textAlign: "center",
        // transform: [{ translateY: 100 }],
    },
    bigtrinketlogo: {
        width: 280,
        height: 150,
        marginTop: 120
    }
});