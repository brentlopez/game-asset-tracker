from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        # 1. Launch with specific args to hide automation
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled", # Crucial: Hides the 'navigator.webdriver' flag mechanism
                "--disable-infobars",
                "--exclude-switches=enable-automation",
            ],
            ignore_default_args=["--enable-automation"] # Prevents the "Chrome is being controlled by..." bar
        )
        
        # 2. Use a realistic User Agent (Intel Mac Chrome)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.new_page()

        # 3. Extra Stealth: Manually delete the webdriver property via JS injection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        print("Navigating to Fab Library...")
        # Redirects to Epic Login if not authenticated
        page.goto("https://www.fab.com/library") 
        
        print("--- ACTION REQUIRED ---")
        print("1. Log in to your Epic Games account.")
        print("   (The Captcha should now behave normally).")
        print("2. Wait until you see your Library grid.")
        print("3. Close the browser window to save the session.")
        
        # Wait for user to close browser
        try:
            page.wait_for_event("close", timeout=0)
        except:
            pass
            
        # Save session
        context.storage_state(path="auth.json")
        print("Session saved to 'auth.json'.")

if __name__ == "__main__":
    run()