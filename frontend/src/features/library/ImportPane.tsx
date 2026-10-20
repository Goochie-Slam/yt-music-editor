import { useEffect, useRef, useState } from "react";
import { t } from "../../i18n";
import { addFiles, addPaths, addUrls, loadSystem } from "./actions";
import { filesFromFolderInput } from "./drop";
import { LibraryTable } from "./LibraryTable";
import { splitInput } from "./model";
import { useLibrary } from "./runtime";

export function ImportPane() {
  const [text, setText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);
  const system = useLibrary((s) => s.system);

  useEffect(() => {
    // not in React's typings; lets the browser's picker select a whole folder
    folderInput.current?.setAttribute("webkitdirectory", "");
  }, []);

  const accept = system?.supportedExtensions.map((e) => `.${e}`).join(",");

  const fetchInput = () => {
    const { urls, paths } = splitInput(text);
    if (!urls.length && !paths.length) return;
    setText("");
    void addUrls(urls);
    void addPaths(paths);
  };

  const onFolder = async (list: FileList | null) => {
    if (!list?.length) return;
    if (!useLibrary.getState().system) await loadSystem();
    addFiles(
      filesFromFolderInput(list, new Set(useLibrary.getState().system?.supportedExtensions ?? [])),
    );
  };

  return (
    <div className="lib-import">
      <div className="drop">
        <div>
          <b>{t("library.drop.title")}</b>{" "}
          <span className="muted">· {t("library.drop.formats")}</span>
        </div>
        <div className="muted">{t("library.drop.or")}</div>
        <div className="row">
          <textarea
            aria-label={t("library.drop.or")}
            placeholder={t("library.drop.placeholder")}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                fetchInput();
              }
            }}
          />
          <button
            className="btn primary"
            title={t("library.drop.fetchHint")}
            disabled={!text.trim()}
            onClick={fetchInput}
          >
            {t("library.drop.fetch")}
          </button>
        </div>
        <div className="row">
          <button className="btn sm" onClick={() => fileInput.current?.click()}>
            {t("library.drop.pickFiles")}
          </button>
          <button className="btn sm" onClick={() => folderInput.current?.click()}>
            {t("library.drop.pickFolder")}
          </button>
          <input
            ref={fileInput}
            type="file"
            multiple
            hidden
            accept={accept}
            onChange={(e) => {
              addFiles(Array.from(e.target.files ?? []));
              e.target.value = "";
            }}
          />
          <input
            ref={folderInput}
            type="file"
            hidden
            onChange={(e) => {
              void onFolder(e.target.files);
              e.target.value = "";
            }}
          />
        </div>
        <div className="muted small">{t("library.drop.tip")}</div>
      </div>
      <LibraryTable />
    </div>
  );
}
