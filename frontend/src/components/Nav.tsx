import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";

const READY: [string, string][] = [["Dashboard", "/dashboard"], ["Scan", "/scan"], ["History", "/history"], ["Analytics", "/analytics"], ["Models", "/model-performance"]];
const SOON = ["Profile", "Settings"];

export default function Nav({ landing = false }: { landing?: boolean }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const toggle = () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch { /* ignore */ }
  };
  const items = (
    <>
      {READY.map(([n, to]) => <NavLink key={to} to={to} onClick={() => setOpen(false)}>{n}</NavLink>)}
      {SOON.map((n) => <span key={n} className="soon" aria-disabled="true" title="Coming in a later phase">{n}<small>soon</small></span>)}
    </>
  );
  return (
    <header>
      <nav aria-label="Primary">
        <Link className="logo" to="/"><i />Sentinel</Link>
        {landing && !user && (
          <div className="links"><a href="#channels">Website</a><a href="#channels">Email</a><a href="#channels">Messages</a><a href="#channels">QR</a><a href="#channels">Files</a></div>
        )}
        {user && <div className="links">{items}</div>}
        {user && <NotificationBell />}
        <button className="btn" onClick={toggle} aria-label="Toggle light and dark theme">◐ Theme</button>
        {user ? (
          <>
            <button className="btn primary" onClick={logout}>Sign out</button>
            <button className="btn menu-btn" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X size={18} /> : <Menu size={18} />}</button>
          </>
        ) : (
          <><Link className="btn" to="/login">Sign in</Link><Link className="btn primary" to="/register">Get started</Link></>
        )}
      </nav>
      {user && open && <div className="mobile-menu">{items}</div>}
    </header>
  );
}
