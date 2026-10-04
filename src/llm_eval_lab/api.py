import json, re
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from .engine import ROOT

app = FastAPI(title="LLM Eval Lab", version="0.1.0")


@app.get("/api/report")
def report(run: str | None = None):
    if run is not None and not re.fullmatch("[a-f0-9]{20}", run):
        raise HTTPException(422, "Invalid run identifier")
    p = (
        ROOT / "reports" / run / "report.json"
        if run
        else ROOT / "reports" / "latest.json"
    )
    if not p.exists():
        raise HTTPException(503, "No experiment report; run evaluation first")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/health")
def health():
    return {"status": "ok"}


if (ROOT / "web" / "dist").exists():
    app.mount("/", StaticFiles(directory=ROOT / "web" / "dist", html=True), name="web")
