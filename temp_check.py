from playwright.sync_api import sync_playwright
from pathlib import Path
html = Path('input/thumbnail_generator.html').resolve()
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={'width':1280,'height':720})
    url = 'file:///' + str(html).replace('\\','/')
    page.goto(url)
    page.wait_for_load_state('load')
    content = page.content()
    print('contains thumb-wrap string?', '#thumb-wrap' in content)
    print('first 200 chars:', content[:200])
    print('id occurrences:', content.count('thumb-wrap'))
    el = page.query_selector('#thumb-wrap')
    print('query_selector object:', el)
    if el:
        print('outerHTML len', len(el.evaluate('el => el.outerHTML')))
    browser.close()