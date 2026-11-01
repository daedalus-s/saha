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

const SCRIPT_RANGES: ReadonlyArray<readonly [ScriptKey, number, number]> = [
  ["devanagari", 0x0900, 0x097f],
  ["bengali", 0x0980, 0x09ff],
  ["gujarati", 0x0a80, 0x0aff],
  ["tamil", 0x0b80, 0x0bff],
  ["telugu", 0x0c00, 0x0c7f],
  ["kannada", 0x0c80, 0x0cff],
  ["malayalam", 0x0d00, 0x0d7f],
];

/** Dominant script of a typed sloka name. Latin when no Indic letters are present. */
export function detectQueryScript(text: string): string {
  const counts = new Map<string, number>();
  for (const ch of text) {
    const code = ch.codePointAt(0) ?? 0;
    for (const [name, start, end] of SCRIPT_RANGES) {
      if (code >= start && code <= end) {
        counts.set(name, (counts.get(name) ?? 0) + 1);
        break;
      }
    }
  }
  let best = "";
  let bestCount = 0;
  for (const [name, count] of counts) {
    if (count > bestCount) {
      best = name;
      bestCount = count;
    }
  }
  return best || "latin";
}
