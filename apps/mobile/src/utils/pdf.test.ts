import { buildPdfHtml, pdfFileName } from "./pdf";

describe("buildPdfHtml", () => {
  test("includes title, verses, meaning disclaimer, and escapes HTML", () => {
    const html = buildPdfHtml({
      title: "Gayatri <Mantra>",
      sourceUrl: "https://example.org/g",
      generatedAt: "2026-09-17",
      original: ["ॐ भूर्भुवः स्वः"],
      originalScript: "devanagari",
      transliteration: ["oṃ bhūr bhuvaḥ svaḥ"],
      transliterationScript: "iast",
      meanings: ["We meditate on the divine light of Savitr."],
      meaningLanguage: "English",
    });
    expect(html).toContain("Gayatri &lt;Mantra&gt;");
    expect(html).toContain("ॐ भूर्भुवः स्वः");
    expect(html).toContain("oṃ bhūr bhuvaḥ svaḥ");
    expect(html).toContain("AI-generated meaning");
    expect(html).toContain("Meaning (English)");
    expect(html).not.toContain("verses loaded so far");
    expect(html).toContain("https://example.org/g");
    expect(html).not.toContain("Gayatri <Mantra>");
  });

  test("labels Gemini lyrics instead of a web source", () => {
    const html = buildPdfHtml({
      title: "Hanuman Chalisa",
      sourceUrl: "saha://ai/gemini/devanagari/hanuman-chalisa",
      generatedAt: "2026-09-17",
      original: ["श्रीगुरु चरन सरोज रज"],
      originalScript: "Devanagari",
      aiGenerated: true,
    });
    expect(html).toContain("AI-generated lyrics (Gemini)");
    expect(html).not.toContain("saha://");
  });
});

describe("partial pdf", () => {
  test("says the file is only the loaded verses", () => {
    const html = buildPdfHtml({
      title: "Ramayana",
      sourceUrl: "saha://ai/gemini/devanagari/ramayana",
      generatedAt: "2026-10-31",
      original: ["line"],
      originalScript: "Devanagari",
      aiGenerated: true,
      incomplete: true,
    });
    expect(html).toContain("verses loaded so far");
  });
});

describe("pdfFileName", () => {
  test("slugifies a title", () => {
    expect(pdfFileName("Hanuman Chalisa")).toBe("hanuman-chalisa.pdf");
  });
});
