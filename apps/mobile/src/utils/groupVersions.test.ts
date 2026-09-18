import { levenshtein, similarity, groupVersions } from "./groupVersions";
import type { SlokaVersion } from "../api/types";

function version(partial: Partial<SlokaVersion> & { verses: string[]; fingerprint: string; normalized: string; source_url: string }): SlokaVersion {
  return {
    title: "Test",
    script: "devanagari",
    source_domain: "example.org",
    also_on: [],
    ...partial,
  };
}

describe("groupVersions", () => {
  test("levenshtein identical", () => {
    expect(levenshtein("rama", "rama")).toBe(0);
  });

  test("similarity of close strings", () => {
    expect(similarity("omnamah", "omnamah")).toBe(100);
    expect(similarity("omnamah", "omnamaha")).toBeGreaterThan(80);
  });

  test("collapses matching fingerprints", () => {
    const a = version({
      verses: ["a"],
      fingerprint: "abc",
      normalized: "omnamahsivaya",
      source_url: "https://a.example",
    });
    const b = version({
      verses: ["a"],
      fingerprint: "abc",
      normalized: "omnamahsivaya",
      source_url: "https://b.example",
    });
    const grouped = groupVersions([a, b]);
    expect(grouped).toHaveLength(1);
    expect(grouped[0].alsoOn).toContain("https://b.example");
  });

  test("keeps different slokas apart", () => {
    const a = version({
      verses: ["a"],
      fingerprint: "aaa",
      normalized: "gayatrimantra",
      source_url: "https://a.example",
    });
    const b = version({
      verses: ["b"],
      fingerprint: "bbb",
      normalized: "hanumanchalisa",
      source_url: "https://b.example",
    });
    expect(groupVersions([a, b])).toHaveLength(2);
  });
});
