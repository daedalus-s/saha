import type { GroupedVersion, SlokaVersion } from "../api/types";

export function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  if (!a) return b.length;
  if (!b) return a.length;
  const rows = a.length + 1;
  const cols = b.length + 1;
  const matrix: number[][] = Array.from({ length: rows }, () => Array(cols).fill(0));
  for (let i = 0; i < rows; i += 1) matrix[i][0] = i;
  for (let j = 0; j < cols; j += 1) matrix[0][j] = j;
  for (let i = 1; i < rows; i += 1) {
    for (let j = 1; j < cols; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost,
      );
    }
  }
  return matrix[a.length][b.length];
}

export function similarity(a: string, b: string): number {
  if (a === b) return 100;
  if (!a || !b) return 0;
  const distance = levenshtein(a, b);
  return Math.round((1 - distance / Math.max(a.length, b.length)) * 100);
}

export function groupVersions(
  versions: SlokaVersion[],
  threshold = 85,
): GroupedVersion[] {
  const groups: GroupedVersion[] = [];
  for (const version of versions) {
    const match = groups.find(
      (group) =>
        (group.fingerprint && group.fingerprint === version.fingerprint) ||
        similarity(group.normalized, version.normalized) >= threshold,
    );
    if (match) {
      if (
        version.source_url !== match.source_url &&
        !match.alsoOn.includes(version.source_url)
      ) {
        match.alsoOn.push(version.source_url);
      }
    } else {
      groups.push({ ...version, alsoOn: [...(version.also_on ?? [])] });
    }
  }
  return groups;
}
