#!/bin/bash
set -e  # stop immediately if any step fails

URL="$1"
MAX_PAGES="${2:-10}"

if [ -z "$URL" ]; then
  echo "Usage: ./run_pipeline.sh <url> [max_pages]"
  exit 1
fi

echo "== Step 1: Crawling $URL =="
cd crawler
python crawl.py "$URL" --max-pages "$MAX_PAGES" --out ../crawl_output.json
cd ..

echo "== Step 2: Generating test plan =="
cd test-gen
python generate_test_plan.py ../crawl_output.json --out ../test_plan.json
cd ..

echo "== Step 3: Running tests =="
cd executor
python run_tests.py ../test_plan.json --out ../results.json
cd ..

echo "== Done. Review test_plan.json before trusting results on a real site. =="