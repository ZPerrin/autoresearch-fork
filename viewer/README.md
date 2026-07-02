---
kind: readme
status: living
updated: 2026-07-01
---
# viewer

Local Vite + React + TypeScript review app for the autoresearch harness. Two-pane layout:
**left** = the document page image with an interactive structure overlay; **right** = source
picker (datasets / runs), metadata, and selected-element detail.

## Overview

Split-pane review app, no backend — a Vite dev-server middleware serves the repo-root `runs/` and
`datasets/` at `/runs` and `/datasets` (JSON + PNG), and the app reads only the static schema-v5
contract. Left pane: the page image under a selectable **overlay lens** — raw / words / cells /
regions / key-value / composed — with role-colored clickable words, role-outlined cells, and an
Alt-hover normalized-coordinate HUD. Right pane: metadata + selected-element detail, and (in progress)
the grounded `fields` / `field_groups` target tree with a first-pass prediction diff.

## Setup

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # type-check + production build
```

A Vite dev-server middleware serves the repo-root `runs/` and `datasets/` at `/runs` and
`/datasets` (JSON + PNG images) — there is **no backend**. The app reads only the static artifact
contract (schema v5): `runs/index.json`, `runs/<id>/{run,samples}.json`, and
`datasets/<id>/{manifest,samples}.json` + `images/`.

## Overlay

The overlay is a set of mutually-exclusive **view modes** (one lens at a time), tier-colored
(primary green / alt blue / tertiary purple) and switched from the top sub-nav:

- **Words** — every word box.
- **Composed** — header / section / summary cells, drawn as their member word boxes.
- **Cells** — full cell outlines.
- **Key/Val** — key & value cells.
- **Regions** — table / form container bounds.

Click any box to select it (neon-pink); the right pane shows full detail for the selected
word / cell / region. Hold **Alt** while hovering to read normalized `[0,1]` coordinates; pan by
drag and zoom at the pointer (see the in-app **Controls** popover for the full list).

## Agentic Validation

- `npm install`, then `npm run dev` → http://localhost:5173 for interactive review.
- `npm run build` — type-check + production build; the smallest check that a change compiles.
