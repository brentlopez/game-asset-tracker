#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape Fab (Unreal Engine) Library metadata using Playwright (Python).

Outputs a single `fab_metadata.json` (array of objects):
- fab_id: string (UUID extracted from URL)
- title: string
- description: string (HTML)
- tags: array of strings
- license_text: string
- original_url: string

Navigation strategy:
1) Load storage state from auth.json (manual export)
2) Visit https://www.fab.com/library
3) Infinite scroll: keep scrolling until the number of listing cards (a[href^="/listings/"]) stops increasing or safety limit reached
4) Collect unique listing URLs
5) For each URL: open in a new page, scrape fields, rate-limit between pages

Usage examples:
    python scrape_fab_metadata.py --headless
    python scrape_fab_metadata.py           # headed by default for debugging

Requirements:
    pip install playwright
    playwright install
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Set

from playwright.sync_api import Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE_URL = "https://www.fab.com"
LIBRARY_URL = f"{BASE_URL}/library"
LISTING_LINK_SELECTOR = 'a[href^="/listings/"]'

# Default waits
SCROLL_IDLE_WAIT_MS = 2500
NETWORK_IDLE_TIMEOUT_MS = 5000
PER_PAGE_SLEEP_SEC = 0.5

# Safety limits
MAX_SCROLLS = 50


UUID_RE = re.compile(r"/listings/([0-9a-fA-F-]{36})")


def debug(msg: str) -> None:
    print(msg, file=sys.stderr)


def extract_uuid_from_url(url: str) -> str | None:
    m = UUID_RE.search(url)
    return m.group(1) if m else None


def wait_network_idle_if_possible(page: Page, timeout_ms: int = NETWORK_IDLE_TIMEOUT_MS) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        # Not all SPAs hit networkidle predictably; fallback to a short timeout
        page.wait_for_timeout(min(timeout_ms, 2000))


def infinite_scroll_to_load_all(page: Page, max_scrolls: int = MAX_SCROLLS, idle_wait_ms: int = SCROLL_IDLE_WAIT_MS) -> int:
    last_count = 0
    stable_rounds = 0

    for i in range(max_scrolls):
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        # Give time for new content to load
        wait_network_idle_if_possible(page)
        page.wait_for_timeout(idle_wait_ms)

        # Count listing links
        count = page.locator(LISTING_LINK_SELECTOR).count()
        debug(f"[scroll {i+1}/{max_scrolls}] listings visible: {count}")

        if count <= last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        last_count = count

        # If count hasn't increased for two consecutive rounds, assume we've reached the end
        if stable_rounds >= 2:
            break

    return last_count


def collect_listing_urls(page: Page) -> List[str]:
    # Collect all hrefs starting with /listings/
    hrefs = page.eval_on_selector_all(
        LISTING_LINK_SELECTOR,
        "els => Array.from(new Set(els.map(e => e.getAttribute('href')).filter(Boolean)))",
    )
    # Normalize and make absolute
    urls: List[str] = []
    seen: Set[str] = set()
    for href in hrefs:
        # Some links may include query params or fragments; keep them (useful as original_url)
        if not href.startswith("/listings/"):
            continue
        abs_url = BASE_URL + href
        if abs_url not in seen:
            seen.add(abs_url)
            urls.append(abs_url)
    return urls


def click_overview_and_expand(page: Page) -> None:
    # Try to ensure Overview tab is active
    try:
        overview_tab = page.locator('button[role="tab"]:has-text("Overview")').first
        if overview_tab and overview_tab.is_visible():
            overview_tab.click()
            wait_network_idle_if_possible(page, 2000)
    except Exception:
        pass

    # Try to click "Show more" within the overview panel, if present
    try:
        panel = page.locator('div[role="tabpanel"][id="overview-Panel"]')
        if panel.count() > 0:
            show_more = panel.locator('button:has-text("Show more")')
            if show_more.count() > 0 and show_more.first.is_visible():
                show_more.first.click()
                wait_network_idle_if_possible(page, 2000)
    except Exception:
        pass


def scrape_listing(page: Page, url: str) -> Dict:
    page.goto(url, wait_until="domcontentloaded")
    # Give SPA content a moment
    wait_network_idle_if_possible(page)

    # Title
    title = None
    try:
        h1 = page.locator("h1").first
        if h1 and h1.count() > 0:
            title = (h1.text_content() or "").strip() or None
    except Exception:
        title = None

    # Ensure overview visible and expanded
    click_overview_and_expand(page)

    # Description (inner HTML of the overview panel)
    description_html = None
    try:
        panel = page.locator('div[role="tabpanel"][id="overview-Panel"]')
        if panel and panel.count() > 0:
            # Some sites lazy-render; wait a bit for the content inside
            page.wait_for_timeout(400)
            description_html = panel.evaluate("el => el.innerHTML")  # type: ignore
    except Exception:
        description_html = None

    # Tags (prefer those under a Tags section; fallback to any tag-search links)
    tags: List[str] = []
    try:
        # First attempt: scoped under a section headed by h2:has-text("Tags")
        tag_links = []
        try:
            tags_header = page.locator('h2:has-text("Tags")').first
            if tags_header and tags_header.count() > 0:
                # Search forward from the header for anchors containing tag search
                tag_links = tags_header.locator('xpath=following::*//a[contains(@href, "/search?tags=")]').all()
        except Exception:
            tag_links = []

        if not tag_links:
            # Fallback: any tag search links on the page
            tag_links = page.locator('a[href*="/search?tags="]').all()

        seen_tag: Set[str] = set()
        for a in tag_links:
            txt = (a.text_content() or "").strip()
            if txt and txt not in seen_tag:
                seen_tag.add(txt)
                tags.append(txt)
    except Exception:
        tags = []

    # License text
    license_text = None
    try:
        lic = page.locator('a[href="/eula"]').first
        if lic and lic.count() > 0:
            license_text = (lic.text_content() or "").strip() or None
    except Exception:
        license_text = None

    # fab_id (UUID from URL)
    fab_id = extract_uuid_from_url(url)

    return {
        "fab_id": fab_id,
        "title": title,
        "description": description_html,
        "tags": tags,
        "license_text": license_text,
        "original_url": url,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Fab Library metadata → fab_metadata.json")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (default: False)")
    parser.add_argument("--max-scrolls", type=int, default=MAX_SCROLLS, help="Safety limit for infinite scroll attempts (default: 50)")
    parser.add_argument("--out", type=str, default="fab_metadata.json", help="Output JSON filename (default: fab_metadata.json)")
    parser.add_argument("--clear-cache", action="store_true", help="Delete existing output file before scraping")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    auth_file = script_dir / "auth.json"
    if not auth_file.exists():
        print(f"ERROR: auth.json not found at {auth_file}", file=sys.stderr)
        return 1

    out_path = script_dir / args.out
    if args.clear_cache and out_path.exists():
        try:
            out_path.unlink()
            debug(f"Cleared cache file: {out_path}")
        except Exception as e:
            print(f"WARNING: Failed to clear cache file {out_path}: {e}", file=sys.stderr)

    with sync_playwright() as p:
        browser: Browser
        # Use Chromium by default for compatibility; switch to Firefox/WebKit if needed
        browser = p.chromium.launch(headless=args.headless)
        try:
            context = browser.new_context(storage_state=str(auth_file))
        except Exception as e:
            browser.close()
            print(f"ERROR: Failed to load storage state from auth.json: {e}", file=sys.stderr)
            return 1

        page = context.new_page()
        debug(f"Navigating to {LIBRARY_URL} …")
        page.goto(LIBRARY_URL, wait_until="domcontentloaded")
        wait_network_idle_if_possible(page)

        debug("Beginning infinite scroll to load all listings …")
        final_count = infinite_scroll_to_load_all(page, max_scrolls=args.max_scrolls)
        debug(f"Finished scrolling. Listings detected: {final_count}")

        urls = collect_listing_urls(page)
        if not urls:
            print("No listing URLs found. Exiting.", file=sys.stderr)
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            return 1

        debug(f"Collected {len(urls)} unique listing URLs.")

        results: List[Dict] = []
        total = len(urls)
        for idx, url in enumerate(urls, start=1):
            # New page per listing (reuse same context for auth/cookies)
            listing_page = context.new_page()
            try:
                print(f"Scraping {idx}/{total}: {url}")
                data = scrape_listing(listing_page, url)
                # Fallback: if title is missing, try to read document.title
                if not data.get("title"):
                    try:
                        data["title"] = (listing_page.title() or "").strip() or None
                    except Exception:
                        pass
                results.append(data)
            except Exception as e:
                print(f"WARNING: Failed to scrape {url}: {e}", file=sys.stderr)
            finally:
                try:
                    listing_page.close()
                except Exception:
                    pass
                time.sleep(PER_PAGE_SLEEP_SEC)

        # Write output JSON (array)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    print(f"Wrote {len(results)} records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
