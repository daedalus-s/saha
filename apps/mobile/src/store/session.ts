import { create } from "zustand";

import { api } from "../api/client";
import type { ExtractResponse, SearchHit, SlokaVersion } from "../api/types";

export type HitStatus =
  | { state: "pending" }
  | { state: "loading" }
  | { state: "ready"; version: SlokaVersion }
  | { state: "error"; message: string };

const EXTRACT_CONCURRENCY = 3;

type SessionState = {
  query: string;
  hits: SearchHit[];
  byUrl: Record<string, HitStatus>;
  selected: SlokaVersion | null;
  start: (query: string, hits: SearchHit[], versions?: SlokaVersion[]) => void;
  markLoading: (url: string) => void;
  applyExtract: (url: string, result: ExtractResponse) => void;
  markError: (url: string, message: string) => void;
  select: (version: SlokaVersion) => void;
  readyVersions: () => SlokaVersion[];
  extractAll: (query: string, urls: string[]) => Promise<void>;
};

export const useSearchSession = create<SessionState>((set, get) => ({
  query: "",
  hits: [],
  byUrl: {},
  selected: null,
  start: (query, hits, versions = []) => {
    const resolvedHits =
      hits.length > 0
        ? hits
        : versions.map((version) => ({
            url: version.source_url,
            title: version.title,
            snippet: "",
            source_domain: version.source_domain,
          }));
    const byUrl: Record<string, HitStatus> = {};
    for (const hit of resolvedHits) byUrl[hit.url] = { state: "pending" };
    for (const version of versions) {
      byUrl[version.source_url] = { state: "ready", version };
    }
    set({ query, hits: resolvedHits, byUrl, selected: null });
  },
  markLoading: (url) =>
    set((state) => ({ byUrl: { ...state.byUrl, [url]: { state: "loading" } } })),
  applyExtract: (url, result) =>
    set((state) => {
      if (result.version) {
        return { byUrl: { ...state.byUrl, [url]: { state: "ready", version: result.version } } };
      }
      return {
        byUrl: {
          ...state.byUrl,
          [url]: { state: "error", message: result.error || "No verses found" },
        },
      };
    }),
  markError: (url, message) =>
    set((state) => ({ byUrl: { ...state.byUrl, [url]: { state: "error", message } } })),
  select: (version) => set({ selected: version }),
  readyVersions: () =>
    Object.values(get().byUrl)
      .filter((status): status is { state: "ready"; version: SlokaVersion } => status.state === "ready")
      .map((status) => status.version),
  extractAll: async (query, urls) => {
    let index = 0;
    async function worker() {
      while (index < urls.length) {
        const current = index;
        index += 1;
        const url = urls[current];
        get().markLoading(url);
        try {
          const result = await api.extract(url, query);
          get().applyExtract(url, result);
        } catch (error) {
          get().markError(url, error instanceof Error ? error.message : "Extract failed");
        }
      }
    }
    if (!urls.length) return;
    await Promise.all(
      Array.from({ length: Math.min(EXTRACT_CONCURRENCY, urls.length) }, () => worker()),
    );
  },
}));
