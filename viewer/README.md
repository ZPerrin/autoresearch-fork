# viewer

Local Vite + React + TypeScript review app for the autoresearch harness. Two-pane layout:
**left** = the document page image with the token-box overlay; **right** = source picker
(datasets / runs), metadata, and selected-token detail.

## Run

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # type-check + production build
```

A Vite dev-server middleware serves the repo-root `runs/` and `datasets/` at `/runs` and
`/datasets` (JSON + PNG images) — there is **no backend**. The app reads only the static artifact
contract (schema v2): `runs/index.json`, `runs/<id>/{run,samples}.json`, and
`datasets/<id>/{manifest,samples}.json` + `images/`.

Box coloring: teal = prediction matches label, red = mismatch, neutral = ground truth (no
prediction). See `../AGENTS.md` for conventions and `../docs/specs/` for the design.
