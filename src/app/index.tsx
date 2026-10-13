import { View, StyleSheet } from 'react-native';
import { Image, ImageBackground } from 'expo-image';
import Task from '@/components/task';

const background = require('@/assets/images/onboarding-bg.svg');
export default function Index() {
    return(
        <View style={styles.container}>
            <View style={styles.imageContainer}>
                {/* <Image source={background} style={styles.image} /> */}
                <Image source={background} style={styles.image}/>
            </View>
            {/* <View id='tasksheet'> */}
                <View style={styles.buttonContainer}>
                    <Task label='sdfkjldskf' />
                </View>
            {/* </View> */}
            
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#25292e',
        alignItems: 'center',
    },
    imageContainer: {
        flex: 1
    },
    image: {
        width: 1080,
        height: 1920,
        borderRadius: 18,
        resizeMode: 'center',
        flex: 1
    },
    buttonContainer: {
        flex: 1 / 3,
        alignItems: 'center',
    }
});