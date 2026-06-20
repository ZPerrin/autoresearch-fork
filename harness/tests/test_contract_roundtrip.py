from pathlib import Path
from tablelab.artifacts import (Sample, Word, Cell, Region, Field, Node,
                                DatasetManifest, write_dataset, read_dataset,
                                SCHEMA_VERSION)


def test_schema_version_is_5():
    assert SCHEMA_VERSION == 5


def test_sample_with_cells_regions_and_targets_roundtrips(tmp_path: Path):
    sample = Sample(
        id=0,
        words=[Word(0.1, 0.1, 0.2, 0.15, "Acme"), Word(0.3, 0.1, 0.4, 0.15, "$5.00")],
        width=1000, height=1400, image="/datasets/x/images/0.png",
        cells=[
            Cell(region_index=0, row_index=0, column_index=0, span=[1, 1],
                 bbox=[0.1, 0.1, 0.2, 0.15], role="data", field="description", word_ids=[0]),
            Cell(region_index=0, row_index=0, column_index=1, span=[1, 1],
                 bbox=[0.3, 0.1, 0.4, 0.15], role="data", field="amount", word_ids=[1]),
        ],
        regions=[Region(type="table", name="line_item", index=0, bbox=[0.1, 0.1, 0.4, 0.15])],
        targets={"extraction": Node(field_groups={"line_item": [
            Node(fields={
                "description": Field(value="Acme", word_ids=[0], cell=0),
                "amount": Field(value="$5.00", word_ids=[1], cell=1),
            })
        ]})},
    )
    manifest = DatasetManifest(dataset_id="x", generator_version=1, task="extraction",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got == [sample]


def test_empty_targets_default_and_roundtrip(tmp_path: Path):
    sample = Sample(id=0, words=[Word(0.1, 0.1, 0.2, 0.15, "x")])
    assert sample.targets == {} and sample.predictions == {}
    manifest = DatasetManifest(dataset_id="y", generator_version=1, task="extraction",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "y")
    assert got == [sample]
