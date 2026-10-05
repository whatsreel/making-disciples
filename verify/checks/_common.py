"""Shared helpers for this project's gate checks. The leading underscore keeps the runner
from treating this file as a check."""
import json, os, subprocess, sys
sys.dont_write_bytecode = True   # no __pycache__ inside pipeline/ or verify/

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PIPE = os.path.join(ROOT, 'pipeline')
OUT = os.path.join(ROOT, 'outputs')
PAGE = os.path.join(OUT, 'argument-map.html')
sys.path.insert(0, PIPE)

def rendered(page=PAGE):
    """Every view, tab strip, footer and argument sheet of a built page, as visible text.
    Uses pipeline/render_views.js (no browser). Rendered fresh on every call: a cache could
    answer for a page it was not built from."""
    js = ("const r=require(process.argv[1]);const o=r.render(process.argv[2]);const t={};"
          "Object.keys(o.views).forEach(k=>t[k]=r.text(o.views[k]));"
          "Object.keys(o.sheets).forEach(k=>t['sheet '+k]=r.text(o.sheets[k]));"
          "t.tabs=r.text(o.tabs);t.foot=r.text(o.foot);process.stdout.write(JSON.stringify(t));")
    p = subprocess.run(['node', '-e', js, os.path.join(PIPE, 'render_views.js'), page],
                       capture_output=True, text=True, encoding='utf-8')
    if p.returncode != 0:
        raise RuntimeError('render failed: ' + (p.stderr or p.stdout)[-400:])
    return json.loads(p.stdout)

def need_build():
    if not os.path.isfile(PAGE):
        print('COUNT built-page 0/1')
        print('SAMPLE outputs/argument-map.html missing: check 10 (the build) must run first')
        sys.exit(1)
