import { create } from "zustand";

export type ToastKind = "info" | "ok" | "warn" | "err";

export interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

interface ToastStore {
  toasts: Toast[];
  push: (text: string, kind?: ToastKind) => void;
  dismiss: (id: number) => void;
}

let next = 1;
export const TOAST_MS = 4500;

export const useToasts = create<ToastStore>((set, get) => ({
  toasts: [],
  push: (text, kind = "info") => {
    const id = next++;
    set({ toasts: [...get().toasts.slice(-3), { id, kind, text }] });
    setTimeout(() => get().dismiss(id), kind === "err" ? TOAST_MS * 2 : TOAST_MS);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

export const toast = (text: string, kind?: ToastKind) => useToasts.getState().push(text, kind);
