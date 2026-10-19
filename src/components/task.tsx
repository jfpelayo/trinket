import { StyleSheet, View, Pressable, Text, Image, ImageBackground } from "react-native";

 type Props = {
    label: string;
 }

const paper = require('@/assets/images/mappaper.png');

 export default function Task({ label }: Props) {
    return (
        <Pressable style={styles.button} onPress={() => alert('task complete!')}>
            {/* <ImageBackground source={paper} contentFit='fill' style={styles.buttonImg}></ImageBackground> */}
            <ImageBackground
            source={paper}
            contentFit="fill"
            style={styles.buttonImg}>
                <Text style={styles.buttonLabel}>{label}</Text>
            </ImageBackground>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    button: {
        // height: 50,
        // borderRadius: 10,
        // width: '100%',
        // height: '100%',
        padding: 20,
        alignSelf: 'center',
        position: 'absolute',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        borderColor: 'black'
    },
    buttonImg: {
        // position: 'absolute',
        overflow: 'hidden',
        padding: 20
        // paddingLeft: 10,
        // paddingRight: 10,
        // width: 600,
        // height: 50
        
    },
    buttonLabel: {
        color: 'black',
        // alignItems: 'flex-start',
        fontSize: 16,
        padding: 10,
        // paddingLeft: 30,
        // paddingTop: 12,
        verticalAlign: 'middle',
        // fontFamily: 'PirataOne_400Regular'
        alignSelf: 'center'
    },
 });