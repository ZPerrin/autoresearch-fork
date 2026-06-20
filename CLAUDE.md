@AGENTS.md

## Claude Code notes

- `AGENTS.md` (imported above) is the operating guide — layout, commands, conventions, and the
  bearings protocol into `docs/architecture/`. Read it first; what the project *is* lives in the charter.
- Durable direction lives in `docs/architecture/`: the charter (why), roadmap (milestones + now/next),
  index (what exists today), conventions (how docs work). Get bearings there plus `git log`.
- Use the available skills (superpowers et al.); brainstorm/design before building non-trivial
  features, and review work (run it) before claiming it's done.
- Repo-local, portable project memory lives here + in `AGENTS.md`. Auto memory
  (`~/.claude/projects/.../memory/`) is machine-local and not shared across machines — prefer
  putting durable, shareable context in `AGENTS.md`.
