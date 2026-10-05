#!/usr/bin/env python3
"""The tone guard: one regex, two callers (check_drift.py and the gate's check 20).

The page goes to a whole session, elders holding either view in good faith. Language that
casts a reader as an opponent fails the build. A keyword list cannot judge tone; it can only
stop the phrases that have already slipped through once (two did on 2026-10-04, so "our side",
"their side" and "attack" were added). A person reading every public file is still the real test.
"""
import json, re

ADV = re.compile(
    r"\b(opponents?|the other side|opposing (?:view|reading|position)|push ?back|they will ask|"
    r"lead with|leading with|your opponents|against you|costs you|our side|their side|"
    r"attack(?:s|ing)|"
    # A5 closes the wholesale refusal of Jesus' example; the page offered it as a live position in
    # four places until chunk E (Jon's read, 2026-10-05)
    r"set (?:\w+ )?aside entirely|set entirely aside|practice is set aside|"
    r"declin\w*(?: \w+){0,3} wholesale|declin\w*(?: \w+){0,2} whole category|declin\w* to treat (?:Jesus|Christ)|"
    # presenter coaching: the page read as notes for one side (tone list, Jon chose "apply all" 2026-10-05)
    r"lose the room|push it past this|win a point|damage us|buys credibility|thumb on the scale|"
    r"before anyone else does|lost before starting)\b", re.I)

def _exempt(txt, m):
    ctx = txt[max(0, m.start() - 60):m.end() + 30]
    if re.search(r'(answer|rebuke) ' + re.escape(m.group(0)), ctx, re.I):   # Jesus' opponents in the Gospels
        return True
    if 'passed by on' in ctx or 'Never speak of' in ctx:                    # Luke 10 / the chat rule itself
        return True
    return False

def strip_scripture(txt):
    """A built page carries the KJV table in its payload; scripture is not our tone."""
    vi = txt.find('const V=')
    if vi > 0:
        txt = txt[:vi] + txt[txt.find('};', vi) + 2:]
    pm = re.search(r'<script id="payload"[^>]*>(.*?)</script>', txt, re.S)
    if pm:
        try:
            d = json.loads(pm.group(1).replace('<\\/script>', '</script>'))
            d.pop('scripture', None)
            txt = txt[:pm.start(1)] + json.dumps(d, ensure_ascii=False) + txt[pm.end(1):]
        except ValueError:
            pass
    return txt

def hits(txt):
    """[(line, phrase)] for every adversarial phrase not covered by an exemption."""
    out = []
    for m in ADV.finditer(txt):
        if not _exempt(txt, m):
            out.append((txt.count('\n', 0, m.start()) + 1, m.group(0)))
    return out
