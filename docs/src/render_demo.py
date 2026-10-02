#!/usr/bin/env python3
"""Record a typed terminal session with real gdoc-surgical output as a GIF.

Two sessions, both run offline against the sample doc in offline_demo.py:
  demo    docs/demo.gif    read, replace "Q3 2026" with "Q4 2026", read again
  guards  docs/guards.gif  a stale --expect and a typo are refused, exit 2,
                           and a read shows the doc did not change

1. Capture real output (offline, no Google account):
       python docs/src/render_demo.py capture [demo|guards]
2. Render frames with Playwright and build the GIF with ffmpeg:
       python docs/src/render_demo.py [demo|guards]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
FPS = 12

DEMO_STEPS = [
    (['read', '--id', 'DEMO_DOC'], 'python3 gdoc_surgical.py read --id DEMO_DOC'),
    (['replace', '--id', 'DEMO_DOC', '--find', 'Q3 2026', '--with', 'Q4 2026'],
     'python3 gdoc_surgical.py replace --id DEMO_DOC --find "Q3 2026" --with "Q4 2026"'),
    (['read', '--id', 'DEMO_DOC'], 'python3 gdoc_surgical.py read --id DEMO_DOC'),
]

# 'EXIT' prints the exit code of the step before it, like `echo $?`.
GUARD_STEPS = [
    (['set-cell', '--id', 'DEMO_DOC', '--table', '0', '--row', '1', '--col', '1',
      '--with', 'Q4 2026', '--expect', 'Q2 2026'],
     'python3 gdoc_surgical.py set-cell --id DEMO_DOC --table 0 --row 1 --col 1 '
     '--with "Q4 2026" --expect "Q2 2026"'),
    ('EXIT', 'echo $?'),
    (['replace', '--id', 'DEMO_DOC', '--find', 'Q3 2025', '--with', 'Q4 2026'],
     'python3 gdoc_surgical.py replace --id DEMO_DOC --find "Q3 2025" --with "Q4 2026"'),
    ('EXIT', 'echo $?'),
    (['read', '--id', 'DEMO_DOC'], 'python3 gdoc_surgical.py read --id DEMO_DOC'),
]

SESSIONS = {
    # name: (steps, session json, page, output gif, viewport w, h)
    'demo': (DEMO_STEPS, 'demo_session.json', 'demo.html', 'demo.gif', 800, 450),
    'guards': (GUARD_STEPS, 'guards_session.json', 'guards.html', 'guards.gif', 1000, 640),
}


def capture(name):
    steps, session_file = SESSIONS[name][:2]
    demo = os.path.join(HERE, 'offline_demo.py')
    subprocess.run([sys.executable, demo, 'reset'], check=True)
    session, last_code = [], 0
    for argv, shown in steps:
        if argv == 'EXIT':
            session.append({'cmd': shown, 'out': str(last_code)})
            continue
        # stderr is merged in, because the guards print their refusal there.
        r = subprocess.run([sys.executable, demo] + argv, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, cwd=ROOT)
        if r.returncode not in (0, 2):
            sys.exit('unexpected exit %d:\n%s' % (r.returncode, r.stdout))
        last_code = r.returncode
        session.append({'cmd': shown, 'out': r.stdout.rstrip('\n')})
    subprocess.run([sys.executable, demo, 'reset'], check=True)
    path = os.path.join(HERE, session_file)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(session, fh, indent=1)
    print('wrote', path)


def render(name):
    from playwright.sync_api import sync_playwright
    _, session_file, page_file, gif, w, h = SESSIONS[name]
    OUT = os.path.join(HERE, '..', gif)
    with open(os.path.join(HERE, session_file), encoding='utf-8') as fh:
        session = fh.read()
    with open(os.path.join(HERE, page_file), encoding='utf-8') as fh:
        html = fh.read().replace('__SESSION__', session)
    tmp = tempfile.mkdtemp(prefix='gdoc_demo_')
    page_path = os.path.join(tmp, 'demo.html')
    with open(page_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': w, 'height': h})
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
    args = sys.argv[1:]
    if args and args[0] == 'capture':
        capture(args[1] if len(args) > 1 else 'demo')
    else:
        render(args[0] if args else 'demo')
