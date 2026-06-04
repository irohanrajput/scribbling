from playwright.sync_api import sync_playwright

def view_dom():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page=browser.new_page()
        
        print("navigating to the page")
        page.goto("https://upinthesky.in")
        # 
        # extract the entire html structure (the dom)
        
        html_content = page.content()
        
        print("---dom content starting--")
        print(html_content)
        print("--dom content end")
        
        
        page.wait_for_timeout(30000)
        browser.close()
        
if __name__=="__main__":
    view_dom()