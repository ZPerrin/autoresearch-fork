from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path

from . import classes as classlib
from .specs import fork
from .build import build_dataset
from .artifacts import read_dataset


def _build(args):
    dc = classlib.get(args.cls)
    L = dc.layout
    if args.rows:
        L = replace(L, rows=(args.rows[0], args.rows[1]))
    if args.page:
        L = replace(L, page=(args.page[0], args.page[1]))
    S = dc.structure
    if args.multi_token:
        S = replace(S, multi_token=True)
    if args.header:
        S = replace(S, header=True)
    if args.background:
        S = replace(S, background=args.background)
    if L is not dc.layout or S is not dc.structure:
        dc = fork(dc, layout=L, structure=S)
    out = Path(args.out)
    build_dataset(out.parent, out.name, dc, seed=args.seed, n=args.n)
    print(f"built {args.n} {args.cls} samples -> {out}")


def _list(args):
    root = Path(args.datasets_dir)
    if not root.exists():
        print(f"no datasets dir at {root}")
        return
    found = False
    for d in sorted(p for p in root.iterdir() if (p / "manifest.json").exists()):
        m, _ = read_dataset(d)
        found = True
        print(f"{m.dataset_id:24} {m.config.get('class', '?'):10} n={m.count:<5} {m.created}")
    if not found:
        print(f"no datasets under {root}")


def _inspect(args):
    d = Path(args.datasets_dir) / args.id
    m, samples = read_dataset(d)
    spec = m.config.get("spec", {})
    fields = [f["name"] for f in spec.get("fields", [])]
    page = spec.get("layout", {}).get("page")
    ntok = sum(len(s.tokens) for s in samples)
    print(f"id:       {m.dataset_id}")
    print(f"class:    {m.config.get('class', '?')}")
    print(f"task:     {m.task}")
    print(f"samples:  {m.count}")
    print(f"tokens:   {ntok} ({ntok / max(m.count, 1):.1f}/sample)")
    print(f"fields:   {fields}")
    print(f"page:     {page}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="tablelab.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a synthetic dataset")
    b.add_argument("--class", dest="cls", required=True,
                   help=f"document class {classlib.classes()}")
    b.add_argument("--n", type=int, default=12, help="number of samples")
    b.add_argument("--out", required=True, help="dataset dir, e.g. ../datasets/<id>")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--rows", type=int, nargs=2, metavar=("MIN", "MAX"),
                   help="override record-count range")
    b.add_argument("--page", type=int, nargs=2, metavar=("W", "H"),
                   help="override page size")
    b.add_argument("--multi-token", action="store_true",
                   help="split multi-word cells into per-word tokens (shared record/field + seq)")
    b.add_argument("--header", action="store_true",
                   help="emit a top header row of field-name tokens")
    b.add_argument("--background", type=int, default=0, metavar="N",
                   help="scatter N non-table tokens (label null) below the table")
    b.set_defaults(fn=_build)

    ls = sub.add_parser("list", help="list local datasets")
    ls.add_argument("--datasets-dir", default="../datasets")
    ls.set_defaults(fn=_list)

    ins = sub.add_parser("inspect", help="inspect a dataset")
    ins.add_argument("id")
    ins.add_argument("--datasets-dir", default="../datasets")
    ins.set_defaults(fn=_inspect)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
