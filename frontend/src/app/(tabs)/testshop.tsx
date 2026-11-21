import Background from "../../components/screen-background";
import { View, Text, StyleSheet } from "react-native";
export default function TestShop(){
    return (
        <Background>
            <View style={styles.container}>
                  <Text style= {styles.text}>test shop page</Text>
                  </View>
        </Background>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1
    },
    text: {
        fontSize: 20
    },
})