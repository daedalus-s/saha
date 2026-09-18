import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

type ConsentState = {
  accepted: boolean;
  accept: () => void;
  withdraw: () => void;
};

export const useConsent = create<ConsentState>()(
  persist(
    (set) => ({
      accepted: false,
      accept: () => set({ accepted: true }),
      withdraw: () => set({ accepted: false }),
    }),
    {
      name: "saha-consent",
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
