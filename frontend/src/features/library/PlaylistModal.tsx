import { useEffect, useMemo, useState } from "react";
import { t } from "../../i18n";
import { addLinkEntries, closePlaylist } from "./actions";
import { formatDuration } from "./model";
import { useLibrary } from "./runtime";

/** A pasted playlist link: pick which entries to import (F1.2). One playlist at a time. */
export function PlaylistModal() {
  const playlist = useLibrary((s) => s.playlists[0]);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState("");

  useEffect(() => {
    setQuery("");
    setChecked(new Set(playlist?.entries.flatMap((e, i) => (e.available ? [i] : [])) ?? []));
  }, [playlist]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (playlist?.entries ?? [])
      .map((e, i) => ({ e, i }))
      .filter(({ e }) => !q || e.title.toLowerCase().includes(q));
  }, [playlist, query]);

  if (!playlist) return null;
  const anyVisibleOn = visible.some(({ i }) => checked.has(i));
  const toggleVisible = () => {
    const next = new Set(checked);
    for (const { e, i } of visible) {
      if (anyVisibleOn) next.delete(i);
      else if (e.available) next.add(i);
    }
    setChecked(next);
  };
  const add = () => {
    addLinkEntries(playlist.entries.filter((_, i) => checked.has(i)));
    closePlaylist(playlist.id);
  };

  return (
    <div className="modal-bg" onClick={() => closePlaylist(playlist.id)}>
      <div className="panel modal pl-modal" role="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="ph">
          <span>{t("library.playlist.title", { title: playlist.title })}</span>
          <span>{t("library.playlist.count", { n: playlist.entries.length })}</span>
        </div>
        <div className="pb row">
          <input
            type="text"
            placeholder={t("library.playlist.search")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn sm" onClick={toggleVisible}>
            {anyVisibleOn ? t("library.playlist.none") : t("library.playlist.all")}
          </button>
        </div>
        <div className="list">
          {visible.map(({ e, i }) => (
            <label key={i} className={`item ${e.available ? "" : "off"}`}>
              <input
                type="checkbox"
                disabled={!e.available}
                checked={checked.has(i)}
                onChange={(ev) => {
                  const next = new Set(checked);
                  if (ev.target.checked) next.add(i);
                  else next.delete(i);
                  setChecked(next);
                }}
              />
              <span className="muted num">{i + 1}</span>
              <span className="grow">{e.title}</span>
              <span className="muted num">
                {e.available ? formatDuration(e.duration) : t("library.playlist.unavailable")}
              </span>
            </label>
          ))}
        </div>
        <div className="pb row" style={{ justifyContent: "flex-end" }}>
          <button className="btn" onClick={() => closePlaylist(playlist.id)}>
            {t("library.playlist.cancel")}
          </button>
          <button className="btn primary" disabled={!checked.size} onClick={add}>
            {t("library.playlist.add", { n: checked.size })}
          </button>
        </div>
      </div>
    </div>
  );
}
