import { View, StyleSheet } from 'react-native';
import { Image } from 'expo-image';

const background = require('@/assets/images/onboarding-bg.svg');
export default function Index() {
    return(
        <View style={styles.container}>
            <View style={StyleSheet.imageContainer}>
                <Image source={background} style={StyleSheet.image} />
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
    imageContainer: {
        flex: 1
    },
    image: {
        width: 320,
        height: 440,
        borderRadius: 18
    },
});