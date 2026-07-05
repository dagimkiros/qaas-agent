"""
test-gen/generate_test_plan.py
Reads crawl_output.json, sends it to Claude, writes a validated test_plan.json.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python generate_test_plan.py crawl_output.json --out test_plan.json
"""
import argparse
import json
import os
import sys
import anthropic
import jsonschema
from prompts import SYSTEM_PROMPT, build_user_prompt

MODEL = "claude-sonnet-4-6"


def generate(crawl_data: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model=MODEL,
       max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(crawl_data)}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        with open("last_failed_response.txt", "w") as f:
            f.write(cleaned)
        print(f"JSON parse failed. Raw response saved to test-gen/last_failed_response.txt")
        raise


def validate(test_plan: dict, schema_path: str):
    with open(schema_path) as f:
        schema = json.load(f)
    jsonschema.validate(instance=test_plan, schema=schema)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("crawl_file")
    parser.add_argument("--out", default="test_plan.json")
    parser.add_argument("--schema", default="../schemas/test_plan_schema.json")
    args = parser.parse_args()

    with open(args.crawl_file) as f:
        crawl_data = json.load(f)

    print(f"Generating test plan for {crawl_data['site_url']}...")
    test_plan = generate(crawl_data)

    try:
        validate(test_plan, args.schema)
        print("Test plan validates against schema.")
    except jsonschema.ValidationError as e:
        print(f"WARNING: generated test plan failed schema validation: {e.message}", file=sys.stderr)

    with open(args.out, "w") as f:
        json.dump(test_plan, f, indent=2)

    print(f"{len(test_plan.get('scenarios', []))} scenarios written to {args.out}")