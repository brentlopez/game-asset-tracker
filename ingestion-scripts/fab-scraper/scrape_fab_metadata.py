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
import fcntl
import json
import re
import sys
import time
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
import random
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Iterable

from playwright.sync_api import Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright, Route, Request

BASE_URL = "https://www.fab.com"
LIBRARY_URL = f"{BASE_URL}/library"
LISTING_LINK_SELECTOR = 'a[href^="/listings/"]'

# Default waits
SCROLL_IDLE_WAIT_MS = 2500
NETWORK_IDLE_TIMEOUT_MS = 5000
PER_PAGE_SLEEP_SEC = 0.5

# Safety limits
MAX_SCROLLS = 50

# Incremental scroll tuning
SCROLL_STEP_PX = 1200
SCROLL_STEPS_PER_ROUND = 8
STABLE_ROUNDS_THRESHOLD = 2

# Captcha detection
CAPTCHA_TITLE_KEYWORDS = ["One more step", "Just a moment", "verification", "captcha", "Checking your browser"]
CAPTCHA_WAIT_TIMEOUT_SEC = 120


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


def infinite_scroll_to_load_all(
    page: Page,
    max_scrolls: int = MAX_SCROLLS,
    idle_wait_ms: int = SCROLL_IDLE_WAIT_MS,
    step_px: int = SCROLL_STEP_PX,
    steps_per_round: int = SCROLL_STEPS_PER_ROUND,
    stable_rounds_threshold: int = STABLE_ROUNDS_THRESHOLD,
) -> int:
    last_count = 0
    last_height = page.evaluate("() => document.body.scrollHeight") or 0
    stable_rounds = 0

    for i in range(max_scrolls):
        # Incremental wheel scrolling to trigger lazy loaders
        for _ in range(steps_per_round):
            try:
                page.mouse.wheel(0, step_px)
            except Exception:
                # Fallback to JS scroll if wheel fails
                page.evaluate("(dy)=>{window.scrollBy(0, dy)}", step_px)
            page.wait_for_timeout(200)

        # Ensure we've hit the bottom once this round
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Attempt to wait for more items to appear
        try:
            page.wait_for_function(
                "({ sel, prev }) => document.querySelectorAll(sel).length > prev",
                arg={ "sel": LISTING_LINK_SELECTOR, "prev": last_count },
                timeout=3000,
            )
        except PlaywrightTimeoutError:
            pass

        # Give network some time and then idle wait
        wait_network_idle_if_possible(page)
        page.wait_for_timeout(idle_wait_ms)

        # Check counts and document height
        count = page.locator(LISTING_LINK_SELECTOR).count()
        height = page.evaluate("() => document.body.scrollHeight") or 0
        debug(f"[scroll {i+1}/{max_scrolls}] listings: {count} (Δ{count - last_count}), height: {height} (Δ{height - last_height})")

        progressed = (count > last_count) or (height > last_height)
        if not progressed:
            stable_rounds += 1
        else:
            stable_rounds = 0

        last_count = count
        last_height = height

        if stable_rounds >= stable_rounds_threshold:
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


def detect_captcha(page: Page) -> bool:
    """Check if the current page is showing a captcha/verification challenge."""
    # Strategy 1: Check page title
    try:
        title = (page.title() or "").lower()
        for keyword in CAPTCHA_TITLE_KEYWORDS:
            if keyword.lower() in title:
                debug(f"Captcha detected via title: '{title}'")
                return True
    except Exception:
        pass
    
    # Strategy 2: Check URL for common captcha/challenge paths
    try:
        url = page.url
        if any(pattern in url.lower() for pattern in ["challenge", "captcha", "verify", "cdn-cgi/challenge"]):
            debug(f"Captcha detected via URL: '{url}'")
            return True
    except Exception:
        pass
    
    # Strategy 3: Check for common captcha DOM elements
    try:
        # Cloudflare challenge
        if page.locator("#challenge-form").count() > 0:
            debug("Captcha detected via #challenge-form")
            return True
        if page.locator("#cf-challenge-running").count() > 0:
            debug("Captcha detected via #cf-challenge-running")
            return True
        # Generic captcha iframes
        if page.locator("iframe[src*='captcha']").count() > 0:
            debug("Captcha detected via captcha iframe")
            return True
        if page.locator("iframe[src*='recaptcha']").count() > 0:
            debug("Captcha detected via recaptcha iframe")
            return True
        # Check for h1/h2 with verification text
        headings = page.locator("h1, h2").all_text_contents()
        for heading in headings:
            heading_lower = heading.lower()
            if any(kw in heading_lower for kw in ["verification", "checking your browser", "one more step", "just a moment"]):
                debug(f"Captcha detected via heading: '{heading}'")
                return True
    except Exception as e:
        debug(f"Error checking captcha DOM elements: {e}")
        pass
    
    return False


def wait_for_captcha_solve(page: Page, timeout_sec: int = CAPTCHA_WAIT_TIMEOUT_SEC) -> bool:
    """Wait for user to manually solve captcha. Returns True if solved, False if timeout."""
    print("\n" + "="*60, file=sys.stderr)
    print("⚠️  CAPTCHA DETECTED", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Please solve the captcha in the browser window within {timeout_sec} seconds.", file=sys.stderr)
    print("The script will automatically continue once the captcha is solved.", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)
    
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        if not detect_captcha(page):
            print("✓ Captcha solved! Continuing...", file=sys.stderr)
            page.wait_for_timeout(1000)  # Brief pause after solve
            return True
        time.sleep(2)
    
    print("✗ Captcha solve timeout. Skipping this page.", file=sys.stderr)
    return False


def scrape_listing(page: Page, url: str, skip_on_captcha: bool = False) -> Dict | None:
    page.goto(url, wait_until="domcontentloaded")
    # Give SPA content a moment
    wait_network_idle_if_possible(page)

    # Check for captcha
    if detect_captcha(page):
        if skip_on_captcha:
            debug(f"Captcha detected on {url}, skipping due to --skip-on-captcha")
            return None
        else:
            solved = wait_for_captcha_solve(page)
            if not solved:
                debug(f"Captcha not solved for {url}, skipping")
                return None

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


def load_existing_metadata(path: Path) -> tuple[List[Dict], Set[str]]:
    """Load existing metadata and return (records, fab_ids_seen)."""
    if not path.exists():
        return [], set()
    
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            debug(f"Warning: {path} does not contain a JSON array, treating as empty")
            return [], set()
        
        fab_ids = {record.get("fab_id") for record in data if record.get("fab_id")}
        debug(f"Loaded {len(data)} existing records ({len(fab_ids)} unique fab_ids) from {path}")
        return data, fab_ids
    except Exception as e:
        debug(f"Warning: Could not load existing metadata from {path}: {e}")
        return [], set()


# ---------------------------- Request Blocking ----------------------------
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
BLOCKED_ANALYTICS_SUBSTRINGS = [
    "googletagmanager.com",
    "google-analytics.com",
    "doubleclick.net",
    "facebook.net",
    "segment.com",
    "mixpanel.com",
    "hotjar.com",
    "clarity.ms",
    "sentry.io",
]

def _should_block_request(req: Request, block_heavy: bool) -> bool:
    if not block_heavy:
        return False
    try:
        if req.resource_type in BLOCKED_RESOURCE_TYPES:
            return True
        url = (req.url or "").lower()
        return any(s in url for s in BLOCKED_ANALYTICS_SUBSTRINGS)
    except Exception:
        return False


def setup_request_blocking(context, block_heavy: bool) -> None:
    if not block_heavy:
        return
    try:
        def handler(route: Route, request: Request):
            try:
                if _should_block_request(request, block_heavy):
                    return route.abort()
                return route.continue_()
            except Exception:
                # In case of any issue, continue the request
                try:
                    route.continue_()
                except Exception:
                    pass
        context.route("**/*", handler)
    except Exception:
        pass


# Global lock for thread-safe file writes
_file_write_lock = threading.Lock()

def save_metadata_incrementally(path: Path, records: List[Dict]) -> None:
    """Save metadata to JSON file with thread-safe locking."""
    with _file_write_lock:
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"ERROR: Failed to save metadata to {path}: {e}", file=sys.stderr)

def append_metadata_record(path: Path, record: Dict) -> None:
    """Append a single record to metadata file with thread-safe locking."""
    with _file_write_lock:
        try:
            # Load existing data
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    data = []
            else:
                data = []
            
            # Append new record
            data.append(record)
            
            # Save back
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"ERROR: Failed to append metadata to {path}: {e}", file=sys.stderr)


UA_POOL = [
    # A small, realistic UA pool (Chromium on macOS/Windows)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

LOCALE_POOL = ["en-US", "en-GB", "en-CA"]
TIMEZONE_POOL = ["America/New_York", "America/Los_Angeles", "America/Chicago", "America/Denver"]

def _context_options(randomize_ua: bool) -> dict:
    opts: dict = {}
    if randomize_ua:
        ua = random.choice(UA_POOL)
        opts["user_agent"] = ua
        # Jitter viewport slightly
        w = 1200 + random.randint(-40, 40)
        h = 800 + random.randint(-30, 30)
        opts["viewport"] = {"width": max(1024, w), "height": max(700, h)}
        # Randomize locale and timezone to vary fingerprint
        opts["locale"] = random.choice(LOCALE_POOL)
        opts["timezone_id"] = random.choice(TIMEZONE_POOL)
    return opts


def _per_page_sleep(args, page_index: int):
    ms = random.randint(max(0, args.sleep_min_ms), max(args.sleep_min_ms, args.sleep_max_ms))
    time.sleep(ms / 1000.0)
    if args.burst_size > 0 and (page_index % args.burst_size == 0):
        time.sleep(max(0, args.burst_sleep_ms) / 1000.0)


class TrafficMeter:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._total = 0
        self._count = 0
        self._by_type: Dict[str, int] = {}
        self._proxy_routed = 0  # bytes that would go through proxy
        self._direct = 0  # bytes that would go direct
        self._by_routing: Dict[str, int] = {}  # breakdown by routing decision
        self._lock = None  # single-threaded in worker; kept for future use

    def attach(self, context):
        if not self.enabled:
            return
        try:
            def on_response(resp):
                try:
                    # Try to get actual body size by reading the response
                    size = 0
                    try:
                        body = resp.body()
                        size = len(body) if body else 0
                    except Exception:
                        # Fallback to Content-Length header if body() fails
                        headers = resp.headers or {}
                        clen = headers.get("content-length")
                        if clen and str(clen).isdigit():
                            size = int(clen)
                    
                    if size > 0:
                        self._total += size
                        self._count += 1
                        rtype = getattr(resp.request, "resource_type", None) or "unknown"
                        self._by_type[rtype] = self._by_type.get(rtype, 0) + size
                        
                        # Determine if this would be routed through proxy
                        url = resp.url.lower()
                        needs_proxy = self._should_route_through_proxy(rtype, url)
                        
                        if needs_proxy:
                            self._proxy_routed += size
                            self._by_routing[f"proxy_{rtype}"] = self._by_routing.get(f"proxy_{rtype}", 0) + size
                        else:
                            self._direct += size
                            self._by_routing[f"direct_{rtype}"] = self._by_routing.get(f"direct_{rtype}", 0) + size
                except Exception:
                    pass
            context.on("response", on_response)
        except Exception:
            pass
    
    def _should_route_through_proxy(self, resource_type: str, url: str) -> bool:
        """Determine if a request should be routed through proxy.
        
        Strategy: Only route requests that need authentication or geo-location.
        - document (HTML): YES (needs auth/geo)
        - xhr/fetch (API calls): YES (likely needs auth)
        - script/stylesheet/font/image/media: NO (static CDN assets)
        """
        # Route through proxy: document HTML and API calls
        if resource_type in {"document", "xhr", "fetch"}:
            return True
        
        # Route through proxy if it's from the main domain (not CDN)
        if "fab.com" in url and resource_type in {"script", "stylesheet"}:
            # Check if it's from the main site or a CDN
            if any(cdn in url for cdn in ["cdn", "static", "assets", "cloudfront", "akamai"]):
                return False  # CDN assets go direct
            return True  # Main site assets through proxy
        
        # Everything else goes direct (images, fonts, third-party scripts)
        return False

    def snapshot_and_reset(self) -> Dict:
        data = {
            "total_bytes": self._total, 
            "requests": self._count, 
            "by_type": dict(self._by_type),
            "proxy_routed_bytes": self._proxy_routed,
            "direct_bytes": self._direct,
            "by_routing": dict(self._by_routing),
            "proxy_percentage": round(100 * self._proxy_routed / self._total, 1) if self._total > 0 else 0
        }
        self._total = 0
        self._count = 0
        self._by_type = {}
        self._proxy_routed = 0
        self._direct = 0
        self._by_routing = {}
        return data


def _append_jsonl(path: Path, record: Dict) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        print(f"WARNING: Failed to append to {path}: {e}", file=sys.stderr)


def _proxy_to_playwright(proxy_url: str | None) -> dict | None:
    if not proxy_url:
        return None
    try:
        u = urllib.parse.urlparse(proxy_url)
        server = f"{u.scheme}://{u.hostname}:{u.port}" if u.hostname and u.port else proxy_url
        pd = {"server": server}
        if u.username:
            pd["username"] = urllib.parse.unquote(u.username)
        if u.password:
            pd["password"] = urllib.parse.unquote(u.password)
        return pd
    except Exception:
        return {"server": proxy_url}


def _scrape_url_process_worker(url: str, idx: int, total: int, 
                                auth_file_path: str, headless: bool, 
                                skip_on_captcha: bool, block_heavy: bool, out_path: str,
                                *, randomize_ua: bool = False, auth_on_listings: bool = False,
                                captcha_retry: bool = False, sleep_cfg: dict | None = None,
                                proxy_url: str | None = None,
                                measure_bytes: bool = False, measure_report_path: str | None = None) -> bool:
    """Legacy per-URL worker: launches a browser per page."""
    
    """Worker function to scrape a single URL in a separate process.
    
    Returns True if successful, False otherwise.
    """
    with sync_playwright() as p:
        per_page_browser = None
        per_page_context = None
        listing_page = None
        try:
            print(f"Scraping {idx}/{total}: {url}")
            # Launch fresh browser for this worker
            pw_proxy = _proxy_to_playwright(proxy_url)
            per_page_browser = p.chromium.launch(
                headless=headless, 
                proxy=pw_proxy,
                args=[
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            try:
                ctx_kwargs = _context_options(randomize_ua)
                if auth_on_listings:
                    ctx_kwargs["storage_state"] = auth_file_path
                per_page_context = per_page_browser.new_context(**ctx_kwargs)
            except Exception as e:
                debug(f"Failed to create context: {e}")
                return False
            
            # Optional: block heavy resources in worker
            try:
                setup_request_blocking(per_page_context, block_heavy)
            except Exception:
                pass
            
            meter = TrafficMeter(enabled=measure_bytes)
            meter.attach(per_page_context)

            listing_page = per_page_context.new_page()
            data = scrape_listing(listing_page, url, skip_on_captcha=skip_on_captcha)
            if data is None and captcha_retry:
                # backoff, swap UA, retry once
                time.sleep(2.0)
                try:
                    listing_page.close()
                except Exception:
                    pass
                try:
                    per_page_context.close()
                except Exception:
                    pass
                try:
                    ctx_kwargs = _context_options(True)
                    if auth_on_listings:
                        ctx_kwargs["storage_state"] = auth_file_path
                    per_page_context = per_page_browser.new_context(**ctx_kwargs)
                    setup_request_blocking(per_page_context, block_heavy)
                    listing_page = per_page_context.new_page()
                    data = scrape_listing(listing_page, url, skip_on_captcha=skip_on_captcha)
                except Exception:
                    data = None
            if data is None:
                debug(f"Skipped {url} (captcha or error)")
                # still record bytes for this attempt if measuring
                if measure_bytes and measure_report_path:
                    snap = meter.snapshot_and_reset()
                    _append_jsonl(Path(measure_report_path), {
                        "ts": datetime.utcnow().isoformat()+"Z",
                        "url": url,
                        "idx": idx,
                        "total": total,
                        "bytes": snap.get("total_bytes", 0),
                        "requests": snap.get("requests", 0),
                        "by_type": snap.get("by_type", {}),
                        "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                        "direct_bytes": snap.get("direct_bytes", 0),
                        "by_routing": snap.get("by_routing", {}),
                        "proxy_percentage": snap.get("proxy_percentage", 0),
                        "status": "skipped"
                    })
                return False
            
            # Fallback: if title is missing, try to read document.title
            if not data.get("title"):
                try:
                    data["title"] = (listing_page.title() or "").strip() or None
                except Exception:
                    pass
            
            # Write to file with file locking (cross-process safe)
            out_path_obj = Path(out_path)
            try:
                with open(out_path_obj, "r+" if out_path_obj.exists() else "w+", encoding="utf-8") as f:
                    # Acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        # Read existing data
                        f.seek(0)
                        content = f.read()
                        if content:
                            existing_data = json.loads(content)
                            if not isinstance(existing_data, list):
                                existing_data = []
                        else:
                            existing_data = []
                        
                        # Append new record
                        existing_data.append(data)
                        
                        # Write back
                        f.seek(0)
                        f.truncate()
                        json.dump(existing_data, f, ensure_ascii=False, indent=2)
                    finally:
                        # Release lock
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception as e:
                print(f"ERROR: Failed to save record for {url}: {e}", file=sys.stderr)
                return False
            
            return True
        except Exception as e:
            print(f"WARNING: Failed to scrape {url}: {e}", file=sys.stderr)
            return False
        finally:
            # Clean up per-worker browser/context
            try:
                if listing_page:
                    listing_page.close()
                if per_page_context:
                    per_page_context.close()
                if per_page_browser:
                    per_page_browser.close()
            except Exception:
                pass
            time.sleep(PER_PAGE_SLEEP_SEC)


def _scrape_urls_process_worker(urls: List[str], start_index: int, total: int,
                                auth_file_path: str, headless: bool,
                                skip_on_captcha: bool, block_heavy: bool,
                                out_path: str,
                                *, randomize_ua: bool = False, auth_on_listings: bool = False,
                                captcha_retry: bool = False, sleep_min_ms: int = 300,
                                sleep_max_ms: int = 800, burst_size: int = 5,
                                burst_sleep_ms: int = 3000,
                                proxy_url: str | None = None,
                                measure_bytes: bool = False, measure_report_path: str | None = None) -> int:
    """Chunk worker: reuse one browser, new incognito context per URL.
    Returns the number of successfully written records.
    """
    written = 0
    with sync_playwright() as p:
        pw_proxy = _proxy_to_playwright(proxy_url)
        browser = p.chromium.launch(
            headless=headless, 
            proxy=pw_proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        try:
            for offset, url in enumerate(urls, start=0):
                idx = start_index + offset
                print(f"Scraping {idx}/{total}: {url}")
                context = None
                page = None
                try:
                    ctx_kwargs = _context_options(randomize_ua)
                    if auth_on_listings:
                        ctx_kwargs["storage_state"] = auth_file_path
                    context = browser.new_context(**ctx_kwargs)
                    # Optional request blocking
                    setup_request_blocking(context, block_heavy)
                    meter = TrafficMeter(enabled=measure_bytes)
                    meter.attach(context)
                    page = context.new_page()
                    data = scrape_listing(page, url, skip_on_captcha=skip_on_captcha)
                    if data is None and captcha_retry:
                        # backoff and swap UA, retry once
                        time.sleep(2.0)
                        try:
                            page.close()
                        except Exception:
                            pass
                        try:
                            context.close()
                        except Exception:
                            pass
                        ctx_kwargs = _context_options(True)
                        if auth_on_listings:
                            ctx_kwargs["storage_state"] = auth_file_path
                        context = browser.new_context(**ctx_kwargs)
                        setup_request_blocking(context, block_heavy)
                        # Create a fresh meter for the retry
                        meter = TrafficMeter(enabled=measure_bytes)
                        meter.attach(context)
                        page = context.new_page()
                        data = scrape_listing(page, url, skip_on_captcha=skip_on_captcha)
                        if measure_bytes and measure_report_path and data is None:
                            snap = meter.snapshot_and_reset()
                            _append_jsonl(Path(measure_report_path), {
                                "ts": datetime.utcnow().isoformat()+"Z",
                                "url": url,
                                "idx": idx,
                                "total": total,
                                "bytes": snap.get("total_bytes", 0),
                                "requests": snap.get("requests", 0),
                                "by_type": snap.get("by_type", {}),
                                "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                                "direct_bytes": snap.get("direct_bytes", 0),
                                "by_routing": snap.get("by_routing", {}),
                                "proxy_percentage": snap.get("proxy_percentage", 0),
                                "status": "skipped"
                            })
                    if data is None:
                        debug(f"Skipped {url} (captcha or error)")
                        continue
                    # Fallback: add title if missing
                    if not data.get("title"):
                        try:
                            data["title"] = (page.title() or "").strip() or None
                        except Exception:
                            pass
                    append_metadata_record(Path(out_path), data)
                    written += 1
                    debug(f"Saved progress: {idx}/{total} completed")
                    if measure_bytes and measure_report_path:
                        snap = meter.snapshot_and_reset()
                        _append_jsonl(Path(measure_report_path), {
                            "ts": datetime.utcnow().isoformat()+"Z",
                            "url": url,
                            "idx": idx,
                            "total": total,
                            "bytes": snap.get("total_bytes", 0),
                            "requests": snap.get("requests", 0),
                            "by_type": snap.get("by_type", {}),
                            "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                            "direct_bytes": snap.get("direct_bytes", 0),
                            "by_routing": snap.get("by_routing", {}),
                            "proxy_percentage": snap.get("proxy_percentage", 0),
                            "status": "ok"
                        })
                    # Cadence shaping
                    ms = random.randint(max(0, sleep_min_ms), max(sleep_min_ms, sleep_max_ms))
                    time.sleep(ms/1000.0)
                    if burst_size > 0 and (idx % burst_size == 0):
                        time.sleep(max(0, burst_sleep_ms)/1000.0)
                except Exception as e:
                    print(f"WARNING: Failed to scrape {url}: {e}", file=sys.stderr)
                finally:
                    try:
                        if page:
                            page.close()
                        if context:
                            context.close()
                    except Exception:
                        pass
                    time.sleep(PER_PAGE_SLEEP_SEC)
        finally:
            try:
                browser.close()
            except Exception:
                pass
    return written

def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Fab Library metadata → fab_metadata.json")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (default: False)")
    parser.add_argument("--max-scrolls", type=int, default=MAX_SCROLLS, help="Safety limit for infinite scroll attempts (default: 50)")
    parser.add_argument("--out", type=str, default="fab_metadata.json", help="Output JSON filename (default: fab_metadata.json)")
    parser.add_argument("--clear-cache", action="store_true", help="Delete existing output file before scraping")
    parser.add_argument("--scroll-step", type=int, default=SCROLL_STEP_PX, help="Pixels per incremental scroll (default: 1200)")
    parser.add_argument("--scroll-steps", type=int, default=SCROLL_STEPS_PER_ROUND, help="Incremental scroll steps per round (default: 8)")
    parser.add_argument("--test-scroll", action="store_true", help="Only test infinite scroll on the library page and report counts; do not scrape listings or write output")
    parser.add_argument("--use-url-file", type=str, default="fab_library_urls.json", help="Load URLs from this JSON file instead of scraping the library page (default: fab_library_urls.json)")
    parser.add_argument("--skip-library-scrape", action="store_true", help="Skip library page scraping and use URLs from --use-url-file instead")
    parser.add_argument("--skip-on-captcha", action="store_true", help="Skip pages with captchas instead of waiting for manual solve")
    parser.add_argument("--force-rescrape", action="store_true", help="Rescrape all URLs even if fab_id already exists in output file")
    parser.add_argument("--new-browser-per-page", action="store_true", help="Open each URL in a fresh browser instance (avoids captchas on subsequent pages)")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel browser instances to run (default: 1 = sequential)")
    parser.add_argument("--block-heavy", action="store_true", help="Block heavy resources (images, media, fonts) and common analytics domains to speed up loads")
    parser.add_argument("--reuse-browser", action="store_true", help="Reuse a single browser per worker and create a fresh incognito context per URL (faster, reduces captchas vs new browser per page)")

    # Anti-captcha mitigations
    parser.add_argument("--auth-on-listings", action="store_true", help="Use auth storage when scraping listing pages (default: off)")
    parser.add_argument("--randomize-ua", action="store_true", help="Randomize User-Agent and viewport per context")
    parser.add_argument("--sleep-min-ms", type=int, default=300, help="Minimum per-page sleep in ms (default: 300)")
    parser.add_argument("--sleep-max-ms", type=int, default=800, help="Maximum per-page sleep in ms (default: 800)")
    parser.add_argument("--burst-size", type=int, default=5, help="After this many pages, insert a longer burst sleep (default: 5)")
    parser.add_argument("--burst-sleep-ms", type=int, default=3000, help="Burst sleep duration in ms (default: 3000)")
    parser.add_argument("--captcha-retry", action="store_true", help="If a listing triggers captcha (skipped), retry once with backoff and UA switch")

    # Traffic metering
    parser.add_argument("--measure-bytes", action="store_true", help="Measure total bytes per listing (based on response Content-Length) and write JSONL report")
    parser.add_argument("--measure-report", type=str, default="fab_bandwidth_report.jsonl", help="Path to JSONL report file (default: fab_bandwidth_report.jsonl)")

    # Proxies
    parser.add_argument("--proxy", action="append", default=[], help="Proxy server URL, e.g. http://user:pass@host:port (can be repeated)")
    parser.add_argument("--proxy-list", type=str, help="Path to file with one proxy URL per line")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    auth_file = script_dir / "auth.json"
    if not auth_file.exists():
        print(f"ERROR: auth.json not found at {auth_file}", file=sys.stderr)
        return 1

    out_path = script_dir / args.out
    
    # Load existing metadata or clear if requested
    if args.clear_cache and out_path.exists():
        try:
            out_path.unlink()
            debug(f"Cleared cache file: {out_path}")
        except Exception as e:
            print(f"WARNING: Failed to clear cache file {out_path}: {e}", file=sys.stderr)
    
    results, scraped_fab_ids = load_existing_metadata(out_path)

    with sync_playwright() as p:
        browser: Browser
        # Use Chromium by default for compatibility; switch to Firefox/WebKit if needed
        browser = p.chromium.launch(
            headless=args.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        try:
            context = browser.new_context(storage_state=str(auth_file))
            # Optional: block heavy resources
            setup_request_blocking(context, args.block_heavy)
        except Exception as e:
            browser.close()
            print(f"ERROR: Failed to load storage state from auth.json: {e}", file=sys.stderr)
            return 1

        page = context.new_page()
        
        urls: List[str] = []
        if args.skip_library_scrape:
            # Load URLs from JSON file instead of scraping
            url_file_path = script_dir / args.use_url_file
            if not url_file_path.exists():
                print(f"ERROR: URL file not found at {url_file_path}", file=sys.stderr)
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass
                return 1
            
            try:
                with url_file_path.open("r", encoding="utf-8") as f:
                    urls = json.load(f)
                if not isinstance(urls, list):
                    print(f"ERROR: {url_file_path} must contain a JSON array of URLs", file=sys.stderr)
                    return 1
                debug(f"Loaded {len(urls)} URLs from {url_file_path}")
            except Exception as e:
                print(f"ERROR: Failed to load URL file {url_file_path}: {e}", file=sys.stderr)
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass
                return 1
        else:
            # Original behavior: scrape library page
            debug(f"Navigating to {LIBRARY_URL} …")
            page.goto(LIBRARY_URL, wait_until="domcontentloaded")
            wait_network_idle_if_possible(page)

            debug("Beginning infinite scroll to load all listings …")
            final_count = infinite_scroll_to_load_all(
                page,
                max_scrolls=args.max_scrolls,
                step_px=args.scroll_step,
                steps_per_round=args.scroll_steps,
            )
            debug(f"Finished scrolling. Listings detected: {final_count}")

            urls = collect_listing_urls(page)
        if args.test_scroll:
            # Report counts and exit without scraping
            print(f"Test-scroll complete. Visible listing links: {final_count}. Unique URLs collected: {len(urls)}")
            if urls:
                sample = urls[:10]
                print("Sample URLs:")
                for u in sample:
                    print(f" - {u}")
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            return 0

        if not urls:
            print("No listing URLs found. Exiting.", file=sys.stderr)
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            return 1

        debug(f"Collected {len(urls)} unique listing URLs.")

        # Filter out already-scraped URLs if not forcing rescrape
        if not args.force_rescrape:
            original_count = len(urls)
            urls_to_scrape = []
            for url in urls:
                fab_id = extract_uuid_from_url(url)
                if fab_id and fab_id in scraped_fab_ids:
                    continue
                urls_to_scrape.append(url)
            
            skipped = original_count - len(urls_to_scrape)
            if skipped > 0:
                debug(f"Skipping {skipped} already-scraped URLs. {len(urls_to_scrape)} remaining.")
            urls = urls_to_scrape
        
        if not urls:
            print(f"All URLs already scraped. {len(results)} total records in {out_path}")
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            return 0

        total = len(urls)
        
        # Load proxies if provided
        proxies: List[str] = []
        if args.proxy_list:
            try:
                with open(args.proxy_list, "r", encoding="utf-8") as pf:
                    for line in pf:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        proxies.append(line)
            except Exception as e:
                print(f"WARNING: Failed to read proxy list: {e}", file=sys.stderr)
        if args.proxy:
            proxies.extend(args.proxy)
        proxies = [p for p in proxies if p]

        # Parallel scraping mode
        if args.parallel > 1:
            debug(f"Starting parallel scraping with {args.parallel} workers...")
            
            # Close initial browser/context since workers will create their own
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            
            def chunked(seq: List[str], k: int) -> List[List[str]]:
                n = len(seq)
                if k <= 0:
                    return [seq]
                size = max(1, (n + k - 1) // k)
                return [seq[i:i+size] for i in range(0, n, size)]
            
            # If reuse-browser, shard URLs into chunks per worker
            if args.reuse_browser:
                if args.new_browser_per_page:
                    print("NOTE: --reuse-browser overrides --new-browser-per-page in parallel mode", file=sys.stderr)
                url_chunks = chunked(urls, args.parallel)
                with ProcessPoolExecutor(max_workers=args.parallel) as executor:
                    futures = []
                    url_offset = 0
                    for chunk_idx, chunk in enumerate(url_chunks):
                        proxy_url = proxies[chunk_idx % len(proxies)] if proxies else None
                        futures.append(executor.submit(
                            _scrape_urls_process_worker,
                            chunk,
                            url_offset + 1,  # 1-indexed start position for this chunk
                            total,
                            str(auth_file),
                            args.headless,
                            args.skip_on_captcha,
                            args.block_heavy,
                            str(out_path),
                            randomize_ua=args.randomize_ua,
                            auth_on_listings=args.auth_on_listings,
                            captcha_retry=args.captcha_retry,
                            sleep_min_ms=args.sleep_min_ms,
                            sleep_max_ms=args.sleep_max_ms,
                            burst_size=args.burst_size,
                            burst_sleep_ms=args.burst_sleep_ms,
                            proxy_url=proxy_url,
                            measure_bytes=args.measure_bytes,
                            measure_report_path=args.measure_report
                        ))
                        url_offset += len(chunk)  # Move offset forward for next chunk
                    completed = 0
                    for fut in as_completed(futures):
                        try:
                            cnt = fut.result()
                            completed += cnt
                            debug(f"Saved progress: {completed}/{total} completed")
                        except Exception as e:
                            debug(f"Worker failed: {e}")
            else:
                # Per-URL process (old behavior)
                with ProcessPoolExecutor(max_workers=args.parallel) as executor:
                    future_to_url = {}
                    for idx, url in enumerate(urls, start=1):
                        proxy_url = proxies[(idx-1) % len(proxies)] if proxies else None
                        fut = executor.submit(_scrape_url_process_worker, 
                                              url, idx, total, 
                                              str(auth_file), args.headless, 
                                              args.skip_on_captcha, args.block_heavy, str(out_path),
                                              randomize_ua=args.randomize_ua,
                                              auth_on_listings=args.auth_on_listings,
                                              captcha_retry=args.captcha_retry,
                                              proxy_url=proxy_url,
                                              measure_bytes=args.measure_bytes,
                                              measure_report_path=args.measure_report)
                        future_to_url[fut] = (url, idx)
                    completed = 0
                    for future in as_completed(future_to_url):
                        try:
                            ok = future.result()
                            if ok:
                                completed += 1
                                debug(f"Saved progress: {completed}/{total} completed")
                        except Exception as e:
                            debug(f"Worker failed: {e}")
        
        elif args.new_browser_per_page:
            # Close initial browser/context since we'll open fresh ones per URL
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            
            # Scrape each URL in a fresh browser instance
            for idx, url in enumerate(urls, start=1):
                per_page_browser = None
                per_page_context = None
                listing_page = None
                try:
                    print(f"Scraping {idx}/{total}: {url}")
                    # Launch fresh browser
                    per_page_browser = p.chromium.launch(
                        headless=args.headless,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                        ]
                    )
                    try:
                        ctx_kwargs = _context_options(args.randomize_ua)
                        ctx_kwargs["storage_state"] = str(auth_file)
                        per_page_context = per_page_browser.new_context(**ctx_kwargs)
                    except Exception as e:
                        debug(f"Failed to create context with auth: {e}")
                        continue
                    
                    # Apply request blocking if enabled
                    setup_request_blocking(per_page_context, args.block_heavy)
                    
                    # Setup bandwidth measurement if enabled
                    meter = TrafficMeter(enabled=args.measure_bytes)
                    meter.attach(per_page_context)
                    
                    listing_page = per_page_context.new_page()
                    data = scrape_listing(listing_page, url, skip_on_captcha=args.skip_on_captcha)
                    if data is None:
                        debug(f"Skipped {url} (captcha or error)")
                        # Log bandwidth even for skipped pages
                        if args.measure_bytes and args.measure_report:
                            snap = meter.snapshot_and_reset()
                            _append_jsonl(Path(args.measure_report), {
                                "ts": datetime.utcnow().isoformat()+"Z",
                                "url": url,
                                "idx": idx,
                                "total": total,
                                "bytes": snap.get("total_bytes", 0),
                                "requests": snap.get("requests", 0),
                                "by_type": snap.get("by_type", {}),
                                "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                                "direct_bytes": snap.get("direct_bytes", 0),
                                "by_routing": snap.get("by_routing", {}),
                                "proxy_percentage": snap.get("proxy_percentage", 0),
                                "status": "skipped"
                            })
                        continue
                    # Fallback: if title is missing, try to read document.title
                    if not data.get("title"):
                        try:
                            data["title"] = (listing_page.title() or "").strip() or None
                        except Exception:
                            pass
                    results.append(data)
                    # Save incrementally after each successful scrape
                    save_metadata_incrementally(out_path, results)
                    debug(f"Saved progress: {len(results)} total records")
                    # Log bandwidth if measurement enabled
                    if args.measure_bytes and args.measure_report:
                        snap = meter.snapshot_and_reset()
                        _append_jsonl(Path(args.measure_report), {
                            "ts": datetime.utcnow().isoformat()+"Z",
                            "url": url,
                            "idx": idx,
                            "total": total,
                            "bytes": snap.get("total_bytes", 0),
                            "requests": snap.get("requests", 0),
                            "by_type": snap.get("by_type", {}),
                            "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                            "direct_bytes": snap.get("direct_bytes", 0),
                            "by_routing": snap.get("by_routing", {}),
                            "proxy_percentage": snap.get("proxy_percentage", 0),
                            "status": "ok"
                        })
                except Exception as e:
                    print(f"WARNING: Failed to scrape {url}: {e}", file=sys.stderr)
                finally:
                    # Clean up per-page browser/context
                    try:
                        if listing_page:
                            listing_page.close()
                        if per_page_context:
                            per_page_context.close()
                        if per_page_browser:
                            per_page_browser.close()
                    except Exception:
                        pass
                    time.sleep(PER_PAGE_SLEEP_SEC)
        else:
            # Original mode: reuse same browser/context for all pages
            # Setup bandwidth measurement for the shared context if enabled
            meter = TrafficMeter(enabled=args.measure_bytes)
            meter.attach(context)
            
            for idx, url in enumerate(urls, start=1):
                listing_page = context.new_page()
                try:
                    print(f"Scraping {idx}/{total}: {url}")
                    data = scrape_listing(listing_page, url, skip_on_captcha=args.skip_on_captcha)
                    if data is None:
                        debug(f"Skipped {url} (captcha or error)")
                        # Log bandwidth even for skipped pages
                        if args.measure_bytes and args.measure_report:
                            snap = meter.snapshot_and_reset()
                            _append_jsonl(Path(args.measure_report), {
                                "ts": datetime.utcnow().isoformat()+"Z",
                                "url": url,
                                "idx": idx,
                                "total": total,
                                "bytes": snap.get("total_bytes", 0),
                                "requests": snap.get("requests", 0),
                                "by_type": snap.get("by_type", {}),
                                "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                                "direct_bytes": snap.get("direct_bytes", 0),
                                "by_routing": snap.get("by_routing", {}),
                                "proxy_percentage": snap.get("proxy_percentage", 0),
                                "status": "skipped"
                            })
                        continue
                    # Fallback: if title is missing, try to read document.title
                    if not data.get("title"):
                        try:
                            data["title"] = (listing_page.title() or "").strip() or None
                        except Exception:
                            pass
                    results.append(data)
                    # Save incrementally after each successful scrape
                    save_metadata_incrementally(out_path, results)
                    debug(f"Saved progress: {len(results)} total records")
                    # Log bandwidth if measurement enabled
                    if args.measure_bytes and args.measure_report:
                        snap = meter.snapshot_and_reset()
                        _append_jsonl(Path(args.measure_report), {
                            "ts": datetime.utcnow().isoformat()+"Z",
                            "url": url,
                            "idx": idx,
                            "total": total,
                            "bytes": snap.get("total_bytes", 0),
                            "requests": snap.get("requests", 0),
                            "by_type": snap.get("by_type", {}),
                            "proxy_routed_bytes": snap.get("proxy_routed_bytes", 0),
                            "direct_bytes": snap.get("direct_bytes", 0),
                            "by_routing": snap.get("by_routing", {}),
                            "proxy_percentage": snap.get("proxy_percentage", 0),
                            "status": "ok"
                        })
                except Exception as e:
                    print(f"WARNING: Failed to scrape {url}: {e}", file=sys.stderr)
                finally:
                    try:
                        listing_page.close()
                    except Exception:
                        pass
                    time.sleep(PER_PAGE_SLEEP_SEC)

            try:
                context.close()
                browser.close()
            except Exception:
                pass

    print(f"Wrote {len(results)} records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
