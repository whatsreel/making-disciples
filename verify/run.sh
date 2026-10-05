#!/usr/bin/env bash
# verify/run.sh — this project's release gate entrypoint.
#
# Intentionally a SHIM. All the logic lives in one shared runner
# (org-context/verify/runner.sh) so a fix reaches every gated project at once. An
# earlier draft had each project copy the whole runner; that guarantees drift, which
# is the same bug class the gate exists to prevent. Do not inline logic here.
#
# What the shared runner does:
#   - runs every check in verify/checks/ (.sh -> bash, .py -> python, .mjs -> node)
#   - fails if a check exits non-zero, prints no COUNT/SAMPLE line, or PASSES its own
#     `--selftest` (a check that cannot fail is worse than no check)
#   - writes verify/.receipt.json with a source hash the Stop hook re-verifies
#
# Add checks in verify/checks/. See org-context/verify/template/README.md.

set -uo pipefail
ORG_CONTEXT="${ORG_CONTEXT_DIR:-C:/dev/claude/org-context}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec bash "$ORG_CONTEXT/verify/runner.sh" "$(cd "$HERE/.." && pwd)"
