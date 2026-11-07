import { Stack } from "expo-router";

// Consistent wood/parchment header across screens.
const screenOptions = {
  headerStyle: { backgroundColor: "#4a2f14" },
  headerTintColor: "#f0e0c0",
  headerTitleStyle: { fontWeight: "600" as const },
  contentStyle: { backgroundColor: "#000" },
};

export default function RootLayout() {
  return (
    <Stack screenOptions={screenOptions}>
      <Stack.Screen name="index" options={{ title: "Trinket", headerShown: false }} />
      <Stack.Screen name="board" options={{ title: "Quest Board" }} />
      <Stack.Screen name="upload" options={{ title: "Upload Document" }} />
    </Stack>
  );
}
