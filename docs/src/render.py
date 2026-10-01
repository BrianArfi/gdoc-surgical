#!/usr/bin/env python3
"""Render docs/src/hero.html to docs/hero.png at 2x (1600x800 CSS px).

    pip install playwright && python -m playwright install chromium
    python docs/src/render.py
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'hero.html')
OUT = os.path.join(HERE, '..', 'hero.png')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1600, 'height': 800}, device_scale_factor=2)
    page.goto('file:///' + SRC.replace('\\', '/'))
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    page.screenshot(path=OUT, full_page=False)
    browser.close()
print('wrote', os.path.normpath(OUT))
