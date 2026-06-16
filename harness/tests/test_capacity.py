from __future__ import annotations

import json
import os
import random
from dataclasses import replace

import pytest

from tablelab import classes as classlib
from tablelab import build as build_module
from tablelab import layout as layout_module
from tablelab.build import _validate_boxes, build_dataset
from tablelab.layout import LayoutCapacityError, layout, layout_with_regions, validate_layout_capacity
from tablelab.specs import fork


def _full_eob(**layout_overrides):
    dc = classlib.get("eob")
    tables = tuple(replace(table, instances=(1, 3)) for table in dc.tables)
    # The eob recipe now adds banner + section + totals rows per instance; give the
    # maxed-out stress config (instances 1-3, background 4) a taller page so 2-3
    # instances remain feasible. Callers that test the too-short path override `page`.
    layout_overrides.setdefault("page", (1500, 2000))
    return fork(
        dc,
        tables=tables,
        layout=replace(dc.layout, **layout_overrides),
        structure=replace(
            dc.structure, header=True, multi_token=True, background=4
        ),
    )


def test_full_eob_cells_stay_within_page_across_seeds():
    dc = _full_eob()
    width, height = dc.layout.page

    for seed in range(200):
        for token in layout(dc, random.Random(seed)):
            x0, y0, x1, y1 = token.cell
            assert 0 <= x0 <= x1 <= width
            assert 0 <= y0 <= y1 <= height


def test_full_eob_background_slots_stay_within_page_across_1000_seeds():
    dc = _full_eob()
    height = dc.layout.page[1]

    for seed in range(1000):
        placed = layout(dc, random.Random(seed))
        assert max(token.cell[3] for token in placed) <= height


def test_full_eob_samples_feasible_region_counts():
    dc = _full_eob()
    observed = set()

    for seed in range(200):
        _tokens, _cells, regions = layout_with_regions(dc, random.Random(seed))
        # count only table regions (exclude the globals form region)
        observed.add(sum(1 for r in regions if r.type == "table"))

    assert observed <= {1, 2, 3}
    assert {1, 2} <= observed


def test_too_short_page_fails_capacity_validation():
    with pytest.raises(LayoutCapacityError, match="no page-feasible document shape"):
        validate_layout_capacity(_full_eob(page=(1000, 500)))


def test_impossible_build_fails_before_creating_output(tmp_path):
    output = tmp_path / "impossible-eob"

    with pytest.raises(LayoutCapacityError, match="no page-feasible document shape"):
        build_dataset(tmp_path, output.name, _full_eob(page=(1000, 500)), n=1)

    assert not output.exists()


def test_late_render_failure_leaves_no_output_or_staging(tmp_path, monkeypatch):
    original_render = build_module.render
    render_count = 0

    def fail_on_second_sample(placed, doc_class):
        nonlocal render_count
        image, boxes = original_render(placed, doc_class)
        render_count += 1
        if render_count == 2:
            boxes[0] = (-1, *boxes[0][1:])
        return image, boxes

    monkeypatch.setattr(build_module, "render", fail_on_second_sample)

    with pytest.raises(
        ValueError, match="invalid rendered box in dataset 'late-failure' sample 1"
    ):
        build_dataset(tmp_path, "late-failure", classlib.get("invoice"), n=2)

    assert not (tmp_path / "late-failure").exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("box_delta", [-1, 1])
def test_box_cardinality_failure_cleans_output(tmp_path, monkeypatch, box_delta):
    original_render = build_module.render
    counts = None

    def render_with_wrong_cardinality(placed, doc_class):
        nonlocal counts
        image, boxes = original_render(placed, doc_class)
        if box_delta < 0:
            boxes = boxes[:box_delta]
        else:
            boxes = [*boxes, boxes[-1]]
        counts = (len(placed), len(boxes))
        return image, boxes

    monkeypatch.setattr(build_module, "render", render_with_wrong_cardinality)

    with pytest.raises(ValueError) as exc_info:
        build_dataset(tmp_path, "cardinality", classlib.get("invoice"), n=1)

    placed_count, box_count = counts
    assert str(exc_info.value) == (
        "dataset 'cardinality' sample 0: rendered token cardinality mismatch: "
        f"placed={placed_count}, boxes={box_count}"
    )
    assert list(tmp_path.iterdir()) == []


def test_existing_dataset_is_not_overwritten(tmp_path):
    output = tmp_path / "curated"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep me")

    with pytest.raises(FileExistsError, match="dataset already exists"):
        build_dataset(tmp_path, output.name, classlib.get("invoice"), n=1)

    assert sentinel.read_text() == "keep me"
    assert list(output.iterdir()) == [sentinel]
    assert list(tmp_path.iterdir()) == [output]


def test_live_build_lock_rejects_build_and_preserves_staging(tmp_path):
    lock = tmp_path / ".concurrent.build.lock"
    staging = tmp_path / ".concurrent.staging-live"
    staging.mkdir()
    sentinel = staging / "sentinel.txt"
    sentinel.write_text("keep me")
    lock.write_text(json.dumps({"pid": os.getpid(), "staging": str(staging)}))

    with pytest.raises(FileExistsError, match="dataset build already in progress"):
        build_dataset(tmp_path, "concurrent", classlib.get("invoice"), n=1)

    assert lock.exists()
    assert sentinel.read_text() == "keep me"


def test_stale_build_lock_recovers_recorded_staging(tmp_path, monkeypatch):
    lock = tmp_path / ".recover.build.lock"
    staging = tmp_path / ".recover.staging-crashed"
    staging.mkdir()
    (staging / "partial.txt").write_text("partial")
    stale_pid = 2_147_483_647
    lock.write_text(json.dumps({"pid": stale_pid, "staging": str(staging)}))
    monkeypatch.setattr(build_module, "_pid_is_alive", lambda pid: False)

    output = build_dataset(tmp_path, "recover", classlib.get("invoice"), n=0)

    assert output.exists()
    assert not staging.exists()
    assert not lock.exists()


def test_malformed_build_lock_is_recovered(tmp_path):
    lock = tmp_path / ".malformed.build.lock"
    lock.write_text("not valid metadata")

    output = build_dataset(tmp_path, "malformed", classlib.get("invoice"), n=0)

    assert output.exists()
    assert not lock.exists()


def test_stale_recovery_never_deletes_final_dataset(tmp_path, monkeypatch):
    output = tmp_path / "protected"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep me")
    lock = tmp_path / ".protected.build.lock"
    lock.write_text(json.dumps({"pid": 2_147_483_647, "staging": str(output)}))
    monkeypatch.setattr(build_module, "_pid_is_alive", lambda pid: False)

    with pytest.raises(FileExistsError, match="dataset already exists"):
        build_dataset(tmp_path, "protected", classlib.get("invoice"), n=0)

    assert sentinel.read_text() == "keep me"
    assert not lock.exists()


@pytest.mark.parametrize(
    "dataset_id",
    [
        "", "foo.", "foo ", "foo space", ".foo.build.lock", "CON",
        "con.txt", "nested/name", "nested\\name", "a" * 101,
    ],
)
def test_invalid_dataset_id_fails_before_creating_output(tmp_path, dataset_id):
    with pytest.raises(ValueError, match="invalid dataset_id"):
        build_dataset(tmp_path, dataset_id, classlib.get("invoice"), n=1)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("dataset_id", ["eob-full", "abc_1.2"])
def test_portable_dataset_ids_are_accepted(tmp_path, dataset_id):
    output = build_dataset(tmp_path, dataset_id, classlib.get("invoice"), n=0)

    assert output == tmp_path / dataset_id
    assert output.exists()


def test_current_pid_is_alive():
    assert build_module._pid_is_alive(os.getpid())


def test_default_invoice_validates():
    validate_layout_capacity(classlib.get("invoice"))


def test_validate_boxes_accepts_page_boundaries():
    placed = [layout_module.PlacedToken("first", (0, 0, 1, 1)),
              layout_module.PlacedToken("second", (0, 0, 1, 1))]
    _validate_boxes(
        [(0, 0, 1000, 500), (4, 5, 4, 5)], placed, "boundary", 7, 1000, 500
    )


@pytest.mark.parametrize(
    ("boxes", "bad_index"),
    [
        ([(0, 0, 1, 1), (-1, 0, 1, 1)], 1),
        ([(2, 0, 1, 1)], 0),
        ([(0, 2, 1, 1)], 0),
        ([(0, 0, 1001, 1)], 0),
        ([(0, 0, 1, 501)], 0),
    ],
)
def test_validate_boxes_rejects_invalid_geometry(boxes, bad_index):
    placed = [
        layout_module.PlacedToken(f"token-{index}", (0, 0, 1, 1))
        for index in range(len(boxes))
    ]
    with pytest.raises(
        ValueError,
        match=(
            rf"dataset 'geometry' sample 42 at token index {bad_index} "
            rf"with text 'token-{bad_index}': "
            rf"page=\(1000, 500\), box="
        ),
    ):
        _validate_boxes(boxes, placed, "geometry", 42, 1000, 500)


@pytest.mark.parametrize(
    ("attribute", "bounds"),
    [
        ("instances", (-1, 2)),
        ("instances", (2, 1)),
        ("rows", (-1, 2)),
        ("rows", (3, 2)),
    ],
)
def test_invalid_table_ranges_fail_clearly(attribute, bounds):
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], **{attribute: bounds})

    with pytest.raises(LayoutCapacityError, match=f"invalid {attribute} range"):
        validate_layout_capacity(fork(dc, tables=(table,)))


def test_negative_background_count_fails_clearly():
    dc = classlib.get("invoice")

    with pytest.raises(LayoutCapacityError, match="invalid background count"):
        validate_layout_capacity(
            fork(dc, structure=replace(dc.structure, background=-1))
        )


def test_empty_field_table_with_possible_instance_fails_clearly():
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], fields=(), instances=(0, 1))

    with pytest.raises(LayoutCapacityError, match="table 'line_item'.*no fields"):
        validate_layout_capacity(fork(dc, tables=(table,)))


@pytest.mark.parametrize(
    ("layout_overrides", "message"),
    [
        ({"page": (0, 1414)}, "invalid page dimensions"),
        ({"page": (1000, 0)}, "invalid page dimensions"),
        ({"margin": (-1, 80)}, "invalid margins"),
        ({"margin": (60, -1)}, "invalid margins"),
        ({"page": (100, 1414), "margin": (50, 80)}, "invalid usable page width"),
        ({"page": (1000, 100), "margin": (60, 50)}, "invalid available page height"),
        ({"row_h": 0}, "invalid row height"),
        ({"row_h": -1}, "invalid row height"),
        ({"table_gap": -1}, "invalid table gap"),
    ],
)
def test_invalid_layout_dimensions_fail_clearly(layout_overrides, message):
    dc = classlib.get("invoice")

    with pytest.raises(LayoutCapacityError, match=message):
        validate_layout_capacity(
            fork(dc, layout=replace(dc.layout, **layout_overrides))
        )


def test_enormous_impossible_range_fails_before_shape_enumeration(monkeypatch):
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], rows=(1, 1_000_000), instances=(1, 1_000_000))
    impossible = fork(
        dc,
        tables=(table,),
        layout=replace(dc.layout, page=(1000, 200)),
    )

    def fail_if_enumerated(_dc):
        raise AssertionError("minimum-height precheck did not stop enumeration")

    monkeypatch.setattr(layout_module, "_iter_feasible_shapes", fail_if_enumerated)
    with pytest.raises(LayoutCapacityError, match="no page-feasible document shape"):
        validate_layout_capacity(impossible)


def test_large_zero_height_instance_range_fails_clearly():
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], rows=(0, 0), instances=(1, 1_000_000))
    degenerate = fork(
        dc,
        tables=(table,),
        layout=replace(dc.layout, table_gap=0),
    )

    with pytest.raises(LayoutCapacityError, match="zero-height instances"):
        validate_layout_capacity(degenerate)


def test_background_supports_narrow_positive_interior():
    dc = classlib.get("invoice")
    narrow = fork(
        dc,
        layout=replace(dc.layout, page=(121, 1414), margin=(60, 80)),
        structure=replace(dc.structure, background=1),
    )

    validate_layout_capacity(narrow)
    placed = layout(narrow, random.Random(7))
    assert all(0 <= token.cell[0] <= token.cell[2] <= 121 for token in placed)


def test_large_valid_instance_depth_uses_iterative_traversal():
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], rows=(0, 0), instances=(1200, 1200))
    deep = fork(
        dc,
        tables=(table,),
        layout=replace(dc.layout, page=(1000, 1361), table_gap=1),
    )

    validate_layout_capacity(deep)
    shape = layout_module._choose_shape(deep, random.Random(7))
    assert len(shape[0]) == 1200
    assert set(shape[0]) == {0}


def test_many_zero_instance_tables_use_iterative_traversal():
    dc = classlib.get("invoice")
    tables = tuple(
        replace(dc.tables[0], name=f"table_{index}", rows=(0, 0), instances=(0, 0))
        for index in range(1200)
    )
    deep = fork(dc, tables=tables)

    validate_layout_capacity(deep)
    shape = layout_module._choose_shape(deep, random.Random(7))
    assert len(shape) == 1200
    assert all(table_shape == () for table_shape in shape)


def test_iterative_traversal_preserves_depth_first_yield_order():
    dc = classlib.get("invoice")
    tables = tuple(
        replace(dc.tables[0], name=f"table_{index}", rows=(0, 1), instances=(0, 1))
        for index in range(2)
    )
    ordered = fork(dc, tables=tables)

    assert list(layout_module._iter_feasible_shapes(ordered)) == [
        ((), ()),
        ((), (0,)),
        ((), (1,)),
        ((0,), ()),
        ((0,), (0,)),
        ((0,), (1,)),
        ((1,), ()),
        ((1,), (0,)),
        ((1,), (1,)),
    ]
