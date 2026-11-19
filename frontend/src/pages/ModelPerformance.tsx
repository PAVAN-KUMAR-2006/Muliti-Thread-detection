import { useState } from "react";
import { motion } from "framer-motion";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { useApi } from "../hooks/useApi";
import { ModelInfo, ModelStatus } from "../types";

type MetricKey = keyof ModelInfo["metrics"];
const NA = "Not available";
const METRICS: [MetricKey, string, string][] = [
  ["accuracy", "Accuracy", "Share of all predictions that were correct."],
  ["precision", "Precision", "Of the items predicted positive, how many really were positive."],
  ["recall", "Recall", "Of the items that really were positive, how many were found."],
  ["f1", "F1 score", "A balance between precision and recall."],
  ["roc_auc", "ROC-AUC", "How well the model ranks positives above negatives across all score thresholds."],
];
const STATUS: Record<ModelStatus, [string, string]> = { trained: ["Trained", "low"], not_trained: ["Model not trained", "medium"], metrics_unavailable: ["Metrics unavailable", "medium"] };
const pct = (v: number | null) => (v === null ? NA : `${(v * 100).toFixed(2)}%`);
const when = (s: string | null) => { if (!s) return NA; const d = new Date(s); return isNaN(d.getTime()) ? s : d.toLocaleString(); };

function StatusBadge({ s }: { s: ModelStatus }) {
  return <span className={`badge ${STATUS[s][1]}`}>{STATUS[s][0]}</span>;
}

function ModelCard({ m, active, onSelect }: { m: ModelInfo; active: boolean; onSelect: () => void }) {
  return (
    <motion.article className={`mcard ${active ? "active" : ""}`} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
      <header><h3>{m.name}</h3><StatusBadge s={m.status} /></header>
      <p className="sub">{m.algorithm ?? "Algorithm not available"}</p>
      {m.status === "trained" ? (
        <ul className="mbars">
          {METRICS.map(([k, label]) => (
            <li key={k}>
              <div className="row"><span>{label}</span><b>{pct(m.metrics[k])}</b></div>
              <div className="bar"><motion.i initial={{ width: 0 }} animate={{ width: `${(m.metrics[k] ?? 0) * 100}%` }} transition={{ duration: 0.9 }} style={{ background: "linear-gradient(90deg,var(--cyan),var(--violet))" }} /></div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="sub">{m.status === "not_trained" ? "This model has not been trained yet. Run its training script to see its metrics." : "The model file exists but its metrics file is missing or unreadable."}</p>
      )}
      <button className="btn" onClick={onSelect} aria-pressed={active} disabled={m.status === "not_trained"}>{active ? "Showing details" : "View details"}</button>
    </motion.article>
  );
}

function ConfusionMatrix({ m }: { m: ModelInfo }) {
  const cm = m.confusion_matrix;
  if (!cm) return <p className="sub">Confusion matrix: {NA}</p>;
  const names = m.class_names ?? ["Class 0 (negative)", m.positive_class ? `Class 1 (positive: ${m.positive_class})` : "Class 1 (positive)"];
  return (
    <div className="cmwrap" role="table" aria-label="Confusion matrix">
      <div className="cmaxis top">Predicted</div>
      <div className="cmgrid">
        <div className="cmaxis side">Actual</div>
        <div />
        {names.map((n) => <div key={n} className="cmhead">{n}</div>)}
        {cm.map((row, i) => {
          const total = row[0] + row[1];
          return [<div key={`h${i}`} className="cmhead rowhead">{names[i]}</div>, ...row.map((v, j) => (
            <div key={`${i}${j}`} className={`cmcell ${i === j ? "ok" : "bad"}`} style={{ ["--a" as string]: total ? v / total : 0 }} role="cell">
              <b>{v.toLocaleString()}</b><small>{total ? `${((v / total) * 100).toFixed(1)}% of actual` : ""}</small>
            </div>))];
        })}
      </div>
    </div>
  );
}

function Details({ m }: { m: ModelInfo }) {
  const rows: [string, string][] = [
    ["Algorithm", m.algorithm ?? NA], ["Description", m.description ?? NA], ["Dataset", m.dataset ?? NA], ["Version", m.version ?? NA],
    ["Trained at", when(m.trained_at)], ["Random seed", m.seed === null ? NA : String(m.seed)],
    ["Features", m.feature_count === null ? NA : String(m.feature_count)], ["Training samples", m.train_size === null ? NA : m.train_size.toLocaleString()],
    ["Test samples", m.test_size === null ? NA : m.test_size.toLocaleString()], ["Positive class", m.positive_class ?? NA], ["Metrics file", m.metrics_file],
  ];
  return (
    <section className="panel2" aria-label={`${m.name} details`}>
      <div className="phead"><h3>{m.name}: details</h3><StatusBadge s={m.status} /></div>
      <div className="mdetail">
        <dl className="info">{rows.flatMap(([k, v]) => [<dt key={`k${k}`}>{k}</dt>, <dd key={`v${k}`}>{v}</dd>])}</dl>
        <ConfusionMatrix m={m} />
      </div>
      <p className="sub" style={{ marginTop: 12 }}>ROC curve: {NA}. Only the single ROC-AUC value is stored by the training scripts.</p>
    </section>
  );
}

export default function ModelPerformance() {
  const { data, error, reload } = useApi<{ models: ModelInfo[] }>("/models/performance");
  const [sel, setSel] = useState<string | null>(null);
  const models = data?.models ?? [];
  const trained = models.filter((m) => m.status === "trained");
  const active = models.find((m) => m.key === sel && m.status !== "not_trained") ?? trained[0] ?? models.find((m) => m.status !== "not_trained");

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <h1>Model performance</h1>
        <p className="sub">Metrics written by the training scripts for the models that power each scanner.</p>
        {!!error && !data && <ErrorState message="Unable to load model performance." onRetry={reload} />}
        {!data && !error && <div className="mgrid">{[0, 1, 2].map((i) => <Skeleton key={i} h={300} />)}</div>}
        {data && models.every((m) => m.status === "not_trained") && (
          <EmptyState title="No trained models available." text="Train the required models to view their performance metrics." />
        )}
        {data && !models.every((m) => m.status === "not_trained") && (
          <>
            <p className="note2">These figures are measured on a held-out test split of each model's own dataset. They describe performance on that dataset, not guaranteed real-world accuracy, and models trained on different datasets and tasks should not be ranked against each other.</p>
            <div className="mgrid">{models.map((m) => <ModelCard key={m.key} m={m} active={active?.key === m.key} onSelect={() => setSel(m.key)} />)}</div>
            {active && <Details m={active} />}
            {trained.length > 0 && (
              <section className="panel2" aria-label="Metric comparison">
                <div className="phead"><h3>Side-by-side metrics</h3></div>
                <div className="tablescroll">
                  <table className="t cmp">
                    <thead><tr><th>Metric</th>{trained.map((m) => <th key={m.key}>{m.name}</th>)}</tr></thead>
                    <tbody>
                      {METRICS.map(([k, label]) => <tr key={k}><td data-label="Metric">{label}</td>{trained.map((m) => <td key={m.key} data-label={m.name}>{pct(m.metrics[k])}</td>)}</tr>)}
                      <tr><td data-label="Metric">Test samples</td>{trained.map((m) => <td key={m.key} data-label={m.name}>{m.test_size === null ? NA : m.test_size.toLocaleString()}</td>)}</tr>
                    </tbody>
                  </table>
                </div>
              </section>
            )}
            <section className="panel2" aria-label="What the metrics mean">
              <div className="phead"><h3>What the metrics mean</h3></div>
              <dl className="info">{METRICS.flatMap(([k, label, text]) => [<dt key={`k${k}`}>{label}</dt>, <dd key={`v${k}`}>{text}</dd>])}</dl>
            </section>
          </>
        )}
      </main>
    </>
  );
}
