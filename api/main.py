"""
api/main.py
FastAPI service exposing the pipeline.

Run:
    uvicorn main:app --reload --port 8000
"""
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl

from pipeline import run_scan

app = FastAPI(title="QaaS Agent API")

scan_status: dict[str, dict] = {}


class ScanRequest(BaseModel):
    site_url: HttpUrl
    max_pages: int = 25


def _execute_scan(run_key: str, site_url: str, max_pages: int):
    try:
        scan_status[run_key]["status"] = "running"
        result = run_scan(site_url, max_pages)
        scan_status[run_key].update({"status": "completed", **result})
    except Exception as e:
        scan_status[run_key]["status"] = "error"
        scan_status[run_key]["error"] = str(e)


@app.post("/scans")
def create_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    run_key = os.urandom(4).hex()
    scan_status[run_key] = {"status": "queued", "site_url": str(req.site_url)}
    background_tasks.add_task(_execute_scan, run_key, str(req.site_url), req.max_pages)
    return {"run_key": run_key, "status": "queued"}


@app.get("/scans/{run_key}")
def get_scan(run_key: str):
    if run_key not in scan_status:
        raise HTTPException(404, "scan not found")
    return scan_status[run_key]


@app.get("/scans/{run_key}/report")
def get_report(run_key: str):
    status = scan_status.get(run_key)
    if not status or status.get("status") != "completed":
        raise HTTPException(404, "report not ready")
    with open(status["report_path"]) as f:
        return {"report_markdown": f.read()}


@app.get("/health")
def health():
    return {"status": "ok"}