import { useJobs, type JobEvent } from "../store/jobs";
import { useUi } from "../store/ui";

/** Server-pushed events (job progress). Reconnects with backoff; the UI shows a banner meanwhile. */
export function connectEvents(): () => void {
  let ws: WebSocket | null = null;
  let retry = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;

  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/api/ws`);
    ws.onopen = () => {
      retry = 0;
      useUi.getState().setConnected(true);
    };
    ws.onmessage = (msg) => {
      const ev = JSON.parse(String(msg.data)) as { type?: string };
      if (ev.type === "job") useJobs.getState().upsert(ev as JobEvent);
    };
    ws.onclose = () => {
      useUi.getState().setConnected(false);
      if (!stopped) timer = setTimeout(open, Math.min(5000, 300 * 2 ** retry++));
    };
  };
  open();
  return () => {
    stopped = true;
    clearTimeout(timer);
    ws?.close();
  };
}
