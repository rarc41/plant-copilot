import re

import duckdb
import pandas as pd
import pytest

from data import load_tep

EXPECTED_TAGS = [f"xmeas_{i}" for i in range(1, 42)] + [f"xmv_{i}" for i in range(1, 12)]


@pytest.fixture
def tag_map():
    return pd.read_csv(load_tep.TAG_MAP_PATH)


def test_mapping_keeps_every_original_tag(tag_map, make_raw_dir, tmp_path):
    assert tag_map["original_tag"].tolist() == EXPECTED_TAGS

    path = tmp_path / "tep.duckdb"
    load_tep.build_database(make_raw_dir(), path)
    with duckdb.connect(str(path), read_only=True) as con:
        stored = con.execute(
            "SELECT original_tag, physical_name, unit, description FROM tag_mapping"
        ).fetchall()
    assert set(stored) == set(tag_map.itertuples(index=False, name=None))


def test_physical_names_are_unique_snake_case(tag_map):
    names = tag_map["physical_name"]
    assert names.is_unique
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in names)


def test_every_tag_has_a_unit_and_description(tag_map):
    assert not tag_map[["unit", "description"]].isna().any().any()


@pytest.mark.parametrize(
    ("tag", "name"),
    [
        ("xmeas_1", "a_feed_flow"),
        ("xmeas_2", "d_feed_flow"),
        ("xmeas_3", "e_feed_flow"),
        ("xmeas_7", "reactor_pressure"),
        ("xmeas_10", "purge_flow"),
        ("xmeas_17", "stripper_underflow"),
        ("xmeas_22", "condenser_cooling_water_outlet_temperature"),
        ("xmeas_24", "reactor_feed_b_mol_pct"),
        ("xmeas_30", "purge_b_mol_pct"),
        ("xmeas_37", "product_d_mol_pct"),
        ("xmv_1", "d_feed_valve"),
        ("xmv_2", "e_feed_valve"),
        ("xmv_3", "a_feed_valve"),
        ("xmv_4", "a_c_feed_valve"),
        ("xmv_6", "purge_valve"),
        ("xmv_10", "reactor_cooling_water_valve"),
        ("xmv_11", "condenser_cooling_water_valve"),
    ],
)
def test_reviewed_tags_keep_their_names(tag_map, tag, name):
    assert dict(zip(tag_map["original_tag"], tag_map["physical_name"], strict=True))[tag] == name
