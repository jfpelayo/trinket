import { PirataOne_400Regular, useFonts } from "@expo-google-fonts/pirata-one";
import { Image, ImageBackground } from "expo-image";
import { router } from "expo-router";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

// Login PREVIEW only — Supabase sign-in is not connected yet.
// Credentials are never logged, sent, or passed to other routes.
export default function LoginScreen() {
  const [fontsLoaded, fontError] = useFonts({ PirataOne_400Regular });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Fall back to the system font while Pirata loads or if it fails.
  const fontFamily = fontsLoaded && !fontError ? "PirataOne_400Regular" : undefined;

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <ImageBackground
          source={require("@/assets/images/login-page.png")}
          contentFit="cover"
          style={styles.background}
        >
          <Image
            source={require("@/assets/images/welcome.png")}
            contentFit="contain"
            style={styles.welcome}
          />

          <View style={styles.form}>
            <Text style={[styles.previewBanner, { fontFamily }]}>
              Login preview — Supabase sign-in is not connected yet
            </Text>

            <ImageBackground
              source={require("@/assets/images/mappaper.png")}
              contentFit="fill"
              style={styles.field}
            >
              <Image
                source={require("@/assets/images/username.png")}
                contentFit="contain"
                style={styles.fieldIcon}
              />
              <View style={styles.fieldTextWrap}>
                <Text style={[styles.fieldLabel, { fontFamily }]}>Username</Text>
                <TextInput
                  value={username}
                  onChangeText={setUsername}
                  placeholder="Username"
                  placeholderTextColor="#40300f"
                  autoCapitalize="none"
                  autoCorrect={false}
                  accessibilityLabel="Username"
                  style={[styles.input, { fontFamily }]}
                />
              </View>
            </ImageBackground>

            <ImageBackground
              source={require("@/assets/images/mappaper.png")}
              contentFit="fill"
              style={styles.field}
            >
              <Image
                source={require("@/assets/images/password.png")}
                contentFit="contain"
                style={styles.fieldIcon}
              />
              <View style={styles.fieldTextWrap}>
                <Text style={[styles.fieldLabel, { fontFamily }]}>Password</Text>
                <TextInput
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Password"
                  placeholderTextColor="#40300f"
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                  accessibilityLabel="Password"
                  style={[styles.input, { fontFamily }]}
                />
              </View>
            </ImageBackground>

            <Pressable
              disabled
              accessibilityRole="button"
              accessibilityLabel="Log in (disabled in preview)"
              accessibilityState={{ disabled: true }}
              style={styles.disabledButtonWrap}
            >
              <ImageBackground
                source={require("@/assets/images/woodtexture1.png")}
                contentFit="fill"
                style={styles.woodButton}
              >
                <Text style={[styles.woodButtonText, { fontFamily }]}>
                  Log in
                </Text>
              </ImageBackground>
            </Pressable>
            <Text style={[styles.disabledNote, { fontFamily }]}>
              Sign-in is disabled until accounts are connected.
            </Text>

            <View style={styles.signupRow}>
              <Text style={[styles.signupText, { fontFamily }]}>
                Don&apos;t have an account?{" "}
              </Text>
              <Text
                accessibilityLabel="Sign up (disabled in preview)"
                style={[styles.signupLinkDisabled, { fontFamily }]}
              >
                Sign Up
              </Text>
              <Text style={[styles.signupText, { fontFamily }]}> Now!</Text>
            </View>

            <Pressable
              onPress={() => router.push("/board")}
              accessibilityRole="button"
              accessibilityLabel="Preview app without signing in"
              style={styles.previewLinkWrap}
            >
              {({ pressed }) => (
                <Text
                  style={[
                    styles.previewLink,
                    { fontFamily },
                    pressed && styles.previewLinkPressed,
                  ]}
                >
                  Preview app (no sign-in) →
                </Text>
              )}
            </Pressable>
          </View>
        </ImageBackground>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  scrollContent: { flexGrow: 1 },
  background: {
    flex: 1,
    width: "100%",
    maxWidth: 500,
    alignSelf: "center",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingBottom: 48,
  },
  welcome: {
    width: "80%",
    maxWidth: 400,
    height: 240,
    marginTop: 48,
  },
  form: {
    width: "100%",
    maxWidth: 320,
    alignItems: "center",
    marginTop: 24,
    gap: 12,
  },
  previewBanner: {
    fontSize: 16,
    color: "#f0e0c0",
    backgroundColor: "rgba(0,0,0,0.55)",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    textAlign: "center",
    marginBottom: 8,
  },
  field: {
    flexDirection: "row",
    alignItems: "center",
    width: "100%",
    minHeight: 72,
    borderRadius: 15,
    overflow: "hidden",
    borderWidth: 2.5,
    borderColor: "#000",
    paddingHorizontal: 12,
  },
  fieldIcon: { width: 30, height: 30, marginRight: 10 },
  fieldTextWrap: { flex: 1, minWidth: 0 },
  fieldLabel: { fontSize: 14, color: "#40300f" },
  input: {
    paddingVertical: 8,
    fontSize: 20,
    color: "#040000",
    minWidth: 0,
  },
  disabledButtonWrap: { width: "100%", opacity: 0.55, marginTop: 4 },
  woodButton: {
    borderRadius: 30,
    overflow: "hidden",
    borderWidth: 2.5,
    borderColor: "#000",
    padding: 16,
    alignItems: "center",
  },
  woodButtonText: { fontSize: 26, color: "#040000" },
  disabledNote: {
    fontSize: 14,
    color: "#f0e0c0",
    backgroundColor: "rgba(0,0,0,0.45)",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    textAlign: "center",
  },
  signupRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 4,
    backgroundColor: "rgba(0,0,0,0.4)",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  signupText: { fontSize: 16, color: "#f0e0c0" },
  signupLinkDisabled: {
    fontSize: 16,
    color: "#9a8a6a",
    textDecorationLine: "underline",
  },
  previewLinkWrap: { marginTop: 12 },
  previewLink: {
    fontSize: 18,
    color: "#f0e0c0",
    textDecorationLine: "underline",
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  previewLinkPressed: { color: "#ffffff" },
});
