import { MEANING_LANGUAGES } from "./languages";

const FROZEN = [
  ["en", "English", "latin"],
  ["hi", "Hindi", "devanagari"],
  ["ta", "Tamil", "tamil"],
  ["te", "Telugu", "telugu"],
  ["kn", "Kannada", "kannada"],
  ["ml", "Malayalam", "malayalam"],
  ["gu", "Gujarati", "gujarati"],
  ["bn", "Bengali", "bengali"],
];

describe("meaning languages", () => {
  test("matches the API frozen list", () => {
    expect(MEANING_LANGUAGES.map((item) => [item.code, item.label, item.script])).toEqual(FROZEN);
  });
});
