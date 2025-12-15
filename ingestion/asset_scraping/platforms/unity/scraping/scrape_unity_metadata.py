#!/usr/bin/env python3
"""
Unity Asset Store Metadata Scraper

Scrapes metadata from the user's "My Assets" page on the Unity Asset Store.
Requires auth.json containing valid authentication cookies.

Output: unity_metadata.json
"""

import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def extract_asset_id_from_url(url: str) -> str:
    """
    Extract asset store ID from URL.
    Expected format: https://assetstore.unity.com/packages/slug-name-12345
    """
    match = re.search(r'-(\d+)$', url.rstrip('/'))
    if match:
        return match.group(1)
    # Fallback: try to find any number sequence at end
    match = re.search(r'(\d+)$', url.rstrip('/'))
    return match.group(1) if match else ""


def scrape_asset_details(page, detail_url: str) -> dict:
    """
    Navigate to asset detail page and extract metadata.
    """
    print(f"  Scraping detail page: {detail_url}", file=sys.stderr)
    
    try:
        page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        
        # Extract asset ID from URL
        asset_id = extract_asset_id_from_url(detail_url)
        
        # Get title from page title or h1
        title = ""
        try:
            title = page.title()
            # Clean up title (often includes " | Unity Asset Store")
            if " | Unity Asset Store" in title:
                title = title.split(" | Unity Asset Store")[0].strip()
        except:
            pass
        
        # Get description
        description = ""
        try:
            desc_elem = page.locator("#collapse-panel-description")
            if desc_elem.count() > 0:
                description = desc_elem.inner_text()
        except:
            print("  Warning: Could not extract description", file=sys.stderr)
        
        # Get keywords
        keywords = []
        try:
            # Strategy 1: Find "Related keywords" heading and get sibling links
            keywords_heading = page.get_by_role("heading", name="Related keywords")
            if keywords_heading.count() > 0:
                # Get parent div, then find all links in the sibling container
                parent = keywords_heading.locator("../..")
                keyword_links = parent.locator("a")
                for i in range(keyword_links.count()):
                    keyword_text = keyword_links.nth(i).inner_text().strip()
                    if keyword_text:
                        keywords.append(keyword_text)
            
            # Fallback: Use XPath
            if not keywords:
                keyword_elements = page.locator('xpath=//*[@id="description-panel"]/div/div[4]/div/div/a')
                for i in range(keyword_elements.count()):
                    keyword_text = keyword_elements.nth(i).inner_text().strip()
                    if keyword_text:
                        keywords.append(keyword_text)
        except Exception as e:
            print(f"  Warning: Could not extract keywords: {e}", file=sys.stderr)
        
        # Get license text
        license_text = ""
        try:
            # Try CSS selector (brittle)
            license_link = page.locator("#main > div > div > div.y0emW > div._1Ngd4 > div._3ZV2G.m3_2T._9EVz3._2CNUL.wnn-Y > div:nth-child(2) > div._2nw25 > div._27124.product-license_agreement > a")
            if license_link.count() > 0:
                license_text = license_link.inner_text().strip()
            else:
                # Fallback: Try to find any element with "license" in text
                license_elements = page.get_by_text(re.compile("license", re.IGNORECASE))
                if license_elements.count() > 0:
                    license_text = license_elements.first.inner_text().strip()
        except Exception as e:
            print(f"  Warning: Could not extract license: {e}", file=sys.stderr)
        
        return {
            "asset_store_id": asset_id,
            "title": title,
            "description": description,
            "keywords": keywords,
            "license_text": license_text,
            "original_url": detail_url
        }
    
    except Exception as e:
        print(f"  Error scraping {detail_url}: {e}", file=sys.stderr)
        return {
            "asset_store_id": extract_asset_id_from_url(detail_url),
            "title": "",
            "description": "",
            "keywords": [],
            "license_text": "",
            "original_url": detail_url
        }


def scrape_unity_assets():
    """
    Main scraping function.
    """
    # Check for auth.json
    script_dir = Path(__file__).resolve().parent
    auth_file = script_dir.parent / "setup" / "auth.json"
    if not auth_file.exists():
        print(f"Error: auth.json not found at {auth_file}", file=sys.stderr)
        print("Please run: cd setup && python3 generate_unity_auth.py", file=sys.stderr)
        sys.exit(1)
    
    assets_data = []
    
    with sync_playwright() as p:
        print("Launching browser...", file=sys.stderr)
        browser = p.chromium.launch(headless=False)  # Set to True for headless mode
        
        # Load authentication state
        context = browser.new_context(storage_state=str(auth_file))
        main_page = context.new_page()
        
        print("Navigating to My Assets page...", file=sys.stderr)
        main_page.goto("https://assetstore.unity.com/account/assets", wait_until="domcontentloaded")
        
        # Wait for assets to load
        try:
            main_page.wait_for_selector('[data-test="package-name"]', timeout=10000)
        except PlaywrightTimeoutError:
            print("Error: Could not find assets. Check if auth.json is valid.", file=sys.stderr)
            browser.close()
            sys.exit(1)
        
        page_num = 1
        
        while True:
            print(f"\nProcessing page {page_num}...", file=sys.stderr)
            
            # Get all asset elements on current page
            asset_elements = main_page.locator('[data-test="package-name"]')
            asset_count = asset_elements.count()
            print(f"Found {asset_count} assets on this page", file=sys.stderr)
            
            for i in range(asset_count):
                print(f"\nProcessing asset {i+1}/{asset_count}...", file=sys.stderr)
                
                try:
                    # Re-query the element (DOM may have changed)
                    asset_link = main_page.locator('[data-test="package-name"]').nth(i)
                    asset_name = asset_link.inner_text()
                    print(f"  Asset: {asset_name}", file=sys.stderr)
                    
                    # Click to open modal
                    asset_link.click()
                    
                    # Wait for modal to appear
                    try:
                        main_page.wait_for_selector("#quick-look-title", timeout=5000)
                    except PlaywrightTimeoutError:
                        print("  Warning: Modal did not appear, skipping", file=sys.stderr)
                        continue
                    
                    # Find "View Full Details" link without clicking it
                    detail_url = None
                    try:
                        # Try multiple strategies to find the detail link
                        detail_link = main_page.get_by_role("link", name=re.compile("View.*[Dd]etails", re.IGNORECASE))
                        if detail_link.count() > 0:
                            detail_url = detail_link.first.get_attribute("href")
                        else:
                            # Fallback: look for any link containing "packages/"
                            all_links = main_page.locator('a[href*="/packages/"]')
                            if all_links.count() > 0:
                                detail_url = all_links.first.get_attribute("href")
                        
                        if detail_url and not detail_url.startswith("http"):
                            detail_url = f"https://assetstore.unity.com{detail_url}"
                    
                    except Exception as e:
                        print(f"  Warning: Could not find detail URL: {e}", file=sys.stderr)
                    
                    if detail_url:
                        # Open new page for detail scraping
                        detail_page = context.new_page()
                        asset_data = scrape_asset_details(detail_page, detail_url)
                        assets_data.append(asset_data)
                        detail_page.close()
                    else:
                        print("  Warning: No detail URL found, skipping", file=sys.stderr)
                    
                    # Close modal - try multiple strategies
                    modal_closed = False
                    try:
                        # Strategy 1: Look for close button by aria-label
                        close_button = main_page.get_by_role("button", name="Close")
                        if close_button.count() > 0:
                            close_button.first.click()
                            modal_closed = True
                    except:
                        pass
                    
                    if not modal_closed:
                        try:
                            # Strategy 2: Look for X button or close icon
                            close_button = main_page.locator('button[aria-label*="close" i]')
                            if close_button.count() > 0:
                                close_button.first.click()
                                modal_closed = True
                        except:
                            pass
                    
                    if not modal_closed:
                        try:
                            # Strategy 3: Click overlay/backdrop to close
                            overlay = main_page.locator('[role="presentation"], .modal-backdrop, [data-test*="overlay"]')
                            if overlay.count() > 0:
                                overlay.first.click()
                                modal_closed = True
                        except:
                            pass
                    
                    if not modal_closed:
                        # Final fallback: Press Escape
                        print("  Using Escape key to close modal", file=sys.stderr)
                        main_page.keyboard.press("Escape")
                    
                    # Wait for modal to close
                    try:
                        main_page.wait_for_selector("#quick-look-title", state="hidden", timeout=2000)
                    except:
                        # If modal still visible, try Escape again
                        main_page.keyboard.press("Escape")
                    
                    main_page.wait_for_timeout(500)  # Brief pause after closing
                
                except Exception as e:
                    print(f"  Error processing asset {i+1}: {e}", file=sys.stderr)
                    # Try to recover by pressing Escape
                    try:
                        main_page.keyboard.press("Escape")
                        main_page.wait_for_timeout(500)
                    except:
                        pass
                    continue
            
            # Check for Next button
            try:
                nav_element = main_page.locator('nav[role="navigation"]')
                next_button = nav_element.get_by_role("button", name="Next")
                
                if next_button.count() > 0 and next_button.is_enabled():
                    print("\nNavigating to next page...", file=sys.stderr)
                    next_button.click()
                    # Wait for page to reload
                    main_page.wait_for_load_state("domcontentloaded")
                    main_page.wait_for_timeout(2000)  # Additional wait for content
                    page_num += 1
                else:
                    print("\nNo more pages. Scraping complete.", file=sys.stderr)
                    break
            
            except Exception as e:
                print(f"\nCould not find Next button: {e}", file=sys.stderr)
                print("Assuming this is the last page.", file=sys.stderr)
                break
        
        browser.close()
    
    # Write output
    output_file = script_dir.parent / "output" / "unity_metadata.json"
    print(f"\nWriting {len(assets_data)} assets to {output_file}", file=sys.stderr)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(assets_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Successfully scraped {len(assets_data)} assets", file=sys.stderr)


if __name__ == "__main__":
    scrape_unity_assets()
