import { create } from "zustand";

export type Tab = "library" | "mix" | "video" | "export";
export const TABS: Tab[] = ["library", "mix", "video", "export"];

interface UiStore {
  tab: Tab;
  connected: boolean;
  settingsOpen: boolean;
  setTab: (tab: Tab) => void;
  setConnected: (v: boolean) => void;
  setSettingsOpen: (v: boolean) => void;
}

export const useUi = create<UiStore>((set) => ({
  tab: "library",
  connected: true,
  settingsOpen: false,
  setTab: (tab) => set({ tab }),
  setConnected: (connected) => set({ connected }),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
}));
