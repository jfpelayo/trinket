import { StyleSheet, View, Pressable, Text, ImageBackground } from "react-native";

 type Props = {
    label: string;
 }

const paper = require('@/assets/images/mappaper.png');
 export default function Task({ label }: Props) {
    return (
        <View style={styles.buttonContainer}>
            {/* <Text style={styles.buttonLabel}>{label}</Text> */}
            <Pressable style={styles.button} onPress={() => alert('task complete!')}>
                <Text style={styles.button}>{'[]'}</Text>
                {/* <View style={styles.button}> */}
                    <ImageBackground source = {paper} contentFit='fill' style={styles.buttonImg}></ImageBackground>
                {/* </View> */}
            </Pressable>
        </View>
    );
 }

 const styles = StyleSheet.create({
    buttonContainer: {
        width: 320,
        height: 68,
        marginHorizontal: 20,
        marginVertical: -230,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 3,
        borderColor: 'white',
        flexDirection: 'row',
        backgroundColor: 'white'
    },
    button: {
        // borderRadius: 10,
        // width: '100%',
        // height: '100%',
        alignItems: 'flex-end',
        // justifyContent: 'center',
        // flexDirection: 'row',
        // color: 'white'
        resizeMode: 'contain',
        position: 'absolute'
    },
    buttonImg: {
        position: 'absolute',
        overflow: 'hidden'
    },
    buttonLabel: {
        color: 'black',
        alignItems: 'flex-start',
        fontSize: 16,
    },
 });