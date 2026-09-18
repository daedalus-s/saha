import type { ScriptKey } from "./scripts";

const SCRIPT_FONTS: Record<string, string> = {
  devanagari: "NotoSansDevanagari_400Regular",
  tamil: "NotoSansTamil_400Regular",
  telugu: "NotoSansTelugu_400Regular",
  kannada: "NotoSansKannada_400Regular",
  malayalam: "NotoSansMalayalam_400Regular",
  gujarati: "NotoSansGujarati_400Regular",
  bengali: "NotoSansBengali_400Regular",
  iast: "NotoSerif_400Regular",
  itrans: "NotoSerif_400Regular",
  latin: "NotoSerif_400Regular",
};

export function fontForScript(script: ScriptKey): string {
  return SCRIPT_FONTS[script] ?? "NotoSerif_400Regular";
}
