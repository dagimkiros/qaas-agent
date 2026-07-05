"""
report-gen/generate_report.py
Turns triaged_results.json into a plain-English Markdown report.

Usage:
    python generate_report.py triaged_results.json --out report.md
"""
import argparse
import json

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_report(results: dict) -> str:
    summary = results["summary"]
    site = results["site_url"]
    run_at = results["run_at"]

    real_bugs = [
        s for s in results["scenario_results"]
        if s["status"] in ("failed", "error")
        and s.get("triage", {}).get("classification") == "real_bug"
    ]
    flaky = [
        s for s in results["scenario_results"]
        if s.get("triage", {}).get("classification") == "flaky"
    ]
    drift = [
        s for s in results["scenario_results"]
        if s.get("triage", {}).get("classification") == "selector_drift"
    ]

    real_bugs.sort(key=lambda s: PRIORITY_ORDER.get(s.get("priority", "low"), 3))

    lines = []
    lines.append(f"# QA Report — {site}")
    lines.append(f"_Run at {run_at}_\n")

    lines.append("## Summary\n")
    lines.append(f"- **{summary['total']}** scenarios run")
    lines.append(f"- **{summary['passed']}** passed")
    lines.append(f"- **{len(real_bugs)}** real bugs found")
    lines.append(f"- **{summary['self_healed_count']}** tests self-healed (UI changed, agent adapted automatically)")
    lines.append(f"- **{len(flaky)}** flaky / inconclusive\n")

    lines.append("## Real Bugs (action needed)\n")
    if not real_bugs:
        lines.append("None found in this run. ✅\n")
    else:
        for bug in real_bugs:
            triage = bug.get("triage", {})
            lines.append(f"### [{bug['priority'].upper()}] {bug['title']} (`{bug['id']}`)")
            lines.append(f"{triage.get('explanation', 'No explanation available.')}")
            lines.append(f"_Confidence: {triage.get('confidence', '?')}_\n")

    if drift:
        lines.append("## Self-Healed / Selector Drift\n")
        lines.append("These tests broke because the UI changed, not because of a bug. "
                      "The agent automatically adapted where possible.\n")
        for d in drift:
            lines.append(f"- `{d['id']}` — {d['title']}")
        lines.append("")

    if flaky:
        lines.append("## Flaky / Inconclusive\n")
        lines.append("Likely timing or network issues — worth a second look if they persist.\n")
        for f in flaky:
            lines.append(f"- `{f['id']}` — {f['title']}")
        lines.append("")

    lines.append("## Technical Appendix\n")
    lines.append("| ID | Title | Type | Status | Duration |")
    lines.append("|---|---|---|---|---|")
    for s in results["scenario_results"]:
        lines.append(
            f"| {s['id']} | {s['title']} | {s.get('type', '-')} | {s['status']} | {s.get('duration_ms', '-')}ms |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("triaged_results_file")
    parser.add_argument("--out", default="report.md")
    args = parser.parse_args()

    with open(args.triaged_results_file) as f:
        results = json.load(f)

    report = build_report(results)

    with open(args.out, "w") as f:
        f.write(report)

    print(f"Report written to {args.out}")