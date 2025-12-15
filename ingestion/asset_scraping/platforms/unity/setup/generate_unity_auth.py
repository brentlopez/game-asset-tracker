# Run this locally with: python generate_auth.py
# It will open a browser. Log in to Unity. 
# When you see your "My Assets" list, close the browser window.
# The script will save your cookies to 'auth.json'.

from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("Navigating to Unity Asset Store...")
        page.goto("https://assetstore.unity.com/account/assets")
        
        print("Please log in manually. The script will wait until you close the browser window.")
        
        # Wait for the user to close the browser manually
        try:
            page.wait_for_event("close", timeout=0) 
        except:
            pass
            
        # Save the storage state (cookies, local storage)
        context.storage_state(path="auth.json")
        print("Successfully saved session to 'auth.json'. Move this file to the ingestion-scripts folder.")

if __name__ == "__main__":
    run()