import { ScrollView, StyleSheet, Text, View } from "react-native";

import type { TrinketEvent } from "@/lib/api";
import Task from "./task";

type Props = {
  questName: string;
  events: TrinketEvent[];
  emptyMessage: string;
};

export function formatWhen(event: TrinketEvent): string {
  const date = new Date(event.starts_at);
  return event.all_day
    ? date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })
    : date.toLocaleString(undefined, {
        weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
      });
}

export default function Board({ questName, events, emptyMessage }: Props) {
  return (
    <View style={styles.board}>
      <Text style={styles.title}>{questName}</Text>
      <ScrollView contentContainerStyle={styles.list}>
        {events.length === 0 && <Text style={styles.empty}>{emptyMessage}</Text>}
        {events.map((event) => (
          <Task
            key={event.id}
            label={event.title}
            detail={`${formatWhen(event)} · ${event.category}${
              event.status === "draft" ? " · needs review" : ""
            }`}
          />
        ))}
      </ScrollView>
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
  list: { alignItems: "center", gap: 4 },
  empty: { color: "#40300f", textAlign: "center", marginTop: 12 },
});
