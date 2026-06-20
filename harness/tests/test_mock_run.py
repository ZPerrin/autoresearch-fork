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


def test_perturb_applies_all_four_and_keeps_grounding(tmp_path):
    root = _eob_root()
    words = [w for w in _words_for("eob")]
    pred = mr.perturb(root, random.Random(0))
    # exactly one leaf is the deliberately-broken (swapped) one; every *other*
    # grounded leaf still satisfies value == join(words[word_ids]).
    bad = 0
    for leaf in mr._leaves(pred):
        if not leaf.word_ids:
            continue
        if leaf.value != " ".join(words[i].text for i in leaf.word_ids):
            bad += 1
    assert bad == 1


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
