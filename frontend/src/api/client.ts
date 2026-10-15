import { t } from "../i18n";
import type { Project, ProjectSummary } from "./types.gen";

/** Mirrors the backend error payload {code, message_vi, detail} (docs/CODING-GUIDE.md §6.1). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly messageVi: string,
    readonly detail = "",
  ) {
    super(messageVi);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network", t("errors.network"));
  }
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const e = (data ?? {}) as Partial<{ code: string; message_vi: string; detail: string }>;
    throw new ApiError(res.status, e.code ?? "internal", e.message_vi ?? res.statusText, e.detail);
  }
  return data as T;
}

export interface SystemInfo {
  appVersion: string;
  python: string;
  os: string;
  dataDir: string;
  defaultProjectsDir: string;
  ffmpeg: { path: string | null; version?: string; nvenc?: boolean; x264?: boolean };
  ffprobe: { path: string | null };
  ytdlp: { path: string | null; version?: string };
}

export interface Opened {
  project: Project;
  path: string;
}

export const api = {
  system: () => request<SystemInfo>("GET", "/api/system"),
  selftest: () => request<{ jobId: string }>("POST", "/api/system/selftest"),
  cancelJob: (id: string) => request<unknown>("POST", `/api/jobs/${id}/cancel`),
  recent: () => request<ProjectSummary[]>("GET", "/api/projects"),
  createProject: (name: string, parentDir: string) =>
    request<Opened>("POST", "/api/projects", { name, parentDir }),
  openProject: (path: string) => request<Opened>("POST", "/api/projects/open", { path }),
  saveProject: (p: Project) => request<Project>("PUT", `/api/projects/${p.id}`, p),
};
