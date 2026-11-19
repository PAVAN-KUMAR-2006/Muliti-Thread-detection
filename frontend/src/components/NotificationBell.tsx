import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { api, errMsg } from "../services/api";
import { useApi } from "../hooks/useApi";
import { NotificationItem, NotificationList } from "../types";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const wrap = useRef<HTMLDivElement>(null);
  const { data, error, reload } = useApi<NotificationList>("/notifications", { limit: 15 });

  useEffect(() => { const t = setInterval(reload, 30000); return () => clearInterval(t); }, [reload]);
  useEffect(() => {
    if (!open) return;
    const click = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", click); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", click); document.removeEventListener("keydown", key); };
  }, [open]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setErr("");
    try { await fn(); reload(); } catch (e) { setErr(errMsg(e)); }
    setBusy(false);
  };
  const markRead = (n: NotificationItem) => { if (!n.read) act(() => api.patch(`/notifications/${n.id}/read`)); };
  const unread = data?.unread_count ?? 0;

  return (
    <div className="bellwrap" ref={wrap}>
      <button className="btn bell" aria-label={`Notifications, ${unread} unread`} aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}>
        <Bell size={18} />{unread > 0 && <span className="badgecount">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="bellpanel" role="region" aria-label="Notifications">
          <div className="bellhead">
            <b>Notifications</b>
            <button className="linkbtn" disabled={busy || unread === 0} onClick={() => act(() => api.post("/notifications/read-all"))}>Mark all as read</button>
          </div>
          {(err || (!!error && !data)) && <p className="err" style={{ padding: "0 14px" }}>{err || "Unable to load notifications."} <button className="linkbtn" onClick={reload}>Retry</button></p>}
          {!data && !error && <p className="sub" style={{ padding: "10px 14px" }}>Loading…</p>}
          {data && data.items.length === 0 && <p className="sub" style={{ padding: "14px" }}>No notifications yet. High-risk scan results will appear here.</p>}
          <ul className="notes">
            {data?.items.map((n) => (
              <li key={n.id}>
                <button className={n.read ? "note" : "note unread"} onClick={() => markRead(n)} title={n.read ? "" : "Mark as read"}>
                  <span className="dot" aria-hidden="true" />
                  <span><b>{n.title}</b><small>{n.body}</small><small>{new Date(n.created_at).toLocaleString()}</small></span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
