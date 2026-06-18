from pathlib import Path
from tablelab.artifacts import (Sample, Word, Cell, Region, DatasetManifest,
                                write_dataset, read_dataset, SCHEMA_VERSION)


def test_schema_version_is_4():
    assert SCHEMA_VERSION == 4


def test_sample_with_cells_and_regions_roundtrips(tmp_path: Path):
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
    )
    manifest = DatasetManifest(dataset_id="x", generator_version=1, task="grid_record_field",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got == [sample]
