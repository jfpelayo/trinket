import { View, StyleSheet } from 'react-native';
import { Image, ImageBackground } from 'expo-image';
import Task from '@/components/task';
import Board from '@/components/board';

const background = require('@/assets/images/onboarding-bg.svg');
export default function Index() {
    return (
        <View style={styles.container}>
            <ImageBackground source={background} style={styles.image}/>
            <View style={styles.board}>
                <Board questName={'dsfhdk'}></Board>
            </View>
         </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#25292e',
        alignItems: 'center',
    },
    image: {
        width: '100%',
        height: '100%',
        // borderRadius: 18,
        resizeMode: 'center',
        flex: 1
    },
    board: {
        position: 'absolute',
        // boxSizing: 'border-box'
        padding: 50,
        height: '100%',
        width: '100%'
    }
});