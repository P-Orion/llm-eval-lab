import { useEffect, useState, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowUpRight, Database } from "lucide-react";
import "./style.css";
export function Frame({
  title,
  children,
  live,
}: {
  title: string;
  children: ReactNode;
  live: boolean;
}) {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">
          <Activity size={24} />
          {title}
        </div>
        <a className="selected" href="#workspace">
          Workspace
        </a>
        <a href="#evidence">Evaluation evidence</a>
        <a
          href={
            "https://github.com/P-Orion/" +
            (title === "Receipt Review"
              ? "receipt-review-ml"
              : title === "FleetSignal"
                ? "fleet-signal-ml"
                : "llm-eval-lab")
          }
        >
          Source code <ArrowUpRight size={14} />
        </a>
        <div className="foot">
          An independent project by
          <br />
          <b>Orion Powers</b>
          <a href="https://orionpowers.com">Portfolio →</a>
        </div>
      </aside>
      <main className="main" id="workspace">
        <div className="topline">
          <span>Orion Powers / ML engineering</span>
          <span className="badge">
            <Database size={12} />
            {live ? "Local API connected" : "Recorded benchmark demo"}
          </span>
        </div>
        {children}
        <footer>
          Independent public-data project · Reproducible results · Measured
          limitations
        </footer>
      </main>
    </div>
  );
}
export function Stat({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="stat">
      <div className="muted">{label}</div>
      <strong>{value}</strong>
      <span>{note}</span>
    </div>
  );
}
export function useReport<T>(endpoint: string, file = "benchmark.json") {
  const [data, setData] = useState<T | null>(null),
    [live, setLive] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setLive(false);
    setError("");
    async function load() {
      try {
        const r = await fetch(endpoint, { signal: controller.signal });
        if (!r.ok || !r.headers.get("content-type")?.includes("json"))
          throw Error("offline");
        setData(await r.json());
        setLive(true);
      } catch {
        if (controller.signal.aborted) return;
        try {
          const r = await fetch("./" + file, { signal: controller.signal });
          if (!r.ok) throw Error("Benchmark file unavailable");
          setData(await r.json());
        } catch (e) {
          if (!controller.signal.aborted) setError(String(e));
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [endpoint, file]);
  return { data, live, error };
}
export function mount(component: ReactNode) {
  createRoot(document.getElementById("root")!).render(component);
}
