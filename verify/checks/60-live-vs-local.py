#!/usr/bin/env python3
"""60 live vs local: the permanent page serves exactly the bytes this build produced.

WHY: a publish that did not happen, or that happened from a stale build, looks identical to
one that did until somebody compares. Until front_door.json sets permanent_url (chunk C:
GitHub Pages), there is nothing to fetch and the check says so with a count.
"""
import hashlib, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, PAGE

def compare(live, local, label):
    same = live == local
    h = lambda b: hashlib.sha256(b).hexdigest()[:12]
    print(f'COUNT live-compare {1 if same else 0}/1 equal ({label}: live {len(live)} B sha {h(live)}, local {len(local)} B sha {h(local)})')
    if not same:
        print('SAMPLE the live page differs from outputs/argument-map.html: publish from the current build')
    return same

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    sys.exit(0 if compare(b'<html>old</html>', b'<html>new</html>', 'planted') else 1)

url = json.load(open(os.path.join(ROOT, 'sources', 'front_door.json'), encoding='utf-8')).get('permanent_url')
if not url:
    print('COUNT live-compare skipped 1 (no permanent_url in sources/front_door.json yet)')
    sys.exit(0)
try:
    live = urllib.request.urlopen(url, timeout=30).read()
except Exception as e:
    print('COUNT live-compare 0/1 (fetch failed)')
    print(f'SAMPLE {url}: {e}')
    sys.exit(1)
sys.exit(0 if compare(live, open(PAGE, 'rb').read(), url) else 1)
