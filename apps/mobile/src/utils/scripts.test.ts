import { SCRIPTS, SCRIPT_LABELS } from "./scripts";

// Frozen list shared with services/api/app/models.py SUPPORTED_SCRIPTS.
const FROZEN_SCRIPTS = [
  "devanagari",
  "tamil",
  "telugu",
  "kannada",
  "malayalam",
  "gujarati",
  "bengali",
  "iast",
  "itrans",
  "latin",
];

describe("script lists", () => {
  test("picker scripts plus latin match the API frozen list", () => {
    expect([...SCRIPTS, "latin"].sort()).toEqual([...FROZEN_SCRIPTS].sort());
  });

  test("labels cover every frozen script", () => {
    expect(Object.keys(SCRIPT_LABELS).sort()).toEqual([...FROZEN_SCRIPTS].sort());
  });
});
