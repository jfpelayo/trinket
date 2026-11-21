import {View, Image,StyleSheet, useWindowDimensions   } from 'react-native';
import type { PropsWithChildren } from "react";
export default function Background({ children }: PropsWithChildren) {
    const { width, height } = useWindowDimensions();
    return (
    <View style={styles.container}>
        <Image
        source={require("../../assets/images/good-trinnket-background.png")}
              style={[StyleSheet.absoluteFill, {width, height}] }
              resizeMode="cover"
            />
            {children}
    </View>

    );
 }

 const styles = StyleSheet.create({
    container: {
        flex: 1
    },
 }
    
 )
