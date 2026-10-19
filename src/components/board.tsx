import { StyleSheet, View, Pressable, Text, Image, ImageBackground, Modal } from "react-native";
import Task from "./task";

 type Props = {
    questName: string;
 }

export default function Board({ questName }: Props) {
    return (
        <View style={styles.board}>
            <Text style={styles.text}>dsflkjsf</Text>
            {/* <View style={styles.task}> */}
                <Task label='sample task'></Task>
            {/* </View> */}
        </View>
    )
}

const styles = StyleSheet.create({
    board: {
        backgroundColor: '#e5b67d',
        flex: 1,
        borderRadius: 10,
        borderWidth: 5,
        borderColor: '#754a18'
    },
    task: {
        position: 'absolute',
        // boxSizing: 'border-box'
        padding: 50,
        height: '100%',
        width: '100%'
    }, 
    text: {
        alignContent: 'center'
    }
})