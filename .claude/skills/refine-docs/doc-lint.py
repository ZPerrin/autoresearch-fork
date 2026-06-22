#!/usr/bin/env python3
"""doc-lint (init-docs seed) — hygiene for the managed Markdown docs.

This is the STARTER the `/init-docs` skill drops into a fresh repo so that
`/refine-linter` has a working artifact to reconcile against `docs/README.md`.
It is a faithful, generic copy of the canonical linter; the only repo-specific
parts are the two lists marked `init-docs: fill ...` below — set them from the
Module Map and the docs/ layout, then `/refine-linter` keeps them honest.

Link checks (every managed doc):

  BROKEN   — a relative link that does not resolve.
  CODELINK — a link whose text is a code-span (`[`path`](path)`), which renders
             as code rather than a clean link. Repo-path links are plain:
             `[path](path)`; backtick code-spans are reserved for concepts and
             non-path mentions.
  MISSING  — a navigation/structure list item of the form `- `path` — desc`
             whose path resolves (file-relative) to a real repo path but is not
             a link. The rule lives in docs/README.md.

Stamping checks enforce the two-tier convention from docs/README.md:

  FRONTMATTER — docs under docs/ + AGENTS.md must open with valid frontmatter
                (`kind` in the enum, `status` in the enum, ISO `updated`).
  STAMP       — the root + module READMEs stay frontmatter-free (clean GitHub
                render) and instead carry a `## Overview` with an
                `_updated: YYYY-MM-DD_` stamp.

Advisory: prints findings; exits 1 if any, 0 if clean. The /wrap and
/refine-docs skills run this and fix what it flags.
"""
from __future__ import annotations
import re
import sys
import pathlib
import subprocess

def _repo_root() -> pathlib.Path:
    """Repo root via git — independent of where this script lives (skill dir,
    plugin cache, or scripts/). Falls back to cwd outside a work tree."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True)
        return pathlib.Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return pathlib.Path.cwd()


ROOT = _repo_root()
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODELINK = re.compile(r"\[`([^`]+)`\]\(")            # `[`text`](…)` — code-styled link, not a clean link
LEAD_PATH = re.compile(r"^\s*[-*]\s+`([^`]+)`\s*—")  # `- `path` — description` (nav/structure list)

# init-docs: these enums mirror the frontmatter block in docs/README.md "Nomenclature".
# Start with the canonical defaults; /refine-linter trims/extends to match the doc.
KINDS = {"charter", "roadmap", "readme", "guide", "reference",
         "spec", "plan", "design", "review"}
STATUSES = {"living", "hardened", "superseded", "scaffolding", "ideation"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OVERVIEW = re.compile(r"^##\s+Overview\s*$")
STAMP = re.compile(r"^_updated:\s*\d{4}-\d{2}-\d{2}_?\s*$")


def is_ignored(target: pathlib.Path) -> bool:
    """True if git ignores the path — gitignored dirs won't exist on GitHub,
    so they must stay code-spans, not links."""
    return subprocess.run(
        ["git", "check-ignore", "-q", str(target)], cwd=ROOT
    ).returncode == 0


def frontmatter_docs() -> list[pathlib.Path]:
    """Tier 1: the docs/ durable tree + AGENTS.md — must carry doc frontmatter.
    init-docs: the `sub` tuple is the docs/ "Module Map" (the doc index) — add/remove dirs to match."""
    files = [ROOT / "AGENTS.md", ROOT / "docs/README.md"]
    for sub in ("config", "specs", "plans", "design"):
        files += sorted((ROOT / "docs" / sub).glob("*.md"))
    return [f for f in files if f.exists()]


def stamped_readmes() -> list[pathlib.Path]:
    """Tier 2: root + module READMEs — frontmatter-free; carry a stamped `## Overview`.
    init-docs: fill one entry per module from the Module Map, e.g. "backend/README.md".
    /refine-linter keeps this list in sync as modules are added or removed."""
    rel = (
        "README.md",
        "harness/README.md",
        "viewer/README.md",
    )
    return [ROOT / p for p in rel if (ROOT / p).exists()]


def skill_docs() -> list[pathlib.Path]:
    # Skills carry the Claude Code name/description frontmatter, not the doc
    # schema — link-checked only.
    return sorted((ROOT / ".claude/skills").glob("*/SKILL.md"))


def link_checked() -> list[pathlib.Path]:
    return frontmatter_docs() + stamped_readmes() + skill_docs()


def check_links(md: pathlib.Path, rel: pathlib.Path, findings: list[str]) -> None:
    in_fence = False
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):  # don't lint inside fenced code blocks
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # BROKEN: every relative link on the line must resolve.
        for m in LINK.finditer(line):
            href = m.group(1).split("#")[0].strip()
            if not href or href.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / href).resolve().exists():
                findings.append(f"BROKEN   {rel}: {href}")
        # CODELINK: link text wrapped in a code-span renders as code, not a link.
        for m in CODELINK.finditer(line):
            findings.append(f"CODELINK {rel}: `{m.group(1)}` — use plain link text [{m.group(1)}](…)")
        # MISSING: a list-item-lead path that resolves (file-relative) but isn't linked.
        lead = LEAD_PATH.match(line)
        if lead and "](" not in line:
            span = lead.group(1)
            if "/" in span or "." in span:
                target = (md.parent / span).resolve()
                if target.exists() and target != md.resolve() and not is_ignored(target):
                    findings.append(f"MISSING {rel}: list path `{span}` should be a link")


def check_frontmatter(md: pathlib.Path, rel: pathlib.Path, findings: list[str]) -> None:
    lines = md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        findings.append(f"FRONTMATTER {rel}: missing frontmatter (expected `---` on line 1)")
        return
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    if fm.get("kind") not in KINDS:
        findings.append(f"FRONTMATTER {rel}: kind={fm.get('kind')!r} not in {sorted(KINDS)}")
    if fm.get("status") not in STATUSES:
        findings.append(f"FRONTMATTER {rel}: status={fm.get('status')!r} not in {sorted(STATUSES)}")
    if not ISO_DATE.match(fm.get("updated", "")):
        findings.append(f"FRONTMATTER {rel}: updated={fm.get('updated')!r} not an ISO date (YYYY-MM-DD)")


def check_overview_stamp(md: pathlib.Path, rel: pathlib.Path, findings: list[str]) -> None:
    lines = md.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        findings.append(f"STAMP {rel}: README should stay frontmatter-free (use a stamped `## Overview`)")
    for i, line in enumerate(lines):
        if OVERVIEW.match(line):
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    continue
                if not STAMP.match(nxt.strip()):
                    findings.append(f"STAMP {rel}: `## Overview` missing `_updated: YYYY-MM-DD_` stamp")
                return
            findings.append(f"STAMP {rel}: `## Overview` missing `_updated: YYYY-MM-DD_` stamp")
            return
    findings.append(f"STAMP {rel}: missing `## Overview` section")


def main() -> int:
    # Windows consoles default to cp1252; force UTF-8 so the ✓ and the em-dashes
    # in findings print instead of raising UnicodeEncodeError on a clean run.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    findings: list[str] = []
    for md in link_checked():
        check_links(md, md.relative_to(ROOT), findings)
    for md in frontmatter_docs():
        check_frontmatter(md, md.relative_to(ROOT), findings)
    for md in stamped_readmes():
        check_overview_stamp(md, md.relative_to(ROOT), findings)
    for f in findings:
        print(f)
    if not findings:
        print("doc-lint: clean ✓")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
