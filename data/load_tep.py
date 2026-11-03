"""Build the DuckDB database from the raw TEP .RData files.

Keeps every fault-free run plus runs 1-5 of each of the 20 faults, renames the signals to the
physical names in tag_map.csv and flags the rows after a plant shutdown.

Usage: python data/load_tep.py [--raw-dir data/raw] [--db data/tep.duckdb]
"""

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyreadr

DATA_DIR = Path(__file__).resolve().parent
TAG_MAP_PATH = DATA_DIR / "tag_map.csv"
DEFAULT_RAW_DIR = DATA_DIR / "raw"
DEFAULT_DB_PATH = DATA_DIR / "tep.duckdb"

FAULT_FREE_FILE = "TEP_FaultFree_Training.RData"
FAULT_FREE_OBJECT = "fault_free_training"
FAULTY_FILE = "TEP_Faulty_Training.RData"
FAULTY_OBJECT = "faulty_training"

KEY_COLUMNS = ["faultNumber", "simulationRun", "sample"]
RUN_COLUMNS = ["faultNumber", "simulationRun"]
EXPECTED_FAULTS = list(range(1, 21))
RUNS_PER_FAULT = 5
# After a trip these freeze; analyzers (xmeas_23-41) and controller outputs keep changing.
CONTINUOUS_TAGS = [f"xmeas_{i}" for i in range(1, 23)]


def read_frame(path: Path, object_name: str, tags: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; see data/download_tep.py")

    objects = pyreadr.read_r(str(path))
    if object_name not in objects:
        raise ValueError(f"{path.name}: expected object {object_name}, found {list(objects)}")

    frame = objects[object_name]
    expected = [*KEY_COLUMNS, *tags]
    if list(frame.columns) != expected:
        missing = sorted(set(expected) - set(frame.columns))
        extra = sorted(set(frame.columns) - set(expected))
        raise ValueError(f"{path.name}: unexpected columns; missing {missing}, extra {extra}")
    # The two files disagree on key column types, and simulationRun is a float in both.
    return frame.astype(dict.fromkeys(KEY_COLUMNS, "int32"))


def select_fault_runs(faulty: pd.DataFrame) -> pd.DataFrame:
    found = sorted(faulty["faultNumber"].unique().tolist())
    if found != EXPECTED_FAULTS:
        raise ValueError(f"Expected faults {EXPECTED_FAULTS}, found {found}")

    subset = faulty[faulty["simulationRun"] <= RUNS_PER_FAULT]
    runs = subset.groupby("faultNumber")["simulationRun"].nunique()
    short = runs[runs != RUNS_PER_FAULT]
    if not short.empty:
        raise ValueError(f"Expected {RUNS_PER_FAULT} runs per fault, found {short.to_dict()}")
    return subset


def check_complete_runs(frame: pd.DataFrame) -> None:
    samples = frame.groupby(RUN_COLUMNS)["sample"].agg(["size", "nunique"])
    if samples["size"].nunique() != 1 or (samples["size"] != samples["nunique"]).any():
        raise ValueError("Runs do not all have the same number of distinct samples")


def flag_shutdown(frame: pd.DataFrame) -> np.ndarray:
    """True from the trip sample on. Expects rows sorted by fault, run and sample.

    Once the simulated plant trips, all 22 continuous measurements stop changing, even though
    the file keeps rows up to the last sample. The first row of the frozen block is the trip.
    """
    values = frame[CONTINUOUS_TAGS].to_numpy()
    runs = frame[RUN_COLUMNS].to_numpy()
    same_run = (runs[1:] == runs[:-1]).all(axis=1)
    repeats = same_run & (values[1:] == values[:-1]).all(axis=1)
    return np.r_[False, repeats] | np.r_[repeats, False]


def write_database(db_path: Path, process_data: pd.DataFrame, tag_map: pd.DataFrame) -> None:
    """Build next to the target and swap it in, so a rerun or a failure leaves no partial file."""
    tmp_path = db_path.with_name(f"{db_path.name}.tmp")
    tmp_path.unlink(missing_ok=True)
    with duckdb.connect(str(tmp_path)) as con:
        for table, frame in (("process_data", process_data), ("tag_mapping", tag_map)):
            con.register("source", frame)
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM source")
            con.unregister("source")
    tmp_path.replace(db_path)


def build_database(raw_dir: Path, db_path: Path) -> None:
    tag_map = pd.read_csv(TAG_MAP_PATH)
    tags = tag_map["original_tag"].tolist()

    normal = read_frame(raw_dir / FAULT_FREE_FILE, FAULT_FREE_OBJECT, tags)
    if normal["faultNumber"].unique().tolist() != [0]:
        raise ValueError(f"{FAULT_FREE_FILE}: contains rows that are not fault 0")
    faulty = select_fault_runs(read_frame(raw_dir / FAULTY_FILE, FAULTY_OBJECT, tags))

    frame = pd.concat([normal, faulty]).sort_values(KEY_COLUMNS, ignore_index=True)
    check_complete_runs(frame)
    frame.insert(len(KEY_COLUMNS), "plant_shutdown", flag_shutdown(frame))
    frame = frame.rename(
        columns={
            "faultNumber": "fault_number",
            "simulationRun": "run",
            **dict(zip(tag_map["original_tag"], tag_map["physical_name"], strict=True)),
        }
    )
    write_database(db_path, frame, tag_map)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    build_database(args.raw_dir, args.db)
    print(f"Built {args.db}")


if __name__ == "__main__":
    main()
