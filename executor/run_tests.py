"""
executor/run_tests.py
Runs every scenario in test_plan.json against the live site using Playwright,
interpreting the JSON directly so self-healing can retry mid-scenario.

Usage:
    python run_tests.py test_plan.json --out results.json
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

sys.path.append("../self-healing")
from heal import attempt_heal  # noqa: E402


def run_step(page, step: dict, fallback_selectors: list, audit_log: list) -> dict:
    action = step["action"]
    selector = step.get("selector")
    value = step.get("value", "")
    expected = step.get("expected", "")

    candidates = [selector] + fallback_selectors if selector else [None]

    last_error = None
    for i, candidate in enumerate(candidates):
        try:
            if action == "goto":
                page.goto(value, timeout=15000)
            elif action == "click":
                page.click(candidate, timeout=5000)
            elif action == "fill":
                page.fill(candidate, value, timeout=5000)
            elif action == "select":
                page.select_option(candidate, value, timeout=5000)
            elif action == "assert_visible":
                page.wait_for_selector(candidate, state="visible", timeout=5000)
            elif action == "assert_text":
                page.wait_for_selector(candidate, timeout=5000)
                actual = page.text_content(candidate) or ""
                if expected not in actual:
                    raise AssertionError(f"expected '{expected}' in '{actual}'")
            elif action == "wait_for":
                page.wait_for_selector(candidate, timeout=8000)
            else:
                return {"status": "skipped", "reason": f"unsupported action {action}"}

            if i > 0:
                audit_log.append(attempt_heal(
                    original_selector=selector,
                    healed_selector=candidate,
                    action=action,
                    success=True,
                ))
            return {"status": "passed"}

        except Exception as e:
            last_error = str(e)
            continue

    return {"status": "failed", "error": last_error}


def run_scenario(page, scenario: dict, audit_log: list) -> dict:
    results = []
    overall_status = "passed"
    for step in scenario["steps"]:
        result = run_step(page, step, scenario.get("fallback_selectors", []), audit_log)
        results.append({**step, "result": result})
        if result["status"] == "failed":
            overall_status = "failed"
            break

    return {
        "id": scenario["id"],
        "title": scenario["title"],
        "type": scenario["type"],
        "priority": scenario["priority"],
        "status": overall_status,
        "step_results": results,
    }


def run_all(test_plan: dict) -> dict:
    audit_log = []
    scenario_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for scenario in test_plan["scenarios"]:
            page = browser.new_page()
            start = time.time()
            try:
                result = run_scenario(page, scenario, audit_log)
            except Exception as e:
                result = {
                    "id": scenario["id"], "title": scenario["title"],
                    "status": "error", "error": str(e),
                }
            result["duration_ms"] = int((time.time() - start) * 1000)
            scenario_results.append(result)
            page.close()
            print(f"  [{result['status'].upper()}] {scenario['id']} - {scenario['title']}")

        browser.close()

    passed = sum(1 for r in scenario_results if r["status"] == "passed")
    failed = sum(1 for r in scenario_results if r["status"] == "failed")

    return {
        "site_url": test_plan["site_url"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(scenario_results),
            "passed": passed,
            "failed": failed,
            "self_healed_count": len(audit_log),
        },
        "scenario_results": scenario_results,
        "self_healing_audit_log": audit_log,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("test_plan_file")
    parser.add_argument("--out", default="results.json")
    args = parser.parse_args()

    with open(args.test_plan_file) as f:
        test_plan = json.load(f)

    print(f"Running {len(test_plan['scenarios'])} scenarios against {test_plan['site_url']}...")
    results = run_all(test_plan)

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    s = results["summary"]
    print(f"\nDone: {s['passed']}/{s['total']} passed, {s['self_healed_count']} self-healed.")
    print(f"Results written to {args.out}")