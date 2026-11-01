import { useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { api } from "../../src/api/client";
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
import { MEANING_LANGUAGES, meaningLanguageLabel, meaningLanguageScript } from "../../src/utils/languages";
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
  const [paging, setPaging] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const pendingLanguage = useRef("en");
  const actions = useSlokaActions(version);
  const sourceUrl = version?.source_url ?? "";

  useEffect(() => {
    const start = useSearchSession.getState().selected;
    if (!start?.has_more || start.source_url !== sourceUrl || !sourceUrl) return;
    let cancelled = false;
    setPaging(true);
    setPageError(null);
    (async () => {
      while (!cancelled) {
        const current = useSearchSession.getState().selected;
        if (!current?.has_more || current.source_url !== sourceUrl) break;
        try {
          const page = await api.continueLyrics({
            query: useSearchSession.getState().query || current.title,
            script: current.script,
            offset: current.next_offset ?? current.verses.length,
            title: current.title,
            previous_tail: current.verses.slice(-2),
          });
          if (cancelled) return;
          const latest = useSearchSession.getState().selected;
          if (!latest || latest.source_url !== sourceUrl) return;
          if (!page.verses.length) {
            useSearchSession.getState().select({ ...latest, has_more: false });
            break;
          }
          const previousOffset = current.next_offset ?? current.verses.length;
          const verses = [...latest.verses, ...page.verses];
          const advanced = page.next_offset > previousOffset;
          useSearchSession.getState().select({
            ...latest,
            title: page.title || latest.title,
            verses,
            has_more: page.has_more && advanced && verses.length < 4000,
            next_offset: page.next_offset,
          });
          if (!advanced) break;
        } catch (err) {
          if (!cancelled) {
            setPageError(err instanceof Error ? err.message : "Could not load more verses");
          }
          break;
        }
      }
      if (!cancelled) setPaging(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [sourceUrl, retryToken]);

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

  const savedItem = saved ? items.find(
    (item) => item.fingerprint === version.fingerprint && item.source_url === version.source_url,
  ) : undefined;
  const fullySaved = Boolean(
    savedItem && savedItem.verses.length >= version.verses.length && !version.has_more,
  );
  const saveLabel = fullySaved
    ? "Saved on this device"
    : savedItem
      ? "Update saved copy"
      : version.has_more
        ? "Save loaded verses"
        : "Save";

  return (
    <FlatList
      style={styles.list}
      data={version.verses}
      keyExtractor={(_item, index) => String(index)}
      contentContainerStyle={styles.container}
      initialNumToRender={12}
      maxToRenderPerBatch={16}
      windowSize={7}
      extraData={{ xlit: displayXlit, meanings: actions.meanings, showMeaning: actions.showMeaning, sideBySide }}
      ListHeaderComponent={
    <View style={styles.header}>
      <ConsentSheet
        visible={sheetVisible}
        onContinue={() => {
          accept();
          setSheetVisible(false);
          void actions.loadMeaning(pendingLanguage.current);
        }}
        onNotNow={() => setSheetVisible(false)}
      />
      <Text style={styles.title}>{version.title}</Text>
      <Text style={styles.meta}>
        {scriptLabel(version.script)}
        {version.deity ? ` · ${version.deity}` : ""} · {version.source_domain}
        {` · ${version.verses.length} verse${version.verses.length === 1 ? "" : "s"}`}
        {version.has_more ? " loaded so far" : ""}
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

      <Text style={styles.section}>Meaning</Text>
      <ScriptChips
        scripts={MEANING_LANGUAGES.map((item) => item.code)}
        selected={actions.showMeaning ? actions.meaningLanguage : null}
        onSelect={(value) => {
          if (!value) return;
          pendingLanguage.current = value;
          void actions.showMeaningIn(value).then((result) => {
            if (result === "needs-consent") setSheetVisible(true);
          });
        }}
        includeAll={false}
        labelFor={meaningLanguageLabel}
      />
      <Text style={styles.meta}>Tap a language to show the meaning. Tap it again to hide.</Text>

      <View style={styles.row}>
        <Pressable style={styles.secondary} onPress={() => setSideBySide((value) => !value)}>
          <Text style={styles.secondaryLabel}>{sideBySide ? "Stacked" : "Side by side"}</Text>
        </Pressable>
      </View>
      {actions.meaningBusy ? <ActivityIndicator color={colors.saffron} /> : null}
      {actions.showMeaning ? <MeaningDisclaimer /> : null}
      {actions.error ? <Text style={styles.error}>{actions.error}</Text> : null}

      <View style={styles.actions}>
        <Pressable style={styles.button} onPress={() => save(version)} disabled={fullySaved}>
          <Text style={styles.buttonLabel}>{saveLabel}</Text>
        </Pressable>
        <Pressable style={styles.button} onPress={() => void actions.exportPdf()} disabled={actions.pdfBusy}>
          <Text style={styles.buttonLabel}>
            {actions.pdfBusy ? "Preparing PDF…" : version.has_more ? "Export loaded verses" : "Export PDF"}
          </Text>
        </Pressable>
      </View>
      <Text style={styles.section}>Text</Text>
      </View>
      }
      renderItem={({ item, index }) => {
        const xlitLine = displayXlit?.[index];
        const meaningLine = actions.showMeaning ? actions.meanings?.[index] : undefined;
        const meaningFont = fontForScript(meaningLanguageScript(actions.meaningLanguage));
        if (sideBySide && xlitLine) {
          return (
            <View style={styles.pair}>
              <Text style={[styles.verse, styles.pairCol, { fontFamily: fontForScript(version.script) }]}>{item}</Text>
              <Text style={[styles.verse, styles.pairCol, { fontFamily: fontForScript(actions.targetScript ?? "latin") }]}>{xlitLine}</Text>
              {meaningLine ? (
                <Text style={[styles.meaning, { fontFamily: meaningFont }]}>{meaningLine}</Text>
              ) : null}
            </View>
          );
        }
        return (
          <View style={styles.block}>
            <Text style={[styles.verse, { fontFamily: fontForScript(version.script) }]}>{item}</Text>
            {xlitLine ? (
              <Text style={[styles.xlit, { fontFamily: fontForScript(actions.targetScript ?? "latin") }]}>{xlitLine}</Text>
            ) : null}
            {meaningLine ? (
              <Text style={[styles.meaning, { fontFamily: meaningFont }]}>{meaningLine}</Text>
            ) : null}
          </View>
        );
      }}
      ListFooterComponent={
        <View style={styles.footer}>
          {paging ? <ActivityIndicator color={colors.saffron} /> : null}
          {paging ? <Text style={styles.meta}>Loading the rest of this sloka…</Text> : null}
          {pageError ? <Text style={styles.error}>{pageError}</Text> : null}
          {pageError ? (
            <Pressable onPress={() => setRetryToken((value) => value + 1)}>
              <Text style={styles.link}>Try loading the rest again</Text>
            </Pressable>
          ) : null}
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  list: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  header: {
    gap: 12,
  },
  footer: {
    gap: 8,
    marginTop: 12,
    marginBottom: 24,
  },
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
