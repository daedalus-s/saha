import { useLocalSearchParams } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { ConsentSheet } from "../../src/components/ConsentSheet";
import { LyricsDisclaimer } from "../../src/components/LyricsDisclaimer";
import { MeaningDisclaimer } from "../../src/components/MeaningDisclaimer";
import { ScriptChips } from "../../src/components/ScriptChips";
import { useSlokaActions } from "../../src/hooks/useSlokaActions";
import { useConsent } from "../../src/store/consent";
import { useSaved } from "../../src/store/saved";
import { useSearchSession } from "../../src/store/session";
import { colors } from "../../src/theme";
import { fontForScript } from "../../src/utils/fonts";
import { SCRIPTS, scriptLabel } from "../../src/utils/scripts";
import { isAiGenerated } from "../../src/utils/source";

export default function SlokaDetailScreen() {
  useLocalSearchParams<{ id: string }>();
  const version = useSearchSession((state) => state.selected);
  const save = useSaved((state) => state.save);
  const items = useSaved((state) => state.items);
  const accept = useConsent((state) => state.accept);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [sideBySide, setSideBySide] = useState(false);
  const actions = useSlokaActions(version);

  const saved = useMemo(
    () =>
      version
        ? items.some((item) => item.fingerprint === version.fingerprint && item.source_url === version.source_url)
        : false,
    [items, version],
  );

  if (!version) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>No sloka selected</Text>
        <Text style={styles.meta}>Go back to results and pick a version.</Text>
      </View>
    );
  }

  const displayXlit =
    actions.targetScript && actions.targetScript !== version.script ? actions.xlit : null;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <ConsentSheet
        visible={sheetVisible}
        onContinue={() => {
          accept();
          setSheetVisible(false);
          void actions.loadMeaning();
        }}
        onNotNow={() => setSheetVisible(false)}
      />
      <Text style={styles.title}>{version.title}</Text>
      <Text style={styles.meta}>
        {scriptLabel(version.script)}
        {version.deity ? ` · ${version.deity}` : ""} · {version.source_domain}
      </Text>
      {isAiGenerated(version) ? (
        <LyricsDisclaimer />
      ) : (
        <Text style={styles.link} onPress={() => Linking.openURL(version.source_url)}>
          Source page
        </Text>
      )}

      <Text style={styles.section}>Transliterate into</Text>
      <ScriptChips
        scripts={[version.script, ...SCRIPTS.filter((item) => item !== version.script)]}
        selected={actions.targetScript ?? version.script}
        onSelect={(value) => void actions.pickScript(value)}
        includeAll={false}
      />
      {actions.xlitBusy ? <ActivityIndicator color={colors.saffron} /> : null}

      <View style={styles.row}>
        <Pressable
          style={styles.secondary}
          onPress={async () => {
            const result = await actions.toggleMeaning();
            if (result === "needs-consent") setSheetVisible(true);
          }}
        >
          <Text style={styles.secondaryLabel}>
            {actions.showMeaning ? "Hide meaning" : "Show meaning"}
          </Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={() => setSideBySide((value) => !value)}>
          <Text style={styles.secondaryLabel}>{sideBySide ? "Stacked" : "Side by side"}</Text>
        </Pressable>
      </View>
      {actions.meaningBusy ? <ActivityIndicator color={colors.saffron} /> : null}
      {actions.showMeaning ? <MeaningDisclaimer /> : null}
      {actions.error ? <Text style={styles.error}>{actions.error}</Text> : null}

      <Text style={styles.section}>Text</Text>
      {version.verses.map((verse, index) => {
        const xlitLine = displayXlit?.[index];
        const meaningLine = actions.showMeaning ? actions.meanings?.[index] : undefined;
        if (sideBySide && xlitLine) {
          return (
            <View key={index} style={styles.pair}>
              <Text style={[styles.verse, styles.pairCol, { fontFamily: fontForScript(version.script) }]}>{verse}</Text>
              <Text style={[styles.verse, styles.pairCol, { fontFamily: fontForScript(actions.targetScript ?? "latin") }]}>{xlitLine}</Text>
              {meaningLine ? <Text style={styles.meaning}>{meaningLine}</Text> : null}
            </View>
          );
        }
        return (
          <View key={index} style={styles.block}>
            <Text style={[styles.verse, { fontFamily: fontForScript(version.script) }]}>{verse}</Text>
            {xlitLine ? (
              <Text style={[styles.xlit, { fontFamily: fontForScript(actions.targetScript ?? "latin") }]}>{xlitLine}</Text>
            ) : null}
            {meaningLine ? <Text style={styles.meaning}>{meaningLine}</Text> : null}
          </View>
        );
      })}

      <View style={styles.actions}>
        <Pressable style={styles.button} onPress={() => save(version)} disabled={saved}>
          <Text style={styles.buttonLabel}>{saved ? "Saved on this device" : "Save"}</Text>
        </Pressable>
        <Pressable style={styles.button} onPress={() => void actions.exportPdf()} disabled={actions.pdfBusy}>
          <Text style={styles.buttonLabel}>{actions.pdfBusy ? "Preparing PDF…" : "Export PDF"}</Text>
        </Pressable>
      </View>
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
  title: {
    fontFamily: "NotoSerif_700Bold",
    fontSize: 24,
    color: colors.maroon,
  },
  meta: {
    color: colors.muted,
    fontSize: 13,
  },
  link: {
    color: colors.saffron,
    fontSize: 13,
  },
  section: {
    marginTop: 8,
    fontWeight: "700",
    color: colors.ink,
  },
  row: {
    flexDirection: "row",
    gap: 8,
  },
  secondary: {
    backgroundColor: colors.chip,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
  },
  secondaryLabel: {
    color: colors.ink,
    fontSize: 13,
  },
  verse: {
    fontSize: 18,
    lineHeight: 30,
    color: colors.ink,
  },
  xlit: {
    fontSize: 16,
    lineHeight: 26,
    color: colors.maroon,
  },
  meaning: {
    fontSize: 14,
    lineHeight: 22,
    color: colors.muted,
    marginTop: 4,
  },
  block: {
    gap: 4,
    paddingBottom: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  pair: {
    gap: 6,
    paddingBottom: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  pairCol: {
    flex: 1,
  },
  actions: {
    gap: 10,
    marginTop: 12,
    marginBottom: 24,
  },
  button: {
    backgroundColor: colors.saffron,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  buttonLabel: {
    color: "#fff",
    fontWeight: "700",
  },
  error: {
    color: colors.error,
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
});
