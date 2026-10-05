#!/usr/bin/env python3
"""70 master fresh: the committed master.json is byte-identical to the one this build made.

WHY: master.json at the repo root is a generated file kept in git so readers can see the
source of truth. On 2026-10-04 it was found stale (it still said "Strong" after the ratings
were renamed). rebuild.sh now copies the fresh one back; this proves it did.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, need_build

def compare(a, b):
    same = a == b
    diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b))) if not same else -1
    print(f'COUNT master-fresh {1 if same else 0}/1 (root {len(a)} B, build {len(b)} B)')
    if not same:
        print(f'SAMPLE first difference at byte {diff}: run ./rebuild.sh and commit master.json')
    return same

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    sys.exit(0 if compare(b'{"rating":"Strong"}', b'{"rating":"firm"}') else 1)

need_build()
root = open(os.path.join(ROOT, 'master.json'), 'rb').read()
built = open(os.path.join(ROOT, 'outputs', 'master.json'), 'rb').read()
sys.exit(0 if compare(root, built) else 1)
