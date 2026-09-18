export type PdfInput = {
  title: string;
  sourceUrl: string;
  generatedAt: string;
  original: string[];
  originalScript: string;
  transliteration?: string[];
  transliterationScript?: string;
  meanings?: string[];
  aiGenerated?: boolean;
};

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function verseBlock(text: string): string {
  return `<p class="verse">${escapeHtml(text)}</p>`;
}

export function buildPdfHtml(input: PdfInput): string {
  const original = input.original.map(verseBlock).join("\n");
  const xlit =
    input.transliteration && input.transliteration.length
      ? `<h2>Transliteration (${escapeHtml(input.transliterationScript ?? "")})</h2>
         ${input.transliteration.map(verseBlock).join("\n")}`
      : "";
  const meaning =
    input.meanings && input.meanings.length
      ? `<h2>Meaning</h2>
         ${input.meanings.map((m) => `<p class="meaning">${escapeHtml(m)}</p>`).join("\n")}
         <p class="disclaimer">AI-generated meaning; verify with a scholar.</p>`
      : "";
  const sourceMeta = input.aiGenerated
    ? `<p class="meta">Source: AI-generated lyrics (Gemini); verify with a printed edition.<br/>
  Script: ${escapeHtml(input.originalScript)} · Generated ${escapeHtml(input.generatedAt)}</p>`
    : `<p class="meta">Source: <a href="${escapeHtml(input.sourceUrl)}">${escapeHtml(input.sourceUrl)}</a><br/>
  Script: ${escapeHtml(input.originalScript)} · Generated ${escapeHtml(input.generatedAt)}</p>`;

  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>${escapeHtml(input.title)}</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400&family=Noto+Sans+Tamil:wght@400&family=Noto+Sans+Telugu:wght@400&family=Noto+Sans+Kannada:wght@400&family=Noto+Sans+Malayalam:wght@400&family=Noto+Sans+Gujarati:wght@400&family=Noto+Sans+Bengali:wght@400&family=Noto+Serif:wght@400;700&display=swap"/>
  <style>
    body { font-family: "Noto Serif", Georgia, serif; color: #2B2118; padding: 32px; }
    h1 { font-size: 22px; margin-bottom: 4px; }
    h2 { font-size: 16px; margin-top: 28px; color: #6B2D3C; }
    .meta { color: #7A6A58; font-size: 12px; margin-bottom: 24px; }
    .verse { font-size: 16px; line-height: 1.7; margin: 0 0 8px;
      font-family: "Noto Sans Devanagari", "Noto Sans Tamil", "Noto Sans Telugu", "Noto Sans Kannada", "Noto Sans Malayalam", "Noto Sans Gujarati", "Noto Sans Bengali", "Noto Serif", serif; }
    .meaning { font-size: 14px; line-height: 1.5; margin: 0 0 10px; }
    .disclaimer { font-size: 11px; color: #7A6A58; margin-top: 16px; font-style: italic; }
    a { color: #C45C26; }
  </style>
</head>
<body>
  <h1>${escapeHtml(input.title)}</h1>
  ${sourceMeta}
  <h2>Original</h2>
  ${original}
  ${xlit}
  ${meaning}
</body>
</html>`;
}
