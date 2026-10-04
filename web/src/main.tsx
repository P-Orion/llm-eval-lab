import { useState, useEffect } from "react";
import { FlaskConical, FileJson } from "lucide-react";
import { Frame, Stat, useReport, mount } from "./shared";
type Row = {
  qid: number;
  condition: string;
  seed: number;
  question: string;
  target: string;
  response: string | null;
  extracted: string | null;
  correct: boolean;
  status: string;
  error: string | null;
  latency: number;
  tokens: number;
  attempts: number;
};
type Summary = {
  scheduled: number;
  completed: number;
  failed: number;
  correct: number;
  task_success: number;
  extraction_failures: number;
  p50_seconds: number | null;
  tokens: number;
};
type Report = {
  run_id: string;
  manifest: {
    model: string;
    model_digest: string;
    dataset_sha256: string;
    source_sha256?: string;
    conditions: string[];
    seeds: number[];
    temperature: number;
    think: boolean;
    ollama_version?: string;
    output_format?: string;
  };
  summary: Record<string, Summary>;
  paired: {
    difference: number;
    ci95: number[];
    n_questions: number;
    comparison: string;
  };
  responses: Row[];
  limitations: string[];
};
function App() {
  const [runId, setRunId] = useState(""),
    [runs, setRuns] = useState<{ id: string; label: string }[]>([]);
  const runFile = runId ? "runs/" + runId + ".json" : "report.json";
  useEffect(() => {
    void fetch("./runs.json")
      .then((r) => r.json())
      .then(setRuns)
      .catch(() => {});
  }, []);
  const {
    data: r,
    live,
    error,
  } = useReport<Report>(
    runId ? "/api/report?run=" + runId : "/api/report",
    runFile,
  );
  const [query, setQuery] = useState(""),
    [condition, setCondition] = useState("all"),
    [status, setStatus] = useState("all"),
    [selected, setSelected] = useState(0);
  if (!r)
    return (
      <div className="loading">{error || "Loading recorded experiment…"}</div>
    );
  const total = Object.values(r.summary).reduce((n, s) => n + s.scheduled, 0),
    completed = Object.values(r.summary).reduce((n, s) => n + s.completed, 0),
    badParse = Object.values(r.summary).reduce(
      (n, s) => n + s.extraction_failures,
      0,
    ),
    rows = r.responses.filter(
      (p) =>
        (condition === "all" || p.condition === condition) &&
        (status === "all" ||
          (status === "correct"
            ? p.correct
            : status === "parse"
              ? p.status === "completed" && !p.extracted
              : !p.correct)) &&
        (p.question + " " + p.qid).toLowerCase().includes(query.toLowerCase()),
    ),
    row = r.responses[selected],
    inconclusive = r.paired.ci95[0] <= 0 && r.paired.ci95[1] >= 0;
  return (
    <Frame title="Eval Lab" live={live}>
      <div className="heading">
        <div>
          <div className="eyebrow">
            Independent BrainBench follow-up / Experiment browser
          </div>
          <h1>Every result has a trace.</h1>
          <p className="muted">
            Compare prompts, inspect failures, and reproduce the report from
            saved responses.
          </p>
        </div>
        <a className="button" href={"./" + runFile} download>
          <FileJson size={16} /> Download run
        </a>
      </div>
      <div className="controls">
        <label htmlFor="run">Recorded experiment</label>
        <select
          id="run"
          style={{ maxWidth: 440 }}
          value={runId}
          onChange={(e) => {
            setRunId(e.target.value);
            setSelected(0);
          }}
        >
          <option value="">Latest experiment</option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {run.label}
            </option>
          ))}
        </select>
        <span className="badge">
          {r.manifest.output_format || "delimiter"} output
        </span>
      </div>
      <div className="stats">
        <Stat
          label="Scheduled requests"
          value={String(total)}
          note={r.paired.n_questions + " GSM8K questions · paired prompts"}
        />
        <Stat
          label="Completed"
          value={completed + "/" + total}
          note="Failures stay in the denominator"
        />
        <Stat
          label="Answer-format failures"
          value={String(badParse)}
          note="Completed responses without a valid answer payload"
        />
        <Stat
          label="Model"
          value={r.manifest.model}
          note="Local Ollama · pinned model digest"
        />
      </div>
      <div className="grid">
        <section className="card" id="evidence">
          <div className="cardhead">
            <h2>
              <FlaskConical size={18} /> Prompt comparison
            </h2>
            <span className="badge">
              {r.manifest.seeds.length} seed / condition
            </span>
          </div>
          {Object.entries(r.summary).map(([name, s]) => (
            <div className="metricrow" key={name}>
              <div>
                <b>{name}</b>
                <span className="mono">
                  {(s.task_success * 100).toFixed(1)}% · {s.correct}/
                  {s.scheduled}
                </span>
              </div>
              <div className="bar">
                <i style={{ width: s.task_success * 100 + "%" }} />
              </div>
              <div className="caption">
                {s.extraction_failures} extraction failures · {s.failed} request
                failures · p50 {s.p50_seconds?.toFixed(2) ?? "—"} seconds
              </div>
            </div>
          ))}
          <p className="caption">
            Task success requires a completed response, the required
            final-answer format, and a numerically correct answer. Reasoning
            text is never used to guess the answer.
          </p>
        </section>
        <section className="card">
          <div className="eyebrow">Paired difference</div>
          <strong className="mono" style={{ fontSize: 38 }}>
            {r.paired.difference >= 0 ? "+" : ""}
            {(r.paired.difference * 100).toFixed(1)} pp
          </strong>
          <p className="muted">{r.paired.comparison}</p>
          <p className="mono" style={{ margin: "18px 0" }}>
            95% CI:{" "}
            {r.paired.ci95.map((x) => (x * 100).toFixed(1)).join(" to ")} pp
          </p>
          <span className={"badge " + (inconclusive ? "amber" : "green")}>
            {inconclusive
              ? "Inconclusive at this sample size"
              : "Interval excludes zero in this run"}
          </span>
          <p className="caption">
            Bootstrap unit: question. Repeated seeds stay grouped by question.
            This public benchmark may overlap model training data.
          </p>
        </section>
      </div>
      <section className="card" style={{ marginTop: 22 }}>
        <div className="cardhead">
          <h2>Response and failure explorer</h2>
          <span className="badge">{rows.length} matching responses</span>
        </div>
        <div className="controls">
          <input
            type="search"
            aria-label="Search questions"
            placeholder="Search question text or ID…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            aria-label="Prompt condition"
            style={{ maxWidth: 170 }}
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
          >
            <option value="all">All prompts</option>
            {r.manifest.conditions.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select
            aria-label="Outcome filter"
            style={{ maxWidth: 190 }}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="all">All outcomes</option>
            <option value="incorrect">Incorrect or failed</option>
            <option value="parse">Format failures</option>
            <option value="correct">Correct</option>
          </select>
        </div>
        <div className="grid">
          <div className="tablewrap" style={{ maxHeight: 480 }}>
            <table>
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Prompt</th>
                  <th>Result</th>
                  <th>Latency</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr
                    key={p.qid + "-" + p.condition + "-" + p.seed}
                    className={p === row ? "active" : ""}
                  >
                    <td>
                      <button
                        onClick={() => setSelected(r.responses.indexOf(p))}
                      >
                        #{p.qid}
                      </button>
                    </td>
                    <td>{p.condition}</td>
                    <td>
                      <span
                        className={"badge " + (p.correct ? "green" : "amber")}
                      >
                        {p.correct
                          ? "Correct"
                          : p.extracted
                            ? "Wrong answer"
                            : "Format / failure"}
                      </span>
                    </td>
                    <td>{p.latency?.toFixed(2)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <div className="eyebrow">
              Question #{row.qid} / {row.condition}
            </div>
            <p>{row.question}</p>
            <div className="controls" style={{ marginTop: 16 }}>
              <span className="badge">Target {row.target}</span>
              <span className="badge amber">
                Extracted {row.extracted ?? "None"}
              </span>
            </div>
            <pre className="response">
              {row.response || row.error || "No completed response"}
            </pre>
            <p className="caption">
              Seed {row.seed} · {row.tokens} generated tokens · {row.attempts}{" "}
              attempt(s) · {row.status}
            </p>
          </div>
        </div>
      </section>
      <section className="card" style={{ marginTop: 22 }}>
        <h2>Run identity and reproducibility</h2>
        <p className="mono">Run {r.run_id}</p>
        <div className="tablewrap">
          <table>
            <tbody>
              <tr>
                <td>Model digest</td>
                <td className="mono" style={{ overflowWrap: "anywhere" }}>
                  {r.manifest.model_digest}
                </td>
              </tr>
              <tr>
                <td>Dataset SHA-256</td>
                <td className="mono" style={{ overflowWrap: "anywhere" }}>
                  {r.manifest.dataset_sha256}
                </td>
              </tr>
              <tr>
                <td>Runner source SHA-256</td>
                <td className="mono" style={{ overflowWrap: "anywhere" }}>
                  {r.manifest.source_sha256 || "Not recorded (legacy pilot)"}
                </td>
              </tr>
              <tr>
                <td>Settings</td>
                <td>
                  Temperature {r.manifest.temperature} · internal thinking{" "}
                  {String(r.manifest.think)} · Ollama{" "}
                  {r.manifest.ollama_version || "not recorded (legacy pilot)"}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <details>
          <summary>Experiment limitations</summary>
          {r.limitations.map((l) => (
            <p className="muted" key={l}>
              {l}
            </p>
          ))}
        </details>
        <p className="caption">
          A new independent toolkit inspired by BrainBench. These experiments
          are separate from the original senior-design study and its unpublished
          runner.
        </p>
      </section>
    </Frame>
  );
}
mount(<App />);
