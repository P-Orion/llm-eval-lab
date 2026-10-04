import argparse
from .engine import download, start, Store, ROOT, run_tasks, make_report


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("download")
    r = sub.add_parser("run")
    r.add_argument("--model", default="qwen3:0.6b")
    r.add_argument("--count", type=int, default=20)
    r.add_argument("--format", choices=["json", "delimiter"], default="json")
    for name in ["resume", "rescore"]:
        r = sub.add_parser(name)
        r.add_argument("run_id")
    sub.add_parser("serve")
    a = p.parse_args()
    if a.command == "download":
        download()
    elif a.command == "run":
        start(a.model, a.count, output_format=a.format)
    elif a.command == "resume":
        run_tasks(Store(ROOT / "data" / "runs.sqlite"), a.run_id)
    elif a.command == "rescore":
        make_report(Store(ROOT / "data" / "runs.sqlite"), a.run_id)
    else:
        import uvicorn

        uvicorn.run("llm_eval_lab.api:app", host="127.0.0.1", port=8013)


if __name__ == "__main__":
    main()
