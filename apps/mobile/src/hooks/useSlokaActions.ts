import { useState } from "react";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";

import { api } from "../api/client";
import type { SlokaVersion } from "../api/types";
import { useConsent } from "../store/consent";
import { buildPdfHtml } from "../utils/pdf";
import { scriptLabel } from "../utils/scripts";

export function useSlokaActions(sloka: SlokaVersion | null) {
  const accepted = useConsent((state) => state.accepted);
  const [targetScript, setTargetScript] = useState<string | null>(null);
  const [xlit, setXlit] = useState<string[] | null>(null);
  const [xlitBusy, setXlitBusy] = useState(false);
  const [showMeaning, setShowMeaning] = useState(false);
  const [meanings, setMeanings] = useState<string[] | null>(null);
  const [meaningBusy, setMeaningBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pdfBusy, setPdfBusy] = useState(false);

  async function pickScript(script: string | null) {
    if (!sloka) return;
    setTargetScript(script);
    setError(null);
    if (!script || script === sloka.script) {
      setXlit(null);
      return;
    }
    setXlitBusy(true);
    try {
      const result = await api.transliterate(sloka.verses, sloka.script, script);
      setXlit(result.verses);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transliteration failed");
      setXlit(null);
    } finally {
      setXlitBusy(false);
    }
  }

  async function loadMeaning() {
    if (!sloka || meanings) {
      setShowMeaning(true);
      return;
    }
    setMeaningBusy(true);
    setError(null);
    try {
      const result = await api.translate(sloka.verses, sloka.script, sloka.title);
      setMeanings(result.verses.map((item) => item.meaning));
      setShowMeaning(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Translation failed");
      setShowMeaning(false);
    } finally {
      setMeaningBusy(false);
    }
  }

  async function toggleMeaning(): Promise<"needs-consent" | "ok"> {
    if (showMeaning) {
      setShowMeaning(false);
      return "ok";
    }
    if (!accepted) return "needs-consent";
    await loadMeaning();
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
        aiGenerated: Boolean(sloka.ai_generated) || sloka.source_url.startsWith("saha://ai/"),
      });
      const { uri } = await Print.printToFileAsync({ html });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, { UTI: "com.adobe.pdf", mimeType: "application/pdf" });
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
    meanings,
    meaningBusy,
    error,
    pdfBusy,
    pickScript,
    toggleMeaning,
    loadMeaning,
    exportPdf,
  };
}
