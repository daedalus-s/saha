export type SearchHit = {
  url: string;
  title: string;
  snippet: string;
  source_domain: string;
};

export type SearchResponse = {
  hits: SearchHit[];
  expanded_queries: string[];
  versions?: SlokaVersion[];
};

export type SlokaVersion = {
  title: string;
  script: string;
  verses: string[];
  source_url: string;
  source_domain: string;
  fingerprint: string;
  normalized: string;
  deity?: string | null;
  category?: string | null;
  also_on: string[];
  ai_generated?: boolean;
};

export type ExtractResponse = {
  version: SlokaVersion | null;
  error: string | null;
};

export type GroupedVersion = SlokaVersion & { alsoOn: string[] };

export type TranslatedVerse = {
  verse: string;
  meaning: string;
};

export type TransliterateResponse = {
  verses: string[];
  source_script: string;
  target_script: string;
};

export type TranslateResponse = {
  verses: TranslatedVerse[];
  target_language?: string;
  disclaimer: string;
};

export type SavedItem = {
  id: string;
  title: string;
  script: string;
  verses: string[];
  source_url: string;
  source_domain: string;
  fingerprint: string;
  savedAt: string;
  ai_generated?: boolean;
};
