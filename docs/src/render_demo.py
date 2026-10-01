#!/usr/bin/env python3
"""Record docs/demo.gif: a typed terminal session with real gdoc-surgical output.

1. Capture real output (offline, no Google account):
       python docs/src/render_demo.py capture
2. Render frames with Playwright and build the GIF with ffmpeg:
       python docs/src/render_demo.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SESSION = os.path.join(HERE, 'demo_session.json')
OUT = os.path.join(HERE, '..', 'demo.gif')
FPS = 12

STEPS = [
    (['read', '--id', 'DEMO_DOC'], 'python3 gdoc_surgical.py read --id DEMO_DOC'),
    (['replace', '--id', 'DEMO_DOC', '--find', 'Q3 2026', '--with', 'Q4 2026'],
     'python3 gdoc_surgical.py replace --id DEMO_DOC --find "Q3 2026" --with "Q4 2026"'),
    (['read', '--id', 'DEMO_DOC'], 'python3 gdoc_surgical.py read --id DEMO_DOC'),
]


def capture():
    demo = os.path.join(HERE, 'offline_demo.py')
    subprocess.run([sys.executable, demo, 'reset'], check=True)
    session = []
    for argv, shown in STEPS:
        r = subprocess.run([sys.executable, demo] + argv, capture_output=True,
                           text=True, cwd=ROOT, check=True)
        session.append({'cmd': shown, 'out': r.stdout.rstrip('\n')})
    subprocess.run([sys.executable, demo, 'reset'], check=True)
    with open(SESSION, 'w', encoding='utf-8') as fh:
        json.dump(session, fh, indent=1)
    print('wrote', SESSION)


def render():
    from playwright.sync_api import sync_playwright
    with open(SESSION, encoding='utf-8') as fh:
        session = fh.read()
    with open(os.path.join(HERE, 'demo.html'), encoding='utf-8') as fh:
        html = fh.read().replace('__SESSION__', session)
    tmp = tempfile.mkdtemp(prefix='gdoc_demo_')
    page_path = os.path.join(tmp, 'demo.html')
    with open(page_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 800, 'height': 450})
        page.goto('file:///' + page_path.replace('\\', '/'))
        page.wait_for_load_state('networkidle')
        page.evaluate('document.fonts.ready')
        total = page.evaluate('window.TOTAL_MS')
        n = int(total / 1000 * FPS) + 1
        for i in range(n):
            page.evaluate('renderAt(%d)' % int(i * 1000 / FPS))
            page.screenshot(path=os.path.join(tmp, 'f%04d.png' % i))
        browser.close()
    pattern = os.path.join(tmp, 'f%04d.png')
    palette = os.path.join(tmp, 'palette.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', pattern,
                    '-vf', 'palettegen=max_colors=64:stats_mode=diff', palette], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', pattern,
                    '-i', palette, '-lavfi', 'paletteuse=dither=none:diff_mode=rectangle',
                    '-loop', '0', OUT], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print('wrote %s (%d frames, %.1f s, %.0f KB)'
          % (os.path.normpath(OUT), n, n / FPS, os.path.getsize(OUT) / 1024))


if __name__ == '__main__':
    if sys.argv[1:] == ['capture']:
        capture()
    else:
        render()
