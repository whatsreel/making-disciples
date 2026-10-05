#!/usr/bin/env python3
"""The author's rating of an argument, read from its index label. One function, two callers
(gen_hub_data.py and the gate's check 40), so the build and the gate cannot disagree.

Internal keys stay Strong/Contested/Undecidable (CSS, sort, filters). Readers see the words
firm/contested/open (Jon, 2026-10-04); the page template maps keys to words.
"""
KEYS = (('Strong', 'firm'), ('Contested', 'contested'), ('Undecidable', 'open'))
WORD = dict(KEYS)

def verdict_short(v):
    """'firm, and prior to everything' -> 'Strong'. Anything unrecognized -> 'Unrated'."""
    if not v:
        return 'Unrated'
    s = v.strip().lower()
    for k, word in KEYS:
        if s.startswith((k.lower(), word)):
            return k
    return 'Unrated'
