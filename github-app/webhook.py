"""
github-app/webhook.py
Receives GitHub PR webhook events and triggers a scan against the PR's
preview URL.

Setup:
- Register a GitHub App, webhook -> POST /webhook/github
- Subscribe to "pull_request" events
- Set GITHUB_WEBHOOK_SECRET
- get_preview_url() is a placeholder — wire it to your actual deploy
  preview convention (Vercel/Netlify API, or a bot comment on the PR).
"""
import hashlib
import hmac
import os
import sys
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

sys.path.append("../api")
from pipeline import run_scan  # noqa: E402

router = APIRouter()

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    if not WEBHOOK_SECRET:
        return True  # dev mode only — always set a secret in production
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")


def get_preview_url(payload: dict) -> str | None:
    pr = payload.get("pull_request", {})
    return pr.get("_preview_url_placeholder")


@router.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature):
        raise HTTPException(401, "invalid signature")

    event = request.headers.get("X-GitHub-Event")
    payload = await request.json()

    if event != "pull_request" or payload.get("action") not in ("opened", "synchronize"):
        return {"status": "ignored"}

    preview_url = get_preview_url(payload)
    if not preview_url:
        return {"status": "no preview url found, skipping scan"}

    pr_number = payload["pull_request"]["number"]
    repo = payload["repository"]["full_name"]
    print(f"Triggering scan for {repo} PR #{pr_number} -> {preview_url}")

    background_tasks.add_task(run_scan, preview_url)
    return {"status": "scan triggered", "preview_url": preview_url}