import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import type { GroupedVersion } from "../api/types";
import { colors } from "../theme";
import { fontForScript } from "../utils/fonts";
import { isAiGenerated } from "../utils/source";
import { scriptLabel } from "../utils/scripts";

type Props = {
  version: GroupedVersion;
  onPress: () => void;
};

export function VersionCard({ version, onPress }: Props) {
  const preview = version.verses[0] ?? "";
  const extra = version.alsoOn.length;
  return (
    <Pressable onPress={onPress} style={styles.card}>
      <View style={styles.top}>
        <Text style={styles.title}>{version.title}</Text>
        <Text style={styles.script}>{scriptLabel(version.script)}</Text>
      </View>
      <Text style={[styles.verse, { fontFamily: fontForScript(version.script) }]} numberOfLines={3}>
        {preview}
      </Text>
      <Text style={styles.meta}>
        {isAiGenerated(version) ? "AI-generated lyrics" : version.source_domain}
        {extra ? ` · also on ${extra} other site${extra === 1 ? "" : "s"}` : ""}
      </Text>
      {isAiGenerated(version) ? (
        <Text style={styles.meta}>Verify with a printed edition.</Text>
      ) : (
        <Text style={styles.link} onPress={() => Linking.openURL(version.source_url)}>
          Open source
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.line,
    gap: 8,
  },
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
    alignItems: "flex-start",
  },
  title: {
    flex: 1,
    fontSize: 17,
    color: colors.maroon,
    fontWeight: "600",
  },
  script: {
    fontSize: 12,
    color: colors.saffron,
    fontWeight: "600",
  },
  verse: {
    fontSize: 16,
    lineHeight: 26,
    color: colors.ink,
  },
  meta: {
    fontSize: 12,
    color: colors.muted,
  },
  link: {
    fontSize: 12,
    color: colors.saffron,
  },
});
