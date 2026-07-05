"""
triage/triage.py
Classifies each failed scenario as real_bug, flaky, or selector_drift.

Usage:
    python triage.py results.json --out triaged_results.json
"""
import argparse
import json
import os
import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a senior QA engineer triaging automated test failures.
For each failure given, classify it as exactly one of:
  "real_bug", "flaky", or "selector_drift"

Also give a one-sentence, plain-English explanation a non-technical stakeholder
could understand, and a confidence score 0-1.

Respond with ONLY a JSON array, one object per failure, in the same order given:
[{"id": "TC-001", "classification": "real_bug", "explanation": "...", "confidence": 0.9}]
"""


def triage_failures(failures: list[dict]) -> list[dict]:
    if not failures:
        return []

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    failure_summaries = [
        {
            "id": f["id"],
            "title": f["title"],
            "error_steps": [
                s for s in f.get("step_results", []) if s["result"]["status"] == "failed"
            ],
        }
        for f in failures
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(failure_summaries)}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    cleaned = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_file")
    parser.add_argument("--out", default="triaged_results.json")
    args = parser.parse_args()

    with open(args.results_file) as f:
        results = json.load(f)

    failures = [r for r in results["scenario_results"] if r["status"] in ("failed", "error")]
    print(f"Triaging {len(failures)} failures...")

    triage_output = triage_failures(failures)
    triage_map = {t["id"]: t for t in triage_output}

    for scenario in results["scenario_results"]:
        if scenario["id"] in triage_map:
            scenario["triage"] = triage_map[scenario["id"]]

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Triaged results written to {args.out}")