import { t, type MessageKey } from "../../i18n";
import { isActive, useJobs } from "../../store/jobs";
import { useProject } from "../../store/project";
import { TABS, useUi } from "../../store/ui";

const SAVE_LABEL: Record<string, MessageKey> = {
  saved: "save.saved",
  saving: "save.saving",
  dirty: "save.dirty",
  error: "save.error",
};

export function TopBar() {
  const { project, save, saveError, hist, change, undo, redo, close } = useProject();
  const { tab, setTab, setSettingsOpen } = useUi();
  const active = Object.values(useJobs((s) => s.jobs)).filter(isActive).length;
  if (!project) return null;

  return (
    <header className="top">
      <div className="logo">
        <i />
        {t("app.name")}
      </div>
      <div className="proj">
        <input
          type="text"
          aria-label={t("top.rename")}
          value={project.name}
          onChange={(e) => change((d) => void (d.name = e.target.value), "rename")}
        />
        <span className={`save ${save === "saved" ? "ok" : save === "error" ? "err" : "muted"}`}>
          {t(SAVE_LABEL[save] ?? "save.saved", { message: saveError })}
        </span>
      </div>
      <nav className="steps">
        {TABS.map((id, i) => (
          <button key={id} className={`step ${tab === id ? "on" : ""}`} onClick={() => setTab(id)}>
            <span>{i + 1}</span>
            {t(`steps.${id}`)}
          </button>
        ))}
      </nav>
      <div className="tools">
        <button
          className="btn icon"
          title={t("top.undo")}
          disabled={!hist.past.length}
          onClick={undo}
        >
          ↶
        </button>
        <button
          className="btn icon"
          title={t("top.redo")}
          disabled={!hist.future.length}
          onClick={redo}
        >
          ↷
        </button>
        <button
          className="btn icon warn"
          title={t("top.queue")}
          onClick={() => setSettingsOpen(true)}
        >
          ⏳ <span className="num">{active}</span>
        </button>
        <button
          className="btn icon"
          title={t("top.settings")}
          onClick={() => setSettingsOpen(true)}
        >
          ⚙
        </button>
        <button className="btn icon" title={t("top.close")} onClick={close}>
          ✕
        </button>
      </div>
    </header>
  );
}
