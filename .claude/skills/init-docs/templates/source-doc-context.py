#!/usr/bin/env python3
"""source-doc-context (init-docs seed) — SessionStart documentation slice.

This is the STARTER the `/init-docs` skill drops into a fresh repo so `/refine-context`
has a working artifact to tune. stdout is injected as each session's opening context:
the next ring of progressive disclosure — the context AGENTS.md only points at — so a
session boots already holding it. AGENTS.md/CLAUDE.md are free (always-on) and NOT
re-pushed here.

The helpers below are generic; the only repo-specific part is the slice list at the
bottom of main() — uncomment one `module("<dir>")` per module from the root README
Module Map, then `/refine-context` trims/reorders it against the always-on token tax.
Each `section(...)` / `module(...)` call targets a canonical sliceable header (see
docs/README.md "Canonical headers (sliceable)").
"""
from __future__ import annotations
import re
import sys
import pathlib
import subprocess


def repo_root() -> pathlib.Path:
    """Repo root via git — independent of where this script lives. Falls back to cwd."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True)
        return pathlib.Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return pathlib.Path.cwd()


ROOT = repo_root()


def section(rel: str, header: str) -> list[str]:
    """The markdown under "<header>" in <rel>: from the header line to the next "## "
    sibling (or EOF), header line included. Missing file or header → empty list."""
    path = ROOT / rel
    if not path.exists():
        return []
    out: list[str] = []
    capturing = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == header:
            out.append(line)
            capturing = True
            continue
        if capturing and line.startswith("## "):
            break
        if capturing:
            out.append(line)
    return out


def map_line(dir_name: str) -> str:
    """The root README Module-Map bullet for <dir_name> (live, so descriptions stay
    DRY), minus the leading '- '. Empty if absent."""
    readme = ROOT / "README.md"
    if not readme.exists():
        return ""
    for line in readme.read_text(encoding="utf-8").splitlines():
        if f"[{dir_name}]" in line:
            return re.sub(r"^- ", "", line)
    return ""


def emit_body(lines: list[str]) -> None:
    """Print a section minus its header line (the "## …" first line)."""
    for line in lines[1:]:
        print(line)


def module(dir_name: str) -> None:
    """One module inline: its Module-Map line as a '### ' heading, then that module's
    README `## Overview` body."""
    line = map_line(dir_name)
    if line:
        print(f"### {line}")
    emit_body(section(f"{dir_name}/README.md", "## Overview"))
    print()


def main() -> int:
    # Windows consoles default to cp1252; force UTF-8 so em-dashes print.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # --- slice list: what each session boots with. Edit these lines. ---
    # Each block gets an italic preamble that nods to its purpose, so a booting
    # session knows what each slice *is* — the next ring of progressive disclosure
    # past AGENTS.md, pointing at the deeper docs rather than replacing them.
    print("_The slices below are your opening context — the next ring of progressive "
          "disclosure past AGENTS.md. Each points at deeper docs; read those when a "
          "task goes past the slice._\n")

    print("## Bearings — recent activity (from git)\n")
    print("_Where the work just was, newest first:_\n")
    log = subprocess.run(["git", "log", "--oneline", "-15"], cwd=ROOT,
                         capture_output=True, text=True)
    print(log.stdout.strip() or "(no git history)")
    print()

    now = section("docs/config/roadmap.md", "## Now")
    if now:
        # Preamble stands in for the "## Now" header — emit the body only.
        print("_A slice of the currently active milestone — the increment in flight:_\n")
        emit_body(now)
        print()

    print("## Module Map\n")
    print("_Slices of context from each module, pointing at the deeper module docs:_\n")
    # init-docs: one module() call per module, from the root README Module Map:
    # module("backend")
    # module("frontend")
    # docs renders like a module, then appends its own ## Module Map (the doc index):
    # module("docs")
    # emit_body(section("docs/README.md", "## Module Map"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
