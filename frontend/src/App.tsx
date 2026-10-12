import { useEffect } from "react";
import { connectEvents } from "./api/ws";
import { Home } from "./features/home/Home";
import { Placeholder } from "./features/placeholder/Placeholder";
import { SettingsDialog } from "./features/settings/SettingsDialog";
import { TopBar } from "./features/shell/TopBar";
import { t } from "./i18n";
import { useProject } from "./store/project";
import { TABS, useUi } from "./store/ui";

function isTyping(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
}

/** docs/UI-UX.md §7 */
function useShortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const p = useProject.getState();
      if (!p.project) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void p.saveNow();
      } else if (mod && e.key.toLowerCase() === "z" && !isTyping(e)) {
        e.preventDefault();
        if (e.shiftKey) p.redo();
        else p.undo();
      } else if (!mod && !isTyping(e) && /^[1-4]$/.test(e.key)) {
        const tab = TABS[Number(e.key) - 1];
        if (tab) useUi.getState().setTab(tab);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

export function App() {
  const project = useProject((s) => s.project);
  const { tab, connected, settingsOpen } = useUi();
  useEffect(() => connectEvents(), []);
  useShortcuts();

  return (
    <div className="app">
      {project ? <TopBar /> : <div />}
      {!connected ? <div className="banner">{t("conn.lost")}</div> : <div />}
      <main>{project ? <Placeholder tab={tab} /> : <Home />}</main>
      {settingsOpen && <SettingsDialog />}
    </div>
  );
}
