from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        print("Connecting to existing Chrome instance on port 9222...")
        try:
            # Connect to the browser you launched manually via terminal
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print(f"Failed to connect. Make sure you ran Chrome with --remote-debugging-port=9222. Error: {e}")
            return

        # Get the existing context (your main profile)
        default_context = browser.contexts[0]
        
        # Use the first open page or create a new one
        if default_context.pages:
            page = default_context.pages[0]
        else:
            page = default_context.new_page()
            
        print("Navigating to Fab Library...")
        page.goto("https://www.fab.com/library")
        
        print("--- ACTION REQUIRED ---")
        print("1. Perform the login/Captcha in the browser window manually.")
        print("   (Since this is your real Chrome, the Captcha should pass).")
        print("2. Navigate until you see your Library grid.")
        print("3. Press ENTER in this terminal to save the session.")
        
        input() # Wait for you to confirm you are logged in
            
        # Save session
        default_context.storage_state(path="auth.json")
        print("Session saved to 'auth.json'. You can now close Chrome and the script.")

if __name__ == "__main__":
    run()