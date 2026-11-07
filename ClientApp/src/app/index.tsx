import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ActivityIndicator,
  FlatList,
  Alert,
  Platform
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

// Replace with your actual local IP address (or 10.0.2.2 for Android emulator)
// In index.tsx
const BACKEND_URL = Platform.OS === 'web'
  ? "http://localhost:8000/api/v1/upload"
  : "http://10.44.13.36:8000/api/v1/upload";

interface EventItem {
  title: string;
  category: string;
  event_date: string;
}

export default function HomeScreen() {
  const [selectedFile, setSelectedFile] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [uploading, setUploading] = useState(false);
  const [extractedEvents, setExtractedEvents] = useState<EventItem[]>([]);

  // 1. Pick a PDF or Image Document
  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/*'],
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setSelectedFile(result.assets[0]);
        setExtractedEvents([]);
      }
    } catch (err) {
      console.error("Error picking document:", err);
    }
  };

  // 2. Upload Document to FastAPI Backend
  const uploadDocument = async () => {
    if (!selectedFile) {
      Alert.alert("Notice", "Please select a document first.");
      return;
    }

    setUploading(true);

    // Get device timezone string (e.g., 'America/New_York')
    const clientTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        // Fetch Push Notification Token
    let pushToken = "SIMULATOR_MOCK_TOKEN";

    // Only fetch real push tokens on native iOS/Android devices (skip on Web & Simulators)
    if (Platform.OS !== 'web' && Device.isDevice) {
      try {
        const { status } = await Notifications.requestPermissionsAsync();
        if (status === 'granted') {
          const tokenData = await Notifications.getDevicePushTokenAsync();
          pushToken = tokenData.data;
        }
      } catch (err) {
        console.warn("Could not fetch push token:", err);
      }
    }

    const formData = new FormData();
    // @ts-ignore - FormData expects file object on React Native
    if (Platform.OS === 'web') {
      // On Web: Convert URI to Blob/File so browser sends valid multipart file
      const res = await fetch(selectedFile.uri);
      const blob = await res.blob();
      const file = new File([blob], selectedFile.name, {
        type: selectedFile.mimeType || 'application/pdf'
      });
      formData.append('file', file);
    } else {
      // On Mobile (iOS/Android): Pass standard React Native file object
      // @ts-ignore
      formData.append('file', {
        uri: selectedFile.uri,
        name: selectedFile.name,
        type: selectedFile.mimeType || 'application/pdf',
      });
    }

    if (pushToken) {
      formData.append('device_token', pushToken);
    }

    try {
      const headers: Record<string, string> = {
        'X-Timezone': clientTimezone,
      };

      // Only set Content-Type on native mobile; on web, let the browser auto-generate the boundary
      if (Platform.OS !== 'web') {
        headers['Content-Type'] = 'multipart/form-data';
      }

      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        body: formData,
        headers: headers,
      });

      const data = await response.json();

      if (response.ok) {
        setExtractedEvents(data.extracted_events || []);
        Alert.alert("Success", `Events processed for timezone: ${data.user_timezone}`);
      } else {
        Alert.alert("Error", data.detail || "Failed to parse document.");
      }
    } catch (error) {
      console.error("Upload error:", error);
      Alert.alert("Network Error", "Could not reach the backend server. Verify local IP.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>DocExtract Mobile</Text>

      <TouchableOpacity style={styles.button} onPress={pickDocument}>
        <Text style={styles.buttonText}>
          {selectedFile ? `Selected: ${selectedFile.name}` : "Pick Document (PDF/Image)"}
        </Text>
      </TouchableOpacity>

      {selectedFile && (
        <TouchableOpacity
          style={[styles.button, styles.uploadButton]}
          onPress={uploadDocument}
          disabled={uploading}
        >
          {uploading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Upload & Process</Text>
          )}
        </TouchableOpacity>
      )}

      {extractedEvents.length > 0 && (
        <View style={styles.resultsContainer}>
          <Text style={styles.subtitle}>Extracted Events</Text>
          <FlatList
            data={extractedEvents}
            keyExtractor={(_, index) => index.toString()}
            renderItem={({ item }) => (
              <View style={styles.eventCard}>
                <Text style={styles.eventTitle}>{item.title}</Text>
                <Text style={styles.eventDetail}>Category: {item.category}</Text>
                <Text style={styles.eventDetail}>Date: {item.event_date}</Text>
              </View>
            )}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: '#f5f5f7',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  uploadButton: {
    backgroundColor: '#34C759',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  resultsContainer: {
    marginTop: 20,
    flex: 1,
  },
  eventCard: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  eventDetail: {
    fontSize: 14,
    color: '#555',
    marginTop: 2,
  },
});