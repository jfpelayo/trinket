import { ImageBackground, Pressable, StyleSheet, Text } from "react-native";

 type Props = {
    label: string;
 }

const paper = require('@/assets/images/mappaper.png');

 export default function TaskButton({ label }: Props) {
    return (
        <Pressable style={styles.button} onPress={() => alert('task complete!')}>
            {/* <ImageBackground source={paper} contentFit='fill' style={styles.buttonImg}></ImageBackground> */}
            <ImageBackground
            source={paper}
            // contentFit="fill"    
            style={styles.buttonImg}>
                <Text style={styles.buttonLabel}>{label}</Text>
            </ImageBackground>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    button: {
        padding: 80,
        alignSelf: 'center',
        position: 'absolute',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        borderColor: 'black',
        width: '100%'
    },
    buttonImg: {
        overflow: 'hidden',
        padding: 20,
        flex: 1,
        shadowColor: '#000000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.25,
        shadowRadius: 3.84,
    },
    buttonLabel: {
        color: 'white',
        fontSize: 16,
        padding: 10,
        verticalAlign: 'middle',
        alignSelf: 'center',
        width: '100%'
    },
 });