import { useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { ScriptChips } from "../src/components/ScriptChips";
import { VersionCard } from "../src/components/VersionCard";
import { useSearchSession } from "../src/store/session";
import { colors } from "../src/theme";
import { groupVersions } from "../src/utils/groupVersions";

export default function ResultsScreen() {
  const router = useRouter();
  const query = useSearchSession((state) => state.query);
  const hits = useSearchSession((state) => state.hits);
  const byUrl = useSearchSession((state) => state.byUrl);
  const select = useSearchSession((state) => state.select);
  const [script, setScript] = useState<string | null>(null);

  const ready = useMemo(
    () =>
      Object.values(byUrl).flatMap((status) => (status.state === "ready" ? [status.version] : [])),
    [byUrl],
  );

  const grouped = useMemo(() => groupVersions(ready), [ready]);
  const filtered = script ? grouped.filter((item) => item.script === script) : grouped;
  const scripts = grouped.map((item) => item.script);

  const pending = Object.values(byUrl).filter(
    (status) => status.state === "pending" || status.state === "loading",
  ).length;
  const errors = Object.values(byUrl).filter((status) => status.state === "error").length;

  if (!hits.length) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>No search yet</Text>
        <Text style={styles.emptyBody}>Go back and enter a sloka or mantra name.</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.query}>Results for “{query}”</Text>
      <Text style={styles.progress}>
        {grouped.length} version{grouped.length === 1 ? "" : "s"}
        {pending ? ` · still reading ${pending} page${pending === 1 ? "" : "s"}` : ""}
        {errors ? ` · ${errors} page${errors === 1 ? "" : "s"} skipped` : ""}
      </Text>
      {pending ? <ActivityIndicator color={colors.saffron} style={{ marginVertical: 8 }} /> : null}
      {scripts.length ? (
        <ScriptChips scripts={scripts} selected={script} onSelect={setScript} />
      ) : null}

      {!pending && !filtered.length ? (
        <Text style={styles.emptyBody}>
          No verse text could be extracted. Try a more specific name, or another script spelling.
        </Text>
      ) : null}

      {filtered.map((version) => (
        <VersionCard
          key={`${version.fingerprint}:${version.source_url}`}
          version={version}
          onPress={() => {
            select(version);
            router.push("/sloka/view");
          }}
        />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    gap: 12,
    backgroundColor: colors.parchment,
    flexGrow: 1,
  },
  query: {
    fontFamily: "NotoSerif_700Bold",
    fontSize: 22,
    color: colors.maroon,
  },
  progress: {
    color: colors.muted,
    fontSize: 13,
  },
  empty: {
    flex: 1,
    backgroundColor: colors.parchment,
    padding: 24,
    justifyContent: "center",
    gap: 8,
  },
  emptyTitle: {
    fontFamily: "NotoSerif_700Bold",
    fontSize: 22,
    color: colors.maroon,
  },
  emptyBody: {
    color: colors.muted,
    lineHeight: 22,
  },
});
