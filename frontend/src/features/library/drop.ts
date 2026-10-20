/** Collect files from a drop, walking dropped folders (F1.1). */
import { extOf } from "./model";

type Entry = FileSystemEntry;

function readAll(dir: FileSystemDirectoryEntry): Promise<Entry[]> {
  const reader = dir.createReader();
  const out: Entry[] = [];
  return new Promise((resolve, reject) => {
    // readEntries returns at most ~100 entries per call: keep reading until it returns none
    const next = () =>
      reader.readEntries((batch) => {
        if (!batch.length) return resolve(out);
        out.push(...batch);
        next();
      }, reject);
    next();
  });
}

function fileOf(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file(resolve, reject));
}

async function walk(entry: Entry, exts: Set<string>, out: File[], topLevel: boolean) {
  if (entry.isFile) {
    const file = await fileOf(entry as FileSystemFileEntry);
    // a file dropped by itself is always tried; inside a folder, only known audio / video types
    if (topLevel || exts.has(extOf(file.name))) out.push(file);
  } else if (entry.isDirectory) {
    const children = await readAll(entry as FileSystemDirectoryEntry);
    children.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    for (const child of children) await walk(child, exts, out, false);
  }
}

/**
 * Must run synchronously inside the drop handler: the DataTransfer is emptied as soon as the
 * event returns, so take the entries first and walk them afterwards.
 */
export function takeDrop(dt: DataTransfer): { entries: Entry[]; files: File[] } {
  const entries = Array.from(dt.items)
    .map((i) => (i.kind === "file" ? i.webkitGetAsEntry() : null))
    .filter((e): e is Entry => e !== null);
  return { entries, files: entries.length ? [] : Array.from(dt.files) };
}

export async function collectFiles(
  dropped: { entries: Entry[]; files: File[] },
  exts: Set<string>,
): Promise<File[]> {
  const out = [...dropped.files];
  for (const e of dropped.entries) await walk(e, exts, out, true);
  return out;
}

/** <input type="file" webkitdirectory> gives a flat list of every file in the folder. */
export function filesFromFolderInput(files: FileList, exts: Set<string>): File[] {
  return Array.from(files)
    .filter((f) => exts.has(extOf(f.name)))
    .sort((a, b) =>
      a.webkitRelativePath.localeCompare(b.webkitRelativePath, undefined, { numeric: true }),
    );
}
