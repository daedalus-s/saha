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
    });
    expect(html).toContain("Gayatri &lt;Mantra&gt;");
    expect(html).toContain("ॐ भूर्भुवः स्वः");
    expect(html).toContain("oṃ bhūr bhuvaḥ svaḥ");
    expect(html).toContain("AI-generated meaning");
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

describe("pdfFileName", () => {
  test("slugifies a title", () => {
    expect(pdfFileName("Hanuman Chalisa")).toBe("hanuman-chalisa.pdf");
  });
});
