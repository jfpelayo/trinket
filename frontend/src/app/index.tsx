import { PirataOne_400Regular, useFonts } from "@expo-google-fonts/pirata-one";
import { Image, ImageBackground } from "expo-image";
import { Redirect } from "expo-router";
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

import { supabase, supabaseConfigured, useSession } from "@/lib/supabase";

type Mode = "signIn" | "signUp";

export default function LoginScreen() {
  const [fontsLoaded, fontError] = useFonts({ PirataOne_400Regular });
  const session = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<Mode>("signIn");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(
    supabaseConfigured
      ? null
      : "Sign-in is not configured. Add EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_KEY to frontend/.env and restart Expo.",
  );

  // Fall back to the system font while Pirata loads or if it fails.
  const fontFamily = fontsLoaded && !fontError ? "PirataOne_400Regular" : undefined;

  if (session) return <Redirect href="/board" />;

  const submit = async () => {
    if (!supabaseConfigured || busy) return;
    if (!email.trim() || !password) {
      setMessage("Enter your email and password.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const credentials = { email: email.trim(), password };
      const { data, error } = mode === "signIn"
        ? await supabase.auth.signInWithPassword(credentials)
        : await supabase.auth.signUp(credentials);
      if (error) setMessage(error.message);
      else if (mode === "signUp" && !data.session) {
        setMessage("Check your email to confirm your account, then log in.");
        setMode("signIn");
      }
    } catch {
      setMessage("Could not reach the sign-in service. Check your connection.");
    } finally {
      setPassword("");
      setBusy(false);
    }
  };

  const actionLabel = mode === "signIn" ? "Log in" : "Sign up";

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
            {message && (
              <Text accessibilityLiveRegion="polite" style={[styles.previewBanner, { fontFamily }]}>
                {message}
              </Text>
            )}

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
                <Text style={[styles.fieldLabel, { fontFamily }]}>Email</Text>
                <TextInput
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@berkeley.edu"
                  placeholderTextColor="#40300f"
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="email"
                  keyboardType="email-address"
                  accessibilityLabel="Email"
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
                  onSubmitEditing={submit}
                  placeholder="Password"
                  placeholderTextColor="#40300f"
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete={mode === "signIn" ? "current-password" : "new-password"}
                  accessibilityLabel="Password"
                  style={[styles.input, { fontFamily }]}
                />
              </View>
            </ImageBackground>

            <Pressable
              onPress={submit}
              disabled={busy || !supabaseConfigured}
              accessibilityRole="button"
              accessibilityLabel={actionLabel}
              accessibilityState={{ disabled: busy || !supabaseConfigured, busy }}
              style={[styles.buttonWrap, (busy || !supabaseConfigured) && styles.buttonBusy]}
            >
              <ImageBackground
                source={require("@/assets/images/woodtexture1.png")}
                contentFit="fill"
                style={styles.woodButton}
              >
                <Text style={[styles.woodButtonText, { fontFamily }]}>
                  {busy ? "One moment…" : actionLabel}
                </Text>
              </ImageBackground>
            </Pressable>

            <View style={styles.signupRow}>
              <Text style={[styles.signupText, { fontFamily }]}>
                {mode === "signIn" ? "Don't have an account? " : "Already have an account? "}
              </Text>
              <Pressable
                accessibilityRole="button"
                onPress={() => {
                  setMode(mode === "signIn" ? "signUp" : "signIn");
                  setMessage(null);
                }}
              >
                <Text style={[styles.signupLink, { fontFamily }]}>
                  {mode === "signIn" ? "Sign Up" : "Log In"}
                </Text>
              </Pressable>
            </View>
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
  buttonWrap: { width: "100%", marginTop: 4 },
  buttonBusy: { opacity: 0.55 },
  woodButton: {
    borderRadius: 30,
    overflow: "hidden",
    borderWidth: 2.5,
    borderColor: "#000",
    padding: 16,
    alignItems: "center",
  },
  woodButtonText: { fontSize: 26, color: "#040000" },
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
  signupLink: {
    fontSize: 16,
    color: "#ffe9b8",
    textDecorationLine: "underline",
  },
});
