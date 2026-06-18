from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path

from . import classes as classlib
from .specs import fork, JitterSpec
from .build import build_dataset
from .artifacts import read_dataset


def _build(args):
    dc = classlib.get(args.cls)
    L = dc.layout
    if args.page:
        L = replace(L, page=(args.page[0], args.page[1]))
    tables = dc.tables
    if args.rows:
        tables = tuple(replace(t, rows=(args.rows[0], args.rows[1])) for t in tables)
    if args.instances:
        tables = tuple(replace(t, instances=(args.instances[0], args.instances[1])) for t in tables)
    S = dc.structure
    if args.header:
        S = replace(S, header=True)
    if args.background:
        S = replace(S, background=args.background)
    layout_kw = {}
    if args.row_gap is not None:
        layout_kw["row_gap"] = args.row_gap
    if args.instance_gap is not None:
        layout_kw["instance_gap"] = args.instance_gap
    if args.section_gap is not None:
        layout_kw["section_gap"] = args.section_gap
    if args.globals_per_row is not None:
        layout_kw["globals_per_row"] = args.globals_per_row
    if layout_kw:
        L = replace(L, **layout_kw)
    jitter = dc.jitter
    if args.jitter:
        jitter = JitterSpec(*args.jitter)
    R = dc.render
    if args.autoscale_font:
        R = replace(R, autoscale_font=True)
    if (L is not dc.layout or tables is not dc.tables or S is not dc.structure
            or jitter is not dc.jitter or R is not dc.render):
        dc = fork(dc, layout=L, tables=tables, structure=S, jitter=jitter, render=R)
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
    tables = spec.get("tables", [])
    fields = [f["name"] for t in tables for f in t.get("fields", [])]
    glds = [f["name"] for f in spec.get("globals", [])]
    page = spec.get("layout", {}).get("page")
    ntok = sum(len(s.words) for s in samples)
    print(f"id:       {m.dataset_id}")
    print(f"class:    {m.config.get('class', '?')}")
    print(f"task:     {m.task}")
    print(f"samples:  {m.count}")
    print(f"words:    {ntok} ({ntok / max(m.count, 1):.1f}/sample)")
    print(f"tables:   {[t.get('name') for t in tables]}")
    print(f"fields:   {fields}")
    print(f"globals:  {glds}")
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
    b.add_argument("--instances", type=int, nargs=2, metavar=("MIN", "MAX"),
                   help="number of instances per table (adds a region label)")
    b.add_argument("--page", type=int, nargs=2, metavar=("W", "H"),
                   help="override page size")
    b.add_argument("--header", action="store_true",
                   help="emit a top header row of field-name words")
    b.add_argument("--background", type=int, default=0, metavar="N",
                   help="scatter N non-table words (belong to no cell) below the table")
    b.add_argument("--row-gap", type=int, metavar="PX", help="gap between data rows")
    b.add_argument("--instance-gap", type=int, metavar="PX", help="gap between table instances")
    b.add_argument("--section-gap", type=int, metavar="PX", help="gap between sections")
    b.add_argument("--globals-per-row", type=int, metavar="N",
                   help="label:value pairs packed across one global row")
    b.add_argument("--jitter", type=float, nargs=4, metavar=("ROW_H", "COL_W", "OFFSET", "BASELINE"),
                   help="per-axis jitter magnitudes (0 = off)")
    b.add_argument("--autoscale-font", action="store_true",
                   help="shrink a table's font to fit when its columns overflow the page width")
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
