import { produce, type Draft } from "immer";
import { create } from "zustand";
import { api, ApiError } from "../api/client";
import type { Project } from "../api/types.gen";
import { emptyHistory, record, redo, undo, type History } from "./history";

export type SaveState = "saved" | "dirty" | "saving" | "error";
export const AUTOSAVE_MS = 1000;

interface ProjectStore {
  project: Project | null;
  path: string | null;
  hist: History;
  save: SaveState;
  saveError: string;
  load: (project: Project, path: string) => void;
  close: () => void;
  /** Every edit to the project goes through here (undo + autosave). */
  change: (recipe: (draft: Draft<Project>) => void, key?: string) => void;
  /**
   * Results that arrive from background jobs (decoded file, duration…). Saved, but not an undo
   * step: undoing "import" must not be needed twice, and undo must never drop a finished decode.
   */
  patch: (recipe: (draft: Draft<Project>) => void) => void;
  undo: () => void;
  redo: () => void;
  saveNow: () => Promise<void>;
}

let timer: ReturnType<typeof setTimeout> | undefined;
let inFlight: Promise<void> | null = null;
let editedDuringSave = false;

export const useProject = create<ProjectStore>((set, get) => {
  const touched = () => {
    if (get().save === "saving") editedDuringSave = true;
    else set({ save: "dirty" });
    clearTimeout(timer);
    timer = setTimeout(() => void get().saveNow(), AUTOSAVE_MS);
  };

  return {
    project: null,
    path: null,
    hist: emptyHistory(),
    save: "saved",
    saveError: "",

    load: (project, path) =>
      set({ project, path, hist: emptyHistory(), save: "saved", saveError: "" }),

    close: () => {
      clearTimeout(timer);
      set({ project: null, path: null, hist: emptyHistory(), save: "saved" });
    },

    change: (recipe, key) => {
      const { project, hist } = get();
      if (!project) return;
      const r = record(project, hist, recipe, key);
      if (r.state === project) return;
      set({ project: r.state, hist: r.hist });
      touched();
    },

    patch: (recipe) => {
      const { project } = get();
      if (!project) return;
      const next = produce(project, recipe);
      if (next === project) return;
      set({ project: next });
      touched();
    },

    undo: () => {
      const { project, hist } = get();
      if (!project || hist.past.length === 0) return;
      const r = undo(project, hist);
      set({ project: r.state, hist: r.hist });
      touched();
    },

    redo: () => {
      const { project, hist } = get();
      if (!project || hist.future.length === 0) return;
      const r = redo(project, hist);
      set({ project: r.state, hist: r.hist });
      touched();
    },

    saveNow: async () => {
      clearTimeout(timer);
      if (inFlight) {
        editedDuringSave = true;
        return inFlight;
      }
      const project = get().project;
      if (!project) return;
      set({ save: "saving" });
      editedDuringSave = false;
      inFlight = (async () => {
        try {
          const saved = await api.saveProject(project);
          const current = get().project;
          // Only the timestamp comes back; never overwrite edits made while saving.
          if (current?.id === saved.id)
            set({ project: { ...current, updatedAt: saved.updatedAt } });
          set({ save: editedDuringSave ? "dirty" : "saved", saveError: "" });
        } catch (e) {
          set({ save: "error", saveError: e instanceof ApiError ? e.messageVi : String(e) });
        } finally {
          inFlight = null;
        }
      })();
      await inFlight;
      if (editedDuringSave) {
        editedDuringSave = false;
        timer = setTimeout(() => void get().saveNow(), AUTOSAVE_MS);
      }
    },
  };
});
