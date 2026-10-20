/**
 * Library state that is NOT saved in project.json: what is selected, uploads in flight, links
 * being looked up, playlists waiting for the picker, and the File objects of dropped files (the
 * only way to retry them — a browser never reveals a dropped file's path).
 */
import { create } from "zustand";
import type { LinkEntry, SystemInfo } from "../../api/client";

export interface PendingPlaylist {
  id: string;
  url: string;
  title: string;
  entries: LinkEntry[];
}

interface LibraryRuntime {
  selected: Set<string>;
  uploads: Record<string, number>; // itemId → 0..1
  resolving: { id: string; url: string }[];
  playlists: PendingPlaylist[];
  system: SystemInfo | null;
  exportJobId: string | null;
  setSelected: (ids: Iterable<string>) => void;
  toggle: (id: string, on: boolean) => void;
  setUpload: (itemId: string, fraction: number | null) => void;
  setSystem: (s: SystemInfo) => void;
  setExportJob: (id: string | null) => void;
}

export const useLibrary = create<LibraryRuntime>((set) => ({
  selected: new Set(),
  uploads: {},
  resolving: [],
  playlists: [],
  system: null,
  exportJobId: null,
  setSelected: (ids) => set({ selected: new Set(ids) }),
  toggle: (id, on) =>
    set((s) => {
      const next = new Set(s.selected);
      if (on) next.add(id);
      else next.delete(id);
      return { selected: next };
    }),
  setUpload: (itemId, fraction) =>
    set((s) => {
      const rest = Object.fromEntries(Object.entries(s.uploads).filter(([k]) => k !== itemId));
      return { uploads: fraction === null ? rest : { ...rest, [itemId]: fraction } };
    }),
  setSystem: (system) => set({ system }),
  setExportJob: (exportJobId) => set({ exportJobId }),
}));

/** Dropped files kept for retry. Memory is not an issue: a File is a handle, not its bytes. */
export const droppedFiles = new Map<string, File>();
export const uploadAborts = new Map<string, () => void>();
