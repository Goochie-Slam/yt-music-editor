import { t } from "../../i18n";
import { useProject } from "../../store/project";
import type { Tab } from "../../store/ui";
import { audioOf, byId, formatDuration } from "../library/model";

const MILESTONE: Record<Tab, string> = { library: "M2", mix: "M3", video: "M4–M5", export: "M6" };

/** Honest stand-in until the milestone lands — no fake UI. */
export function Placeholder({ tab }: { tab: Tab }) {
  const project = useProject((s) => s.project);
  const tracks = project?.mix.tracks ?? [];
  const items = project ? byId(project) : new Map();
  const seconds = tracks.reduce((a, tr) => {
    const item = items.get(tr.libId);
    return a + (item ? (audioOf(item, items)?.duration ?? 0) : 0);
  }, 0);
  return (
    <div className="placeholder">
      <h2>{t(`steps.${tab}`)}</h2>
      <p className="muted">{t(`placeholder.${tab}`)}</p>
      {tab === "mix" && tracks.length > 0 && (
        <p>{t("placeholder.mixCount", { n: tracks.length, duration: formatDuration(seconds) })}</p>
      )}
      <p className="warn">{t("placeholder.milestone", { milestone: MILESTONE[tab] })}</p>
    </div>
  );
}
