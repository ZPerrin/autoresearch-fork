---
kind: plan
status: scaffolding
updated: 2026-06-21
---

# Doc-Harness Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt Jack's five-skill doc-harness family onto autoresearch-fork by porting the machinery, then dogfooding `/init-docs` to migrate this repo's doc tree to the canonical module-README topology, closing out with the explicit-merge convention.

**Architecture:** Two stages. Stage 1 is mechanical — copy the 5 skill directories + `init-docs`'s templates from Jack into `.claude/skills/`. Stage 2 is operator-in-the-loop — run the ported `/init-docs`, `/refine-linter`, `/refine-context` skills to generate and tune this repo's live linter + bearings hook and restructure the docs, then `/wrap` to close out. There is no application code and no TDD; the **verification gates are the harness's own**: `doc-lint.py` exits 0, and `source-doc-context.py` runs clean.

**Tech Stack:** Markdown docs, Python doc tooling (`doc-lint.py`, `source-doc-context.py`), git worktrees, Claude Code skills. Run Python as `python` on this Windows host (Jack's SKILL.md prose says `python3`).

**Locations:**
- Work dir (worktree, on `harness/doc-harness-port`): `C:/Users/Zebulon/IdeaProjects/autoresearch-fork/.claude/worktrees/harness+doc-harness-port`
- Port source (Jack, read-only): `C:/Users/Zebulon/Software Projects/jack/.claude/skills`

**File structure (what each ported artifact owns):**
- `.claude/skills/init-docs/SKILL.md` + `templates/{doc-lint.py,source-doc-context.py}` — generative scaffolder + the two seed templates (with `init-docs:`-marked fill lists).
- `.claude/skills/refine-context/SKILL.md` — owns the bearings slice script.
- `.claude/skills/refine-linter/SKILL.md` — owns the linter, reconciled to `docs/README.md`.
- `.claude/skills/refine-docs/SKILL.md` + `doc-lint.py` — whole-tree reconciliation; the live linter is **bundled here** (seeded from the template by `/init-docs`).
- `.claude/skills/wrap/SKILL.md` — session-delta distillation + branch close-out (the merge convention).
- `.claude/hooks/source-doc-context.py` — live bearings hook (seeded by `/init-docs`), replaces `session-bearings.sh`.
- `docs/README.md` — new doc source-of-truth; `docs/config/{roadmap,charter}.md`; per-module `README.md`s. (Authored during Stage 2, not pre-scripted.)

---

### Task 1: Port the skill machinery (mechanical)

Copy the five skill directories from Jack. Overwrite the two skills that already exist here (`refine-docs`, `wrap`) with Jack's newer versions; add the three new ones. Copy `init-docs`'s templates but **not** Jack's live `refine-docs/doc-lint.py` or `.claude/hooks/source-doc-context.py` — those encode Jack's module set; ours are generated in Task 2 from the templates.

**Files:**
- Create: `.claude/skills/init-docs/SKILL.md`, `.claude/skills/init-docs/templates/doc-lint.py`, `.claude/skills/init-docs/templates/source-doc-context.py`
- Create: `.claude/skills/refine-context/SKILL.md`, `.claude/skills/refine-linter/SKILL.md`
- Modify (overwrite): `.claude/skills/refine-docs/SKILL.md`, `.claude/skills/wrap/SKILL.md`

- [ ] **Step 1: Copy the five SKILL.md files + init-docs templates**

```bash
cd "C:/Users/Zebulon/IdeaProjects/autoresearch-fork/.claude/worktrees/harness+doc-harness-port"
SRC="C:/Users/Zebulon/Software Projects/jack/.claude/skills"
DST=".claude/skills"
mkdir -p "$DST/init-docs/templates" "$DST/refine-context" "$DST/refine-linter"
cp "$SRC/init-docs/SKILL.md"                       "$DST/init-docs/SKILL.md"
cp "$SRC/init-docs/templates/doc-lint.py"          "$DST/init-docs/templates/doc-lint.py"
cp "$SRC/init-docs/templates/source-doc-context.py" "$DST/init-docs/templates/source-doc-context.py"
cp "$SRC/refine-context/SKILL.md"                  "$DST/refine-context/SKILL.md"
cp "$SRC/refine-linter/SKILL.md"                   "$DST/refine-linter/SKILL.md"
cp "$SRC/refine-docs/SKILL.md"                     "$DST/refine-docs/SKILL.md"
cp "$SRC/wrap/SKILL.md"                            "$DST/wrap/SKILL.md"
```

- [ ] **Step 2: Verify structure landed**

Run:
```bash
find .claude/skills -type f | sort
```
Expected: the 7 files above present (init-docs SKILL + 2 templates, refine-context SKILL, refine-linter SKILL, refine-docs SKILL, wrap SKILL), plus pre-existing `refine-docs`/`wrap` now overwritten. No stray `__pycache__`.

- [ ] **Step 3: Verify the templates are valid Python**

Run:
```bash
python -m py_compile .claude/skills/init-docs/templates/doc-lint.py .claude/skills/init-docs/templates/source-doc-context.py && echo "templates compile OK"
```
Expected: `templates compile OK` (no traceback).

- [ ] **Step 4: Commit the machinery**

```bash
git add .claude/skills
git commit -m "$(cat <<'EOF'
feat(harness): port Jack's doc-harness skill family

Add init-docs (generative scaffolder + seed templates), refine-context
(bearings slice), refine-linter (linter reconciler); update refine-docs
and wrap to Jack's versions (wrap gains the branch close-out / explicit-
merge flow). Live linter + bearings hook are generated next via /init-docs.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT:** Pause for review. The skills now reference a canonical topology (`docs/README.md`, module READMEs, `.claude/skills/refine-docs/doc-lint.py`) that does not exist yet — that's expected; Task 2 builds it.

---

### Task 2: Migrate the doc topology via `/init-docs` (interactive)

Drive the ported `/init-docs` skill in its existing-repo "detect-and-adapt" path. This is a facilitator loop — the skill maps existing content into canonical homes and asks for decisions; do not pre-script its edits. Steer it toward the decisions already settled in the spec.

**Files (created/moved by the skill, for reference):**
- Create: `docs/README.md` (fold ethos from `docs/architecture/conventions.md`)
- Create: `docs/config/roadmap.md`, `docs/config/charter.md` (moved from `docs/architecture/`)
- Modify: `harness/README.md`, `viewer/README.md` → canonical headers (`## Overview` stamped + `## Setup`/`## Structure`/`## Agentic Guidelines`/`## Agentic Validation`); fold relevant `docs/architecture/index.md` content into their `## Overview`
- Create: `.claude/skills/refine-docs/doc-lint.py`, `.claude/hooks/source-doc-context.py` (seeded from templates, filled for our modules)
- Modify: `AGENTS.md` (slim to router + GLOBAL guidelines), `.claude/settings.json` (point `SessionStart` at the new hook)
- Delete (once superseded): `docs/architecture/` tree, `scripts/doc-lint.py`, `.claude/hooks/session-bearings.sh`

- [ ] **Step 1: Invoke the skill**

Invoke `/init-docs`. Confirm it detects an existing repo (not blank) and enters detect-and-adapt.

- [ ] **Step 2: Settle the two foundation decisions**

Drive these per the spec:
- **Project identity:** keep the root `README.md` `## Overview` + derive `## Module Map` from real top-level dirs.
- **Module set:** `harness/` and `viewer/` are modules (own canonical README). `runs/` documented as a tracked dir, not a module. `datasets/` (gitignored), `reference/` (parked), `worktrees/` (gitignored) are not modules.
- **Doc location:** keep `docs/`; author `docs/README.md` as source-of-truth (fold ethos from `docs/architecture/conventions.md`); relocate roadmap + charter to `docs/config/`.

- [ ] **Step 3: Let the skill seed the tooling from templates**

Confirm `/init-docs` copies `templates/doc-lint.py` → `.claude/skills/refine-docs/doc-lint.py` and `templates/source-doc-context.py` → `.claude/hooks/source-doc-context.py`, fills the `init-docs:`-marked lists with our module set + `docs/` dirs, and rewires `.claude/settings.json`'s `SessionStart` hook to the new python hook.

- [ ] **Step 4: Run the skill's self-check**

Run:
```bash
python .claude/skills/refine-docs/doc-lint.py
```
Expected: `doc-lint: clean ✓` (exit 0). If it flags issues, fix the docs (not the linter) until clean.

- [ ] **Step 5: Remove superseded artifacts (only after the new ones are proven)**

```bash
git rm scripts/doc-lint.py .claude/hooks/session-bearings.sh
git rm -r docs/architecture
```
Re-run `python .claude/skills/refine-docs/doc-lint.py` — expected still `clean ✓` (no dangling links to the removed tree).

- [ ] **Step 6: Commit the migration**

```bash
git add -A
git commit -m "$(cat <<'EOF'
docs(harness): migrate doc tree to canonical module-README topology

Author docs/README.md as the doc source-of-truth; distribute the old
index.md map into harness/ and viewer/ module READMEs; relocate roadmap +
charter to docs/config/; seed the bundled linter and source-doc-context.py
bearings hook from init-docs templates and rewire SessionStart. Remove the
superseded docs/architecture tree, scripts/doc-lint.py, and session-bearings.sh.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT:** Pause for review of the restructured tree before refining the two generated artifacts.

---

### Task 3: Finalize the linter via `/refine-linter` (interactive)

Reconcile the seeded `doc-lint.py` against the freshly authored `docs/README.md` so its kinds/statuses, path globs, module-README list, and canonical headers exactly match what the doc declares.

- [ ] **Step 1: Invoke `/refine-linter`.** Confirm it reads `docs/README.md` + the seeded `.claude/skills/refine-docs/doc-lint.py` and lists any disagreements (e.g. a module README not in `stamped_readmes()`).

- [ ] **Step 2: Reconcile each disagreement with confirmation.** Apply the linter edits the skill proposes; keep it plain Python (no runtime prose parsing).

- [ ] **Step 3: Prove clean.** Run:
```bash
python .claude/skills/refine-docs/doc-lint.py
```
Expected: `doc-lint: clean ✓`.

- [ ] **Step 4: Commit (only if the linter changed).**
```bash
git add .claude/skills/refine-docs/doc-lint.py
git commit -m "chore(harness): reconcile doc-lint.py to docs/README.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
If `/refine-linter` reports linter and doc already agreed, skip this commit.

---

### Task 4: Tune the bearings slice via `/refine-context` (interactive)

Tune `source-doc-context.py`'s slice list (the `section(...)` / `module(...)` calls) to materialize the right opening context for this repo: git recency, roadmap `## Now` + `## Milestones`, root `## Module Map`, each module README `## Overview`.

- [ ] **Step 1: Invoke `/refine-context`.** Confirm it reads the current slice list and renders the actual context with rough per-slice cost.

- [ ] **Step 2: Tune with the operator.** Drop/add/reorder slices until the always-on tax is justified. Re-run and re-show each iteration.

- [ ] **Step 3: Land it.** Run:
```bash
python -m py_compile .claude/hooks/source-doc-context.py && python .claude/hooks/source-doc-context.py
```
Expected: compiles clean and prints the bearings context (no traceback). Confirm `.claude/settings.json` `SessionStart` points at this hook.

- [ ] **Step 4: Commit.**
```bash
git add .claude/hooks/source-doc-context.py .claude/settings.json
git commit -m "feat(harness): bearings slice hook tuned for this repo

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Full-tree verification gate

Before close-out, prove the whole harness is coherent and the tree is clean.

- [ ] **Step 1: Linter clean.** Run `python .claude/skills/refine-docs/doc-lint.py` → expected `doc-lint: clean ✓` (exit 0).
- [ ] **Step 2: Bearings clean.** Run `python .claude/hooks/source-doc-context.py` → expected: prints context, exit 0.
- [ ] **Step 3: No stray files.** Run `git status --porcelain` → expected: empty (every change committed; no untracked `??` or deleted ` D` paths). Surface and resolve anything listed.
- [ ] **Step 4: Skill links resolve.** Spot-check that ported SKILL.md relative links now resolve against the new tree (e.g. `docs/README.md`, `docs/config/roadmap.md`, `.claude/skills/refine-docs/doc-lint.py` all exist).

---

### Task 6: Close out via `/wrap` — explicit merge into master (gated on confirmation)

Dogfood the new `wrap` close-out flow. **Do not merge without explicit user confirmation.**

- [ ] **Step 1: Invoke `/wrap`.** Let it distill any session delta into the durable layer (likely minimal — this work is itself the harness). Stage the doc diff.
- [ ] **Step 2: Answer the close-out prompt.** When `wrap` asks "close out this branch by merging? into which branch?", **first confirm with the user.** Target: `master`.
- [ ] **Step 3: Gate.** `wrap` re-runs the linter (`clean ✓`) and `git status --porcelain` (no stray files). Do not merge through a failing gate.
- [ ] **Step 4: Commit the sync** (if `wrap` distilled anything) on the branch: `docs(wrap): <what was distilled>` with the trailer.
- [ ] **Step 5: Merge with explicit commit.** From the main dir on `master`:
```bash
cd "C:/Users/Zebulon/IdeaProjects/autoresearch-fork"
git checkout master
git merge --no-ff harness/doc-harness-port -m "$(cat <<'EOF'
Merge harness/doc-harness-port: adopt the doc-harness skill family

Ports init-docs, refine-context, refine-docs, refine-linter, wrap from the
Jack project and migrates the doc tree to the canonical module-README
topology (docs/README.md source-of-truth, docs/config/, bundled linter,
sliced bearings hook). wrap now closes out branches with this explicit merge.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
`--no-ff` is required (always an explicit merge commit, never fast-forward). Re-run `python .claude/skills/refine-docs/doc-lint.py` on `master` → expected `clean ✓`.
- [ ] **Step 6: Clean up the worktree (on confirmation).** `ExitWorktree` (remove) for the harness-managed worktree, then `git worktree prune`. Skip if keeping it.

---

## Notes on verification philosophy

There is no unit-test suite for this work — it is documentation + tooling. The gates that stand in for tests are: (1) `doc-lint.py` exits 0 (link hygiene + frontmatter/stamp coherence proves the cross-reference web), and (2) `source-doc-context.py` compiles and runs. Every task ends on one of these or a structural `find`/`git status` check. Tasks 2–4 are interactive skill runs: their "steps" are invoke-and-steer, and the operator confirms each consequential edit per those skills' own facilitator loops.
