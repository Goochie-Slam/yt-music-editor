import { useMemo, useState } from "react";
import type { LibraryItem } from "../../api/types.gen";
import { t } from "../../i18n";
import { useJobs } from "../../store/jobs";
import { useProject } from "../../store/project";
import { cancelItem, removeSelected, retry } from "./actions";
import {
  audioOf,
  byId,
  formatDuration,
  isLowBitrate,
  latestJobs,
  sourceLabel,
  statusOf,
  type Status,
} from "./model";
import { droppedFiles, useLibrary } from "./runtime";

const DEFAULT_LOW_KBPS = 160;

function StatusCell({ item, status }: { item: LibraryItem; status: Status }) {
  const pct = (f: number) => Math.round(f * 100);
  switch (status.kind) {
    case "ready":
      return status.low ? (
        <span
          className="warn"
          title={t("library.status.lowHint", { kbps: item.srcBitrateKbps ?? 0 })}
        >
          {t("library.status.low")}
        </span>
      ) : (
        <span className="ok">{t("library.status.ready")}</span>
      );
    case "queued":
      return (
        <span className="run">
          {t("library.status.queued")}{" "}
          <button className="link" onClick={() => cancelItem(item.id)}>
            {t("library.status.cancel")}
          </button>
        </span>
      );
    case "running":
    case "uploading":
      return (
        <span className="run" title={status.kind === "running" ? status.message : undefined}>
          {status.kind === "running"
            ? t("library.status.running", { pct: pct(status.progress) })
            : t("library.status.uploading", { pct: pct(status.progress) })}{" "}
          <span className="mini-prog">
            <i style={{ width: `${pct(status.progress)}%` }} />
          </span>{" "}
          <button className="link" onClick={() => cancelItem(item.id)}>
            {t("library.status.cancel")}
          </button>
        </span>
      );
    case "error":
      return (
        <span className="err" title={status.message}>
          {t("library.status.error", { message: status.message })}{" "}
          <button className="link" onClick={() => retry(item)}>
            {t("library.status.retry")}
          </button>
        </span>
      );
    case "needsDrop":
      return (
        <span className="warn" title={t("library.status.needsDropHint")}>
          {t("library.status.needsDrop")}
        </span>
      );
    case "interrupted":
      return (
        <span className="warn">
          {t("library.status.interrupted")}{" "}
          <button className="link" onClick={() => retry(item)}>
            {t("library.status.retry")}
          </button>
        </span>
      );
    case "waitingParent":
      return <span className="muted">{t("library.status.waitingParent")}</span>;
  }
}

function TitleCell({ item }: { item: LibraryItem }) {
  const [editing, setEditing] = useState(false);
  const change = useProject((s) => s.change);
  if (!editing)
    return (
      <span
        className="title"
        title={t("library.table.rename")}
        onDoubleClick={() => setEditing(true)}
      >
        {item.title}
      </span>
    );
  const commit = (value: string) => {
    setEditing(false);
    const title = value.trim();
    if (!title || title === item.title) return;
    change((d) => {
      const it = d.library.find((i) => i.id === item.id);
      if (it) it.title = title;
    });
  };
  return (
    <input
      type="text"
      className="cell-edit"
      autoFocus
      defaultValue={item.title}
      onBlur={(e) => commit(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit(e.currentTarget.value);
        if (e.key === "Escape") setEditing(false);
      }}
    />
  );
}

export function LibraryTable() {
  const project = useProject((s) => s.project);
  const jobs = useJobs((s) => s.jobs);
  const { selected, uploads, resolving, system, toggle, setSelected } = useLibrary();
  const lowKbps = system?.lowBitrateKbps ?? DEFAULT_LOW_KBPS;

  const items = useMemo(
    () => (project ? byId(project) : new Map<string, LibraryItem>()),
    [project],
  );
  const latest = useMemo(
    () => (project ? latestJobs(jobs, project.id) : new Map()),
    [jobs, project],
  );
  if (!project) return null;
  const library = project.library;
  const allOn = library.length > 0 && library.every((i) => selected.has(i.id));

  return (
    <div className="tbl-wrap">
      <div className="row tbl-tools">
        <span className="muted num">
          {t("library.table.selectedOf", {
            n: library.filter((i) => selected.has(i.id)).length,
            total: library.length,
          })}
        </span>
        <button
          className="btn sm"
          style={{ marginLeft: "auto" }}
          title={t("library.table.removeHint")}
          disabled={!library.some((i) => selected.has(i.id))}
          onClick={removeSelected}
        >
          {t("library.table.remove")}
        </button>
      </div>
      <table className="lib-table">
        <thead>
          <tr>
            <th style={{ width: 30 }}>
              <input
                type="checkbox"
                aria-label={t("library.table.selectAll")}
                checked={allOn}
                onChange={(e) => setSelected(e.target.checked ? library.map((i) => i.id) : [])}
              />
            </th>
            <th style={{ width: 34 }}>{t("library.table.index")}</th>
            <th>{t("library.table.title")}</th>
            <th>{t("library.table.source")}</th>
            <th>{t("library.table.format")}</th>
            <th className="num">{t("library.table.duration")}</th>
            <th className="num">{t("library.table.kbps")}</th>
            <th style={{ width: 210 }}>{t("library.table.status")}</th>
          </tr>
        </thead>
        <tbody>
          {library.map((item, i) => {
            const src = sourceLabel(item, items);
            const status = statusOf(item, {
              items,
              job: latest.get(item.id),
              upload: uploads[item.id],
              hasFile: droppedFiles.has(item.id),
              lowKbps,
            });
            const audio = audioOf(item, items);
            return (
              <tr key={item.id} className={selected.has(item.id) ? "sel" : ""}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={item.title}
                    checked={selected.has(item.id)}
                    onChange={(e) => toggle(item.id, e.target.checked)}
                  />
                </td>
                <td className="muted num">{i + 1}</td>
                <td className="name">
                  <TitleCell item={item} />
                </td>
                <td>
                  <span className="src" title={src.title}>
                    <i className="dot" style={{ background: src.color }} />
                    <span>{src.label}</span>
                  </span>
                </td>
                <td className="muted">{item.srcFormat || "—"}</td>
                <td className="num">{formatDuration(audio?.duration ?? item.duration)}</td>
                <td className={`num ${isLowBitrate(item, lowKbps) ? "warn" : ""}`}>
                  {item.srcBitrateKbps ?? "—"}
                </td>
                <td>
                  <StatusCell item={item} status={status} />
                </td>
              </tr>
            );
          })}
          {resolving.map((r) => (
            <tr key={r.id} className="resolving">
              <td />
              <td />
              <td colSpan={5} className="muted" title={r.url}>
                {r.url}
              </td>
              <td className="run">⟳ {t("library.table.resolving")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!library.length && !resolving.length && (
        <p className="muted empty">{t("library.drop.empty")}</p>
      )}
    </div>
  );
}
