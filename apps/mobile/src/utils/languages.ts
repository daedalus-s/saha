// Keep in sync with services/api/app/models.py MEANING_LANGUAGES.
export const MEANING_LANGUAGES = [
  { code: "en", label: "English", script: "latin" },
  { code: "hi", label: "Hindi", script: "devanagari" },
  { code: "ta", label: "Tamil", script: "tamil" },
  { code: "te", label: "Telugu", script: "telugu" },
  { code: "kn", label: "Kannada", script: "kannada" },
  { code: "ml", label: "Malayalam", script: "malayalam" },
  { code: "gu", label: "Gujarati", script: "gujarati" },
  { code: "bn", label: "Bengali", script: "bengali" },
] as const;

export type MeaningLanguageCode = (typeof MEANING_LANGUAGES)[number]["code"];

export function meaningLanguageLabel(code: string): string {
  return MEANING_LANGUAGES.find((item) => item.code === code)?.label ?? code;
}

export function meaningLanguageScript(code: string): string {
  return MEANING_LANGUAGES.find((item) => item.code === code)?.script ?? "latin";
}
