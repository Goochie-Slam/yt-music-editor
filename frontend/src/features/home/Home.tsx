import { useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { ProjectSummary } from "../../api/types.gen";
import { t } from "../../i18n";
import { useProject } from "../../store/project";

export function Home() {
  const load = useProject((s) => s.load);
  const [recent, setRecent] = useState<ProjectSummary[]>([]);
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [openPath, setOpenPath] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .recent()
      .then(setRecent)
      .catch(() => setRecent([]));
    api
      .system()
      .then((s) => setParent((p) => p || s.defaultProjectsDir))
      .catch(() => undefined);
  }, []);

  const run = async (fn: () => Promise<{ project: Parameters<typeof load>[0]; path: string }>) => {
    setBusy(true);
    setError("");
    try {
      const r = await fn();
      load(r.project, r.path);
    } catch (e) {
      setError(e instanceof ApiError ? e.messageVi : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="home">
      <h1>
        <span className="logo">
          <i />
        </span>
        {t("home.title")}
      </h1>
      <div style={{ gridColumn: "1 / 3" }}>{error && <div className="error-box">{error}</div>}</div>

      <section className="panel">
        <div className="ph">{t("home.create")}</div>
        <form
          className="pb"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() => api.createProject(name.trim(), parent.trim()));
          }}
        >
          <div className="field">
            <label htmlFor="pname">{t("home.name")}</label>
            <input
              id="pname"
              type="text"
              value={name}
              placeholder={t("home.namePlaceholder")}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="pparent">{t("home.parent")}</label>
            <input
              id="pparent"
              type="text"
              value={parent}
              onChange={(e) => setParent(e.target.value)}
            />
          </div>
          <button className="btn primary" disabled={busy || !name.trim() || !parent.trim()}>
            {t("home.createBtn")}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="ph">{t("home.recent")}</div>
        {recent.length === 0 ? (
          <p className="pb muted">{t("home.noRecent")}</p>
        ) : (
          <ul className="recent">
            {recent.map((r) => (
              <li key={r.id} onClick={() => void run(() => api.openProject(r.path))}>
                <b>{r.name}</b>
                <small>{r.path}</small>
              </li>
            ))}
          </ul>
        )}
        <form
          className="pb"
          style={{ borderTop: "1px solid var(--border)" }}
          onSubmit={(e) => {
            e.preventDefault();
            void run(() => api.openProject(openPath.trim()));
          }}
        >
          <div className="field">
            <label htmlFor="popen">{t("home.openPath")}</label>
            <input
              id="popen"
              type="text"
              value={openPath}
              onChange={(e) => setOpenPath(e.target.value)}
            />
          </div>
          <button className="btn" disabled={busy || !openPath.trim()}>
            {t("home.openBtn")}
          </button>
        </form>
      </section>
    </div>
  );
}
