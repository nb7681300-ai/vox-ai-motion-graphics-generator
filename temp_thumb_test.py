from pathlib import Path
from playwright.sync_api import sync_playwright
import time
html = Path('input/thumbnail_generator.html').resolve()
out = Path('temp-thumb.png').resolve()
print('html', html)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={'width':1280,'height':720})
    page.goto('file:///' + str(html).replace('\\','/'))
    try:
        page.wait_for_load_state('networkidle', timeout=5000)
    except Exception as e:
        print('wait', e)
    time.sleep(1.0)
    page.evaluate('''() => {
        const wrapper = document.querySelector('#thumb-wrap, #thumb');
        if (wrapper) {
            wrapper.style.maxWidth = 'none';
            wrapper.style.width = '1280px';
            wrapper.style.height = '720px';
            wrapper.style.margin = '0';
        }
        document.body.style.margin = '0';
        document.body.style.padding = '0';
    }''')
    locator = page.locator('#thumb-wrap, #thumb')
    print('count', locator.count())
    if locator.count() > 0:
        locator.first.screenshot(path=str(out))
    else:
        page.screenshot(path=str(out), full_page=False)
    browser.close()
print('wrote', out.exists(), out)