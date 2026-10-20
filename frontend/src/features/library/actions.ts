/** Library side effects: start imports, uploads, link lookups, exports; keep items in sync. */
import {
  api,
  ApiError,
  uploadFile,
  type ExportEntry,
  type Resolved,
  type LinkEntry,
} from "../../api/client";
import type { LibraryItem } from "../../api/types.gen";
import { t } from "../../i18n";
import { useJobs, type JobEvent } from "../../store/jobs";
import { useProject } from "../../store/project";
import { toast } from "../../store/toast";
import {
  addToMix,
  byId,
  isDuplicate,
  isReady,
  latestJobs,
  linkKey,
  newId,
  newItem,
  reconcile,
  removeItems,
  stemOf,
  uniqueBy,
} from "./model";
import { droppedFiles, uploadAborts, useLibrary } from "./runtime";

const UPLOAD_CONCURRENCY = 3;
const FINISHED = new Set(["done", "failed", "cancelled"]);

const errText = (e: unknown) => (e instanceof ApiError ? e.messageVi : String(e));

/**
 * Register a job we just started, so the UI shows it (and reconcile treats it as the item's
 * latest) before its first WebSocket event. Never overwrites an event that already arrived.
 */
function trackJob(id: string, kind: string, title: string, meta: Record<string, string>) {
  const jobs = useJobs.getState();
  if (jobs.jobs[id]) return;
  jobs.upsert({
    type: "job",
    id,
    kind,
    title,
    state: "queued",
    progress: 0,
    message: "",
    error: null,
    result: null,
    meta,
    createdAt: Date.now() / 1000,
  });
}

export function waitForJob(id: string): Promise<JobEvent> {
  return new Promise((resolve) => {
    let unsub = () => {};
    const check = (jobs: Record<string, JobEvent>) => {
      const j = jobs[id];
      if (!j || !FINISHED.has(j.state)) return false;
      unsub();
      resolve(j);
      return true;
    };
    if (check(useJobs.getState().jobs)) return;
    unsub = useJobs.subscribe((s) => void check(s.jobs));
  });
}

function projectId(): string | null {
  return useProject.getState().project?.id ?? null;
}

function setItemError(itemId: string, message: string | null) {
  useProject.getState().patch((d) => {
    const item = d.library.find((i) => i.id === itemId);
    if (item) item.error = message;
  });
}

// --------------------------------------------------------------------------- uploads

const queue: { pid: string; itemId: string; file: File }[] = [];
let active = 0;

function queueUpload(pid: string, itemId: string, file: File) {
  useLibrary.getState().setUpload(itemId, 0);
  queue.push({ pid, itemId, file });
  pump();
}

function pump() {
  while (active < UPLOAD_CONCURRENCY) {
    const next = queue.shift();
    if (!next) return;
    const { pid, itemId, file } = next;
    active++;
    const lib = useLibrary.getState();
    const { promise, abort } = uploadFile(pid, itemId, file, (f) => lib.setUpload(itemId, f));
    uploadAborts.set(itemId, abort);
    promise
      .then(({ jobId }) => {
        trackJob(jobId, "ingest", file.name, { projectId: pid, itemId });
        setItemError(itemId, null);
      })
      .catch((e: unknown) => setItemError(itemId, errText(e)))
      .finally(() => {
        active--;
        uploadAborts.delete(itemId);
        useLibrary.getState().setUpload(itemId, null);
        pump();
      });
  }
}

// --------------------------------------------------------------------------- ingest

async function startIngest(pid: string, item: LibraryItem) {
  const s = item.source;
  if (s.kind === "segment") return;
  if (s.kind === "file" && s.uploaded) {
    const file = droppedFiles.get(item.id);
    if (file) queueUpload(pid, item.id, file);
    else toast(t("library.toast.dropAgain", { title: item.title }), "warn");
    return;
  }
  try {
    const { jobId } = await api.ingest(pid, item.id, item.title, s);
    trackJob(jobId, s.kind === "url" ? "download" : "ingest", item.title, {
      projectId: pid,
      itemId: item.id,
    });
    if (item.error) setItemError(item.id, null); // only now: the row goes ✕ → queued, no flicker
  } catch (e) {
    setItemError(item.id, errText(e));
  }
}

/** Add to the library (one undo step), select the new items, start importing them. */
function addItems(items: LibraryItem[]) {
  const pid = projectId();
  if (!pid || !items.length) return;
  useProject.getState().change((d) => void d.library.push(...items));
  const lib = useLibrary.getState();
  lib.setSelected([...lib.selected, ...items.map((i) => i.id)]);
  for (const item of items) void startIngest(pid, item);
}

function reportDuplicates(n: number) {
  if (n) toast(t("library.toast.duplicates", { n }), "info");
}

export function addFiles(files: File[]) {
  const project = useProject.getState().project;
  if (!project || !files.length) return;
  const unique = uniqueBy(files, (f) => [`${f.name}|${f.size}|${f.lastModified}`]);
  reportDuplicates(files.length - unique.length);
  const items = unique.map((f) => {
    const item = newItem(stemOf(f.name), { kind: "file", path: f.name, uploaded: true });
    droppedFiles.set(item.id, f);
    return item;
  });
  addItems(items);
}

export async function addPaths(paths: string[]) {
  if (!paths.length) return;
  try {
    const { files, missing } = await api.expandPaths(paths);
    if (missing.length)
      toast(t("library.toast.missing", { n: missing.length, first: missing[0] ?? "" }), "warn");
    const project = useProject.getState().project;
    if (!project) return;
    const fresh = files.filter(
      (f) => !isDuplicate(project, { kind: "file", path: f.path, uploaded: false }),
    );
    reportDuplicates(files.length - fresh.length);
    addItems(fresh.map((f) => newItem(f.name, { kind: "file", path: f.path, uploaded: false })));
  } catch (e) {
    toast(errText(e), "err");
  }
}

export function addLinkEntries(entries: LinkEntry[]) {
  const project = useProject.getState().project;
  if (!project) return;
  const usable = uniqueBy(
    entries.filter((e) => e.available),
    (e) => linkKey(e),
  );
  const fresh = usable.filter(
    (e) => !isDuplicate(project, { kind: "url", url: e.url, site: e.site, remoteId: e.remoteId }),
  );
  reportDuplicates(entries.filter((e) => e.available).length - fresh.length);
  addItems(
    fresh.map((e) =>
      newItem(e.title, { kind: "url", url: e.url, site: e.site, remoteId: e.remoteId }),
    ),
  );
}

export async function addUrls(urls: string[]) {
  for (const url of urls) {
    const project = useProject.getState().project;
    if (!project) return;
    if (isDuplicate(project, { kind: "url", url, site: "", remoteId: "" })) {
      reportDuplicates(1);
      continue;
    }
    const id = newId();
    useLibrary.setState((s) => ({ resolving: [...s.resolving, { id, url }] }));
    void (async () => {
      try {
        const { jobId } = await api.resolveLink(url);
        trackJob(jobId, "resolve", url, { url });
        const job = await waitForJob(jobId);
        if (job.state === "done") {
          const r = job.result as Resolved;
          if (r.kind === "single") addLinkEntries(r.entries);
          else
            useLibrary.setState((s) => ({
              playlists: [...s.playlists, { id, url, title: r.title, entries: r.entries }],
            }));
        } else if (job.state === "failed") {
          toast(
            t("library.toast.linkFailed", { url, message: job.error?.message_vi ?? "" }),
            "err",
          );
        }
      } catch (e) {
        toast(errText(e), "err");
      } finally {
        useLibrary.setState((s) => ({ resolving: s.resolving.filter((r) => r.id !== id) }));
      }
    })();
  }
}

export function closePlaylist(id: string) {
  useLibrary.setState((s) => ({ playlists: s.playlists.filter((p) => p.id !== id) }));
}

export function retry(item: LibraryItem) {
  const pid = projectId();
  if (pid) void startIngest(pid, item);
}

export function cancelItem(itemId: string) {
  const qi = queue.findIndex((q) => q.itemId === itemId);
  if (qi >= 0) {
    queue.splice(qi, 1);
    useLibrary.getState().setUpload(itemId, null);
    setItemError(itemId, t("library.status.cancelled"));
    return;
  }
  const abort = uploadAborts.get(itemId);
  if (abort) return abort();
  const pid = projectId();
  const job = pid ? latestJobs(useJobs.getState().jobs, pid).get(itemId) : undefined;
  if (job && !FINISHED.has(job.state)) void api.cancelJob(job.id);
}

// --------------------------------------------------------------------------- selection actions

export function removeSelected() {
  const { selected, setSelected } = useLibrary.getState();
  if (!selected.size) return;
  let counts = { items: 0, tracks: 0 };
  useProject.getState().change((d) => void (counts = removeItems(d, selected)));
  for (const id of selected) cancelItem(id); // no point downloading what was just removed
  setSelected([]);
  toast(
    counts.tracks
      ? t("library.toast.removedWithMix", { n: counts.items, m: counts.tracks })
      : t("library.toast.removed", { n: counts.items }),
  );
}

export function selectedReady(): LibraryItem[] {
  const project = useProject.getState().project;
  if (!project) return [];
  const { selected } = useLibrary.getState();
  const items = byId(project);
  return project.library.filter((i) => selected.has(i.id) && isReady(i, items));
}

export function addSelectedToMix() {
  const ready = selectedReady();
  if (!ready.length) return;
  useProject.getState().change((d) => void addToMix(d, ready));
  toast(t("library.toast.addedToMix", { n: ready.length }), "ok");
}

export async function startExport(entries: ExportEntry[]) {
  const project = useProject.getState().project;
  const lib = useLibrary.getState();
  if (!project || !entries.length || exportBusy(lib.exportRequesting, lib.exportJobId)) return;
  const { folder, pattern } = project.libraryExport;
  lib.setExportRequesting(true); // a double-click must not start two exports
  try {
    const { jobId } = await api.exportMp3(project.id, folder, pattern, entries);
    trackJob(jobId, "export", t("library.export.jobTitle", { n: entries.length }), {
      projectId: project.id,
    });
    useLibrary.getState().setExportJob(jobId);
  } catch (e) {
    toast(errText(e), "err");
  } finally {
    useLibrary.getState().setExportRequesting(false);
  }
}

export function exportBusy(requesting: boolean, jobId: string | null): boolean {
  const job = jobId ? useJobs.getState().jobs[jobId] : undefined;
  return requesting || (!!job && !FINISHED.has(job.state));
}

// --------------------------------------------------------------------------- sync

/** Apply finished job results to the project whenever jobs or the project change. */
export function startLibrarySync(): () => void {
  const run = () => {
    const project = useProject.getState().project;
    if (!project) return;
    const recipe = reconcile(project, useJobs.getState().jobs, t("library.status.cancelled"));
    if (recipe) useProject.getState().patch(recipe);
  };
  const offJobs = useJobs.subscribe(run);
  const offProject = useProject.subscribe((s, prev) => {
    if (s.project !== prev.project) run();
  });
  run();
  return () => {
    offJobs();
    offProject();
  };
}

export async function loadSystem() {
  try {
    useLibrary.getState().setSystem(await api.system());
  } catch {
    /* Settings shows the problem; the library falls back to defaults */
  }
}
