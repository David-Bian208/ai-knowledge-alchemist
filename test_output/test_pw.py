
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1]

try:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = context.new_page()
    page.goto(url, wait_until="networkidle", timeout=15000)
    
    title = page.title()
    content = page.inner_text("body")
    
    print(f"SUCCESS|{title}|{len(content)}")
    browser.close()
    pw.stop()
except Exception as e:
    print(f"ERROR|{str(e)}|0")
