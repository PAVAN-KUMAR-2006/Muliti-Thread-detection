import { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import ScanDetail from "./pages/ScanDetail";
import Analytics from "./pages/Analytics";
import ModelPerformance from "./pages/ModelPerformance";
import Nav from "./components/Nav";
import Scanner, { ScanHub } from "./pages/Scanner";
import PhoneScanner from "./pages/PhoneScanner";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <p style={{ padding: 40 }} role="status">Checking your session…</p>;
  return user ? <>{children}</> : <Navigate to="/login" replace state={{ from: loc }} />;
}

function Guest({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const from = (useLocation().state as { from?: { pathname: string } } | null)?.from?.pathname;
  if (loading) return <p style={{ padding: 40 }} role="status">Checking your session…</p>;
  return user ? <Navigate to={from ?? "/dashboard"} replace /> : <>{children}</>;
}

function Soon() {
  return <><Nav /><main className="dash"><h1>Coming soon</h1><p className="sub">This section is built in a later phase.</p></main></>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Guest><Login /></Guest>} />
      <Route path="/register" element={<Guest><Register /></Guest>} />
      <Route path="/forgot-password" element={<Guest><ForgotPassword /></Guest>} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/scan" element={<Protected><ScanHub /></Protected>} />
      <Route path="/scan/phone" element={<Protected><PhoneScanner /></Protected>} />
      <Route path="/scan/:kind" element={<Protected><Scanner /></Protected>} />
      <Route path="/analytics" element={<Protected><Analytics /></Protected>} />
      <Route path="/model-performance" element={<Protected><ModelPerformance /></Protected>} />
      <Route path="/history" element={<Protected><History /></Protected>} />
      <Route path="/history/:id" element={<Protected><ScanDetail /></Protected>} />
      {["profile", "settings"].map((p) => <Route key={p} path={`/${p}`} element={<Protected><Soon /></Protected>} />)}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
