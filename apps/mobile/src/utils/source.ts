export function isAiGenerated(version: {
  ai_generated?: boolean;
  source_url: string;
}): boolean {
  return Boolean(version.ai_generated) || version.source_url.startsWith("saha://ai/");
}
