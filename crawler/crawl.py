"""
crawler/crawl.py
Walks a website with Playwright, discovers pages/forms/API calls,
and outputs a structured JSON map for the test-generation step.

Usage:
    python crawl.py https://example.com --max-pages 25
"""
import argparse
import json
import sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


def is_same_domain(base_url, candidate_url):
    return urlparse(base_url).netloc == urlparse(candidate_url).netloc


def crawl(start_url: str, max_pages: int = 25) -> dict:
    visited = set()
    queue = [start_url]
    pages_data = []
    api_calls_seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_request(request):
            if request.resource_type in ("xhr", "fetch"):
                api_calls_seen.add(f"{request.method} {request.url}")

        page.on("request", on_request)

        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                print(f"  [skip] {url} -> {e}", file=sys.stderr)
                continue

            title = page.title()

            forms = page.eval_on_selector_all(
                "form",
                """forms => forms.map(f => ({
                    action: f.action,
                    method: f.method,
                    fields: Array.from(f.elements).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || null,
                        name: el.name || null,
                        id: el.id || null
                    }))
                }))""",
            )

            buttons = page.eval_on_selector_all(
                "button, a[role=button], [type=submit]",
                """els => els.map(e => ({
                    text: e.innerText?.trim().slice(0, 60) || null,
                    id: e.id || null,
                    testid: e.getAttribute('data-testid') || null
                }))""",
            )

            pages_data.append({
                "url": url,
                "title": title,
                "forms": forms,
                "interactive_elements": buttons,
            })

            print(f"  [crawled] {url}  ({len(forms)} forms, {len(buttons)} interactive elements)")

            links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for link in links:
                if is_same_domain(start_url, link) and link not in visited:
                    clean = link.split("#")[0]
                    if clean not in visited and clean not in queue:
                        queue.append(clean)

        browser.close()

    return {
        "site_url": start_url,
        "pages_found": len(pages_data),
        "pages": pages_data,
        "api_endpoints": sorted(api_calls_seen),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--max-pages", type=int, default=25)
    parser.add_argument("--out", default="crawl_output.json")
    args = parser.parse_args()

    print(f"Crawling {args.url} (max {args.max_pages} pages)...")
    result = crawl(args.url, args.max_pages)

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nDone. {result['pages_found']} pages, {len(result['api_endpoints'])} API calls.")
    print(f"Output written to {args.out}")