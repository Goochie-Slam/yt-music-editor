import { t } from "../i18n";
import type { FileSource, Project, ProjectSummary, UrlSource } from "./types.gen";

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
  jsRuntime: { deno: string | null; node: string | null };
  supportedExtensions: string[];
  lowBitrateKbps: number;
}

export interface JobStarted {
  jobId: string;
}

/** One entry of a resolved link (backend audio/ytdlp.py). */
export interface LinkEntry {
  url: string;
  title: string;
  duration: number | null;
  site: string;
  remoteId: string;
  available: boolean;
}

export interface Resolved {
  kind: "single" | "playlist";
  title: string;
  entries: LinkEntry[];
}

/** What an ingest / download job returns. */
export interface IngestResult {
  itemId: string;
  cacheWav: string;
  duration: number;
  srcBitrateKbps: number | null;
  srcFormat: string;
  srcLossless: boolean;
  title: string | null;
}

export type TracklistLineError = "bad_format" | "bad_seconds" | "not_increasing" | "past_end";

export interface TracklistParsed {
  segments: { index: number; title: string; start: number; end: number }[];
  errors: { lineNo: number; text: string; error: TracklistLineError }[];
}

export interface ExportEntry {
  title: string;
  wav: string;
  start?: number;
  end?: number | null;
  duration: number;
}

export interface ExportResult {
  folder: string;
  files: string[];
  failed: { title: string; message: string; detail: string }[];
}

/**
 * Stream a dropped file to the backend. XHR, not fetch: fetch cannot report upload progress.
 * Resolves with the ingest job the backend starts once the bytes are in.
 */
export function uploadFile(
  projectId: string,
  itemId: string,
  file: File,
  onProgress: (fraction: number) => void,
): { promise: Promise<JobStarted>; abort: () => void } {
  const xhr = new XMLHttpRequest();
  const url = `/api/projects/${projectId}/library/${itemId}/upload?name=${encodeURIComponent(file.name)}`;
  const promise = new Promise<JobStarted>((resolve, reject) => {
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      let data: Partial<JobStarted & { code: string; message_vi: string; detail: string }> = {};
      try {
        data = JSON.parse(xhr.responseText) as typeof data;
      } catch {
        /* not JSON */
      }
      if (xhr.status >= 200 && xhr.status < 300 && data.jobId) resolve({ jobId: data.jobId });
      else
        reject(
          new ApiError(
            xhr.status,
            data.code ?? "internal",
            data.message_vi ?? xhr.statusText,
            data.detail,
          ),
        );
    };
    xhr.onerror = () => reject(new ApiError(0, "network", t("errors.network")));
    xhr.onabort = () => reject(new ApiError(0, "aborted", t("library.status.cancelled")));
  });
  xhr.open("PUT", url);
  xhr.send(file);
  return { promise, abort: () => xhr.abort() };
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

  expandPaths: (paths: string[]) =>
    request<{ files: { path: string; name: string }[]; missing: string[] }>(
      "POST",
      "/api/library/expand",
      { paths },
    ),
  resolveLink: (url: string) => request<JobStarted>("POST", "/api/library/resolve", { url }),
  ingest: (projectId: string, itemId: string, title: string, source: FileSource | UrlSource) =>
    request<JobStarted>("POST", `/api/projects/${projectId}/library/ingest`, {
      itemId,
      title,
      source,
    }),
  parseTracklist: (text: string, duration: number) =>
    request<TracklistParsed>("POST", "/api/tracklist/parse", { text, duration }),
  exportMp3: (projectId: string, folder: string, pattern: string, entries: ExportEntry[]) =>
    request<JobStarted>("POST", `/api/projects/${projectId}/library/export`, {
      folder,
      pattern,
      entries,
    }),
  updateYtdlp: () => request<JobStarted>("POST", "/api/system/ytdlp/update"),
  openFolder: (path: string) => request<undefined>("POST", "/api/system/open-folder", { path }),
};
