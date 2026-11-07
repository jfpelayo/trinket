import { ImageBackground } from "expo-image";
import { StyleSheet, Text, View } from "react-native";

type Props = {
  label: string;
  detail?: string;
};

const paper = require("@/assets/images/mappaper.png");

export default function Task({ label, detail }: Props) {
  return (
    <View style={styles.wrap} accessibilityLabel={detail ? `${label}, ${detail}` : label}>
      <ImageBackground
        source={paper}
        contentFit="fill"
        style={styles.buttonImg}
      >
        <Text style={styles.buttonLabel}>{label}</Text>
        {detail && <Text style={styles.detail}>{detail}</Text>}
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
  detail: { color: "#40300f", fontSize: 13, alignSelf: "center" },
});
