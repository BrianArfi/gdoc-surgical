#!/usr/bin/env python3
"""Render the animated explainer GIFs from their HTML sources.

    pip install playwright && python -m playwright install chromium   # plus ffmpeg on PATH
    python docs/src/render_gifs.py            # all three
    python docs/src/render_gifs.py hero       # just one: hero, before-after, how-it-works

These are illustrations. The real-output terminal recordings are made by
render_demo.py (demo.gif, guards.gif), and the static hero.png by render.py.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, '..'))

# name: (source page, output gif, width, height, seconds, fps, colors)
GIFS = {
    'hero': ('hero_anim.html', 'hero.gif', 1200, 640, 10, 12, 128),
    'before-after': ('before_after.html', 'before-after.gif', 1100, 600, 10, 12, 128),
    'how-it-works': ('how_it_works.html', 'how-it-works.gif', 1100, 560, 11, 12, 128),
}

for name in sys.argv[1:] or list(GIFS):
    src, out, w, h, dur, fps, colors = GIFS[name]
    subprocess.run([sys.executable, os.path.join(HERE, 'record_html.py'),
                    os.path.join(HERE, src), os.path.join(DOCS, out),
                    '--w', str(w), '--h', str(h), '--dur', str(dur),
                    '--fps', str(fps), '--colors', str(colors)], check=True)
    print('%s: %.0f KB' % (out, os.path.getsize(os.path.join(DOCS, out)) / 1024))
