import { useEffect, useState } from "react";
import { api, ApiError, type SystemInfo } from "../../api/client";
import { t } from "../../i18n";
import { useJobs } from "../../store/jobs";
import { useUi } from "../../store/ui";

export function SettingsDialog() {
  const close = () => useUi.getState().setSettingsOpen(false);
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJobs((s) => (jobId ? s.jobs[jobId] : undefined));

  useEffect(() => {
    api
      .system()
      .then(setInfo)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.messageVi : String(e)));
  }, []);

  const startTest = async () => {
    try {
      setJobId((await api.selftest()).jobId);
    } catch (e) {
      setError(e instanceof ApiError ? e.messageVi : String(e));
    }
  };
  const running = job && (job.state === "queued" || job.state === "running");

  return (
    <div className="modal-bg" onClick={close}>
      <div
        className="panel modal"
        role="dialog"
        aria-label={t("settings.title")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ph">{t("settings.title")}</div>
        <div className="pb">
          {error && <div className="error-box">{error}</div>}
          {info && (
            <dl className="kv">
              <dt>{t("settings.version")}</dt>
              <dd>{info.appVersion}</dd>
              <dt>{t("settings.dataDir")}</dt>
              <dd>{info.dataDir}</dd>
              <dt>{t("settings.projectsDir")}</dt>
              <dd>{info.defaultProjectsDir}</dd>
              <dt>{t("settings.ffmpeg")}</dt>
              <dd className={info.ffmpeg.path ? "" : "err"}>
                {info.ffmpeg.version ?? t("settings.missing")}
              </dd>
              <dt>{t("settings.encoders")}</dt>
              <dd className={info.ffmpeg.nvenc ? "ok" : "warn"}>
                {info.ffmpeg.nvenc ? t("settings.nvencOk") : t("settings.nvencNo")}
              </dd>
              <dt>{t("settings.ytdlp")}</dt>
              <dd className={info.ytdlp.path ? "" : "warn"}>
                {info.ytdlp.version ?? t("settings.missing")}
              </dd>
            </dl>
          )}
          <div className="row" style={{ marginBottom: 10 }}>
            <button className="btn" disabled={!!running} onClick={() => void startTest()}>
              {t("settings.selftest")}
            </button>
            {running && jobId && (
              <button className="btn sm" onClick={() => void api.cancelJob(jobId)}>
                {t("settings.cancel")}
              </button>
            )}
            {job && <span className="muted num">{job.message}</span>}
          </div>
          {job && (
            <>
              <div className="bar">
                <i style={{ width: `${Math.round(job.progress * 100)}%` }} />
              </div>
              {job.state === "done" && <p className="ok">{t("settings.selftestDone")}</p>}
              {job.error && <p className="err">{job.error.message_vi}</p>}
            </>
          )}
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}>
            <button className="btn" onClick={close}>
              {t("settings.close")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
