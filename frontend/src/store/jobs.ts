import { create } from "zustand";

export type JobState = "queued" | "running" | "done" | "failed" | "cancelled";

export interface JobEvent {
  type: "job";
  id: string;
  kind: string;
  title: string;
  state: JobState;
  progress: number;
  message: string;
  error: { code: string; message_vi: string; detail: string } | null;
  result: unknown;
}

interface JobsStore {
  jobs: Record<string, JobEvent>;
  upsert: (ev: JobEvent) => void;
}

export const useJobs = create<JobsStore>((set) => ({
  jobs: {},
  upsert: (ev) => set((s) => ({ jobs: { ...s.jobs, [ev.id]: ev } })),
}));

export const isActive = (j: JobEvent) => j.state === "queued" || j.state === "running";
