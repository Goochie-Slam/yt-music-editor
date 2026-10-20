import { api, type ExportResult } from "../../api/client";
import { t } from "../../i18n";
import { useJobs } from "../../store/jobs";
import { useProject } from "../../store/project";
import { toast } from "../../store/toast";
import { addSelectedToMix, startExport } from "./actions";
import {
  byId,
  exportEntries,
  formatBytes,
  isLowBitrate,
  isReady,
  MP3_BYTES_PER_SECOND,
  previewName,
} from "./model";
import { useLibrary } from "./runtime";

/** F1.4 / F1.6 / F1.8 — right-hand panel of the Library tab. */
export function ExportPanel() {
  const project = useProject((s) => s.project);
  const path = useProject((s) => s.path);
  const change = useProject((s) => s.change);
  const { selected, system, exportJobId, exportRequesting, setExportJob } = useLibrary();
  const job = useJobs((s) => (exportJobId ? s.jobs[exportJobId] : undefined));
  if (!project) return null;

  const items = byId(project);
  const chosen = project.library.filter((i) => selected.has(i.id));
  const ready = chosen.filter((i) => isReady(i, items));
  const entries = exportEntries(ready, items);
  const seconds = entries.reduce((a, e) => a + e.duration, 0);
  const lowKbps = system?.lowBitrateKbps ?? 160;
  const low = ready.filter((i) => isLowBitrate(i, lowKbps)).length;
  const { folder, pattern } = project.libraryExport;
  const sep = path?.includes("\\") ? "\\" : "/";
  const defaultFolder = `${path ?? ""}${sep}export`;
  const example = previewName(
    pattern,
    1,
    Math.max(1, ready.length),
    ready[0]?.title ?? "Midnight Coffee",
  );
  const running = job && (job.state === "queued" || job.state === "running");
  const result = job?.state === "done" ? (job.result as ExportResult) : null;

  return (
    <aside className="panel lib-side">
      <div className="ph">{t("library.export.title")}</div>
      <div className="pb">
        <div className="field">
          <label>{t("library.export.quality")}</label>
          <div className="row">
            <b>{t("library.export.qualityValue")}</b>
            <span className="badge">{t("library.export.fixed")}</span>
          </div>
        </div>
        <div className="field">
          <label htmlFor="exp-folder">{t("library.export.folder")}</label>
          <input
            id="exp-folder"
            type="text"
            value={folder}
            placeholder={t("library.export.folderDefault", { path: defaultFolder })}
            onChange={(e) =>
              change((d) => void (d.libraryExport.folder = e.target.value), "export-folder")
            }
          />
        </div>
        <div className="field">
          <label htmlFor="exp-pattern">{t("library.export.pattern")}</label>
          <input
            id="exp-pattern"
            type="text"
            maxLength={200}
            value={pattern}
            onChange={(e) =>
              change((d) => void (d.libraryExport.pattern = e.target.value), "export-pattern")
            }
          />
          <span className="muted small">{t("library.export.example", { name: example })}</span>
        </div>
        {low > 0 && (
          <div className="note warn">{t("library.export.lowWarn", { n: low, kbps: lowKbps })}</div>
        )}
        <div className="field">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="muted">{t("library.export.selected")}</span>
            <b className="num">
              {t("library.export.selectedValue", {
                n: ready.length,
                size: formatBytes(seconds * MP3_BYTES_PER_SECOND),
              })}
            </b>
          </div>
          {chosen.length > ready.length && (
            <span className="muted small">
              {t("library.export.notReady", { n: chosen.length - ready.length })}
            </span>
          )}
        </div>
        <button
          className="btn primary block"
          disabled={!entries.length || !!running || exportRequesting}
          onClick={() => void startExport(entries)}
        >
          {t("library.export.button", { n: entries.length })}
        </button>
        <button className="btn block" disabled={!ready.length} onClick={addSelectedToMix}>
          {t("library.export.toMix", { n: ready.length })}
        </button>

        {job && (
          <div className="export-job">
            {running && (
              <>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className="muted small num">{job.message}</span>
                  <button className="btn sm" onClick={() => void api.cancelJob(job.id)}>
                    {t("library.export.cancel")}
                  </button>
                </div>
                <div className="bar">
                  <i style={{ width: `${Math.round(job.progress * 100)}%` }} />
                </div>
              </>
            )}
            {result && (
              <>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className="ok">{t("library.export.done", { n: result.files.length })}</span>
                  <button
                    className="btn sm"
                    onClick={() =>
                      void api.openFolder(result.folder).catch(() => toast(result.folder, "info"))
                    }
                  >
                    {t("library.export.open")}
                  </button>
                </div>
                <div className="muted small path">{result.folder}</div>
                {result.failed.length > 0 && (
                  <div className="err small">
                    {t("library.export.failed", { n: result.failed.length })}
                    <ul>
                      {result.failed.map((f) => (
                        <li key={f.title} title={f.detail}>
                          {f.title}: {f.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
            {job.state === "failed" && <div className="err small">{job.error?.message_vi}</div>}
            {job.state === "cancelled" && (
              <div className="muted small" onClick={() => setExportJob(null)}>
                {t("library.status.cancelled")}
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
