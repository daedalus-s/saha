// Keep in sync with services/api/app/models.py SUPPORTED_SCRIPTS / SCRIPT_LABELS.
export const SCRIPTS = [
  "devanagari",
  "tamil",
  "telugu",
  "kannada",
  "malayalam",
  "gujarati",
  "bengali",
  "iast",
  "itrans",
] as const;

export type ScriptKey = (typeof SCRIPTS)[number] | "latin" | string;

export const SCRIPT_LABELS: Record<string, string> = {
  devanagari: "Devanagari",
  tamil: "Tamil",
  telugu: "Telugu",
  kannada: "Kannada",
  malayalam: "Malayalam",
  gujarati: "Gujarati",
  bengali: "Bengali",
  iast: "Roman (IAST)",
  itrans: "Roman (ITRANS)",
  latin: "Roman",
};

export function scriptLabel(script: string): string {
  return SCRIPT_LABELS[script] ?? script;
}
