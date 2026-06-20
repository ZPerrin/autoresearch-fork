import copy
import random

from tablelab import classes as classlib
from tablelab.artifacts import Field, Node
from tablelab.layout import layout_with_targets
from tablelab import mock_run as mr


def _eob_root(seed=7):
    dc = classlib.get("eob")
    _w, _c, _r, targets = layout_with_targets(dc, random.Random(seed))
    return targets["extraction"]


def test_swap_grounding_points_leaf_at_other_word_ids():
    root = _eob_root()
    pred = mr.swap_grounding(copy.deepcopy(root), random.Random(0))
    # some leaf's word_ids differ from the target's
    tgt_leaves = list(mr._leaves(root))
    pred_leaves = list(mr._leaves(pred))
    changed = [i for i, (a, b) in enumerate(zip(tgt_leaves, pred_leaves))
               if a.word_ids != b.word_ids]
    assert len(changed) == 1


def test_drop_record_shortens_one_group():
    root = _eob_root()
    pred = mr.drop_record(copy.deepcopy(root), random.Random(0))
    assert len(pred.field_groups["claim_line"]) == len(root.field_groups["claim_line"]) - 1


def test_spurious_field_adds_a_leaf_absent_in_target():
    root = _eob_root()
    pred = mr.add_spurious_field(copy.deepcopy(root), random.Random(0))
    extra = set(pred.fields) - set(root.fields)
    assert len(extra) == 1


def test_drop_field_removes_a_leaf_present_in_target():
    root = _eob_root()
    pred = mr.drop_field(copy.deepcopy(root), random.Random(0))
    # a record leaf that existed in target is gone from prediction
    t_rec = root.field_groups["claim_line"][0].fields
    p_rec = pred.field_groups["claim_line"][0].fields
    assert set(p_rec).issubset(set(t_rec)) and len(p_rec) == len(t_rec) - 1


def test_perturb_breaks_exactly_one_real_target_leaf_across_seeds():
    # The swap must land on a real target leaf, never the spurious injection — otherwise a run
    # silently loses its `mismatch` case. Sweep seeds because the bad interaction is seed-dependent.
    target = _eob_root()
    words = _words_for("eob")

    def grounds_ok(f):
        return f.value == " ".join(words[i].text for i in f.word_ids)

    for seed in range(50):
        pred = mr.perturb(target, random.Random(seed))
        # exactly one grounded leaf is the deliberately-broken (swapped) one
        bad = [f for f in mr._leaves(pred) if f.word_ids and not grounds_ok(f)]
        assert len(bad) == 1, f"seed {seed}: expected 1 broken leaf, got {len(bad)}"
        # and it is a real target root field, not a `_spurious_` injection
        broken = [k for k, f in pred.fields.items() if f.word_ids and not grounds_ok(f)]
        assert broken == [b for b in broken if not b.startswith("_spurious_")], \
            f"seed {seed}: break landed on a spurious field: {broken}"
        assert len(broken) == 1 and broken[0] in target.fields


def _words_for(dc_name, seed=7):
    dc = classlib.get(dc_name)
    words, _c, _r, _t = layout_with_targets(dc, random.Random(seed))
    return words


def test_mock_run_writes_a_loadable_run(tmp_path):
    from tablelab.build import build_dataset
    from tablelab.artifacts import read_run
    ds = build_dataset(tmp_path, "mr-eob", classlib.get("eob"), seed=7, n=2)
    record, samples = mr.mock_run(ds, run_id="t-run", seed=1)
    runs_dir = tmp_path / "runs"
    from tablelab.artifacts import write_run
    write_run(runs_dir, record, samples)
    rec2, samples2 = read_run(runs_dir / "t-run")
    assert rec2.status == "mock" and rec2.dataset_id == "mr-eob"
    for s in samples2:
        assert "extraction" in s.predictions          # predictions present
        assert "extraction" in s.targets              # targets preserved
        assert s.image and s.image.startswith("/datasets/")  # binary-free, points at dataset
