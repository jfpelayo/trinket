import { StyleSheet, View, Pressable, Text, Image, ImageBackground } from "react-native";

 type Props = {
    label: string;
 }

const paper = require('@/assets/images/mappaper.png');

 export default function Task({ label }: Props) {
    return (
        <Pressable style={styles.button} onPress={() => alert('task complete!')}>
            <ImageBackground source={paper} contentFit="cover" style={styles.buttonImg}>
                <Text style={styles.buttonLabel}>{label}</Text>
            </ImageBackground>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    // buttonContainer: {
    //     width: 320,
    //     height: 68,
    //     marginHorizontal: 20,
    //     marginVertical: -230,
    //     alignItems: 'center',
    //     justifyContent: 'center',
    //     padding: 3,
    //     borderColor: 'white',
    //     flexDirection: 'row',
    //     backgroundColor: 'white'
    // },
    button: {
        borderRadius: 10,
        width: '100%',
        height: 50,
        paddingLeft: 200,
        paddingRight: 200,
        // marginHorizontal: 20,
        marginVertical: -630,
        alignItems: 'center',
        // justifyContent: 'center',
        // flexDirection: 'row',
        // color: 'white',
        // resizeMode: 'contain',
        // position: 'absolute'
    },
    buttonImg: {
        position: 'absolute',
        overflow: 'hidden',
        paddingLeft: 10,
        paddingRight: 10,
        width: 600,
        height: 50
    },
    buttonLabel: {
        color: 'black',
        // alignItems: 'flex-start',
        fontSize: 16,
        paddingLeft: 30,
        // paddingTop: 12,
        verticalAlign: 'middle',
        fontFamily: 'PirataOne_400Regular'
    },
 });