#!/usr/bin/env bash
# Thin bearings push (Claude Code only): live git recency + the roadmap's current focus.
# Portable grounding (read index/roadmap) lives in AGENTS.md — this hook is not load-bearing.
set -euo pipefail
root="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
cd "$root"

echo "## Bearings — recent activity (from git)"
echo
git log --oneline -15 2>/dev/null || echo "(no git history)"

roadmap="docs/architecture/roadmap.md"
if [ -f "$roadmap" ]; then
  echo
  echo "## Roadmap — Now"
  awk '/^## Now/{f=1; next} /^## /{f=0} f' "$roadmap"
fi
