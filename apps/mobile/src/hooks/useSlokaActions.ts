import { useEffect, useRef, useState } from "react";
import * as FileSystem from "expo-file-system/legacy";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";

import { api } from "../api/client";
import type { SlokaVersion } from "../api/types";
import { useConsent } from "../store/consent";
import { meaningLanguageLabel } from "../utils/languages";
import { buildPdfHtml, pdfFileName } from "../utils/pdf";
import { scriptLabel } from "../utils/scripts";

const XLIT_BATCH = 80;
const MEANING_BATCH = 40;

export function useSlokaActions(sloka: SlokaVersion | null) {
  const accepted = useConsent((state) => state.accepted);
  const [targetScript, setTargetScript] = useState<string | null>(null);
  const [xlit, setXlit] = useState<string[] | null>(null);
  const [xlitBusy, setXlitBusy] = useState(false);
  const [showMeaning, setShowMeaning] = useState(false);
  const [meaningLanguage, setMeaningLanguage] = useState("en");
  const [meanings, setMeanings] = useState<string[] | null>(null);
  const [meaningBusy, setMeaningBusy] = useState(false);
  const meaningCache = useRef<Record<string, string[]>>({});
  const meaningFlight = useRef<string | null>(null);
  const xlitBelongsTo = useRef<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfBusy, setPdfBusy] = useState(false);

  function pickScript(script: string | null) {
    if (!sloka) return;
    setTargetScript(script);
    setError(null);
    if (!script || script === sloka.script) {
      setXlit(null);
    }
  }

  useEffect(() => {
    if (!sloka || !targetScript || targetScript === sloka.script) return;
    const scriptChanged = xlitBelongsTo.current !== targetScript;
    const have = scriptChanged ? 0 : (xlit?.length ?? 0);
    if (!scriptChanged && have >= sloka.verses.length) return;
    let cancelled = false;
    const slice = sloka.verses.slice(have);
    const sourceScript = sloka.script;
    (async () => {
      setXlitBusy(true);
      try {
        const lines: string[] = [];
        for (let index = 0; index < slice.length; index += XLIT_BATCH) {
          const batch = slice.slice(index, index + XLIT_BATCH);
          const result = await api.transliterate(batch, sourceScript, targetScript);
          lines.push(...result.verses);
        }
        if (cancelled) return;
        xlitBelongsTo.current = targetScript;
        setXlit((prev) => (scriptChanged || !prev ? lines : [...prev, ...lines]));
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Transliteration failed");
        }
      } finally {
        if (!cancelled) setXlitBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [targetScript, sloka?.script, sloka?.source_url, sloka?.verses.length]);

  useEffect(() => {
    meaningCache.current = {};
    xlitBelongsTo.current = null;
    setXlit(null);
    setTargetScript(null);
    setMeanings(null);
    setShowMeaning(false);
    setMeaningLanguage("en");
  }, [sloka?.fingerprint, sloka?.source_url]);

  async function loadMeaning(language = "en") {
    if (!sloka) return;
    const have = meaningCache.current[language] ?? [];
    const flight = `${sloka.source_url}:${language}:${have.length}`;
    if (meaningFlight.current === flight) return;
    if (have.length >= sloka.verses.length) {
      setMeaningLanguage(language);
      setMeanings(have.slice(0, sloka.verses.length));
      setShowMeaning(true);
      return;
    }
    meaningFlight.current = flight;
    setMeaningBusy(true);
    setError(null);
    try {
      const lines = [...have];
      const sourceScript = sloka.script;
      const title = sloka.title;
      for (let index = have.length; index < sloka.verses.length; index += MEANING_BATCH) {
        const batch = sloka.verses.slice(index, index + MEANING_BATCH);
        const result = await api.translate(batch, sourceScript, title, language);
        lines.push(...result.verses.map((item) => item.meaning));
      }
      meaningCache.current = { ...meaningCache.current, [language]: lines };
      setMeaningLanguage(language);
      setMeanings(lines);
      setShowMeaning(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Translation failed");
      if (!have.length) setShowMeaning(false);
    } finally {
      if (meaningFlight.current === flight) meaningFlight.current = null;
      setMeaningBusy(false);
    }
  }

  useEffect(() => {
    if (!showMeaning || !sloka) return;
    const have = meaningCache.current[meaningLanguage]?.length ?? 0;
    if (have >= sloka.verses.length || meaningFlight.current) return;
    void loadMeaning(meaningLanguage);
  }, [showMeaning, meaningLanguage, sloka?.verses.length, sloka?.source_url, meaningBusy]);

  async function showMeaningIn(language: string): Promise<"needs-consent" | "ok"> {
    if (showMeaning && meaningLanguage === language) {
      setShowMeaning(false);
      return "ok";
    }
    if (!accepted) return "needs-consent";
    await loadMeaning(language);
    return "ok";
  }

  async function exportPdf() {
    if (!sloka) return;
    setPdfBusy(true);
    setError(null);
    try {
      const html = buildPdfHtml({
        title: sloka.title,
        sourceUrl: sloka.source_url,
        generatedAt: new Date().toISOString().slice(0, 10),
        original: sloka.verses,
        originalScript: scriptLabel(sloka.script),
        transliteration: xlit ?? undefined,
        transliterationScript: targetScript ? scriptLabel(targetScript) : undefined,
        meanings: showMeaning ? meanings ?? undefined : undefined,
        meaningLanguage: showMeaning ? meaningLanguageLabel(meaningLanguage) : undefined,
        incomplete: Boolean(sloka.has_more),
        aiGenerated: Boolean(sloka.ai_generated) || sloka.source_url.startsWith("saha://ai/"),
      });
      const { base64 } = await Print.printToFileAsync({ html, base64: true });
      if (!base64) {
        throw new Error("PDF export produced an empty file.");
      }
      const directory = FileSystem.cacheDirectory;
      if (!directory) {
        throw new Error("No cache directory available for PDF export.");
      }
      const dest = `${directory}${pdfFileName(sloka.title)}`;
      await FileSystem.writeAsStringAsync(dest, base64, {
        encoding: FileSystem.EncodingType.Base64,
      });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(dest, {
          UTI: "com.adobe.pdf",
          mimeType: "application/pdf",
          dialogTitle: sloka.title,
        });
      } else {
        await Print.printAsync({ uri: dest });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF export failed");
    } finally {
      setPdfBusy(false);
    }
  }

  return {
    targetScript,
    xlit,
    xlitBusy,
    showMeaning,
    meaningLanguage,
    meanings,
    meaningBusy,
    error,
    pdfBusy,
    pickScript,
    showMeaningIn,
    loadMeaning,
    exportPdf,
  };
}
