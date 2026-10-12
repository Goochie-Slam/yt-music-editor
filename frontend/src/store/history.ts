import { applyPatches, enablePatches, produceWithPatches, type Draft, type Patch } from "immer";

enablePatches();

/** Undo/redo as immer patches (F5.2). Pure functions so they are easy to test. */
export interface Entry {
  patches: Patch[];
  inverse: Patch[];
  key?: string;
  at: number;
}

export interface History {
  past: Entry[];
  future: Entry[];
}

export const HISTORY_LIMIT = 100; // requirement: ≥ 50 steps
export const COALESCE_MS = 1000;
export const emptyHistory = (): History => ({ past: [], future: [] });

/**
 * Apply a change and record it. Changes with the same `key` within COALESCE_MS merge into one
 * undo step — dragging a slider is one step, not sixty.
 */
export function record<T>(
  state: T,
  hist: History,
  recipe: (draft: Draft<T>) => void,
  key?: string,
  now = Date.now(),
): { state: T; hist: History } {
  const [next, patches, inverse] = produceWithPatches(state, recipe);
  if (patches.length === 0) return { state, hist };
  const last = hist.past.at(-1);
  let past: Entry[];
  if (key !== undefined && last?.key === key && now - last.at < COALESCE_MS) {
    const merged = {
      patches: [...last.patches, ...patches],
      inverse: [...inverse, ...last.inverse],
      key,
      at: now,
    };
    past = [...hist.past.slice(0, -1), merged];
  } else {
    past = [...hist.past, { patches, inverse, key, at: now }].slice(-HISTORY_LIMIT);
  }
  return { state: next as T, hist: { past, future: [] } };
}

export function undo<T>(state: T, hist: History): { state: T; hist: History } {
  const entry = hist.past.at(-1);
  if (!entry) return { state, hist };
  return {
    state: applyPatches(state as object, entry.inverse) as T,
    hist: { past: hist.past.slice(0, -1), future: [entry, ...hist.future] },
  };
}

export function redo<T>(state: T, hist: History): { state: T; hist: History } {
  const [entry, ...rest] = hist.future;
  if (!entry) return { state, hist };
  return {
    state: applyPatches(state as object, entry.patches) as T,
    hist: { past: [...hist.past, { ...entry, key: undefined }], future: rest },
  };
}
