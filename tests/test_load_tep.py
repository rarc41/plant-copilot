from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyreadr
import pytest
from conftest import (
    CONTINUOUS_TAGS,
    FIXTURE_RUNS,
    FIXTURE_SAMPLES,
    SHUTDOWN_FAULT,
    SHUTDOWN_RUN,
    SHUTDOWN_SAMPLE,
    signal_value,
)

from data import load_tep

REPO = Path(__file__).resolve().parent.parent
REAL_RAW_DIR = REPO / "data" / "raw"
ONE_MEGABYTE = 1024 * 1024


@pytest.fixture
def db_path(make_raw_dir, tmp_path):
    path = tmp_path / "tep.duckdb"
    load_tep.build_database(make_raw_dir(), path)
    return path


def _query(path, sql):
    with duckdb.connect(str(path), read_only=True) as con:
        return con.execute(sql).fetchall()


def _columns(path, table="process_data"):
    with duckdb.connect(str(path), read_only=True) as con:
        return {row[0]: row[1] for row in con.execute(f"DESCRIBE {table}").fetchall()}


def _flagged_rows(path, fault):
    sql = f"SELECT count(*) FROM process_data WHERE fault_number = {fault} AND plant_shutdown"
    return _query(path, sql)[0][0]


def _build(raw_dir, tmp_path):
    path = tmp_path / "tep.duckdb"
    load_tep.build_database(raw_dir, path)
    return path


# Normal operation plus 5 runs for each of the 20 faults


def test_db_has_normal_plus_five_runs_per_fault(db_path):
    rows = _query(
        db_path,
        "SELECT fault_number, count(DISTINCT run), count(*) FROM process_data "
        "GROUP BY fault_number ORDER BY fault_number",
    )
    assert rows[0] == (0, FIXTURE_RUNS, FIXTURE_RUNS * FIXTURE_SAMPLES)
    assert rows[1:] == [(fault, 5, 5 * FIXTURE_SAMPLES) for fault in range(1, 21)]


def test_loader_takes_only_runs_1_to_5(db_path):
    rows = _query(
        db_path, "SELECT DISTINCT run FROM process_data WHERE fault_number > 0 ORDER BY 1"
    )
    assert [row[0] for row in rows] == [1, 2, 3, 4, 5]


def test_loader_keeps_every_normal_run(db_path):
    rows = _query(
        db_path, "SELECT DISTINCT run FROM process_data WHERE fault_number = 0 ORDER BY 1"
    )
    assert [row[0] for row in rows] == list(range(1, FIXTURE_RUNS + 1))


def test_key_columns_are_integers_and_flag_is_boolean(db_path):
    columns = _columns(db_path)
    assert [columns[name] for name in ("fault_number", "run", "sample")] == ["INTEGER"] * 3
    assert columns["plant_shutdown"] == "BOOLEAN"


@pytest.mark.parametrize(
    "change_faulty",
    [
        pytest.param(lambda f: f[f["faultNumber"] != 7], id="missing_fault"),
        pytest.param(
            lambda f: f[~((f["faultNumber"] == 3) & (f["simulationRun"] > 4))], id="too_few_runs"
        ),
        pytest.param(
            lambda f: f[
                ~((f["faultNumber"] == 4) & (f["simulationRun"] == 2) & (f["sample"] == 3))
            ],
            id="incomplete_run",
        ),
        pytest.param(lambda f: f.drop(columns="xmeas_7"), id="missing_column"),
        pytest.param(lambda f: f.assign(xmeas_42=1.0), id="unexpected_column"),
        pytest.param(lambda f: f.rename(columns={"xmv_1": "XMV_1"}), id="renamed_column"),
    ],
)
def test_loader_fails_on_missing_fault_or_unexpected_columns(make_raw_dir, tmp_path, change_faulty):
    path = tmp_path / "tep.duckdb"
    with pytest.raises(ValueError):
        load_tep.build_database(make_raw_dir(change_faulty=change_faulty), path)
    assert not path.exists()


def test_loader_fails_when_normal_file_contains_a_fault(make_raw_dir, tmp_path):
    path = tmp_path / "tep.duckdb"
    with pytest.raises(ValueError):
        load_tep.build_database(
            make_raw_dir(change_normal=lambda f: f.assign(faultNumber=1.0)), path
        )
    assert not path.exists()


def test_loader_fails_when_a_raw_file_is_missing(make_raw_dir, tmp_path):
    raw_dir = make_raw_dir()
    (raw_dir / "TEP_Faulty_Training.RData").unlink()
    path = tmp_path / "tep.duckdb"
    with pytest.raises(FileNotFoundError):
        load_tep.build_database(raw_dir, path)
    assert not path.exists()


def test_rerun_does_not_duplicate_rows(make_raw_dir, tmp_path):
    raw_dir = make_raw_dir()
    path = _build(raw_dir, tmp_path)
    first = _query(path, "SELECT count(*) FROM process_data")
    load_tep.build_database(raw_dir, path)
    assert _query(path, "SELECT count(*) FROM process_data") == first
    assert [p.name for p in tmp_path.iterdir()] == ["tep.duckdb"]


def test_leftover_tmp_file_does_not_break_the_build(make_raw_dir, tmp_path):
    (tmp_path / "tep.duckdb.tmp").write_bytes(b"left behind by a crashed run")
    path = _build(make_raw_dir(), tmp_path)
    assert _query(path, "SELECT count(*) FROM process_data")[0][0] > 0
    assert [p.name for p in tmp_path.iterdir()] == ["tep.duckdb"]


# Physical names, and a mapping table that keeps the original tag


def test_no_raw_tag_columns_remain(db_path):
    columns = _columns(db_path)
    signals = [c for c in columns if c not in ("fault_number", "run", "sample", "plant_shutdown")]
    assert len(signals) == 52
    assert not [c for c in columns if c.startswith(("xmeas_", "xmv_"))]
    assert "reactor_pressure" in columns


def test_rename_keeps_values_on_the_right_column(db_path):
    tag_map = pd.read_csv(load_tep.TAG_MAP_PATH)
    fault, run, sample = 3, 2, 4
    names = ", ".join(tag_map["physical_name"])
    row = _query(
        db_path,
        f"SELECT {names} FROM process_data "
        f"WHERE fault_number = {fault} AND run = {run} AND sample = {sample}",
    )[0]
    assert list(row) == [
        signal_value(index, fault, run, sample) for index in range(1, len(tag_map) + 1)
    ]


# plant_shutdown: rows after a trip are kept and flagged


def test_loader_flags_rows_after_shutdown(db_path):
    rows = _query(
        db_path,
        "SELECT fault_number, run, sample FROM process_data WHERE plant_shutdown ORDER BY 1, 2, 3",
    )
    assert rows == [
        (SHUTDOWN_FAULT, SHUTDOWN_RUN, sample)
        for sample in range(SHUTDOWN_SAMPLE, FIXTURE_SAMPLES + 1)
    ]


def test_repeat_in_only_some_continuous_signals_is_not_a_shutdown(make_raw_dir, tmp_path):
    def repeat_most_signals(frame):
        run = (frame["faultNumber"] == 9) & (frame["simulationRun"] == 1)
        tags = CONTINUOUS_TAGS[:-1]
        frame.loc[run & (frame["sample"] == 3), tags] = frame.loc[
            run & (frame["sample"] == 2), tags
        ].to_numpy()
        return frame

    path = _build(make_raw_dir(change_faulty=repeat_most_signals), tmp_path)
    assert _flagged_rows(path, fault=9) == 0


def test_repeat_across_two_runs_is_not_a_shutdown(make_raw_dir, tmp_path):
    def repeat_across_runs(frame):
        fault = frame["faultNumber"] == 5
        last_of_run_1 = fault & (frame["simulationRun"] == 1) & (frame["sample"] == FIXTURE_SAMPLES)
        first_of_run_2 = fault & (frame["simulationRun"] == 2) & (frame["sample"] == 1)
        frame.loc[first_of_run_2, CONTINUOUS_TAGS] = frame.loc[
            last_of_run_1, CONTINUOUS_TAGS
        ].to_numpy()
        return frame

    path = _build(make_raw_dir(change_faulty=repeat_across_runs), tmp_path)
    assert _flagged_rows(path, fault=5) == 0


# Tests run without the full dataset


def test_fixture_is_small(make_raw_dir):
    sizes = [path.stat().st_size for path in make_raw_dir().iterdir()]
    assert len(sizes) == 2
    assert max(sizes) < ONE_MEGABYTE


# The real files: pytest -q -m realdata


@pytest.fixture(scope="module")
def real_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("real") / "tep.duckdb"
    load_tep.build_database(REAL_RAW_DIR, path)
    return path


@pytest.mark.realdata
def test_real_db_row_counts(real_db):
    rows = _query(
        real_db,
        "SELECT fault_number, count(DISTINCT run), count(*) FROM process_data "
        "GROUP BY fault_number ORDER BY fault_number",
    )
    assert rows[0] == (0, 500, 250_000)
    assert rows[1:] == [(fault, 5, 2_500) for fault in range(1, 21)]
    assert _query(real_db, "SELECT count(*) FROM process_data") == [(300_000,)]


@pytest.mark.realdata
def test_real_shutdown_rows(real_db):
    rows = _query(
        real_db,
        "SELECT fault_number, run, min(sample), count(*) FROM process_data "
        "WHERE plant_shutdown GROUP BY 1, 2 ORDER BY 1, 2",
    )
    assert [row[:3] for row in rows] == [
        (6, 1, 139),
        (6, 2, 136),
        (6, 3, 137),
        (6, 4, 140),
        (6, 5, 139),
        (18, 1, 443),
        (18, 3, 353),
        (18, 4, 324),
    ]
    totals = {}
    for fault, _, first, count in rows:
        assert count == 500 - first + 1
        totals[fault] = totals.get(fault, 0) + count
    assert totals == {6: 1_814, 18: 383}


@pytest.mark.realdata
def test_real_schema_matches_fixture(real_db, db_path):
    assert _columns(real_db) == _columns(db_path)
    assert _columns(real_db, "tag_mapping") == _columns(db_path, "tag_mapping")


@pytest.mark.realdata
def test_real_values_land_on_the_mapped_columns(real_db):
    tag_map = pd.read_csv(load_tep.TAG_MAP_PATH)
    raw = pyreadr.read_r(str(REAL_RAW_DIR / "TEP_Faulty_Training.RData"))["faulty_training"]
    run = raw[(raw["faultNumber"] == 6) & (raw["simulationRun"] == 3)].sort_values("sample")
    names = ", ".join(tag_map["physical_name"])
    stored = _query(
        real_db,
        f"SELECT {names} FROM process_data WHERE fault_number = 6 AND run = 3 ORDER BY sample",
    )
    assert np.array_equal(np.array(stored), run[tag_map["original_tag"]].to_numpy())
