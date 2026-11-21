import { useState } from "react";
import { ImageBackground, StyleSheet, Text, View } from "react-native";
import TaskButton from "./taskButton";

type Props = {
    questName: string;
}

type Task = {
    id: string;
    label: string;
}

const wood = require('@/assets/images/woodbg.png');



export default function Board({ questName }: Props) {
    const [tasks, setTasks] = useState<Task[]>([]);
    function addTask(label: string) {
    const newTask: Task = {
        id: '0', // i don't know what to do for this actually
        label: label
    };
    setTasks([...tasks, newTask]);
}
    return (
        <View style={styles.board}>
            <ImageBackground source={wood} style={styles.bg}>
                <Text style={styles.text}>Task Board</Text>
                {tasks.map((task) => (
                    <TaskButton key={task.id} label={task.label} />))}
            </ImageBackground>
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
        padding: 50,
        height: '100%',
        width: '100%'
    }, 
    text: {
        alignSelf: 'center',
        padding: 10,
        fontSize: 40,
        color: '#ffffff'
    },
    bg: {
        overflow: 'hidden',
        padding: 20,
        flex: 1,
        width: '100%'
    }
})