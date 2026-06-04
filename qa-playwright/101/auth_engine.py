import os
from playwright.sync_api import sync_playwright


def get_authenticated_context(browser, config):
    storage_path = config["storage_path"]
    
    if os.path.exists(storage_path):
        print("session cache found, reusing")
        return browser.new_context(storage_state=storage_path)
    
    print("no cache found, executing login")
    context = browser.new_context()
    page = context.new_page()
    
    page.goto(config["login_url"])
    
    if config.get("modal_selector"):
        page.locator(config["modal_selector"]).click()
        
    page.locator(config["email_selector"]).fill(config["email"])
    page.locator(config["password_selector"]).fill(config["password"])
    
    with page.expect_navigation(url=config["success_url"]):
        page.locator(config["submit_selector"]).click()
        
    context.storage_state(path=storage_path)
    
    print("session cached at", storage_path)
    
    return context


# ==================================================
if __name__ == "__main__":
    # Generic configurations payload 
    test_config = {
        "login_url": "https://upinthesky.in/authenticate",
        "success_url": "**/trips",
        "email": "tushar@vibemonitor.ai",
        "password": "123456",
        "modal_selector": "button:has-text('Got it!')",
        "email_selector": "form.login input[name='email']",
        "password_selector": "form.login input[name='password']",
        "submit_selector": "form.login input[type='submit']",
        "storage_path": "session_alpha.json"  # Saves in current folder
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        # Get our setup context dynamically
        context = get_authenticated_context(browser, test_config)
        
        # Open a page and run tests
        page = context.new_page()
        page.goto("https://upinthesky.in/explore")
        
        print("--> Browser tab is open and authenticated. Ready for assertions.")
        page.wait_for_timeout(500)
        
        browser.close()