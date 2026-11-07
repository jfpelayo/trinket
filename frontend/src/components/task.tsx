import { ImageBackground } from "expo-image";
import { StyleSheet, Text, View } from "react-native";

type Props = {
  label: string;
};

const paper = require("@/assets/images/mappaper.png");

// Static sample only — not an interactive control while the board is
// a local preview.
export default function Task({ label }: Props) {
  return (
    <View style={styles.wrap} accessibilityLabel={label}>
      <ImageBackground
        source={paper}
        contentFit="fill"
        style={styles.buttonImg}
      >
        <Text style={styles.buttonLabel}>{label}</Text>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    padding: 12,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  buttonImg: {
    overflow: "hidden",
    padding: 20,
    minWidth: 220,
    alignItems: "center",
  },
  buttonLabel: {
    color: "black",
    fontSize: 16,
    padding: 10,
    alignSelf: "center",
  },
});
