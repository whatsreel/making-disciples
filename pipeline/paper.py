#!/usr/bin/env python3
"""Where the session paper lives, and what proves it is current. One implementation, used by
check_drift.py (which the gate's build check runs).

The paper (docs/discipleship-session.md) is private: it is about one church and stays in a
private notes repo, never in the public page repo. A gitignored `.notes-expected` file at a
repo root marks a machine that has the notes, so an absent paper there is a failure, not a
skip. Its one line, if present, names the notes folder (the public repo names no church, so
the location lives only on the machines that have it).
"""
import os

PAPER = os.path.join('docs', 'discipleship-session.md')
MARKER = '.notes-expected'

# The newest arguments, each with a phrase that only appears once that argument reached the paper.
PROBES = {'C12': 'skopeite', 'C13': 'Lightfoot', 'C14': 'Hena hekaston',
          'C15': 'strengthen thy brethren', 'D5': 'ensamples to all that believe',
          'D6': 'Heterous', 'A4': 'John 17:20'}

def marker_line(root):
    """The marker's first line as written, or None (no marker, or an empty one)."""
    m = os.path.join(root, MARKER)
    if not os.path.isfile(m):
        return None
    from manifest import decode   # one decoder: a BOM or UTF-16 (PowerShell 5's `>`) is tolerated
    lines = decode(open(m, 'rb').read()).strip().splitlines()
    return (lines[0].strip() or None) if lines else None

def _resolve(root, line):
    if os.name == 'nt' and len(line) > 2 and line[0] == '/' and line[2] == '/' and line[1].isalpha():
        line = line[1].upper() + ':' + line[2:]   # Git Bash's /c/dev/... is C:/dev/...
    path = line if os.path.isabs(line) else os.path.join(root, line)   # relative = to the repo, not the cwd
    return os.path.normpath(path)

def notes_dir(root):
    """The folder named on the marker's first line, or None (no marker, or a first line that is
    not a folder, such as a plain note; marker_problem says which)."""
    line = marker_line(root)
    if not line:
        return None
    path = _resolve(root, line)
    return path if os.path.isdir(path) else None

def marker_problem(root):
    """Why the marker named no folder, in words for a failure message ('' when there is nothing to say)."""
    line = marker_line(root)
    if line is None:
        return 'the marker names no folder'
    if notes_dir(root):
        return ''
    return f"the marker's first line ('{line[:60]}') is not a folder on this machine"

def find_paper(root):
    """(path or None, expected) for the repo at `root`."""
    root = os.path.abspath(root)
    expected = os.path.isfile(os.path.join(root, MARKER))
    cands = [os.path.join(root, PAPER)]
    nd = notes_dir(root)
    if nd:
        cands.append(os.path.join(nd, PAPER))
    for cand in cands:
        if os.path.isfile(cand):
            return cand, expected
    return None, expected
