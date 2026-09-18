import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { SavedItem, SlokaVersion } from "../api/types";

type SavedState = {
  items: SavedItem[];
  save: (version: SlokaVersion) => void;
  remove: (id: string) => void;
};

function idFor(version: SlokaVersion): string {
  return `${version.fingerprint}:${version.source_url}`;
}

export const useSaved = create<SavedState>()(
  persist(
    (set, get) => ({
      items: [],
      save: (version) => {
        const id = idFor(version);
        if (get().items.some((item) => item.id === id)) return;
        const item: SavedItem = {
          id,
          title: version.title,
          script: version.script,
          verses: version.verses,
          source_url: version.source_url,
          source_domain: version.source_domain,
          fingerprint: version.fingerprint,
          savedAt: new Date().toISOString(),
        };
        set({ items: [item, ...get().items] });
      },
      remove: (id) => set({ items: get().items.filter((item) => item.id !== id) }),
    }),
    {
      name: "saha-saved",
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
