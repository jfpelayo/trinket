import { ImageBackground } from "expo-image";
import { Link } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import Board from "@/components/board";

const background = require("@/assets/images/onboarding-bg.svg");

// Local-only preview board: the quest list is static sample content,
// nothing here is loaded from or saved to a backend.
export default function BoardScreen() {
  return (
    <View style={styles.container}>
      <ImageBackground
        source={background}
        contentFit="cover"
        style={styles.image}
      />
      <View style={styles.board}>
        <Board questName="Sample quests" />
        <Text style={styles.previewNote}>
          Local-only preview — tasks are not saved or synced.
        </Text>
        <View style={styles.links}>
          <Link href="/upload" style={styles.link}>
            Upload document
          </Link>
          <Link href="/" style={styles.link}>
            Back to login
          </Link>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#25292e",
    alignItems: "center",
  },
  image: {
    width: "100%",
    height: "100%",
    flex: 1,
  },
  board: {
    position: "absolute",
    padding: 24,
    height: "100%",
    width: "100%",
    gap: 12,
  },
  previewNote: {
    color: "#f0e0c0",
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    textAlign: "center",
  },
  links: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 24,
  },
  link: {
    color: "#f0e0c0",
    textDecorationLine: "underline",
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    fontSize: 16,
  },
});
