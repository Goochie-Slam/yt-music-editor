import { useEffect, useState, type DragEvent } from "react";
import { isTyping } from "../../components/keys";
import { t } from "../../i18n";
import { useProject } from "../../store/project";
import { addFiles, loadSystem, removeSelected } from "./actions";
import { collectFiles, takeDrop } from "./drop";
import { ExportPanel } from "./ExportPanel";
import { ImportPane } from "./ImportPane";
import { PlaylistModal } from "./PlaylistModal";
import { useLibrary } from "./runtime";
import { SplitPane } from "./SplitPane";

/** ① Thư viện — docs/UI-UX.md §4 ①, F1.1–F1.11 */
export function LibraryTab() {
  const [mode, setMode] = useState<"import" | "split">("import");
  const [dragging, setDragging] = useState(false);
  const system = useLibrary((s) => s.system);

  useEffect(() => {
    if (!useLibrary.getState().system) void loadSystem();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e) || mode !== "import") return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a") {
        e.preventDefault();
        const ids = useProject.getState().project?.library.map((i) => i.id) ?? [];
        useLibrary.getState().setSelected(ids);
      } else if (e.key === "Delete") {
        removeSelected();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode]);

  const onDrop = async (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = takeDrop(e.dataTransfer);
    if (!useLibrary.getState().system) await loadSystem();
    const exts = new Set(useLibrary.getState().system?.supportedExtensions ?? []);
    const files = await collectFiles(dropped, exts);
    if (files.length) {
      setMode("import");
      addFiles(files);
    }
  };

  const ytdlp = system?.ytdlp;
  return (
    <div
      className={`lib ${dragging ? "dragging" : ""}`}
      onDragOver={(e) => {
        if (!e.dataTransfer.types.includes("Files")) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDrop={(e) => void onDrop(e)}
    >
      <div className="lib-main">
        <div className="row lib-head">
          <div className="seg" role="tablist">
            <button className={mode === "import" ? "on" : ""} onClick={() => setMode("import")}>
              {t("library.modeImport")}
            </button>
            <button className={mode === "split" ? "on" : ""} onClick={() => setMode("split")}>
              {t("library.modeSplit")}
            </button>
          </div>
          {ytdlp && (
            <span
              className={`muted small ${ytdlp.version ? "" : "warn"}`}
              style={{ marginLeft: "auto" }}
            >
              {ytdlp.version
                ? t("library.ytdlpVersion", { version: ytdlp.version })
                : t("library.ytdlpMissing")}
            </span>
          )}
        </div>
        {mode === "import" ? <ImportPane /> : <SplitPane />}
      </div>
      <ExportPanel />
      <PlaylistModal />
      {dragging && (
        <div className="drop-overlay" onDragLeave={() => setDragging(false)}>
          {t("library.drop.overlay")}
        </div>
      )}
    </div>
  );
}
