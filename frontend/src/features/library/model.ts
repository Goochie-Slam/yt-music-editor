/** Library logic without React: statuses, applying job results, removing, adding to the mix. */
import type { Draft } from "immer";
import type { ExportEntry, IngestResult } from "../../api/client";
import type { LibraryItem, Project, SegmentSource } from "../../api/types.gen";
import type { JobEvent } from "../../store/jobs";

const ID_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

/** Same shape as the backend's new_id(): it ends up in file names, so letters and digits only. */
export function newId(length = 10): string {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(bytes, (b) => ID_ALPHABET[b % ID_ALPHABET.length]).join("");
}

export const INGEST_KINDS = new Set(["ingest", "download"]);

// --------------------------------------------------------------------------- input

/** One pasted line per entry: http(s) links go to yt-dlp, anything else is a file / folder path. */
export function splitInput(text: string): { urls: string[]; paths: string[] } {
  const urls: string[] = [];
  const paths: string[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim().replace(/^["']|["']$/g, "");
    if (!line) continue;
    if (/^https?:\/\//i.test(line)) urls.push(line);
    else paths.push(line);
  }
  return { urls: [...new Set(urls)], paths: [...new Set(paths)] };
}

export function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i > 0 ? name.slice(i + 1).toLowerCase() : "";
}

export function stemOf(name: string): string {
  const base = name.split(/[\\/]/).pop() ?? name;
  const i = base.lastIndexOf(".");
  return i > 0 ? base.slice(0, i) : base;
}

// --------------------------------------------------------------------------- lookups

export function byId(project: Project): Map<string, LibraryItem> {
  return new Map(project.library.map((i) => [i.id, i]));
}

/** The WAV an item plays and the range in it — segments play part of their parent's WAV. */
export function audioOf(
  item: LibraryItem,
  items: Map<string, LibraryItem>,
): { wav: string; start: number; end: number | null; duration: number } | null {
  if (item.source.kind === "segment") {
    const parent = items.get(item.source.parentId);
    if (!parent?.cacheWav) return null;
    const { start, end } = item.source;
    return { wav: parent.cacheWav, start, end, duration: end - start };
  }
  if (!item.cacheWav || item.duration == null) return null;
  return { wav: item.cacheWav, start: 0, end: null, duration: item.duration };
}

export function isReady(item: LibraryItem, items: Map<string, LibraryItem>): boolean {
  return audioOf(item, items) !== null;
}

/** F1.8: lossy and at or below the threshold. A FLAC can be small and still lossless. */
export function isLowBitrate(item: LibraryItem, threshold: number): boolean {
  return !item.srcLossless && item.srcBitrateKbps != null && item.srcBitrateKbps <= threshold;
}

/** Latest ingest / download job per library item of this project. */
export function latestJobs(jobs: Record<string, JobEvent>, projectId: string) {
  const out = new Map<string, JobEvent>();
  for (const j of Object.values(jobs)) {
    if (!INGEST_KINDS.has(j.kind) || j.meta?.projectId !== projectId) continue;
    const itemId = j.meta.itemId;
    if (!itemId) continue;
    const prev = out.get(itemId);
    if (!prev || j.createdAt >= prev.createdAt) out.set(itemId, j);
  }
  return out;
}

// --------------------------------------------------------------------------- status

export type Status =
  | { kind: "ready"; low: boolean }
  | { kind: "queued" }
  | { kind: "running"; progress: number; message: string }
  | { kind: "uploading"; progress: number }
  | { kind: "error"; message: string }
  | { kind: "needsDrop" } // dropped file whose bytes are gone (page reloaded): drop it again
  | { kind: "interrupted" } // app closed mid-import: retry
  | { kind: "waitingParent" };

export function statusOf(
  item: LibraryItem,
  ctx: {
    items: Map<string, LibraryItem>;
    job?: JobEvent;
    upload?: number;
    hasFile: boolean;
    lowKbps: number;
  },
): Status {
  if (item.source.kind === "segment") {
    const parent = ctx.items.get(item.source.parentId);
    return parent?.cacheWav
      ? { kind: "ready", low: isLowBitrate(item, ctx.lowKbps) }
      : { kind: "waitingParent" };
  }
  if (item.cacheWav) return { kind: "ready", low: isLowBitrate(item, ctx.lowKbps) };
  if (ctx.upload !== undefined) return { kind: "uploading", progress: ctx.upload };
  const job = ctx.job;
  if (job?.state === "queued") return { kind: "queued" };
  if (job?.state === "running")
    return { kind: "running", progress: job.progress, message: job.message };
  if (item.error) return { kind: "error", message: item.error };
  if (item.source.kind === "file" && item.source.uploaded && !ctx.hasFile)
    return { kind: "needsDrop" };
  return { kind: "interrupted" };
}

// --------------------------------------------------------------------------- job results

/**
 * Store finished job results on their items. Returns null when there is nothing to do, so it can
 * run after every job event and every undo without creating saves for nothing.
 */
export function reconcile(
  project: Project,
  jobs: Record<string, JobEvent>,
  cancelledText: string,
): ((d: Draft<Project>) => void) | null {
  const latest = latestJobs(jobs, project.id);
  const todo: { index: number; job: JobEvent }[] = [];
  project.library.forEach((item, index) => {
    const job = latest.get(item.id);
    if (!job || item.cacheWav || item.source.kind === "segment") return;
    if (job.state === "done" && job.result) todo.push({ index, job });
    else if (job.state === "failed" && item.error !== (job.error?.message_vi ?? null))
      todo.push({ index, job });
    else if (job.state === "cancelled" && item.error !== cancelledText) todo.push({ index, job });
  });
  if (!todo.length) return null;
  return (d) => {
    for (const { index, job } of todo) {
      const item = d.library[index];
      if (!item) continue;
      if (job.state === "done") {
        const r = job.result as IngestResult;
        item.cacheWav = r.cacheWav;
        item.duration = r.duration;
        item.srcBitrateKbps = r.srcBitrateKbps;
        item.srcFormat = r.srcFormat;
        item.srcLossless = r.srcLossless;
        item.error = null;
        if (r.title && !item.title.trim()) item.title = r.title;
      } else {
        item.error = job.state === "failed" ? (job.error?.message_vi ?? "") : cancelledText;
      }
    }
  };
}

// --------------------------------------------------------------------------- edits

/** Remove items, the segments cut from them, and their tracks in the mix (one undo step). */
export function removeItems(
  d: Draft<Project>,
  ids: Set<string>,
): { items: number; tracks: number } {
  const gone = new Set(ids);
  for (const item of d.library) {
    if (item.source.kind === "segment" && gone.has(item.source.parentId)) gone.add(item.id);
  }
  const before = d.library.length;
  d.library = d.library.filter((i) => !gone.has(i.id));
  const tracksBefore = d.mix.tracks.length;
  d.mix.tracks = d.mix.tracks.filter((t) => !gone.has(t.libId));
  const kept = new Set(d.mix.tracks.map((t) => t.id));
  d.mix.transitions = Object.fromEntries(
    Object.entries(d.mix.transitions).filter(([key]) => {
      const [a = "", b = ""] = key.split(">");
      return kept.has(a) && kept.has(b);
    }),
  );
  return { items: before - d.library.length, tracks: tracksBefore - d.mix.tracks.length };
}

/** Append to the end of the mix. Transitions are filled in by the Mix tab (missing = default). */
export function addToMix(d: Draft<Project>, items: LibraryItem[]): number {
  for (const item of items) {
    d.mix.tracks.push({
      id: newId(),
      libId: item.id,
      title: item.title,
      trimIn: 0,
      trimOut: null,
      gainDb: 0,
    });
  }
  return items.length;
}

/** Tracklist segments → library items that reference the parent's WAV (no copy, sample-exact). */
export function segmentItems(
  parent: LibraryItem,
  segments: { title: string; start: number; end: number }[],
): LibraryItem[] {
  return segments.map((s) => {
    const source: SegmentSource = {
      kind: "segment",
      parentId: parent.id,
      start: s.start,
      end: s.end,
    };
    return {
      id: newId(),
      title: s.title,
      source,
      cacheWav: null,
      duration: s.end - s.start,
      srcBitrateKbps: parent.srcBitrateKbps,
      srcFormat: parent.srcFormat,
      srcLossless: parent.srcLossless,
      error: null,
      loudness: null,
    };
  });
}

export function newItem(title: string, source: LibraryItem["source"]): LibraryItem {
  return {
    id: newId(),
    title,
    source,
    cacheWav: null,
    duration: null,
    srcBitrateKbps: null,
    srcFormat: "",
    srcLossless: false,
    error: null,
    loudness: null,
  };
}

/** Identity of a link: the site's own id, except for yt-dlp's generic extractor whose "id" is
 * just the file name (a/mix.mp3 vs b/mix.mp3). Mirrors the backend's url_key(). */
export function linkKey(s: { url: string; site: string; remoteId: string }): string[] {
  const site = s.site.toLowerCase();
  return site && site !== "generic" && s.remoteId ? [s.url, `${site}:${s.remoteId}`] : [s.url];
}

/** Already in the library? Same link (or same site id), or same file path. */
export function isDuplicate(project: Project, source: LibraryItem["source"]): boolean {
  return project.library.some((i) => {
    const s = i.source;
    if (source.kind === "url" && s.kind === "url") {
      const mine = new Set(linkKey(s));
      return linkKey(source).some((k) => mine.has(k));
    }
    if (source.kind === "file" && s.kind === "file" && !source.uploaded)
      return s.path === source.path;
    return false;
  });
}

/** Keep the first of items that share a key — a playlist can list one video twice. */
export function uniqueBy<T>(xs: T[], keys: (x: T) => string[]): T[] {
  const seen = new Set<string>();
  return xs.filter((x) => {
    const ks = keys(x);
    if (ks.some((k) => seen.has(k))) return false;
    for (const k of ks) seen.add(k);
    return true;
  });
}

// --------------------------------------------------------------------------- export

export function exportEntries(items: LibraryItem[], all: Map<string, LibraryItem>): ExportEntry[] {
  const out: ExportEntry[] = [];
  for (const item of items) {
    const a = audioOf(item, all);
    if (a)
      out.push({ title: item.title, wav: a.wav, start: a.start, end: a.end, duration: a.duration });
  }
  return out;
}

/** Preview only — the backend's export.render_names() decides the real name. */
export function previewName(pattern: string, index: number, total: number, title: string): string {
  const width = Math.max(2, String(total).length);
  const name = pattern
    .replaceAll("{index}", String(index).padStart(width, "0"))
    .replaceAll("{title}", title);
  return `${name.replace(/[<>:"/\\|?*]/g, "_")}.mp3`;
}

export const MP3_BYTES_PER_SECOND = 320_000 / 8;

// --------------------------------------------------------------------------- display

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

export function formatBytes(n: number): string {
  if (n < 1024 * 1024) return `${Math.max(1, Math.round(n / 1024))} KB`;
  if (n < 1024 ** 3) return `${Math.round(n / 1024 ** 2)} MB`;
  return `${(n / 1024 ** 3).toFixed(1)} GB`;
}

const SITES: Record<string, { label: string; color: string }> = {
  youtube: { label: "YouTube", color: "#f87171" },
  soundcloud: { label: "SoundCloud", color: "#fb923c" },
  mixcloud: { label: "Mixcloud", color: "#a78bfa" },
  bandcamp: { label: "Bandcamp", color: "#22d3ee" },
};

export function sourceLabel(
  item: LibraryItem,
  items: Map<string, LibraryItem>,
): { label: string; color: string; title: string } {
  const s = item.source;
  if (s.kind === "url") {
    const known = SITES[s.site];
    let host = s.site;
    try {
      host = new URL(s.url).hostname.replace(/^www\./, "");
    } catch {
      /* keep the site name */
    }
    return { label: known?.label ?? host, color: known?.color ?? "#8b93a5", title: s.url };
  }
  if (s.kind === "segment") {
    const parent = items.get(s.parentId);
    return { label: `✂ ${parent?.title ?? "?"}`, color: "#34d399", title: parent?.title ?? "" };
  }
  const name = s.path.split(/[\\/]/).pop() ?? s.path;
  return { label: name, color: "#8b93a5", title: s.path };
}
