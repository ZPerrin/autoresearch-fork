@AGENTS.md

## Claude Code notes

- `AGENTS.md` (imported above) is the source of truth for what this project is, its layout,
  commands, and conventions. Read it first.
- Authoritative design + roadmap: `docs/specs/2026-06-13-design-and-roadmap.md`. The **active
  milestone is the synthetic data toolkit**; the ML model loop is deferred.
- Use the available skills (superpowers et al.); brainstorm/design before building non-trivial
  features, and review work (run it) before claiming it's done.
- Repo-local, portable project memory lives here + in `AGENTS.md`. Auto memory
  (`~/.claude/projects/.../memory/`) is machine-local and not shared across machines — prefer
  putting durable, shareable context in `AGENTS.md`.
