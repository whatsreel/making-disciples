# CLAUDE.md — read this first

## What this is
A Scripture-and-standards case on what it means to make disciples, and whose work it is, prepared
for a church session. One source of truth (`master.json`, generated from `sources/`) feeds every
view: the web page, a spreadsheet and an argument index. Push to `main` and GitHub Pages publishes
the page.

**Audience: the whole session — elders holding either view, in good faith.** Everything visible
must be readable by someone who disagrees without feeling argued against. This is the most
important constraint, and the build enforces it with a tone guard (`pipeline/tone.py`).

## Rules (the build enforces most of these)
1. Edit content in `sources/` only. `master.json` and everything in `outputs/` are generated.
2. An argument lives in two files: prose in `sources/argument-index.md`, fields in
   `sources/args.json`. The build fails if they disagree.
3. Every ID in `front_door.json` and `dependencies.json` must exist. The build fails otherwise.
4. Visible counts are computed, never typed.
5. Verify every citation against a primary source before it goes in.
6. US spellings. KJV quotations keep their original spelling.
7. The page follows *don't make me think*: one behavior per control, numbers before controls,
   no insider vocabulary.
8. **This repo is gated.** Nothing is done, fixed or ready until `bash verify/run.sh` exits 0 on
   the current source. It runs the build (on Windows `PYTHONUTF8=1 WORK=$PWD/work OUT=$PWD/outputs
   ./rebuild.sh`, which must end `No drift. All views agree with master.json.`), then the checks in
   `verify/checks/` (tone, no church name, rating words, typed counts and the phone-size UX floor
   among them), and requires a current code review and UX review. A failing check is a finding:
   fix the code or the check, never weaken it.
9. The page never names a church. Check 25 enforces it only on a machine that has the author's
   private notes (its names list lives there); elsewhere, including CI, it counts itself skipped.
   Without the notes, keep names out by hand and leave the check to the author's machine.

## Engineering decisions
- **Two separate questions, not one "side":** `what` (Word and sacrament received / Modeled,
  equipped, sent / Both / —) and `who` (Officers / Every member, under officers / Both / —).
- **Ratings are the author's own**, and the page says so: "Author's rating: firm / contested /
  open". Inside the code the keys stay Strong / Contested / Undecidable; the template maps them.
- **Dependencies are authored, not text-mined.** Every edge in `dependencies.json` can be pointed
  to in the index.
- **No scatter plot.** The two questions are categorical, so the page shows a grid with counts.
- **The page opens on Start**: large buttons that fit the first phone screen. The type floor is
  15px, and tap targets are at least 44px.
- **Backgrounds are plain.** Color goes into headings, IDs and rules, never tinted backgrounds.
- **On GitHub Pages there is no in-page chat.** "Common questions", authored in
  `front_door.json`, answers the starter questions there.
