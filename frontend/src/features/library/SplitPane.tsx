import { useEffect, useMemo, useState } from "react";
import { api, ApiError, type TracklistParsed } from "../../api/client";
import { t } from "../../i18n";
import { useProject } from "../../store/project";
import { toast } from "../../store/toast";
import { startExport } from "./actions";
import { addToMix, formatDuration, segmentItems } from "./model";
import { useLibrary } from "./runtime";

const PARSE_DEBOUNCE_MS = 250;

/** F1.5: cut one long file by a pasted tracklist, losslessly. */
export function SplitPane() {
  const project = useProject((s) => s.project);
  const sources = useMemo(
    () =>
      (project?.library ?? []).filter(
        (i) => i.source.kind !== "segment" && i.cacheWav && i.duration,
      ),
    [project],
  );
  const [sourceId, setSourceId] = useState("");
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<TracklistParsed | null>(null);
  const [error, setError] = useState("");

  const source = sources.find((s) => s.id === sourceId) ?? sources[0];
  const duration = source?.duration ?? 0;

  useEffect(() => {
    if (!text.trim() || !duration) {
      setParsed(null);
      return;
    }
    const timer = setTimeout(() => {
      api
        .parseTracklist(text, duration)
        .then((r) => {
          setParsed(r);
          setError("");
        })
        .catch((e: unknown) => setError(e instanceof ApiError ? e.messageVi : String(e)));
    }, PARSE_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text, duration]);

  if (!project) return null;
  if (!source) return <p className="muted split-empty">{t("library.split.noSource")}</p>;

  const segments = parsed?.segments ?? [];
  const errors = parsed?.errors ?? [];
  // A line without a timestamp is usually a heading ("Tracklist:"), safe to skip. A wrong or
  // out-of-order timestamp is not: the previous segment would run into the next song.
  const blocking = errors.filter((e) => e.error !== "bad_format");
  const canCut = segments.length > 0 && blocking.length === 0;

  const cut = () => {
    const items = segmentItems(source, segments);
    useProject.getState().change((d) => {
      d.library.push(...items);
      addToMix(d, items);
    });
    const lib = useLibrary.getState();
    lib.setSelected([...lib.selected, ...items.map((i) => i.id)]); // like every other new item
    toast(t("library.split.done", { n: items.length }), "ok");
    setText("");
  };

  const exportOnly = () => {
    const wav = source.cacheWav ?? "";
    void startExport(
      segments.map((s) => ({
        title: s.title,
        wav,
        start: s.start,
        end: s.end,
        duration: s.end - s.start,
      })),
    );
  };

  return (
    <div className="split">
      <div className="row">
        <label className="muted" htmlFor="split-src">
          {t("library.split.source")}
        </label>
        <select id="split-src" value={source.id} onChange={(e) => setSourceId(e.target.value)}>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title} · {formatDuration(s.duration)}
            </option>
          ))}
        </select>
      </div>
      <div className="tl-grid">
        <div className="col">
          <span className="lbl">{t("library.split.paste")}</span>
          <textarea
            aria-label={t("library.split.paste")}
            placeholder={t("library.split.placeholder")}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
        <div className="panel col">
          <div className="ph">
            <span>{t("library.split.preview")}</span>
            <span>
              {errors.length
                ? t("library.split.countErr", { n: segments.length, e: errors.length })
                : t("library.split.count", { n: segments.length })}
            </span>
          </div>
          <div className="scroll">
            {error && <div className="error-box">{error}</div>}
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>{t("library.table.title")}</th>
                  <th className="num">{t("library.split.start")}</th>
                  <th className="num">{t("library.split.end")}</th>
                  <th className="num">{t("library.split.length")}</th>
                </tr>
              </thead>
              <tbody>
                {segments.map((s) => (
                  <tr key={s.index}>
                    <td className="muted num">{s.index}</td>
                    <td>{s.title}</td>
                    <td className="num">{formatDuration(s.start)}</td>
                    <td className="num">{formatDuration(s.end)}</td>
                    <td className="num">{formatDuration(s.end - s.start)}</td>
                  </tr>
                ))}
                {errors.map((e) => (
                  <tr key={`e${e.lineNo}`}>
                    <td />
                    <td colSpan={4} className={e.error === "bad_format" ? "muted" : "err"}>
                      {t("library.split.line", { n: e.lineNo })}: “{e.text.trim()}” —{" "}
                      {e.error === "bad_format"
                        ? t("library.split.skipped")
                        : t(`library.split.errors.${e.error}`)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {blocking.length > 0 && (
            <div className="note err">{t("library.split.fixFirst", { n: blocking.length })}</div>
          )}
          <div
            className="pb row"
            style={{ justifyContent: "flex-end", borderTop: "1px solid var(--border)" }}
          >
            <button className="btn" disabled={!canCut} onClick={exportOnly}>
              {t("library.split.exportOnly")}
            </button>
            <button className="btn primary" disabled={!canCut} onClick={cut}>
              {t("library.split.cut")}
            </button>
          </div>
          <div className="note" style={{ margin: "0 14px 14px" }}>
            {t("library.split.note")}
          </div>
        </div>
      </div>
    </div>
  );
}
