import { useRouter } from "expo-router";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useSaved } from "../../src/store/saved";
import { useSearchSession } from "../../src/store/session";
import { colors } from "../../src/theme";
import { scriptLabel } from "../../src/utils/scripts";
import type { SlokaVersion } from "../../src/api/types";

export default function SavedScreen() {
  const items = useSaved((state) => state.items);
  const remove = useSaved((state) => state.remove);
  const select = useSearchSession((state) => state.select);
  const router = useRouter();

  function open(item: (typeof items)[number]) {
    const version: SlokaVersion = {
      title: item.title,
      script: item.script,
      verses: item.verses,
      source_url: item.source_url,
      source_domain: item.source_domain,
      fingerprint: item.fingerprint,
      normalized: "",
      also_on: [],
      ai_generated: item.ai_generated,
    };
    select(version);
    router.push("/sloka/saved");
  }

  if (!items.length) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>Nothing saved yet</Text>
        <Text style={styles.emptyBody}>
          When you find a version you like, tap Save on the sloka screen. It stays on this device.
        </Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.list}>
      {items.map((item) => (
        <Pressable key={item.id} style={styles.card} onPress={() => open(item)}>
          <Text style={styles.title}>{item.title}</Text>
          <Text style={styles.meta}>
            {scriptLabel(item.script)} · {item.source_domain}
          </Text>
          <Text style={styles.verse} numberOfLines={2}>
            {item.verses[0]}
          </Text>
          <Pressable onPress={() => remove(item.id)}>
            <Text style={styles.remove}>Remove</Text>
          </Pressable>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  list: {
    padding: 16,
    gap: 12,
    backgroundColor: colors.parchment,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.line,
    gap: 6,
  },
  title: {
    fontSize: 17,
    color: colors.maroon,
    fontWeight: "600",
  },
  meta: {
    fontSize: 12,
    color: colors.muted,
  },
  verse: {
    fontSize: 15,
    color: colors.ink,
    lineHeight: 24,
  },
  remove: {
    color: colors.error,
    fontSize: 13,
    marginTop: 4,
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
