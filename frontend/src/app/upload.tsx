import * as DocumentPicker from "expo-document-picker";
import type { DocumentPickerAsset } from "expo-document-picker";
import { Link, Redirect } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { formatWhen } from "@/components/board";
import {
  confirmDocument,
  getDocument,
  setEventStatus,
  type TrinketDocument,
  type TrinketEvent,
  uploadDocument,
} from "@/lib/api";
import { useApi } from "@/lib/use-api";

const POLL_MS = 3000;
const FAILURE_MESSAGES: Record<string, string> = {
  invalid_dates: "Some dates in this document were ambiguous, so nothing was saved. Try a clearer copy.",
  worker_timeout: "Date extraction took too long and was stopped. Try again later.",
};

export default function UploadScreen() {
  const state = useApi();
  const api = state.kind === "ready" ? state.api : null;
  const [selectedFile, setSelectedFile] = useState<DocumentPickerAsset | null>(null);
  const [busy, setBusy] = useState(false);
  const [document, setDocument] = useState<TrinketDocument | null>(null);
  const [events, setEvents] = useState<TrinketEvent[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const mounted = useRef(true);
  useEffect(() => () => {
    mounted.current = false;
  }, []);

  const show = (text: string | null, error = false) => {
    setMessage(text);
    setIsError(error);
  };

  // Poll while the worker extracts dates (can take a few minutes).
  const documentId = document?.id;
  const processing = document?.status === "processing";
  useEffect(() => {
    if (!api || !documentId || !processing) return;
    const timer = setInterval(async () => {
      try {
        const result = await getDocument(api, documentId);
        if (!mounted.current) return;
        if (!result.ok) return show(result.message, true);
        setDocument(result.value.document);
        setEvents(result.value.events);
        if (result.value.document.status === "failed") {
          show(FAILURE_MESSAGES[result.value.document.error_code ?? ""] ??
            "We couldn't read dates from this document. Try another file.", true);
        } else if (result.value.document.status === "review") {
          show("Review these dates, dismiss any that are wrong, then confirm.");
        }
      } catch {
        if (mounted.current) show("Lost connection to the backend; still retrying…", true);
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [api, documentId, processing]);

  if (state.kind === "signedOut") return <Redirect href="/" />;

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*"],
        copyToCacheDirectory: true,
      });
      if (!result.canceled && result.assets?.length) {
        setSelectedFile(result.assets[0]);
        setDocument(null);
        setEvents([]);
        show(null);
      }
    } catch {
      show("Could not open the document picker.", true);
    }
  };

  const run = async (action: () => Promise<void>) => {
    if (!api || busy) return;
    setBusy(true);
    try {
      await action();
    } catch {
      show(`Could not reach the backend at ${api.base}. Is it running?`, true);
    } finally {
      if (mounted.current) setBusy(false);
    }
  };

  const upload = () => run(async () => {
    if (!api || !selectedFile) return;
    show(null);
    const result = await uploadDocument(api, selectedFile);
    if (!result.ok) return show(result.message, true);
    setDocument(result.value.document);
    setEvents([]);
    show("Uploaded. Finding dates — this can take a few minutes.");
  });

  const toggleDismissed = (event: TrinketEvent) => run(async () => {
    if (!api) return;
    const result = await setEventStatus(api, event.id, event.status === "dismissed" ? "draft" : "dismissed");
    if (!result.ok) return show(result.message, true);
    setEvents((current) => current.map((e) => (e.id === event.id ? result.value : e)));
  });

  const confirmAll = () => run(async () => {
    if (!api || !document) return;
    const result = await confirmDocument(api, document.id);
    if (!result.ok) return show(result.message, true);
    setDocument(result.value);
    setEvents((current) => current.map((e) => (e.status === "draft" ? { ...e, status: "confirmed" } : e)));
    show("Saved to your quest board. Reminders will arrive in a later update.");
  });

  const reviewing = document?.status === "review";
  const disabled = busy || !api || processing;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Upload a document</Text>
      <Text style={styles.subtitle}>
        PDF or image. Trinket finds the dates, then you review them before they are saved.
      </Text>

      {state.kind === "misconfigured" && (
        <Text style={[styles.message, styles.error]}>{state.message}</Text>
      )}

      <Pressable
        style={[styles.button, disabled && styles.buttonDisabled]}
        onPress={pickDocument}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityState={{ disabled, busy }}
      >
        <Text style={styles.buttonText}>
          {selectedFile ? `Selected: ${selectedFile.name}` : "Pick document (PDF / image)"}
        </Text>
      </Pressable>

      {selectedFile && !document && (
        <Pressable
          style={[styles.button, styles.uploadButton, disabled && styles.buttonDisabled]}
          onPress={upload}
          disabled={disabled}
          accessibilityRole="button"
          accessibilityState={{ disabled, busy }}
        >
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Upload & find dates</Text>}
        </Pressable>
      )}

      {processing && <ActivityIndicator color="#754a18" accessibilityLabel="Finding dates" />}

      {message && (
        <Text accessibilityLiveRegion="polite" style={[styles.message, isError ? styles.error : styles.success]}>
          {message}
        </Text>
      )}

      {document && document.status !== "processing" && document.status !== "failed" && (
        <View style={styles.results}>
          <Text style={styles.resultsTitle}>
            {reviewing ? "Dates found — not saved until you confirm" : "Saved dates"}
          </Text>
          {events.length === 0 && <Text style={styles.empty}>No dates were found in this document.</Text>}
          {events.map((event) => (
            <View key={event.id} style={[styles.eventCard, event.status === "dismissed" && styles.dismissed]}>
              <Text style={styles.eventTitle}>{event.title}</Text>
              <Text style={styles.eventDetail}>{formatWhen(event)} · {event.category}</Text>
              {reviewing && (
                <View style={styles.eventActions}>
                  <Pressable accessibilityRole="button" disabled={busy} onPress={() => toggleDismissed(event)}>
                    <Text style={styles.smallAction}>
                      {event.status === "dismissed" ? "Restore" : "Dismiss"}
                    </Text>
                  </Pressable>
                </View>
              )}
            </View>
          ))}
          {reviewing && (
            <Pressable
              style={[styles.button, styles.uploadButton, busy && styles.buttonDisabled]}
              onPress={confirmAll}
              disabled={busy}
              accessibilityRole="button"
              accessibilityState={{ disabled: busy, busy }}
            >
              <Text style={styles.buttonText}>Confirm dates</Text>
            </Pressable>
          )}
        </View>
      )}

      <View style={styles.links}>
        <Link href="/board" style={styles.link}>
          Back to board
        </Link>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f0e6" },
  content: { padding: 24, paddingBottom: 48 },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 8,
    textAlign: "center",
    color: "#2a1c0d",
  },
  subtitle: {
    fontSize: 14,
    color: "#5c4526",
    textAlign: "center",
    marginBottom: 20,
  },
  button: {
    backgroundColor: "#754a18",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 12,
  },
  uploadButton: { backgroundColor: "#3e6b35" },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
  message: {
    marginTop: 8,
    padding: 12,
    borderRadius: 8,
    fontSize: 14,
  },
  success: { backgroundColor: "#e2efd8", color: "#274e13" },
  error: { backgroundColor: "#f7ddd8", color: "#8a1f11" },
  results: { marginTop: 20 },
  resultsTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#5c4526",
    marginBottom: 10,
  },
  empty: { color: "#5c4526", fontStyle: "italic" },
  eventCard: {
    backgroundColor: "#fff",
    padding: 14,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#e0d4b8",
  },
  eventTitle: { fontSize: 16, fontWeight: "bold", color: "#2a1c0d" },
  eventDetail: { fontSize: 14, color: "#555", marginTop: 2 },
  eventActions: { flexDirection: "row", gap: 16, marginTop: 8 },
  smallAction: { color: "#754a18", textDecorationLine: "underline", fontSize: 14 },
  dismissed: { opacity: 0.5 },
  links: {
    marginTop: 24,
    flexDirection: "row",
    justifyContent: "center",
    gap: 24,
  },
  link: { color: "#754a18", textDecorationLine: "underline", fontSize: 16 },
});
