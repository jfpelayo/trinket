import * as DocumentPicker from "expo-document-picker";
import type { DocumentPickerAsset } from "expo-document-picker";
import { Link } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  EventItem,
  getApiBase,
  uploadDocument,
} from "@/lib/upload";

export default function UploadScreen() {
  const [selectedFile, setSelectedFile] =
    useState<DocumentPickerAsset | null>(null);
  const [uploading, setUploading] = useState(false);
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);

  const apiBase = getApiBase();

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*"],
        copyToCacheDirectory: true,
      });
      if (!result.canceled && result.assets?.length) {
        setSelectedFile(result.assets[0]);
        setEvents(null);
        setMessage(null);
        setIsError(false);
      }
    } catch {
      setIsError(true);
      setMessage("Could not open the document picker.");
    }
  };

  const upload = async () => {
    if (!selectedFile || uploading) return;
    if (!apiBase) {
      setIsError(true);
      setMessage(
        Platform.OS === "web"
          ? "EXPO_PUBLIC_API_URL is missing or invalid. Set an absolute http(s) URL in frontend/.env (e.g. http://localhost:8000) and restart Expo."
          : "EXPO_PUBLIC_API_URL is missing or invalid. On a device/emulator set an absolute http(s) URL to your computer's LAN IP, e.g. http://192.168.x.x:8000 (Android emulator: http://10.0.2.2:8000), in frontend/.env and restart Expo.",
      );
      return;
    }

    setUploading(true);
    setMessage(null);
    setIsError(false);
    try {
      const result = await uploadDocument(selectedFile, apiBase);
      if (result.ok) {
        setEvents(result.events);
        setMessage(
          `Processed ${result.filename || "document"} (timezone: ${result.userTimezone || "unknown"}).`,
        );
      } else {
        setEvents(null);
        setIsError(true);
        setMessage(result.message);
      }
    } catch {
      setEvents(null);
      setIsError(true);
      setMessage(
        `Could not reach the backend at ${apiBase}. Is it running?`,
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      <Text style={styles.title}>Upload a document</Text>
      <Text style={styles.subtitle}>
        PDF or image — the backend extracts draft events for review.
      </Text>

      <Pressable
        style={[styles.button, uploading && styles.buttonDisabled]}
        onPress={pickDocument}
        disabled={uploading}
        accessibilityRole="button"
        accessibilityState={{ disabled: uploading, busy: uploading }}
      >
        <Text style={styles.buttonText}>
          {selectedFile
            ? `Selected: ${selectedFile.name}`
            : "Pick document (PDF / image)"}
        </Text>
      </Pressable>

      {selectedFile && (
        <Pressable
          style={[styles.button, styles.uploadButton, uploading && styles.buttonDisabled]}
          onPress={upload}
          disabled={uploading}
          accessibilityRole="button"
          accessibilityState={{ disabled: uploading, busy: uploading }}
        >
          {uploading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Upload & process</Text>
          )}
        </Pressable>
      )}

      {message && (
        <Text style={[styles.message, isError ? styles.error : styles.success]}>
          {message}
        </Text>
      )}

      {events !== null && (
        <View style={styles.results}>
          <Text style={styles.resultsTitle}>
            Draft events — review only; not saved or scheduled
          </Text>
          {events.length === 0 && (
            <Text style={styles.empty}>
              No events were found in this document.
            </Text>
          )}
          {events.map((item, index) => (
            <View key={index} style={styles.eventCard}>
              <Text style={styles.eventTitle}>{item.title}</Text>
              <Text style={styles.eventDetail}>Category: {item.category}</Text>
              <Text style={styles.eventDetail}>Date: {item.event_date}</Text>
            </View>
          ))}
        </View>
      )}

      <View style={styles.links}>
        <Link href="/board" style={styles.link}>
          Back to board
        </Link>
        <Link href="/" style={styles.link}>
          Back to login
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
  links: {
    marginTop: 24,
    flexDirection: "row",
    justifyContent: "center",
    gap: 24,
  },
  link: { color: "#754a18", textDecorationLine: "underline", fontSize: 16 },
});
