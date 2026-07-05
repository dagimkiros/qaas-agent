"""
self-healing/audit_log.py
Persists healing events so clients see exactly what the agent changed,
run over run — builds trust instead of a black-box "auto-fixed" claim.
"""
import json
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.jsonl")


def append_events(events: list[dict]):
    with open(LOG_PATH, "a") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def load_recent(limit: int = 50) -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-limit:]]