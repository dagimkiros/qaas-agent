"""
api/pipeline.py
Orchestrates: crawl -> generate test plan -> execute -> triage -> report.
One source of truth that both the API endpoints and the GitHub webhook call.
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.append("../crawler")
sys.path.append("../test-gen")
sys.path.append("../executor")
sys.path.append("../triage")
sys.path.append("../report-gen")

from crawl import crawl  # noqa: E402
from generate_test_plan import generate as generate_test_plan  # noqa: E402
from run_tests import run_all  # noqa: E402
from triage import triage_failures  # noqa: E402
from generate_report import build_report  # noqa: E402

RUNS_DIR = os.path.join(os.path.dirname(__file__), "runs")


def run_scan(site_url: str, max_pages: int = 25) -> dict:
    run_id = str(uuid.uuid4())[:8]
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    print(f"[{run_id}] Step 1/4: crawling {site_url}")
    crawl_data = crawl(site_url, max_pages)
    _save(run_dir, "crawl.json", crawl_data)

    print(f"[{run_id}] Step 2/4: generating test plan")
    test_plan = generate_test_plan(crawl_data)
    _save(run_dir, "test_plan.json", test_plan)

    print(f"[{run_id}] Step 3/4: executing {len(test_plan['scenarios'])} scenarios")
    results = run_all(test_plan)
    _save(run_dir, "results.json", results)

    print(f"[{run_id}] Step 4/4: triaging and reporting")
    failures = [r for r in results["scenario_results"] if r["status"] in ("failed", "error")]
    triage_output = triage_failures(failures)
    triage_map = {t["id"]: t for t in triage_output}
    for s in results["scenario_results"]:
        if s["id"] in triage_map:
            s["triage"] = triage_map[s["id"]]

    report_md = build_report(results)
    _save_text(run_dir, "report.md", report_md)

    return {
        "run_id": run_id,
        "site_url": site_url,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": results["summary"],
        "report_path": os.path.join(run_dir, "report.md"),
    }


def _save(run_dir, filename, data):
    with open(os.path.join(run_dir, filename), "w") as f:
        json.dump(data, f, indent=2)


def _save_text(run_dir, filename, text):
    with open(os.path.join(run_dir, filename), "w") as f:
        f.write(text)