#!/usr/bin/env python3
"""10 build: the whole pipeline runs from sources and ends with its drift line.

WHY: the build used to swallow its own check failures ('|| true'), so a broken view could
reach the artifact under a green-looking log. Every later check reads what this one builds.
"""
import os, shutil, subprocess, sys, tempfile
# On Windows, a bare "bash" resolves to the WSL bash in System32 before PATH is searched.
# shutil.which follows PATH, which finds Git Bash first.
BASH = shutil.which('bash') or 'bash'
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT

DRIFT_LINE = 'No drift. All views agree with master.json.'

def build(root):
    """Run rebuild.sh in `root`. Returns (ok, lines printed)."""
    env = dict(os.environ, PYTHONUTF8='1', WORK=os.path.join(root, 'work'), OUT=os.path.join(root, 'outputs'))
    p = subprocess.run([BASH, './rebuild.sh'], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8')
    lines = (p.stdout + p.stderr).splitlines()
    ok = p.returncode == 0 and DRIFT_LINE in lines
    passes = sum(1 for l in lines if l.strip().startswith('PASS'))
    fails = [l.strip() for l in lines if l.strip().startswith(('FAIL', 'BUILD FAILED', 'MISS', 'EMPTY', 'RUNTIME ERROR'))]
    views = next((l.strip() for l in lines if l.strip().startswith('all ') and 'views rendered' in l), 'views: not reported')
    print(f'COUNT build exit {p.returncode}; drift checks passed {passes}; failures {len(fails)}; {views}')
    for f in fails[:8]:
        print('SAMPLE ' + f)
    if not ok and not fails:
        print('SAMPLE last lines: ' + ' | '.join(lines[-6:]))
    return ok

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    # Poison pill: a copy of the repo whose front door names an argument that does not exist.
    tmp = tempfile.mkdtemp()
    try:
        for d in ('sources', 'pipeline', 'kjv'):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
        shutil.copy(os.path.join(ROOT, 'rebuild.sh'), tmp)
        fd = os.path.join(tmp, 'sources', 'front_door.json')
        s = open(fd, encoding='utf-8').read().replace('"C17",', '"Z99",', 1)
        open(fd, 'w', encoding='utf-8', newline='').write(s)
        sys.exit(0 if build(tmp) else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

sys.exit(0 if build(ROOT) else 1)
