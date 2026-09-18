import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { API_URL, api } from "../../src/api/client";
import { ConsentSheet } from "../../src/components/ConsentSheet";
import { useConsent } from "../../src/store/consent";
import { useHistory } from "../../src/store/history";
import { useSearchSession } from "../../src/store/session";
import { colors } from "../../src/theme";

export default function SearchScreen() {
  const router = useRouter();
  const recent = useHistory((state) => state.recent);
  const addRecent = useHistory((state) => state.add);
  const clearRecent = useHistory((state) => state.clear);
  const accepted = useConsent((state) => state.accepted);
  const accept = useConsent((state) => state.accept);
  const withdraw = useConsent((state) => state.withdraw);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);
  const pendingQuery = useRef<string | null>(null);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: 1,
  });

  async function actuallySearch(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.search(trimmed);
      addRecent(trimmed);
      useSearchSession.getState().start(trimmed, result.hits);
      router.push("/results");
      void useSearchSession.getState().extractAll(
        trimmed,
        result.hits.map((hit) => hit.url),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  function runSearch(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return;
    if (!useConsent.getState().accepted) {
      pendingQuery.current = trimmed;
      setSheetVisible(true);
      return;
    }
    void actuallySearch(trimmed);
  }

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <ConsentSheet
        visible={sheetVisible}
        onContinue={() => {
          accept();
          setSheetVisible(false);
          const queued = pendingQuery.current;
          pendingQuery.current = null;
          if (queued) void actuallySearch(queued);
        }}
        onNotNow={() => {
          setSheetVisible(false);
          pendingQuery.current = null;
        }}
      />
      <Text style={styles.kicker}>Find a sloka or mantra</Text>
      <Text style={styles.lede}>
        Search the web for versions in different scripts, transliterate, add an English meaning, and export a PDF.
      </Text>
      <View style={styles.searchBox}>
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder="e.g. Hanuman Chalisa"
          placeholderTextColor={colors.muted}
          style={styles.input}
          autoCorrect={false}
          returnKeyType="search"
          onSubmitEditing={() => runSearch(query)}
        />
        <Pressable
          style={[styles.button, busy && styles.buttonDisabled]}
          onPress={() => runSearch(query)}
          disabled={busy}
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonLabel}>Search</Text>
          )}
        </Pressable>
      </View>
      {health.isError ? (
        <Text style={styles.error}>
          Cannot reach the API at the configured URL. Start the backend or set EXPO_PUBLIC_API_URL.
        </Text>
      ) : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {recent.length ? (
        <View style={styles.recent}>
          <View style={styles.recentHeader}>
            <Text style={styles.section}>Recent</Text>
            <Pressable onPress={clearRecent}>
              <Text style={styles.clear}>Clear</Text>
            </Pressable>
          </View>
          {recent.map((item) => (
            <Pressable key={item} onPress={() => runSearch(item)} style={styles.recentItem}>
              <Text style={styles.recentText}>{item}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}

      <Text style={styles.footer}>
        Verse text is shown with a link to the page it was found on. English meanings are
        AI-generated; verify with a scholar.{" "}
        <Text style={styles.link} onPress={() => Linking.openURL(`${API_URL}/privacy`)}>
          Privacy policy
        </Text>
        {" · "}
        <Text style={styles.link} onPress={() => Linking.openURL(`${API_URL}/terms`)}>
          Terms of use
        </Text>
      </Text>
      {accepted ? (
        <Pressable onPress={withdraw}>
          <Text style={styles.withdraw}>Withdraw data-sharing permission</Text>
        </Pressable>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    gap: 16,
    backgroundColor: colors.parchment,
    flexGrow: 1,
  },
  kicker: {
    fontFamily: "NotoSerif_700Bold",
    fontSize: 26,
    color: colors.maroon,
  },
  lede: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
  },
  searchBox: {
    gap: 10,
  },
  input: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
    color: colors.ink,
  },
  button: {
    backgroundColor: colors.saffron,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonLabel: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 16,
  },
  error: {
    color: colors.error,
  },
  recent: {
    gap: 8,
    marginTop: 8,
  },
  recentHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  section: {
    fontWeight: "700",
    color: colors.ink,
  },
  clear: {
    color: colors.saffron,
    fontSize: 13,
  },
  recentItem: {
    backgroundColor: colors.card,
    borderRadius: 10,
    padding: 12,
    borderColor: colors.line,
    borderWidth: 1,
  },
  recentText: {
    color: colors.ink,
    fontSize: 15,
  },
  footer: {
    color: colors.muted,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 24,
  },
  link: {
    color: colors.saffron,
    fontSize: 12,
  },
  withdraw: {
    color: colors.muted,
    fontSize: 12,
    textDecorationLine: "underline",
  },
});
