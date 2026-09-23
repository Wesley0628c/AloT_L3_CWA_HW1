"""Live-browser smoke check; requires a running server and reachable public CDNs/APIs."""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'artifacts'
out.mkdir(exist_ok=True)
url=os.environ.get('CWA_TEST_URL','http://127.0.0.1:8000')
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='networkidle',timeout=120000)
    page.wait_for_function("!document.getElementById('refresh').disabled",timeout=120000)
    assert page.locator('#connection-badge').inner_text() in ['已同步','快取']
    assert not page.locator('#wind-control').is_visible()
    print('Summary:',page.locator('#station-count').inner_text())
    page.screenshot(path=str(out/'reference-style-desktop.png'),full_page=True)
    for layer in ['rainfall','humidity','weather','stations','wind']:
        page.click(f'[data-layer="{layer}"]')
        page.wait_for_timeout(350)
        assert page.locator(f'[data-layer="{layer}"]').get_attribute('aria-pressed')=='true'
        if layer=='wind':
            assert page.locator('#wind-control').is_visible()
            assert page.locator('.wind-canvas').count()==1
            page.screenshot(path=str(out/'wind.png'),full_page=True)
        print('Layer passed:',layer)
    page.click('[data-layer="radar"]')
    page.wait_for_timeout(700)
    assert page.locator('.leaflet-image-layer').count()==1
    page.wait_for_function("document.querySelector('.leaflet-image-layer')?.naturalWidth>0")
    page.select_option('#radar-source','history')
    page.locator('#radar-range').evaluate("e=>{e.value=0;e.dispatchEvent(new Event('input'));}")
    assert 'RainViewer' in page.locator('#radar-time').inner_text()
    print('Radar image and history passed')
    page.click('[data-layer="typhoon"]')
    page.wait_for_timeout(600)
    assert page.locator('#storm-select option').count()>0
    page.locator('#storm-range').evaluate("e=>{e.value=e.max;e.dispatchEvent(new Event('input'));}")
    assert '官方預報' in page.locator('#storm-time').inner_text()
    page.wait_for_load_state('networkidle')
    page.wait_for_function("Array.from(document.querySelectorAll('.leaflet-tile')).every(image=>image.complete && image.naturalWidth>0)")
    page.screenshot(path=str(out/'typhoon.png'),full_page=True)
    print('Typhoon forecast timeline passed')
    page.click('#home')
    page.click('#forecast-open')
    assert page.locator('#forecast-table tr').count()==7
    assert page.locator('#daily-table tr').count()==6
    page.select_option('#forecast-region',label='東南部地區')
    with page.expect_download() as download:page.click('#forecast-export')
    assert download.value.suggested_filename=='weekly_forecasts.csv'
    page.locator('#data-drawer').evaluate('e=>e.scrollTop=0')
    page.screenshot(path=str(out/'forecast.png'),full_page=True)
    page.click('#drawer-close')
    page.click('#tools-open')
    page.select_option('#county',label='臺北市')
    print('Filter:',page.locator('#station-count').inner_text())
    page.fill('#search','不存在的測站')
    assert '0 站' in page.locator('#station-count').inner_text()
    page.fill('#search','');page.select_option('#county','ALL')
    page.locator('#history-range').evaluate("e=>{e.value=0;e.dispatchEvent(new Event('input'));}")
    page.wait_for_function("document.getElementById('connection-badge').textContent==='歷史'")
    page.click('#history-live')
    page.locator('summary').filter(has_text='唯讀 SQL').click()
    page.fill('#sql-query','SELECT count(*) AS total FROM WeeklyForecasts')
    page.click('#sql-run')
    page.wait_for_function("document.getElementById('sql-result').textContent.includes('42')")
    print('Filter, CSV, SQL and snapshots passed')
    page.click('#drawer-close')
    page.set_viewport_size({'width':390,'height':844})
    page.click('#toggle-layers')
    page.click('[data-layer="temperature"]')
    page.screenshot(path=str(out/'mobile-layers.png'),full_page=True)
    page.click('#toggle-info')
    page.screenshot(path=str(out/'mobile-summary.png'),full_page=True)
    page.click('#forecast-open')
    page.screenshot(path=str(out/'mobile-forecast.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    assert not errors,errors
    print('Desktop/mobile passed; JavaScript errors:',errors)
    browser.close()
