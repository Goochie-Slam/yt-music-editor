import { produce } from "immer";
import type { LibraryItem, Project } from "../../api/types.gen";
import type { JobEvent } from "../../store/jobs";
import {
  addToMix,
  byId,
  exportEntries,
  formatDuration,
  isDuplicate,
  isLowBitrate,
  newId,
  newItem,
  previewName,
  reconcile,
  removeItems,
  segmentItems,
  splitInput,
  statusOf,
} from "./model";

function project(library: LibraryItem[] = []): Project {
  return {
    id: "p1",
    library,
    libraryExport: { folder: "", pattern: "{index} - {title}" },
    mix: {
      targetLufs: -14,
      autoTrimSilence: true,
      fadeInStart: 2,
      fadeOutEnd: 5,
      tracks: [],
      transitions: {},
    },
  } as unknown as Project;
}

function ready(id: string, extra: Partial<LibraryItem> = {}): LibraryItem {
  return {
    ...newItem(id, { kind: "file", path: `D:\\Nhạc\\${id}.flac`, uploaded: false }),
    id,
    cacheWav: `cache/audio/${id}.wav`,
    duration: 200,
    srcBitrateKbps: 900,
    srcFormat: "flac",
    srcLossless: true,
    ...extra,
  };
}

function job(
  id: string,
  itemId: string,
  state: JobEvent["state"],
  createdAt: number,
  extra: Partial<JobEvent> = {},
): JobEvent {
  return {
    type: "job",
    id,
    kind: "ingest",
    title: "",
    state,
    progress: 0.5,
    message: "Đang giải mã… 50%",
    error: null,
    result: null,
    meta: { projectId: "p1", itemId },
    createdAt,
    ...extra,
  };
}

const RESULT = {
  itemId: "a",
  cacheWav: "cache/audio/k.wav",
  duration: 182.5,
  srcBitrateKbps: 160,
  srcFormat: "webm/opus",
  srcLossless: false,
  title: "Từ YouTube",
};

describe("splitInput", () => {
  it("separates links from paths, strips quotes, drops blanks and duplicates", () => {
    const r = splitInput(
      'https://youtu.be/x\n  \n"D:\\Nhạc\\Album"\nhttps://youtu.be/x\nHTTP://soundcloud.com/a\r\n/home/me/a.mp3',
    );
    expect(r.urls).toEqual(["https://youtu.be/x", "HTTP://soundcloud.com/a"]);
    expect(r.paths).toEqual(["D:\\Nhạc\\Album", "/home/me/a.mp3"]);
  });
});

describe("status", () => {
  const items = new Map<string, LibraryItem>();
  const base = { items, hasFile: false, lowKbps: 160 };

  it("covers the import lifecycle", () => {
    const pending = newItem("x", {
      kind: "url",
      url: "https://youtu.be/x",
      site: "youtube",
      remoteId: "x",
    });
    expect(statusOf(pending, base).kind).toBe("interrupted");
    expect(statusOf(pending, { ...base, upload: 0.3 })).toEqual({
      kind: "uploading",
      progress: 0.3,
    });
    expect(statusOf(pending, { ...base, job: job("j", "x", "queued", 1) }).kind).toBe("queued");
    expect(statusOf(pending, { ...base, job: job("j", "x", "running", 1) })).toEqual({
      kind: "running",
      progress: 0.5,
      message: "Đang giải mã… 50%",
    });
    expect(statusOf({ ...pending, error: "Video riêng tư." }, base)).toEqual({
      kind: "error",
      message: "Video riêng tư.",
    });
    expect(statusOf(ready("r"), base)).toEqual({ kind: "ready", low: false });
  });

  it("asks to drop a dropped file again once its bytes are gone", () => {
    const dropped = newItem("x", { kind: "file", path: "x.flac", uploaded: true });
    expect(statusOf(dropped, base).kind).toBe("needsDrop");
    expect(statusOf(dropped, { ...base, hasFile: true }).kind).toBe("interrupted");
  });

  it("segments follow their parent", () => {
    const parent = newItem("mix", { kind: "file", path: "D:\\mix.mkv", uploaded: false });
    const [seg] = segmentItems(parent, [{ title: "A", start: 0, end: 60 }]);
    const m = new Map([[parent.id, parent]]);
    expect(statusOf(seg!, { ...base, items: m }).kind).toBe("waitingParent");
    m.set(parent.id, { ...parent, cacheWav: "cache/audio/p.wav", duration: 600 });
    expect(statusOf(seg!, { ...base, items: m }).kind).toBe("ready");
  });
});

describe("low bitrate (F1.8)", () => {
  it("warns for lossy sources at or below the threshold only", () => {
    expect(isLowBitrate(ready("a", { srcBitrateKbps: 128, srcLossless: false }), 160)).toBe(true);
    expect(isLowBitrate(ready("a", { srcBitrateKbps: 160, srcLossless: false }), 160)).toBe(true);
    expect(isLowBitrate(ready("a", { srcBitrateKbps: 256, srcLossless: false }), 160)).toBe(false);
    expect(isLowBitrate(ready("a", { srcBitrateKbps: 118, srcLossless: true }), 160)).toBe(false); // small FLAC
    expect(isLowBitrate(ready("a", { srcBitrateKbps: null, srcLossless: false }), 160)).toBe(false);
  });
});

describe("reconcile", () => {
  it("stores a finished job's result once, then has nothing to do", () => {
    const p = project([
      newItem("", { kind: "url", url: "https://youtu.be/x", site: "youtube", remoteId: "x" }),
    ]);
    const id = p.library[0]!.id;
    const jobs = { j1: job("j1", id, "done", 1, { result: { ...RESULT, itemId: id } }) };
    const recipe = reconcile(p, jobs, "Đã hủy");
    expect(recipe).not.toBeNull();
    const next = produce(p, recipe!);
    expect(next.library[0]).toMatchObject({
      cacheWav: "cache/audio/k.wav",
      duration: 182.5,
      srcFormat: "webm/opus",
      srcLossless: false,
      title: "Từ YouTube", // the item had no title yet
      error: null,
    });
    expect(reconcile(next, jobs, "Đã hủy")).toBeNull();
  });

  it("keeps a title the user already has", () => {
    const p = project([
      { ...newItem("Tên của tôi", { kind: "file", path: "/a.mp3", uploaded: false }), id: "a" },
    ]);
    const next = produce(
      p,
      reconcile(p, { j: job("j", "a", "done", 1, { result: RESULT }) }, "x")!,
    );
    expect(next.library[0]!.title).toBe("Tên của tôi");
  });

  it("uses only the latest job of an item: a retry wins over the old failure", () => {
    const p = project([
      { ...newItem("a", { kind: "file", path: "/a.mp3", uploaded: false }), id: "a" },
    ]);
    const failed = job("old", "a", "failed", 1, {
      error: { code: "file_not_found", message_vi: "Không tìm thấy file", detail: "" },
    });
    expect(produce(p, reconcile(p, { old: failed }, "x")!).library[0]!.error).toBe(
      "Không tìm thấy file",
    );
    // after "Thử lại" the error is cleared and a new job is queued: the old failure must not come back
    expect(reconcile(p, { old: failed, new: job("new", "a", "queued", 2) }, "x")).toBeNull();
  });

  it("ignores other projects and items that were removed", () => {
    const p = project([]);
    const other = job("j", "a", "done", 1, {
      result: RESULT,
      meta: { projectId: "p2", itemId: "a" },
    });
    expect(
      reconcile(p, { j: other, k: job("k", "gone", "done", 1, { result: RESULT }) }, "x"),
    ).toBeNull();
  });

  it("marks cancelled imports so they can be retried", () => {
    const p = project([
      { ...newItem("a", { kind: "file", path: "/a.mp3", uploaded: false }), id: "a" },
    ]);
    const next = produce(p, reconcile(p, { j: job("j", "a", "cancelled", 1) }, "Đã hủy")!);
    expect(next.library[0]!.error).toBe("Đã hủy");
  });
});

describe("edits", () => {
  it("removing a parent removes its segments and their mix tracks and transitions", () => {
    const parent = ready("mix", { duration: 3600 });
    const segs = segmentItems(parent, [
      { title: "A", start: 0, end: 100 },
      { title: "B", start: 100, end: 300 },
    ]);
    const other = ready("other");
    let p = project([parent, ...segs, other]);
    p = produce(p, (d) => void addToMix(d, [segs[0]!, other, segs[1]!]));
    const [t1, t2, t3] = p.mix.tracks;
    p = produce(p, (d) => {
      d.mix.transitions[`${t1!.id}>${t2!.id}`] = {} as never;
      d.mix.transitions[`${t2!.id}>${t3!.id}`] = {} as never;
    });
    let counts = { items: 0, tracks: 0 };
    p = produce(p, (d) => void (counts = removeItems(d, new Set(["mix"]))));
    expect(counts).toEqual({ items: 3, tracks: 2 });
    expect(p.library.map((i) => i.id)).toEqual(["other"]);
    expect(p.mix.tracks.map((t) => t.libId)).toEqual(["other"]);
    expect(p.mix.transitions).toEqual({});
  });

  it("segments reference the parent WAV exactly and export from it", () => {
    const parent = ready("mix", {
      duration: 7200,
      srcBitrateKbps: 128,
      srcLossless: false,
      srcFormat: "m4a/aac",
    });
    const segs = segmentItems(parent, [{ title: "Bài 2", start: 252.5, end: 570 }]);
    expect(segs[0]).toMatchObject({
      source: { kind: "segment", parentId: "mix", start: 252.5, end: 570 },
      duration: 317.5,
      cacheWav: null,
      srcBitrateKbps: 128,
    });
    const all = byId(project([parent, ...segs]));
    expect(exportEntries([parent, ...segs], all)).toEqual([
      { title: "mix", wav: "cache/audio/mix.wav", start: 0, end: null, duration: 7200 },
      { title: "Bài 2", wav: "cache/audio/mix.wav", start: 252.5, end: 570, duration: 317.5 },
    ]);
  });

  it("detects duplicates by link, site id or path", () => {
    const p = project([
      newItem("a", { kind: "url", url: "https://youtu.be/abc", site: "youtube", remoteId: "abc" }),
      newItem("b", { kind: "file", path: "D:\\a.mp3", uploaded: false }),
    ]);
    expect(
      isDuplicate(p, { kind: "url", url: "https://youtu.be/abc", site: "", remoteId: "" }),
    ).toBe(true);
    expect(
      isDuplicate(p, {
        kind: "url",
        url: "https://www.youtube.com/watch?v=abc",
        site: "youtube",
        remoteId: "abc",
      }),
    ).toBe(true);
    expect(isDuplicate(p, { kind: "file", path: "D:\\a.mp3", uploaded: false })).toBe(true);
    expect(isDuplicate(p, { kind: "file", path: "a.mp3", uploaded: true })).toBe(false); // can't tell
  });
});

describe("display", () => {
  it("formats durations", () => {
    expect(formatDuration(0)).toBe("0:00");
    expect(formatDuration(222.4)).toBe("3:42");
    expect(formatDuration(2 * 3600 + 3 * 60 + 40)).toBe("2:03:40");
    expect(formatDuration(null)).toBe("—");
  });

  it("previews file names like the backend", () => {
    expect(previewName("{index} - {title}", 1, 12, "Mưa")).toBe("01 - Mưa.mp3");
    expect(previewName("{index}", 1, 120, "x")).toBe("001.mp3");
    expect(previewName("{title}", 1, 1, "AC/DC")).toBe("AC_DC.mp3");
  });

  it("makes ids safe for file names", () => {
    expect(newId()).toMatch(/^[A-Za-z0-9]{10}$/);
  });
});
