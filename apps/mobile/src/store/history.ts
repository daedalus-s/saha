import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

const MAX = 12;

type HistoryState = {
  recent: string[];
  add: (query: string) => void;
  clear: () => void;
};

export const useHistory = create<HistoryState>()(
  persist(
    (set, get) => ({
      recent: [],
      add: (query) => {
        const trimmed = query.trim();
        if (!trimmed) return;
        const next = [trimmed, ...get().recent.filter((item) => item !== trimmed)].slice(0, MAX);
        set({ recent: next });
      },
      clear: () => set({ recent: [] }),
    }),
    {
      name: "saha-history",
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
