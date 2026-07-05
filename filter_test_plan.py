import json

SKIP_IDS = {"TC-003", "TC-004", "TC-005", "TC-006", "TC-007", "TC-008", "TC-009",
            "TC-046", "TC-047", "TC-048"}

with open("test_plan.json") as f:
    plan = json.load(f)

before = len(plan["scenarios"])
plan["scenarios"] = [s for s in plan["scenarios"] if s["id"] not in SKIP_IDS]
after = len(plan["scenarios"])

with open("test_plan.json", "w") as f:
    json.dump(plan, f, indent=2)

print(f"Removed {before - after} scenarios that submit real forms. {after} scenarios remain.")
