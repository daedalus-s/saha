import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useFonts as useNotoSerif,
  NotoSerif_400Regular,
  NotoSerif_700Bold,
} from "@expo-google-fonts/noto-serif";
import { useFonts as useDevanagari, NotoSansDevanagari_400Regular } from "@expo-google-fonts/noto-sans-devanagari";
import { useFonts as useTamil, NotoSansTamil_400Regular } from "@expo-google-fonts/noto-sans-tamil";
import { useFonts as useTelugu, NotoSansTelugu_400Regular } from "@expo-google-fonts/noto-sans-telugu";
import { useFonts as useKannada, NotoSansKannada_400Regular } from "@expo-google-fonts/noto-sans-kannada";
import { useFonts as useMalayalam, NotoSansMalayalam_400Regular } from "@expo-google-fonts/noto-sans-malayalam";
import { useFonts as useGujarati, NotoSansGujarati_400Regular } from "@expo-google-fonts/noto-sans-gujarati";
import { useFonts as useBengali, NotoSansBengali_400Regular } from "@expo-google-fonts/noto-sans-bengali";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";

import { colors } from "../src/theme";

SplashScreen.preventAutoHideAsync().catch(() => undefined);

const queryClient = new QueryClient();

export default function RootLayout() {
  const [serif] = useNotoSerif({ NotoSerif_400Regular, NotoSerif_700Bold });
  const [deva] = useDevanagari({ NotoSansDevanagari_400Regular });
  const [tamil] = useTamil({ NotoSansTamil_400Regular });
  const [telugu] = useTelugu({ NotoSansTelugu_400Regular });
  const [kannada] = useKannada({ NotoSansKannada_400Regular });
  const [malayalam] = useMalayalam({ NotoSansMalayalam_400Regular });
  const [gujarati] = useGujarati({ NotoSansGujarati_400Regular });
  const [bengali] = useBengali({ NotoSansBengali_400Regular });

  const ready =
    serif && deva && tamil && telugu && kannada && malayalam && gujarati && bengali;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => undefined);
  }, [ready]);

  if (!ready) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.parchment },
          headerTintColor: colors.maroon,
          headerTitleStyle: { fontFamily: "NotoSerif_700Bold" },
          contentStyle: { backgroundColor: colors.parchment },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="results" options={{ title: "Versions" }} />
        <Stack.Screen name="sloka/[id]" options={{ title: "Sloka" }} />
      </Stack>
    </QueryClientProvider>
  );
}
