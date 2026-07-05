# QaaS Agent

An AI agent that performs automated QA testing on websites. Give it a URL,
and it crawls the site, uses Claude to generate a test plan, runs the tests
in a real browser, automatically recovers when a test breaks due to UI
changes, and produces a plain-English report of what it found.

Built for QA teams and small businesses who want continuous testing
coverage without maintaining a full test suite by hand.

## What it does

1. **Crawls** a website — discovers pages, forms, buttons, and API calls
2. **Generates a test plan** — Claude reasons about what should be tested
   (login flows, form validation, broken links, accessibility basics) and
   writes it as structured test scenarios
3. **Runs the tests** in a real headless browser
4. **Self-heals** — if a page's HTML changes and a test's selector no
   longer matches, the agent automatically tries alternate selectors,
   and as a last resort asks Claude to find the right element on the
   live page, instead of just failing
5. **Triages failures** — classifies each failure as a real bug, a flaky
   test, or the result of the UI simply changing
6. **Reports** — produces a short, plain-English summary of what's
   actually broken, instead of a wall of raw test logs

## Requirements

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install playwright anthropic jsonschema
playwright install chromium

export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Usage

Run the full pipeline against any site with one command:

```bash
./run_pipeline.sh https://example.com 10
```

- First argument: the URL to test
- Second argument (optional): max pages to crawl, default 10

This produces:
- `crawl_output.json` — the site map
- `test_plan.json` — the generated test scenarios
- `results.json` — pass/fail results from the run

**Before pointing this at a real company's website:** open `test_plan.json`
and check for any scenario that fills out or submits a real form (contact,
signup, application). Remove that scenario if you don't want it actually
submitted — the executor will genuinely fill in and click real forms.

## Running one stage at a time

Useful for debugging or inspecting output at each step. All commands below
are run from the project root — no need to `cd` into each folder:

```bash
python crawler/crawl.py https://example.com --out crawl_output.json
python test-gen/generate_test_plan.py crawl_output.json --out test_plan.json
python executor/run_tests.py test_plan.json --out results.json
python triage/triage.py results.json --out triaged_results.json
python report-gen/generate_report.py triaged_results.json --out report.md
```

## Project structure
crawler/        maps a site's pages, forms, and API calls
test-gen/        Claude turns the site map into a structured test plan
executor/        runs the test plan against the live site
self-healing/    recovers automatically when a selector breaks
triage/          classifies failures: real bug / flaky / UI changed
report-gen/      produces the plain-English report
schemas/         the JSON contract every stage reads and writes
api/             FastAPI service wrapping the pipeline
dashboard/       simple web UI to submit a URL and view results
github-app/      webhook to trigger scans automatically on pull requests

## Author

Built by Dagm Kiros.