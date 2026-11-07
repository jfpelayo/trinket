import { StyleSheet, Text, View } from "react-native";

import Task from "./task";

type Props = {
  questName: string;
};

export default function Board({ questName }: Props) {
  return (
    <View style={styles.board}>
      <Text style={styles.title}>{questName}</Text>
      <Task label="Sample task (local preview)" />
    </View>
  );
}

const styles = StyleSheet.create({
  board: {
    backgroundColor: "#e5b67d",
    flex: 1,
    borderRadius: 10,
    borderWidth: 5,
    borderColor: "#754a18",
    padding: 20,
    alignItems: "center",
    gap: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: "600",
    color: "#040000",
  },
});
