import { t } from "../../i18n";
import type { Tab } from "../../store/ui";

const MILESTONE: Record<Tab, string> = { library: "M2", mix: "M3", video: "M4–M5", export: "M6" };

/** Honest stand-in until the milestone lands — no fake UI. */
export function Placeholder({ tab }: { tab: Tab }) {
  return (
    <div className="placeholder">
      <h2>{t(`steps.${tab}`)}</h2>
      <p className="muted">{t(`placeholder.${tab}`)}</p>
      <p className="warn">{t("placeholder.milestone", { milestone: MILESTONE[tab] })}</p>
    </div>
  );
}
