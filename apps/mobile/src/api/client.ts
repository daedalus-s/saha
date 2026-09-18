import Constants from "expo-constants";

import type {
  ExtractResponse,
  SearchResponse,
  TransliterateResponse,
  TranslateResponse,
} from "./types";

type Extra = {
  apiUrl?: string;
  appKey?: string;
};

const extra = (Constants.expoConfig?.extra ?? {}) as Extra;

function isLoopback(url: string): boolean {
  return /https?:\/\/(localhost|127\.0\.0\.1|10\.0\.2\.2)(:|\/|$)/i.test(url);
}

function resolveApiUrl(): string {
  const configured = (process.env.EXPO_PUBLIC_API_URL || extra.apiUrl || "").replace(/\/$/, "");
  if (__DEV__) {
    return configured || "http://127.0.0.1:8000";
  }
  if (!configured || isLoopback(configured)) {
    throw new Error("EXPO_PUBLIC_API_URL must be set to a public HTTPS origin in production builds.");
  }
  return configured;
}

export const API_URL = resolveApiUrl();

export const APP_KEY = process.env.EXPO_PUBLIC_APP_KEY || extra.appKey || (__DEV__ ? "dev-app-key" : "");

async function request<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-App-Key": APP_KEY,
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return data as T;
}

export const api = {
  health: async () => {
    const response = await fetch(`${API_URL}/health`);
    if (!response.ok) throw new Error(`Health check failed (${response.status})`);
    return response.json() as Promise<{ status: string }>;
  },

  search: (query: string) => request<SearchResponse>("/search", { query }),

  extract: (url: string, query?: string) => request<ExtractResponse>("/extract", { url, query }),

  transliterate: (verses: string[], source_script: string, target_script: string) =>
    request<TransliterateResponse>("/transliterate", {
      verses,
      source_script,
      target_script,
    }),

  translate: (verses: string[], source_script: string, title?: string) =>
    request<TranslateResponse>("/translate", {
      verses,
      source_script,
      target_language: "en",
      title,
    }),
};
