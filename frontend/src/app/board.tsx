import { ImageBackground } from "expo-image";
import { Link, Redirect, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import Board from "@/components/board";
import { listEvents, type TrinketEvent } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useApi } from "@/lib/use-api";

const background = require("@/assets/images/onboarding-bg.svg");

function startOfToday(): Date {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

export default function BoardScreen() {
  const state = useApi();
  const [events, setEvents] = useState<TrinketEvent[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const api = state.kind === "ready" ? state.api : null;

  // Reload whenever the board regains focus, e.g. after confirming an upload.
  useFocusEffect(
    useCallback(() => {
      if (!api) return;
      let active = true;
      listEvents(api, startOfToday())
        .then((result) => {
          if (!active) return;
          if (result.ok) {
            setEvents(result.value.filter((event) => event.status !== "dismissed"));
            setMessage(null);
          } else setMessage(result.message);
        })
        .catch(() => active && setMessage("Could not reach the backend. Is it running?"));
      return () => {
        active = false;
      };
    }, [api]),
  );

  if (state.kind === "signedOut") return <Redirect href="/" />;

  const status =
    state.kind === "misconfigured" ? state.message
      : message ?? (events === null ? "Loading your quests…" : null);

  return (
    <View style={styles.container}>
      <ImageBackground
        source={background}
        contentFit="cover"
        style={styles.image}
      />
      <View style={styles.board}>
        <Board
          questName="Upcoming quests"
          events={events ?? []}
          emptyMessage={events === null ? "" : "No upcoming deadlines yet. Upload a syllabus to add some."}
        />
        {status && <Text style={styles.previewNote}>{status}</Text>}
        <View style={styles.links}>
          <Link href="/upload" style={styles.link}>
            Upload document
          </Link>
          <Pressable accessibilityRole="button" onPress={() => supabase.auth.signOut()}>
            <Text style={styles.link}>Sign out</Text>
          </Pressable>
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
