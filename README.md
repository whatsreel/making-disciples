# Making disciples — the argument, its sources, and the build

One artifact, many views, one source of truth. Everything under `outputs/` is generated; never hand-edit it.

## Layout
```
sources/      hand-edited: the only files you change for content
  argument-index.md   full prose of every argument (the authoritative text)
  args.json           structured fields: column, rating, what/who axes, limits, card text
  front_door.json     the summary tab: thesis, three changes, key arguments, author line
  dependencies.json   authored links between arguments (rests on / repairs / licenses / bounds / answers)
  map_frame.txt       instructions for the in-page chat
pipeline/     the build; tone.py, ratings.py and paper.py are each one rule shared by the build and the gate
kjv/          local KJV text used for the scripture popovers
verify/       the release gate: run.sh and its checks
master.json   GENERATED merge of index + args.json; the source every view reads (refreshed by every build)
public_manifest.txt   the files that are public; the tone check reads every one
```

## Rebuild
Requirements: python3 (openpyxl), node. pandoc and wkhtmltopdf are optional (PDFs).
```
./rebuild.sh                                                   # Linux, macOS, CI
PYTHONUTF8=1 WORK=$PWD/work OUT=$PWD/outputs ./rebuild.sh      # Windows (Git Bash): the line the gate runs
```
Outputs land in `outputs/`: `argument-map.html` (the web page), `argument-map.xlsx`, PDFs when available.
The build ends with two checks and must print `No drift. All views agree with master.json.`
Any failing step prints its whole log and the build exits non-zero.

## The gate
```
bash verify/run.sh
```
Runs the build, then checks tone over every public file and the rendered page, that no public
file names a church (check 25 reads the names from the private notes repo and holds none itself;
without the notes it counts itself skipped), rating words,
that every argument is rated, that no count is typed by hand, live-vs-local bytes, and that the
committed `master.json` is fresh. Check 90 opens the built page in a real browser (Playwright)
at phone and desktop sizes and counts text under 15px, tap targets under 44px, sideways overflow,
Start buttons below the first phone screen, and how many font sizes are in use. Each check prints
counts and proves on a planted fault that it can fail. Nothing is called done, fixed or ready
until this exits 0. `verify/reviews.json` also requires a code review and a UX review on the
current tree.

`verify/run.sh` hands off to a shared runner kept outside this repo (`ORG_CONTEXT_DIR`). Without
it, run the build and then each check in `verify/checks/` directly; each one prints its counts.

## Release
One loop, every time:
1. Edit `sources/` (or `pipeline/` for how the page looks).
2. `bash verify/run.sh` is green.
3. Commit, then push. Once GitHub Pages is on, the push deploys the page.
4. Before publishing, read the live artifact and compare it with the build. Port anything that
   exists only on the live page into `sources/` first: other sessions have published to it
   directly (versions 56–58), and a publish from here would otherwise undo their edits.
   Until the move to Pages is finished, also publish `outputs/argument-map.html` to the existing
   artifact URL (https://claude.ai/artifact/AV8daUJZkgov44mGA2aUsz) from the working session.
   Publishing to that URL updates the page in place; never create a new artifact.
5. Reply to and resolve any comment threads the change answers.
6. Note the commit on the task it closes.

Commit after every content change; the diff of `sources/` is the change log.

## Rules that keep it honest
- Add or change an argument in BOTH `argument-index.md` (prose) and `args.json` (fields). The build fails if they disagree.
- IDs referenced in `front_door.json` and `dependencies.json` must exist in master; the build fails otherwise.
- The tone guard (`pipeline/tone.py`, used by the build and the gate) fails on advocate-vs-adversary language. The page goes to a whole session; keep it readable by anyone holding either view.
- Visible counts are computed, never typed. The gate fails on a typed count.

## Permanent home (GitHub Pages)
Push to `main` and `.github/workflows/pages.yml` builds the page and publishes it.
Enable Pages once in the repo: Settings → Pages → Source: GitHub Actions. The URL will be
`https://<user>.github.io/<repo>/`. Then set `permanent_url` in `sources/front_door.json`
to that address, rebuild, and publish the result to the artifact URL one last time: the artifact
page will show a notice pointing readers to the permanent home. The gate then compares the live
page with the local build byte for byte.

Note: the in-page chat ("Ask") only works when hosted on claude.ai; on Pages the tab hides
itself. Everything else, popovers included, works anywhere.
