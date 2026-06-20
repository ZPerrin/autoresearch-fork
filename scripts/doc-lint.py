#!/usr/bin/env python3
"""doc-lint — link hygiene for the managed Markdown docs.

Two checks, scoped to the durable docs + root guides + skills:

  BROKEN  — a relative link that does not resolve.
  MISSING — a navigation/structure list item of the form `- `path` — desc`
            whose path resolves (file-relative) to a real repo path but is not
            a link. This is the negative space a resolve-check alone can't see;
            the rule lives in docs/architecture/conventions.md ("path
            references in navigation lists are links"). Definitional prose
            bullets (path followed by a verb, not an em-dash) are left alone.

Advisory: prints findings; exits 1 if any, 0 if clean. The /wrap and
/refine-docs skills run this and fix what it flags.
"""
from __future__ import annotations
import re
import sys
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
LEAD_PATH = re.compile(r"^\s*[-*]\s+`([^`]+)`\s*—")  # `- `path` — description` (nav/structure list)


def is_ignored(target: pathlib.Path) -> bool:
    """True if git ignores the path — gitignored dirs (e.g. datasets/) won't
    exist on GitHub, so they must stay code-spans, not links."""
    return subprocess.run(
        ["git", "check-ignore", "-q", str(target)], cwd=ROOT
    ).returncode == 0


def managed() -> list[pathlib.Path]:
    files = sorted((ROOT / "docs/architecture").glob("*.md"))
    files += [ROOT / p for p in ("AGENTS.md", "README.md", "CLAUDE.md") if (ROOT / p).exists()]
    files += sorted((ROOT / ".claude/skills").glob("*/SKILL.md"))
    return files


def main() -> int:
    findings: list[str] = []
    for md in managed():
        rel = md.relative_to(ROOT)
        for line in md.read_text().splitlines():
            # BROKEN: every relative link on the line must resolve.
            for m in LINK.finditer(line):
                href = m.group(1).split("#")[0].strip()
                if not href or href.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (md.parent / href).resolve().exists():
                    findings.append(f"BROKEN  {rel}: {href}")
            # MISSING: a list-item-lead path that resolves (file-relative) but isn't linked.
            lead = LEAD_PATH.match(line)
            if lead and "](" not in line:
                span = lead.group(1)
                if "/" in span or "." in span:
                    target = (md.parent / span).resolve()
                    if target.exists() and target != md.resolve() and not is_ignored(target):
                        findings.append(f"MISSING {rel}: list path `{span}` should be a link")
    for f in findings:
        print(f)
    if not findings:
        print("doc-lint: clean ✓")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
